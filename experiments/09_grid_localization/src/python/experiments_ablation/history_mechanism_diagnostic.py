"""
History-mechanism diagnostic: which measurement channels carry the history gain,
for which device group, and does it depend on range?

Copy this file into
    experiments/09_grid_localization/src/python/experiments_ablation/
and run it from the repository root. It reuses model_zoo (same classical models
and hyperparameters as the master benchmark), load_and_prepare_data and
make_unseen_user_split, so the protocol matches seed_repeats_all_models.py.

The depth-h windows are built once per seed. Every condition below is a column
subset of the same flattened [13 x (h+1)] window plus the 3 static features, so
all conditions share identical rows and identical train/test users: comparisons
are paired by sample as well as by seed.

Channels are split three ways:
    RSS side   rss, sinr, d_rss
    angle side sin_az, cos_az, sin_el, cos_el, d_az
    ray        ray_x, ray_y, d_ray_x, d_ray_y   (RSS range estimate x AoA direction)
    time       delta_t
"current" means the most recent step only; "all" means all h+1 steps.

    condition    RSS     angle   ray     time    first differences
    pure_snap    cur     cur     cur     -       excluded (d_* and delta_t dropped)
    snap         cur     cur     cur     cur     current only  (= the recorded h=0 input)
    rss_hist     all     cur     cur     all
    angle_hist   cur     all     cur     all
    ray_hist     cur     cur     all     all
    full         all     all     all     all     (= the recorded h=5 input)

Only the classical families run (k-NN, Random Forest, XGBoost): no GPU needed,
and no early stopping, so nothing is selected on test users.

Usage (from the repository root):
    E=experiments/09_grid_localization/src/python/experiments_ablation
    .venv/Scripts/python $E/history_mechanism_diagnostic.py --data-dir <dataset> --smoke
    .venv/Scripts/python $E/history_mechanism_diagnostic.py --data-dir <dataset>
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

# ── channel layout (must match utils.csi_dataset.SIGNAL_COLS; checked at runtime) ──
SIGNAL_COLS = ['rss', 'sinr',
               'sin_az', 'cos_az', 'sin_el', 'cos_el',
               'ray_x', 'ray_y',
               'd_rss', 'd_az', 'd_ray_x', 'd_ray_y',
               'delta_t']
N_STATIC = 3

RSS_SIDE = ['rss', 'sinr', 'd_rss']
ANGLE_SIDE = ['sin_az', 'cos_az', 'sin_el', 'cos_el', 'd_az']
RAY_SIDE = ['ray_x', 'ray_y', 'd_ray_x', 'd_ray_y']
TIME_SIDE = ['delta_t']
DIFF_COLS = ['d_rss', 'd_az', 'd_ray_x', 'd_ray_y', 'delta_t']

# per condition: which channel groups use all steps; everything else uses the current step
CONDITIONS = {
    'pure_snap':  {'all': [], 'drop': DIFF_COLS},
    'snap':       {'all': [], 'drop': []},
    'rss_hist':   {'all': RSS_SIDE + TIME_SIDE, 'drop': []},
    'angle_hist': {'all': ANGLE_SIDE + TIME_SIDE, 'drop': []},
    'ray_hist':   {'all': RAY_SIDE + TIME_SIDE, 'drop': []},
    'full':       {'all': SIGNAL_COLS, 'drop': []},
}
BASELINE = 'snap'

RANGE_BINS = [(0.0, 40.0, '<40'), (40.0, 80.0, '40-80'),
              (80.0, 120.0, '80-120'), (120.0, np.inf, '>=120')]
WITHIN_R = (5.0, 10.0, 20.0)
GROUPS = ('all', 'multi', 'single')


# ── pure helpers (NumPy only; tested in test_history_mechanism_diagnostic.py) ──
def feature_index(condition, h, signal_cols=SIGNAL_COLS, n_static=N_STATIC):
    """Column indices into a flattened sample [seq.ravel(), static].

    seq is [n_channels, L] with the current step last, so after a C-order ravel
    channel c at step t sits at c * L + t, and the static features follow.
    """
    spec = CONDITIONS[condition]
    L = h + 1
    idx = []
    for c, name in enumerate(signal_cols):
        if name in spec['drop']:
            continue
        steps = range(L) if name in spec['all'] else [L - 1]
        idx.extend(c * L + t for t in steps)
    n_seq = len(signal_cols) * L
    idx.extend(n_seq + k for k in range(n_static))
    return np.asarray(idx, dtype=np.int64)


def decompose(pred, true):
    """Total, radial and tangential error, with the serving BS at the origin.

    Targets are offsets from the serving BS, so the unit vector to the true
    position is the radial direction (same formula as error_decomposition.py).
    """
    rng = np.linalg.norm(true, axis=1)
    unit = true / np.maximum(rng, 1e-9)[:, None]
    delta = pred - true
    radial = np.abs((delta * unit).sum(axis=1))
    tangential = np.abs(delta[:, 0] * unit[:, 1] - delta[:, 1] * unit[:, 0])
    total = np.linalg.norm(delta, axis=1)
    return total, radial, tangential, rng


def group_masks(ant):
    return {'all': np.ones(len(ant), bool), 'multi': ant > 1, 'single': ant == 1}


def _f(x):
    x = float(x)
    return None if not np.isfinite(x) else x


def block_metrics(err, radial, tangential, rng, uid, los=None):
    """Metric block for one group of samples. Empty groups return counts of 0."""
    n = len(err)
    out = {'n_samples': int(n), 'n_users': int(len(np.unique(uid))) if n else 0}
    if n == 0:
        return out
    out.update({
        'mae': _f(err.mean()),
        'p50': _f(np.median(err)),
        'p90': _f(np.percentile(err, 90)),
        'radial_mean': _f(radial.mean()),
        'tangential_mean': _f(tangential.mean()),
    })
    for r in WITHIN_R:
        out[f'within_{int(r)}m'] = _f((err <= r).mean())
    out['range_bins'] = {}
    for lo, hi, lab in RANGE_BINS:
        m = (rng >= lo) & (rng < hi)
        out['range_bins'][lab] = {'n': int(m.sum()), 'mae': _f(err[m].mean()) if m.any() else None}
    if los is not None:
        out['los'] = {}
        for lab, m in (('LOS', los), ('NLOS', ~los)):
            out['los'][lab] = {'n': int(m.sum()), 'mae': _f(err[m].mean()) if m.any() else None}
    return out


def per_group_metrics(pred, true, ant, uid, los=None):
    err, radial, tangential, rng = decompose(pred, true)
    res = {}
    for g, m in group_masks(ant).items():
        res[g] = block_metrics(err[m], radial[m], tangential[m], rng[m], uid[m],
                               None if los is None else los[m])
    return res, err


def per_user_mae(err, uid, ant):
    rows = []
    for u in np.unique(uid):
        m = uid == u
        rows.append({'user_id': int(u), 'n_antennas': int(ant[m][0]),
                     'n_samples': int(m.sum()), 'mae': _f(err[m].mean())})
    return rows


def ci95(vals):
    v = np.asarray([x for x in vals if x is not None], dtype=float)
    if len(v) < 2:
        return None
    return float(1.96 * v.std(ddof=1) / np.sqrt(len(v)))


def paired_gain(base, cond):
    """Seed-paired gain base - cond (positive = condition lowers error)."""
    pairs = [b - c for b, c in zip(base, cond) if b is not None and c is not None]
    if not pairs:
        return None
    mean = float(np.mean(pairs))
    base_mean = float(np.mean([b for b in base if b is not None]))
    ci = ci95(pairs)
    return {'gain_mean_m': mean, 'gain_ci95_m': ci,
            'gain_pct': 100.0 * mean / base_mean if base_mean else None,
            'n_pairs': len(pairs),
            'clears_ci': None if ci is None else bool(abs(mean) - ci > 0)}


def aligned_values(df, col, h, sample_uids):
    """Per-sample values of df[col], in DerivedCSI1DDataset's sample order.

    The dataset iterates users in groupby order, sorts each by step_index and
    drops the first h rows, so rebuild the column the same way and check the
    user ids line up sample for sample.
    """
    vals, uids = [], []
    for uid, udf in df.groupby('user_id'):
        udf = udf.sort_values('step_index')
        if len(udf) < h + 1:
            continue
        vals.append(udf[col].values[h:])
        uids.append(udf['user_id'].values[h:])
    vals, uids = np.concatenate(vals), np.concatenate(uids)
    if len(vals) != len(sample_uids) or not np.array_equal(uids, np.asarray(sample_uids)):
        raise RuntimeError(f'alignment broken for column {col!r}')
    return vals


# ── experiment ────────────────────────────────────────────────────────────────
def summarise(raw, models, conditions):
    """Aggregate per-seed metric blocks into means, CIs and paired gains."""
    summary = {}
    for name in models:
        summary[name] = {}
        for cond in conditions:
            runs = raw[name][cond]
            rec = {}
            for g in GROUPS:
                maes = [r['groups'][g].get('mae') for r in runs]
                rec[g] = {'mae_mean': _f(np.mean([m for m in maes if m is not None])) if any(m is not None for m in maes) else None,
                          'mae_ci95': ci95(maes)}
                if cond != BASELINE:
                    base = [r['groups'][g].get('mae') for r in raw[name][BASELINE]]
                    rec[g]['gain_vs_snap'] = paired_gain(base, maes)
                    rec[g]['gain_vs_snap_by_range'] = {}
                    for _, _, lab in RANGE_BINS:
                        b = [r['groups'][g].get('range_bins', {}).get(lab, {}).get('mae') for r in raw[name][BASELINE]]
                        c = [r['groups'][g].get('range_bins', {}).get(lab, {}).get('mae') for r in runs]
                        rec[g]['gain_vs_snap_by_range'][lab] = paired_gain(b, c)
                    if runs and 'los' in runs[0]['groups'][g]:
                        rec[g]['gain_vs_snap_by_los'] = {}
                        for lab in ('LOS', 'NLOS'):
                            b = [r['groups'][g]['los'][lab]['mae'] for r in raw[name][BASELINE]]
                            c = [r['groups'][g]['los'][lab]['mae'] for r in runs]
                            rec[g]['gain_vs_snap_by_los'][lab] = paired_gain(b, c)
            summary[name][cond] = rec
    return summary


def main():
    ap = argparse.ArgumentParser(
        description='Which channels carry the history gain, per device group and range.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python history_mechanism_diagnostic.py --data-dir results/grid_localization/grid_25x25/sim_data_300users_2026-07-25_11-46-11 --smoke
  python history_mechanism_diagnostic.py --data-dir results/grid_localization/grid_25x25/sim_data_300users_2026-07-25_11-46-11
  python history_mechanism_diagnostic.py --data-dir results/grid_localization/grid_25x25/sim_data_300users_mixed_2026-09-18_20-25-01
""")
    ap.add_argument('--data-dir', required=True,
                    help='dataset folder; required, no glob (the glob picks the newest dataset)')
    ap.add_argument('--seeds', type=int, nargs='+', default=[42, 1, 7, 13, 99])
    ap.add_argument('--models', nargs='+', default=['xgboost', 'random_forest', 'knn'],
                    choices=['xgboost', 'random_forest', 'knn'])
    ap.add_argument('--history', type=int, default=5)
    ap.add_argument('--single-ant-ratio', type=float, default=0.15)
    ap.add_argument('--smoke', action='store_true',
                    help='one seed, XGBoost only, 60-user subsample: checks the pipeline end to end')
    args = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import model_zoo as Z
    from model_zoo import PROJECT_ROOT, log
    from pipelines.multi_user_pipeline_regression import _read_bs_position_3d
    from pipelines.multi_user_200_pipeline import make_unseen_user_split
    from utils import csi_dataset
    from utils.csi_dataset import load_and_prepare_data

    if list(csi_dataset.SIGNAL_COLS) != SIGNAL_COLS:
        raise RuntimeError(f'SIGNAL_COLS changed: {csi_dataset.SIGNAL_COLS}')

    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir
    if not data_dir.is_dir():
        raise SystemExit(f'dataset not found: {data_dir}')

    if args.smoke:
        args.seeds, args.models = args.seeds[:1], ['xgboost']
    conditions = list(CONDITIONS)
    h = args.history

    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    tag = 'smoke_' if args.smoke else ''
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'history_mechanism_diagnostic_{tag}{data_dir.name}_{run_ts}')
    out_dir.mkdir(parents=True, exist_ok=True)

    bs_pos = np.array(_read_bs_position_3d(data_dir))
    log(f'dataset={data_dir.name} | h={h} | seeds={args.seeds} | models={args.models}')

    raw = {n: {c: [] for c in conditions} for n in args.models}
    per_user = []
    user_counts = []
    npz = {}
    t_start = time.time()
    for seed in args.seeds:
        t_seed = time.time()
        df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=seed,
                                         single_ant_ratio=args.single_ant_ratio)
        if args.smoke:
            uids = np.random.RandomState(seed).permutation(sorted(df['user_id'].unique()))[:60]
            df = df[df['user_id'].isin(set(uids))].copy()
        df, _, test_uids = make_unseen_user_split(df, Z.TRAIN_RATIO, seed)
        df_tr, df_te = df[df.split == 'train'], df[df.split == 'test']

        tr, te = Z.make_datasets(df_tr, df_te, h)
        X_tr, Y_tr, _, _, _ = Z.flatten(tr)
        X_te, Y_te, uid_te, _, ant_te = Z.flatten(te)
        ts, tm = tr.targ_std, tr.targ_mean
        true = Y_te * ts + tm

        los_te = None
        if 'is_los' in df_te.columns and df_te['is_los'].notna().all():
            los_te = aligned_values(df_te, 'is_los', h, uid_te).astype(bool)

        counts = {'seed': seed, 'n_test_users': int(len(test_uids))}
        for g, m in group_masks(ant_te).items():
            counts[g] = {'n_samples': int(m.sum()), 'n_users': int(len(np.unique(uid_te[m])))}
        user_counts.append(counts)
        log('=' * 84)
        log(f'SEED {seed}: {counts["n_test_users"]} test users '
            f'({counts["multi"]["n_users"]} multi, {counts["single"]["n_users"]} single), '
            f'{len(X_te):,} test windows | LOS split: {"yes" if los_te is not None else "no"}')

        for name in args.models:
            for cond in conditions:
                t0 = time.time()
                idx = feature_index(cond, h)
                model = Z.build_classical(name, seed)
                model.fit(X_tr[:, idx], Y_tr)
                pred = model.predict(X_te[:, idx]) * ts + tm
                groups, err = per_group_metrics(pred, true, ant_te, uid_te, los_te)
                raw[name][cond].append({'seed': seed, 'n_features': int(len(idx)),
                                        'elapsed_sec': round(time.time() - t0, 1),
                                        'groups': groups})
                per_user.append({'seed': seed, 'model': name, 'condition': cond,
                                 'users': per_user_mae(err, uid_te, ant_te)})
                if seed == args.seeds[0] and cond in ('snap', 'full'):
                    npz[f'{name}__{cond}__err'] = err.astype(np.float32)
                    npz[f'{name}__{cond}__pred_xy'] = pred.astype(np.float32)
                g = groups
                log(f'  {name:<14}{cond:<11}{len(idx):>4} feat | '
                    f'multi {g["multi"].get("mae", float("nan")):6.3f} '
                    f'single {g["single"].get("mae", float("nan")):6.3f} m | '
                    f'{time.time() - t0:.0f}s')
            if seed == args.seeds[0]:
                npz['n_antennas'] = ant_te.astype(np.int8)
                npz['user_id'] = uid_te.astype(np.int32)
                npz['range_m'] = np.linalg.norm(true, axis=1).astype(np.float32)
                npz['true_xy'] = true.astype(np.float32)      # offsets from the serving BS, in sample order
                npz['bs_xy'] = bs_pos[:2].astype(np.float32)  # add to *_xy to get map coordinates
                if los_te is not None:
                    npz['is_los'] = los_te
        log(f'  seed {seed} complete in {time.time() - t_seed:.0f}s')

    summary = summarise(raw, args.models, conditions)

    log('')
    log('=' * 84)
    log(f'SEED-PAIRED GAIN vs {BASELINE} (metres, +ve = lower error), mean +/- 95% CI')
    log('=' * 84)
    for name in args.models:
        for cond in conditions:
            if cond == BASELINE:
                continue
            parts = []
            for g in ('multi', 'single'):
                pg = summary[name][cond][g].get('gain_vs_snap')
                if pg:
                    ci = pg['gain_ci95_m']
                    parts.append(f'{g} {pg["gain_mean_m"]:+6.3f}' + (f' +/- {ci:5.3f}' if ci is not None else ''))
            log(f'  {name:<14}{cond:<11}' + ' | '.join(parts))

    results = {
        'meta': {'dataset': data_dir.name, 'h': h, 'seeds': args.seeds,
                 'models': args.models, 'conditions': {c: CONDITIONS[c] for c in conditions},
                 'baseline': BASELINE, 'smoke': args.smoke,
                 'single_ant_ratio': args.single_ant_ratio,
                 'channel_groups': {'rss': RSS_SIDE, 'angle': ANGLE_SIDE,
                                    'ray': RAY_SIDE, 'time': TIME_SIDE},
                 'range_bins_m': [lab for _, _, lab in RANGE_BINS],
                 'protocol': 'macro-cell protocol: unseen-user split, classical models, '
                             'master-benchmark hyperparameters, no early stopping',
                 'wall_time_sec': round(time.time() - t_start, 1)},
        'user_counts': user_counts,
        'summary': summary,
        'per_seed': raw,
        'per_user': per_user,
    }
    out = out_dir / 'history_mechanism_diagnostic_summary.json'
    out.write_text(json.dumps(results, indent=1), encoding='utf-8')
    np.savez_compressed(out_dir / 'errors_first_seed.npz', **npz)
    log(f'saved -> {out}')
    log(f'saved -> {out_dir / "errors_first_seed.npz"}')
    log(f'total wall time: {time.time() - t_start:.0f}s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
