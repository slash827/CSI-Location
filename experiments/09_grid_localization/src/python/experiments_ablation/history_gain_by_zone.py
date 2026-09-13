"""
A1: Does transition history help more where the distance-ring ambiguity is worse?

The mechanism says history resolves the distance-ring ambiguity. That ambiguity is
worst in LOS, where the range-to-RSS map is clean and monotone and multipath gives
no tie-breaker; in NLOS, rich scattering already gives each position a distinctive
signature. So the mechanism predicts:

    history's benefit should be LARGER in LOS zones than in NLOS zones.

This is a falsifiable prediction testable on data already in hand. The report
currently gives only aggregate MAE per zone (LOS 19.401 m, NLOS 18.868 m) and has
never measured the history *gain* per zone.

One model is trained on all training users per depth; the split by zone happens at
evaluation. That is deliberate - we are asking where a single deployed model's
gain lands, not training a specialist per zone.

Confound to watch: zone and BS range are correlated, and range drives error
independently (report section 7.5). Mean range per zone is reported alongside so
the comparison can be read honestly.

Usage:
    python history_gain_by_zone.py
    python history_gain_by_zone.py --depths 0 1 3 5 10
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'src' / 'python'))

from pipelines.multi_user_pipeline_regression import _read_bs_position_3d
from pipelines.multi_user_200_pipeline import make_unseen_user_split
from utils.csi_dataset import DerivedCSI1DDataset, load_and_prepare_data
from xgboost import XGBRegressor

# Voronoi centres, copied verbatim from utils/environment_viz.py so the zone
# assignment matches every other analysis in the project.
VORONOI = [
    {"center": [35.0, 15.0], "scenario": "LOS",  "name": "Highway"},
    {"center": [95.0, 15.0], "scenario": "NLOS", "name": "Shopping"},
    {"center": [75.0,  5.0], "scenario": "NLOS", "name": "Residential"},
    {"center": [60.0, 90.0], "scenario": "LOS",  "name": "Park"},
]


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def assign_zone(x, y):
    """Nearest Voronoi centre, matching environment_viz.py."""
    centres = np.array([c['center'] for c in VORONOI])
    d = np.sqrt((x[:, None] - centres[None, :, 0]) ** 2 +
                (y[:, None] - centres[None, :, 1]) ** 2)
    return np.argmin(d, axis=1)


def flatten(ds, extra_keys=('x_pos', 'y_pos')):
    n = len(ds)
    d = ds.samples[0]['seq'].size + ds.samples[0]['static'].size
    X = np.empty((n, d), np.float32)
    Y = np.empty((n, 2), np.float32)
    ant = np.empty(n, np.int64)
    for i, s in enumerate(ds.samples):
        X[i] = np.concatenate([s['seq'].ravel(), s['static'].ravel()])
        Y[i] = s['target']
        ant[i] = s['n_antennas']
    return X, Y, ant


def main():
    ap = argparse.ArgumentParser(
        description='History gain per propagation zone (A1).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python history_gain_by_zone.py
  python history_gain_by_zone.py --depths 0 1 3 5 10 --seed 7
""")
    ap.add_argument('--depths', type=int, nargs='+', default=[0, 1, 3, 5])
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--single-ant-ratio', type=float, default=0.15)
    args = ap.parse_args()

    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'history_gain_by_zone_{run_ts}')
    out_dir.mkdir(parents=True, exist_ok=True)

    log('loading...')
    data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
    data_dir = sorted(data_base.glob('sim_data_300users_*'))[-1]
    bs_pos = np.array(_read_bs_position_3d(data_dir))
    df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=args.seed,
                                     single_ant_ratio=args.single_ant_ratio)
    df, _, test_uids = make_unseen_user_split(df, 0.8, args.seed)

    # zone + range are properties of position, so attach them before windowing
    df['zone_idx'] = assign_zone(df.x_pos.values, df.y_pos.values)
    df['bs_range'] = np.sqrt((df.x_pos - bs_pos[0]) ** 2 + (df.y_pos - bs_pos[1]) ** 2)

    df_tr = df[df.split == 'train']
    df_te = df[df.split == 'test']
    log(f'{len(df_tr):,} train / {len(df_te):,} test rows')

    results = {'meta': {'dataset': str(data_dir), 'seed': args.seed,
                        'depths': args.depths,
                        'voronoi_centres': VORONOI}, 'by_depth': {}}
    per_depth_err = {}

    for h in args.depths:
        t0 = time.time()
        tr = DerivedCSI1DDataset(df_tr, h=h)
        te = DerivedCSI1DDataset(df_te, h=h,
                                 sig_mean=tr.sig_mean, sig_std=tr.sig_std,
                                 stat_mean=tr.stat_mean, stat_std=tr.stat_std,
                                 targ_mean=tr.targ_mean, targ_std=tr.targ_std,
                                 speed_mean=tr.speed_mean, speed_std=tr.speed_std)
        X_tr, Y_tr, _ = flatten(tr)
        X_te, Y_te, _ = flatten(te)

        # DerivedCSI1DDataset drops the first h rows of each user, so rebuild the
        # aligned zone/range vectors the same way rather than reusing df_te order
        zone_te, rng_te = [], []
        for uid, udf in df_te.groupby('user_id'):
            udf = udf.sort_values('step_index')
            if len(udf) < h + 1:
                continue
            zone_te.append(udf['zone_idx'].values[h:])
            rng_te.append(udf['bs_range'].values[h:])
        zone_te = np.concatenate(zone_te)
        rng_te = np.concatenate(rng_te)
        assert len(zone_te) == len(X_te), f'alignment broken: {len(zone_te)} vs {len(X_te)}'

        model = XGBRegressor(n_estimators=50, max_depth=5, learning_rate=0.15,
                             subsample=0.8, colsample_bytree=0.8,
                             random_state=args.seed, n_jobs=-1, tree_method='hist',
                             multi_strategy='one_output_per_tree')
        model.fit(X_tr, Y_tr)
        pred = model.predict(X_te) * tr.targ_std + tr.targ_mean
        true = Y_te * tr.targ_std + tr.targ_mean
        err = np.linalg.norm(pred - true, axis=1)
        per_depth_err[h] = (err, zone_te, rng_te)

        rec = {'overall_mae': float(err.mean()), 'elapsed_sec': round(time.time() - t0, 1)}
        for i, c in enumerate(VORONOI):
            m = zone_te == i
            rec[c['name']] = {'mae': float(err[m].mean()), 'n': int(m.sum()),
                              'mean_range_m': float(rng_te[m].mean()),
                              'scenario': c['scenario']}
        for lab in ('LOS', 'NLOS'):
            idx = [i for i, c in enumerate(VORONOI) if c['scenario'] == lab]
            m = np.isin(zone_te, idx)
            rec[lab] = {'mae': float(err[m].mean()), 'n': int(m.sum()),
                        'mean_range_m': float(rng_te[m].mean())}
        results['by_depth'][f'h={h}'] = rec
        log(f'  h={h:<2d} overall {rec["overall_mae"]:6.3f} m | '
            f'LOS {rec["LOS"]["mae"]:6.3f} | NLOS {rec["NLOS"]["mae"]:6.3f} '
            f'| {rec["elapsed_sec"]}s')

    # gains against each stratum's own h=0
    base = args.depths[0]
    log('=' * 78)
    log(f'HISTORY GAIN BY ZONE (vs h={base})')
    log('=' * 78)
    gains = {}
    header = f'{"stratum":<14}{"n":>7}{"range":>8}' + ''.join(f'{"h="+str(h):>10}' for h in args.depths) + f'{"best gain":>11}'
    log(header)
    log('-' * len(header))
    strata = [c['name'] for c in VORONOI] + ['LOS', 'NLOS']
    for s in strata:
        row = results['by_depth'][f'h={base}'][s]
        maes = [results['by_depth'][f'h={h}'][s]['mae'] for h in args.depths]
        best_gain = 100.0 * (maes[0] - min(maes)) / maes[0]
        gains[s] = {'maes': dict(zip([f'h={h}' for h in args.depths], [round(m, 4) for m in maes])),
                    'best_gain_pct': round(best_gain, 2),
                    'n': row['n'], 'mean_range_m': round(row['mean_range_m'], 1)}
        log(f'{s:<14}{row["n"]:>7}{row["mean_range_m"]:>8.1f}'
            + ''.join(f'{m:>10.3f}' for m in maes)
            + f'{best_gain:>10.2f}%')
    results['gains'] = gains

    los_g, nlos_g = gains['LOS']['best_gain_pct'], gains['NLOS']['best_gain_pct']
    results['verdict'] = {
        'los_gain_pct': los_g, 'nlos_gain_pct': nlos_g,
        'los_minus_nlos_pp': round(los_g - nlos_g, 2),
        'prediction_supported': bool(los_g > nlos_g),
        'los_mean_range_m': gains['LOS']['mean_range_m'],
        'nlos_mean_range_m': gains['NLOS']['mean_range_m'],
    }
    log('-' * 78)
    log(f'LOS gain {los_g:+.2f}%  vs  NLOS gain {nlos_g:+.2f}%  '
        f'-> difference {los_g - nlos_g:+.2f} pp')
    log(f'mechanism prediction (LOS > NLOS): '
        f'{"SUPPORTED" if los_g > nlos_g else "NOT SUPPORTED"}')
    log(f'range confound check: LOS mean {gains["LOS"]["mean_range_m"]} m, '
        f'NLOS mean {gains["NLOS"]["mean_range_m"]} m')

    out = out_dir / 'history_gain_by_zone_summary.json'
    out.write_text(json.dumps(results, indent=1), encoding='utf-8')
    log(f'saved -> {out}')


if __name__ == '__main__':
    sys.exit(main())
