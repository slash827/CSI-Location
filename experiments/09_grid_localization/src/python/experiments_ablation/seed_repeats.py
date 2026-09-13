"""
A5: Establish the noise floor.

Every number in the report is a single-seed point estimate. That is tolerable for
the large effects - history's 13-16%, the 2.3x cohort discontinuity, A1's 11 pp
LOS/NLOS difference - but not for the small ones. The feature ablation claims
+2.2%, the multi-antenna masking gain +0.84%, and the per-depth tuning differences
run to hundredths of a metre. None of those mean anything until we know how much
the pipeline moves when only the seed changes.

The seed drives both the train/test user split and model initialisation. With only
47 test users, split variance is expected to dominate, so this measures the
quantity that actually matters for the reported deltas.

Restricted to the cheap models (k-NN, XGBoost). The deep models need the new
machine - see EXPERIMENTS_BACKLOG.md item B2.

Usage:
    python seed_repeats.py
    python seed_repeats.py --seeds 42 1 7 13 99 123 --depths 0 5
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

from sklearn.neighbors import KNeighborsRegressor
from xgboost import XGBRegressor


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def flatten(ds):
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


def ci95(vals):
    v = np.asarray(vals, dtype=float)
    if len(v) < 2:
        return 0.0
    return 1.96 * v.std(ddof=1) / np.sqrt(len(v))


def main():
    ap = argparse.ArgumentParser(
        description='Seed repeats and confidence intervals for the cheap models (A5).')
    ap.add_argument('--seeds', type=int, nargs='+', default=[42, 1, 7, 13, 99])
    ap.add_argument('--depths', type=int, nargs='+', default=[0, 5])
    ap.add_argument('--single-ant-ratio', type=float, default=0.15)
    args = ap.parse_args()

    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'seed_repeats_{run_ts}')
    out_dir.mkdir(parents=True, exist_ok=True)

    data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
    data_dir = sorted(data_base.glob('sim_data_300users_*'))[-1]
    bs_pos = np.array(_read_bs_position_3d(data_dir))

    raw = {}          # (model, h) -> list of dicts
    log(f'seeds: {args.seeds} | depths: {args.depths}')
    log('')
    for seed in args.seeds:
        t0 = time.time()
        df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=seed,
                                         single_ant_ratio=args.single_ant_ratio)
        df, _, test_uids = make_unseen_user_split(df, 0.8, seed)
        df_tr, df_te = df[df.split == 'train'], df[df.split == 'test']
        for h in args.depths:
            tr = DerivedCSI1DDataset(df_tr, h=h)
            te = DerivedCSI1DDataset(df_te, h=h,
                                     sig_mean=tr.sig_mean, sig_std=tr.sig_std,
                                     stat_mean=tr.stat_mean, stat_std=tr.stat_std,
                                     targ_mean=tr.targ_mean, targ_std=tr.targ_std,
                                     speed_mean=tr.speed_mean, speed_std=tr.speed_std)
            X_tr, Y_tr, _ = flatten(tr)
            X_te, Y_te, ant = flatten(te)
            models = {
                'knn': KNeighborsRegressor(n_neighbors=5, n_jobs=-1),
                'xgboost': XGBRegressor(
                    n_estimators=50, max_depth=5, learning_rate=0.15, subsample=0.8,
                    colsample_bytree=0.8, random_state=seed, n_jobs=-1,
                    tree_method='hist', multi_strategy='one_output_per_tree'),
            }
            for mname, model in models.items():
                model.fit(X_tr, Y_tr)
                pred = model.predict(X_te) * tr.targ_std + tr.targ_mean
                true = Y_te * tr.targ_std + tr.targ_mean
                err = np.linalg.norm(pred - true, axis=1)
                multi, single = ant > 1, ant == 1
                raw.setdefault((mname, h), []).append({
                    'seed': seed,
                    'mae': float(err.mean()),
                    'multi_mae': float(err[multi].mean()),
                    'single_mae': float(err[single].mean()),
                    'n_test_users': int(len(test_uids)),
                })
        log(f'  seed {seed:<4} done in {time.time()-t0:.0f}s')

    results = {'meta': {'dataset': str(data_dir), 'seeds': args.seeds,
                        'depths': args.depths}, 'per_config': {}}

    log('')
    log('=' * 78)
    log('SEED VARIABILITY (mean +/- 95% CI over seeds, and full range)')
    log('=' * 78)
    log(f'{"model":<10}{"h":>3}{"MAE mean":>11}{"95% CI":>10}{"min":>9}{"max":>9}{"spread":>9}')
    log('-' * 78)
    for (mname, h), runs in sorted(raw.items()):
        maes = [r['mae'] for r in runs]
        rec = {'runs': runs,
               'mae_mean': float(np.mean(maes)), 'mae_std': float(np.std(maes, ddof=1)),
               'mae_ci95': float(ci95(maes)),
               'mae_min': float(min(maes)), 'mae_max': float(max(maes)),
               'mae_spread': float(max(maes) - min(maes)),
               'multi_mean': float(np.mean([r['multi_mae'] for r in runs])),
               'multi_ci95': float(ci95([r['multi_mae'] for r in runs])),
               'single_mean': float(np.mean([r['single_mae'] for r in runs])),
               'single_ci95': float(ci95([r['single_mae'] for r in runs]))}
        results['per_config'][f'{mname}_h{h}'] = rec
        log(f'{mname:<10}{h:>3}{rec["mae_mean"]:>11.3f}{rec["mae_ci95"]:>9.3f}m'
            f'{rec["mae_min"]:>9.3f}{rec["mae_max"]:>9.3f}{rec["mae_spread"]:>9.3f}')

    # the quantity that matters: is the history gain larger than seed noise?
    log('')
    log('=' * 78)
    log('IS THE HISTORY GAIN LARGER THAN SEED NOISE?')
    log('=' * 78)
    verdict = {}
    lo, hi = args.depths[0], args.depths[-1]
    for mname in ('knn', 'xgboost'):
        a = results['per_config'].get(f'{mname}_h{lo}')
        b = results['per_config'].get(f'{mname}_h{hi}')
        if not a or not b:
            continue
        # paired by seed - the correct comparison, since both arms share a split
        pairs = [(x['mae'] - y['mae']) for x, y in zip(a['runs'], b['runs'])]
        gain_mean, gain_ci = float(np.mean(pairs)), ci95(pairs)
        verdict[mname] = {
            'gain_mean_m': round(gain_mean, 4), 'gain_ci95_m': round(gain_ci, 4),
            'seed_spread_at_h0_m': round(a['mae_spread'], 4),
            'significant': bool(gain_mean - gain_ci > 0),
        }
        log(f'{mname:<10} h={lo} -> h={hi}: gain {gain_mean:+.3f} m '
            f'+/- {gain_ci:.3f} (paired by seed) | seed spread at h={lo}: '
            f'{a["mae_spread"]:.3f} m -> '
            f'{"SIGNIFICANT" if gain_mean - gain_ci > 0 else "NOT SIGNIFICANT"}')
    results['verdict'] = verdict

    log('')
    log('Interpretation guide for the report:')
    worst = max((v['seed_spread_at_h0_m'] for v in verdict.values()), default=0.0)
    log(f'  seed-to-seed spread reaches {worst:.3f} m, so any claimed delta below')
    log(f'  roughly that magnitude should be treated as unresolved by a single run.')
    results['noise_floor_m'] = round(worst, 4)

    out = out_dir / 'seed_repeats_summary.json'
    out.write_text(json.dumps(results, indent=1), encoding='utf-8')
    log(f'saved -> {out}')


if __name__ == '__main__':
    sys.exit(main())
