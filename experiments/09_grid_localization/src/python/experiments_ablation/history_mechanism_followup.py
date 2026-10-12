"""
Follow-up to history_mechanism_diagnostic.py: the runs needed to turn the open
points of REPORT_SKELETON_VALIDATION.md into supported or rejected claims.

Same protocol as the diagnostic (unseen-user split, classical models at the
master-benchmark hyperparameters, depth-h windows built once per seed, every
condition a function of the same windows, so comparisons are paired by sample
and by seed). It adds:

  1. Region control. Per-sample error is stratified by the four Voronoi
     regions (nearest centre, i.e. pure geometry) on BOTH macro-cell datasets.
     The uniform-NLOS dataset has no LOS, so a "LOS-region" advantage that
     appears there cannot be a propagation effect. --did compares two runs.
  2. What in the angle history is used. az_hist / el_hist split azimuth from
     elevation; angle_mean (window mean only), angle_stats (mean + std) and
     angle_shuffled (lagged steps in random order) separate noise averaging
     from the spread and the order of the bearings.
  3. The single-antenna exception on mixed data. snap_los adds the true
     per-sample LOS flag to the snapshot and rss_hist_los adds it to the RSS
     history; error is also stratified by whether the window crosses an
     LOS/NLOS boundary.
  4. --aoa-noise-std / --aoa-quant-step / --aoa-noise-corr change the AoA
     impairment, to test whether the angle-history gain is the averaging of
     per-sample AoA error and how it depends on that error being independent
     from one sample to the next.
  5. More seeds (default 20), Student-t intervals, and per-group radial /
     tangential RMS, radial share of squared error and range correlation.
  6. --b6: the blocked line-of-sight corridor, stratified by device group,
     blocked / unblocked and strip width.

Usage (from the repository root):
    E=experiments/09_grid_localization/src/python/experiments_ablation
    .venv/Scripts/python $E/history_mechanism_followup.py --data-dir <dataset>
    .venv/Scripts/python $E/history_mechanism_followup.py --data-dir <b6 dataset> --b6
    .venv/Scripts/python $E/history_mechanism_followup.py --did <uniform.json> <mixed.json>
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import history_mechanism_diagnostic as D
from history_mechanism_diagnostic import (ANGLE_SIDE, N_STATIC, RANGE_BINS, SIGNAL_COLS,
                                          TIME_SIDE, aligned_values, feature_index)

DEFAULT_SEEDS = [42, 1, 7, 13, 99, 3, 11, 17, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]
BASELINE = 'snap'
AZ_SIDE = ['sin_az', 'cos_az', 'd_az']
EL_SIDE = ['sin_el', 'cos_el']
GROUPS = ('all', 'multi', 'single')

# Voronoi centres in map coordinates, as in history_gain_by_zone.py
VORONOI = [('Highway', 'LOS', (35.0, 15.0)), ('Shopping', 'NLOS', (95.0, 15.0)),
           ('Residential', 'NLOS', (75.0, 5.0)), ('Park', 'LOS', (60.0, 90.0))]


# ── pure helpers ──────────────────────────────────────────────────────────────
def channel_index(names, h, steps='all'):
    """Flattened-window indices of the given channels: all steps, lags only, or current."""
    L = h + 1
    pick = {'all': range(L), 'lags': range(L - 1), 'cur': [L - 1]}[steps]
    return np.asarray([SIGNAL_COLS.index(n) * L + t for n in names for t in pick], dtype=np.int64)


def subset_index(lagged, h):
    """Current step of every channel, plus all steps of the channels in `lagged`."""
    L = h + 1
    idx = []
    for c, name in enumerate(SIGNAL_COLS):
        idx.extend(c * L + t for t in (range(L) if name in lagged else [L - 1]))
    idx.extend(len(SIGNAL_COLS) * L + k for k in range(N_STATIC))
    return np.asarray(idx, dtype=np.int64)


def window_stats(X, names, h, with_std):
    """Order-free summaries of each channel's h+1 steps: mean, and optionally std."""
    L = h + 1
    cols = []
    for n in names:
        c = SIGNAL_COLS.index(n)
        w = X[:, c * L:(c + 1) * L]
        cols.append(w.mean(axis=1))
        if with_std:
            cols.append(w.std(axis=1))
    return np.column_stack(cols).astype(np.float32)


def shuffle_lags(X, names, h, rng):
    """Copy of X with the lagged steps of `names` permuted per sample.

    One permutation per sample is shared by all the channels, so each lagged
    step stays a consistent measurement; only its position in time is lost.
    The current step is left in place.
    """
    L = h + 1
    X = X.copy()
    if L < 3:
        return X
    perm = np.argsort(rng.random((len(X), L - 1)), axis=1)
    rows = np.arange(len(X))[:, None]
    for n in names:
        c = SIGNAL_COLS.index(n)
        block = X[:, c * L:c * L + L - 1]
        X[:, c * L:c * L + L - 1] = block[rows, perm]
    return X


def build_condition(cond, X, h, seed, tag, los=None):
    """Feature matrix for one condition. `tag` keeps train/test shuffles independent."""
    if cond in D.CONDITIONS:
        return X[:, feature_index(cond, h)]
    snap = X[:, feature_index('snap', h)]
    if cond == 'az_hist':
        return X[:, subset_index(AZ_SIDE + TIME_SIDE, h)]
    if cond == 'el_hist':
        return X[:, subset_index(EL_SIDE + TIME_SIDE, h)]
    if cond == 'angle_mean':
        return np.hstack([snap, window_stats(X, ANGLE_SIDE, h, with_std=False)])
    if cond == 'angle_stats':
        return np.hstack([snap, window_stats(X, ANGLE_SIDE, h, with_std=True)])
    if cond == 'angle_shuffled':
        rng = np.random.default_rng([seed, tag])
        return shuffle_lags(X, ANGLE_SIDE + TIME_SIDE, h, rng)[:, feature_index('angle_hist', h)]
    if cond == 'snap_los':
        return np.hstack([snap, los.astype(np.float32)[:, None]])
    if cond == 'rss_hist_los':
        return np.hstack([X[:, feature_index('rss_hist', h)], los.astype(np.float32)[:, None]])
    raise ValueError(f'Unknown condition: {cond}')


def aligned_windows(df, col, h, sample_uids):
    """[n_samples, h+1] windows of df[col], in the dataset's sample order."""
    wins, uids = [], []
    for _, udf in df.groupby('user_id'):
        udf = udf.sort_values('step_index')
        if len(udf) < h + 1:
            continue
        v = udf[col].values
        wins.append(np.lib.stride_tricks.sliding_window_view(v, h + 1))
        uids.append(udf['user_id'].values[h:])
    wins, uids = np.concatenate(wins), np.concatenate(uids)
    if len(wins) != len(sample_uids) or not np.array_equal(uids, np.asarray(sample_uids)):
        raise RuntimeError(f'window alignment broken for column {col!r}')
    return wins


def assign_region(x, y):
    centres = np.array([c for _, _, c in VORONOI])
    d = (x[:, None] - centres[None, :, 0]) ** 2 + (y[:, None] - centres[None, :, 1]) ** 2
    return d.argmin(axis=1)


def t_ci(vals):
    """Mean and Student-t 95% half-width of a list of paired differences."""
    v = np.asarray([x for x in vals if x is not None and np.isfinite(x)], dtype=float)
    if len(v) < 2:
        return (float(v.mean()) if len(v) else None), None, len(v)
    half = stats.t.ppf(0.975, len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v))
    return float(v.mean()), float(half), len(v)


def paired(base, cond):
    """Seed-paired gain base - cond with a Student-t interval."""
    pairs = [b - c for b, c in zip(base, cond) if b is not None and c is not None]
    if not pairs:
        return None
    mean, half, n = t_ci(pairs)
    base_mean = float(np.mean([b for b in base if b is not None]))
    return {'gain_mean_m': mean, 'gain_t95_m': half, 'n_pairs': n,
            'gain_pct': 100.0 * mean / base_mean if base_mean else None,
            'n_positive': int(sum(p > 0 for p in pairs)),
            'clears_t95': None if half is None else bool(abs(mean) > half)}


def shape_metrics(pred, true):
    """Radial / tangential structure of the error, BS at the origin."""
    rng = np.linalg.norm(true, axis=1)
    unit = true / np.maximum(rng, 1e-9)[:, None]
    delta = pred - true
    rad = (delta * unit).sum(axis=1)
    tan = delta[:, 0] * unit[:, 1] - delta[:, 1] * unit[:, 0]
    pr = np.linalg.norm(pred, axis=1)
    return {'radial_mae': float(np.abs(rad).mean()), 'tangential_mae': float(np.abs(tan).mean()),
            'radial_rms': float(np.sqrt((rad ** 2).mean())),
            'tangential_rms': float(np.sqrt((tan ** 2).mean())),
            'radial_share_sq': float((rad ** 2).sum() / ((rad ** 2).sum() + (tan ** 2).sum())),
            'radial_bias': float(rad.mean()),
            'range_corr': float(np.corrcoef(pr, rng)[0, 1]) if len(rng) > 2 else None}


def ar1_noise(n, std, rho, rng):
    """Stationary AR(1) sequence of length n with marginal std `std` and lag-1 correlation rho."""
    z = rng.standard_normal(n)
    e = np.empty(n)
    e[0] = z[0]
    k = np.sqrt(max(0.0, 1.0 - rho * rho))
    for t in range(1, n):
        e[t] = rho * e[t - 1] + k * z[t]
    return std * e


def prepare_correlated(data_dir, bs_pos, seed, single_ant_ratio, noise_std, quant_step, rho):
    """load_and_prepare_data with one change: the AoA error is AR(1) along each walk.

    Every other step (targets, quantisation, zeroing single-antenna AoA, the
    single-antenna downsample and the derived features) follows
    utils.csi_dataset.load_and_prepare_data. rho = 0 is independent error as in
    the original; rho -> 1 is an error that barely changes between steps.
    """
    from pipelines.multi_user_200_pipeline import load_200_users
    from utils.csi_dataset import build_derived_features
    df = load_200_users(Path(data_dir)).sort_values(['user_id', 'step_index']).reset_index(drop=True)
    df['target_x'] = (df['x_pos'] - bs_pos[0]).astype(np.float32)
    df['target_y'] = (df['y_pos'] - bs_pos[1]).astype(np.float32)
    rng = np.random.default_rng([seed, 7919])
    multi = df['n_antennas'] > 1
    for col in ('aoa_azimuth', 'aoa_elevation'):
        vals = df[col].values.astype(np.float64)
        for _, idx in df[multi].groupby('user_id').indices.items():
            rows = df.index[multi][idx]
            vals[rows] += ar1_noise(len(rows), noise_std, rho, rng)
        vals = np.round(vals / quant_step) * quant_step
        vals[~multi.values] = 0.0
        df[col] = vals.astype(np.float32)
    single_uids = df[df['n_antennas'] == 1]['user_id'].unique()
    multi_uids = df[df['n_antennas'] > 1]['user_id'].unique()
    target_n = int(len(multi_uids) * single_ant_ratio / (1.0 - single_ant_ratio))
    keep_single = np.random.RandomState(seed).choice(single_uids, size=min(target_n, len(single_uids)),
                                                     replace=False)
    df = df[df['user_id'].isin(set(multi_uids) | set(keep_single))].reset_index(drop=True)
    return build_derived_features(df)


def keep_awake():
    """Stop Windows from sleeping while this process runs (no-op elsewhere)."""
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
    except Exception:
        pass


# ── difference-in-differences across two runs ─────────────────────────────────
def did(path_a, path_b):
    """Is the LOS-region minus NLOS-region gain different between two datasets?

    Both runs must share seeds: the walks and user ids are identical across the
    two macro-cell datasets, so a seed gives the same test users in both and the
    contrast is paired by seed.
    """
    a, b = (json.loads(Path(p).read_text(encoding='utf-8')) for p in (path_a, path_b))
    seeds = [s for s in a['meta']['seeds'] if s in b['meta']['seeds']]
    print(f'A = {a["meta"]["dataset"]}\nB = {b["meta"]["dataset"]}\n{len(seeds)} shared seeds; '
          f'gain vs snap in metres, Student-t 95%')
    out = {}
    for model in a['meta']['models']:
        if model not in b['per_seed']:
            continue
        for cond in a['meta']['conditions']:
            if cond == BASELINE or cond not in b['per_seed'][model]:
                continue
            for g in ('multi', 'single'):
                def contrast(run, seed):
                    i = run['meta']['seeds'].index(seed)
                    s0 = run['per_seed'][model][BASELINE][i]['strata'][g]
                    s1 = run['per_seed'][model][cond][i]['strata'][g]
                    gl = s0['geo_LOS']['mae'] - s1['geo_LOS']['mae']
                    gn = s0['geo_NLOS']['mae'] - s1['geo_NLOS']['mae']
                    return gl, gn
                ca = np.array([contrast(a, s) for s in seeds])
                cb = np.array([contrast(b, s) for s in seeds])
                rec = {}
                for lab, v in (('A_losregion', ca[:, 0]), ('A_nlosregion', ca[:, 1]),
                               ('A_gap', ca[:, 0] - ca[:, 1]),
                               ('B_losregion', cb[:, 0]), ('B_nlosregion', cb[:, 1]),
                               ('B_gap', cb[:, 0] - cb[:, 1]),
                               ('B_minus_A_losregion', cb[:, 0] - ca[:, 0]),
                               ('B_minus_A_nlosregion', cb[:, 1] - ca[:, 1]),
                               ('B_minus_A_gap', (cb[:, 0] - cb[:, 1]) - (ca[:, 0] - ca[:, 1]))):
                    m, hw, _ = t_ci(v)
                    rec[lab] = {'mean': m, 't95': hw}
                out[f'{model}/{cond}/{g}'] = rec
                if cond in ('full', 'angle_hist', 'rss_hist'):
                    f = lambda k: f'{rec[k]["mean"]:+.2f}±{rec[k]["t95"]:.2f}'
                    print(f'{model:<14}{cond:<11}{g:<7} A: LOSreg {f("A_losregion")} NLOSreg {f("A_nlosregion")} '
                          f'gap {f("A_gap")} | B: LOSreg {f("B_losregion")} NLOSreg {f("B_nlosregion")} '
                          f'gap {f("B_gap")} | B-A gap {f("B_minus_A_gap")}')
    dst = Path(path_b).parent / 'region_gain_did_vs_uniform.json'
    dst.write_text(json.dumps({'A': a['meta']['dataset'], 'B': b['meta']['dataset'],
                               'seeds': seeds, 'contrasts': out}, indent=1), encoding='utf-8')
    print(f'saved -> {dst}')
    return 0


# ── experiment ────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(
        description='Follow-up runs for the history-mechanism diagnostic.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python history_mechanism_followup.py --data-dir results/grid_localization/grid_25x25/sim_data_300users_2026-07-25_11-46-11
  python history_mechanism_followup.py --data-dir results/grid_localization/grid_25x25/sim_data_300users_mixed_2026-09-18_20-25-01
  python history_mechanism_followup.py --data-dir results/b6_los_blocked_los/sim_data_b6_2026-09-19_12-54-09 --b6
  python history_mechanism_followup.py --did <uniform summary.json> <mixed summary.json>
""")
    ap.add_argument('--data-dir', help='dataset folder; no glob')
    ap.add_argument('--seeds', type=int, nargs='+', default=DEFAULT_SEEDS)
    ap.add_argument('--models', nargs='+', default=['xgboost', 'random_forest'],
                    choices=['xgboost', 'random_forest', 'knn'])
    ap.add_argument('--aoa-noise-corr', type=float, default=None,
                    help='lag-1 correlation of the AoA error along a walk (AR(1)); '
                         'omit for the original independent error')
    ap.add_argument('--conditions', nargs='+', default=None,
                    help='subset of conditions to run (snap is always included)')
    ap.add_argument('--history', type=int, default=5)
    ap.add_argument('--single-ant-ratio', type=float, default=0.15)
    ap.add_argument('--b6', action='store_true', help='blocked line-of-sight corridor dataset')
    ap.add_argument('--aoa-noise-std', type=float, default=4.0,
                    help='Gaussian AoA error in degrees, drawn independently per sample (default 4.0)')
    ap.add_argument('--aoa-quant-step', type=float, default=5.0,
                    help='AoA quantisation step in degrees (default 5.0); use a tiny value for none')
    ap.add_argument('--did', nargs=2, metavar=('A_JSON', 'B_JSON'),
                    help='compare region gains between two finished runs and exit')
    args = ap.parse_args()
    if args.did:
        return did(*args.did)
    if not args.data_dir:
        ap.error('--data-dir is required')

    keep_awake()
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

    h = args.history
    conditions = list(D.CONDITIONS) + ['az_hist', 'el_hist', 'angle_mean', 'angle_stats', 'angle_shuffled']
    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    aoa_tag = ('' if (args.aoa_noise_std, args.aoa_quant_step, args.aoa_noise_corr) == (4.0, 5.0, None)
               else f'aoa{args.aoa_noise_std:g}n{args.aoa_quant_step:g}q_')
    if args.aoa_noise_corr is not None:
        aoa_tag += f'rho{args.aoa_noise_corr:g}_'
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'history_mechanism_followup_{aoa_tag}{data_dir.name}_{run_ts}')
    out_dir.mkdir(parents=True, exist_ok=True)
    bs_pos = np.array(_read_bs_position_3d(data_dir))
    log(f'dataset={data_dir.name} | h={h} | {len(args.seeds)} seeds | models={args.models} | b6={args.b6}')

    b6_extra = None
    if args.b6:
        from b6_los_blocked_los_analysis import load_b6_extra_fields
        b6_extra = load_b6_extra_fields(data_dir)

    raw = None
    has_los = False
    user_counts = []
    t_start = time.time()
    for seed in args.seeds:
        t_seed = time.time()
        if args.aoa_noise_corr is None:
            df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=seed,
                                             single_ant_ratio=args.single_ant_ratio,
                                             aoa_noise_std_deg=args.aoa_noise_std,
                                             aoa_quant_step_deg=args.aoa_quant_step)
        else:
            df = prepare_correlated(data_dir, bs_pos, seed, args.single_ant_ratio,
                                    args.aoa_noise_std, args.aoa_quant_step, args.aoa_noise_corr)
        if b6_extra is not None:
            df = df.merge(b6_extra, on=['user_id', 'step_index'], how='left', validate='one_to_one')
            if df['in_blocked_segment'].isna().any():
                raise RuntimeError('B6 merge dropped rows')
        df, _, test_uids = make_unseen_user_split(df, Z.TRAIN_RATIO, seed)
        df_tr, df_te = df[df.split == 'train'], df[df.split == 'test']
        tr, te = Z.make_datasets(df_tr, df_te, h)
        X_tr, Y_tr, uid_tr, _, _ = Z.flatten(tr)
        X_te, Y_te, uid_te, _, ant_te = Z.flatten(te)
        ts, tm = tr.targ_std, tr.targ_mean
        true = Y_te * ts + tm
        rng_m = np.linalg.norm(true, axis=1)

        # strata: named boolean masks over the test samples
        strata = {'all': np.ones(len(true), bool)}
        for lo, hi, lab in RANGE_BINS:
            strata[f'range_{lab}'] = (rng_m >= lo) & (rng_m < hi)
        los_tr = los_te = None
        if args.b6:
            blocked = aligned_values(df_te, 'in_blocked_segment', h, uid_te).astype(bool)
            width = aligned_values(df_te, 'strip_width_m', h, uid_te).astype(float)
            strata['blocked'], strata['unblocked'] = blocked, ~blocked
            for w in sorted(np.unique(width)):
                strata[f'blocked_w{w:g}'] = blocked & (width == w)
        else:
            reg = assign_region(aligned_values(df_te, 'x_pos', h, uid_te).astype(float),
                                aligned_values(df_te, 'y_pos', h, uid_te).astype(float))
            reg_los = np.array([s == 'LOS' for _, s, _ in VORONOI])[reg]
            strata['geo_LOS'], strata['geo_NLOS'] = reg_los, ~reg_los
            for i, (name, _, _) in enumerate(VORONOI):
                strata[f'geo_{name}'] = reg == i
                for lo, hi, lab in RANGE_BINS:
                    strata[f'geo_{name}_range_{lab}'] = (reg == i) & (rng_m >= lo) & (rng_m < hi)
            if 'is_los' in df.columns and df['is_los'].notna().all():
                win = aligned_windows(df_te, 'is_los', h, uid_te).astype(bool)
                los_te = win[:, -1]
                los_tr = aligned_values(df_tr, 'is_los', h, uid_tr).astype(bool)
                cross = win.min(axis=1) != win.max(axis=1)
                strata['real_LOS'], strata['real_NLOS'] = los_te, ~los_te
                strata['win_pure_LOS'] = ~cross & los_te
                strata['win_pure_NLOS'] = ~cross & ~los_te
                strata['win_cross'] = cross
        has_los = los_te is not None
        conds = conditions + (['snap_los', 'rss_hist_los'] if has_los else [])
        if args.conditions:
            unknown = [c for c in args.conditions if c not in conds]
            if unknown:
                raise SystemExit(f'conditions not available on this dataset: {unknown}')
            conds = [BASELINE] + [c for c in conds if c in args.conditions and c != BASELINE]
        if raw is None:
            raw = {n: {c: [] for c in conds} for n in args.models}
        gmask = {'all': np.ones(len(true), bool), 'multi': ant_te > 1, 'single': ant_te == 1}
        user_counts.append({'seed': seed, **{g: int(len(np.unique(uid_te[m]))) for g, m in gmask.items()}})
        log('=' * 84)
        log(f'SEED {seed}: {len(test_uids)} test users ({user_counts[-1]["multi"]} multi, '
            f'{user_counts[-1]["single"]} single), {len(X_te):,} windows')

        for name in args.models:
            for cond in conds:
                t0 = time.time()
                F_tr = build_condition(cond, X_tr, h, seed, 0, los_tr)
                F_te = build_condition(cond, X_te, h, seed, 1, los_te)
                model = Z.build_classical(name, seed)
                model.fit(F_tr, Y_tr)
                pred = model.predict(F_te) * ts + tm
                err = np.linalg.norm(pred - true, axis=1)
                rec = {'seed': seed, 'n_features': int(F_tr.shape[1]), 'strata': {}, 'shape': {}}
                for g, gm in gmask.items():
                    rec['strata'][g] = {}
                    for s, sm in strata.items():
                        m = gm & sm
                        rec['strata'][g][s] = {'n': int(m.sum()),
                                               'mae': float(err[m].mean()) if m.any() else None}
                    if gm.any():
                        rec['shape'][g] = shape_metrics(pred[gm], true[gm])
                rec['elapsed_sec'] = round(time.time() - t0, 1)
                raw[name][cond].append(rec)
                log(f'  {name:<14}{cond:<15}{F_tr.shape[1]:>4} feat | '
                    f'multi {rec["strata"]["multi"]["all"]["mae"]:6.3f} '
                    f'single {rec["strata"]["single"]["all"]["mae"] or float("nan"):6.3f} m | '
                    f'{rec["elapsed_sec"]:.0f}s')
        log(f'  seed {seed} complete in {time.time() - t_seed:.0f}s')

    # ── aggregate ──
    conds = list(next(iter(raw.values())).keys())
    strata_names = list(raw[args.models[0]][BASELINE][0]['strata']['all'].keys())
    summary = {}
    for name in args.models:
        summary[name] = {}
        for cond in conds:
            summary[name][cond] = {}
            for g in GROUPS:
                rec = {'mae_by_stratum': {}, 'gain_vs_snap': {}, 'shape': {}}
                for s in strata_names:
                    c = [r['strata'][g][s]['mae'] for r in raw[name][cond]]
                    b = [r['strata'][g][s]['mae'] for r in raw[name][BASELINE]]
                    ok = [x for x in c if x is not None]
                    rec['mae_by_stratum'][s] = {'mean': float(np.mean(ok)) if ok else None,
                                                'mean_n': float(np.mean([r['strata'][g][s]['n'] for r in raw[name][cond]]))}
                    if cond != BASELINE:
                        rec['gain_vs_snap'][s] = paired(b, c)
                keys = raw[name][cond][0]['shape'].get(g, {}).keys()
                for k in keys:
                    m, hw, _ = t_ci([r['shape'][g][k] for r in raw[name][cond] if g in r['shape']])
                    rec['shape'][k] = {'mean': m, 't95': hw}
                summary[name][cond][g] = rec

    log('')
    log('=' * 84)
    log(f'SEED-PAIRED GAIN vs {BASELINE} (m, +ve = lower error), mean +/- Student-t 95%, {len(args.seeds)} seeds')
    log('=' * 84)
    for name in args.models:
        for cond in conds:
            if cond == BASELINE:
                continue
            parts = []
            for g in ('multi', 'single'):
                pg = summary[name][cond][g]['gain_vs_snap']['all']
                if pg and pg['gain_t95_m'] is not None:
                    parts.append(f'{g} {pg["gain_mean_m"]:+6.3f} +/- {pg["gain_t95_m"]:5.3f} '
                                 f'({pg["n_positive"]}/{pg["n_pairs"]} seeds +)')
            log(f'  {name:<14}{cond:<15}' + ' | '.join(parts))

    results = {
        'meta': {'dataset': data_dir.name, 'h': h, 'seeds': args.seeds, 'models': args.models,
                 'conditions': conds, 'baseline': BASELINE, 'b6': args.b6,
                 'single_ant_ratio': args.single_ant_ratio, 'has_real_los': has_los,
                 'aoa_noise_std_deg': args.aoa_noise_std, 'aoa_quant_step_deg': args.aoa_quant_step,
                 'aoa_noise_lag1_corr': args.aoa_noise_corr,
                 'interval': 'Student-t 95% over seed-paired differences',
                 'regions': [{'name': n, 'label': s, 'centre': list(c)} for n, s, c in VORONOI],
                 'protocol': 'macro-cell protocol: unseen-user split, classical models, '
                             'master-benchmark hyperparameters, no early stopping',
                 'wall_time_sec': round(time.time() - t_start, 1)},
        'user_counts': user_counts,
        'summary': summary,
        'per_seed': raw,
    }
    out = out_dir / 'history_mechanism_followup_summary.json'
    out.write_text(json.dumps(results, indent=1), encoding='utf-8')
    log(f'saved -> {out}')
    log(f'total wall time: {time.time() - t_start:.0f}s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
