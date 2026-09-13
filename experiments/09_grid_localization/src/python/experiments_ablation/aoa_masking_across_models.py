"""
A2: Does explicit AoA validity masking generalise beyond the 1D-CNN?

Single-antenna UEs cannot estimate AoA, and the pipeline assigns them a dummy
(0 deg, 0 deg). The derived features then compute cos(0) = 1 and
ray_y = r_est * cos(0) = r_est, which asserts a *confident* bearing along the
positive y axis. The network is not merely uninformed about these devices, it is
actively misinformed.

The masking fix (report section 7.6) zeroes the trigonometric embeddings so that
sin^2 + cos^2 = 0, which lies strictly off the unit circle of realisable angles,
zeroes the geometric ray projections, and adds an explicit has_valid_aoa channel.

That result is currently measured on the 1D-CNN only. But this is a *feature
pipeline* fix, not an architectural one, so it should help any model consuming
these features. If it does, the contribution stops being an architecture trick and
becomes a second mechanism-level claim, structurally parallel to the history one.

Reference (1D-CNN, report section 7.6):
    single-antenna  33.607 -> 32.188 m   (+4.22%)
    multi-antenna   15.408 -> 15.279 m   (+0.84%)

Usage:
    python aoa_masking_across_models.py
    python aoa_masking_across_models.py --history 5 --seed 42
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
from utils import csi_dataset
from utils.csi_dataset import DerivedCSI1DDataset, load_and_prepare_data

from sklearn.neighbors import KNeighborsRegressor
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

TRIG_COLS = ['sin_az', 'cos_az', 'sin_el', 'cos_el']
RAY_COLS = ['ray_x', 'ray_y']
DELTA_COLS = ['d_az', 'd_ray_x', 'd_ray_y']


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


def build_arm(df, h, masked, seed):
    """Return flattened train/test arrays for one arm (masked or not)."""
    df = df.copy()
    if masked:
        blind = df['n_antennas'] <= 1
        # sin^2 + cos^2 = 0 lies off the unit circle, so "no angle" is
        # representable and distinguishable from "angle = 0 degrees"
        df.loc[blind, TRIG_COLS] = 0.0
        df.loc[blind, RAY_COLS] = 0.0
        df.loc[blind, DELTA_COLS] = 0.0
        df['has_valid_aoa'] = (~blind).astype(np.float32)
        signal_cols = csi_dataset.SIGNAL_COLS + ['has_valid_aoa']
    else:
        signal_cols = list(csi_dataset.SIGNAL_COLS)

    original = csi_dataset.SIGNAL_COLS
    try:
        csi_dataset.SIGNAL_COLS = signal_cols
        tr_df, te_df = df[df.split == 'train'], df[df.split == 'test']
        tr = DerivedCSI1DDataset(tr_df, h=h)
        te = DerivedCSI1DDataset(te_df, h=h,
                                 sig_mean=tr.sig_mean, sig_std=tr.sig_std,
                                 stat_mean=tr.stat_mean, stat_std=tr.stat_std,
                                 targ_mean=tr.targ_mean, targ_std=tr.targ_std,
                                 speed_mean=tr.speed_mean, speed_std=tr.speed_std)
        X_tr, Y_tr, _ = flatten(tr)
        X_te, Y_te, ant = flatten(te)
    finally:
        csi_dataset.SIGNAL_COLS = original
    return X_tr, Y_tr, X_te, Y_te, ant, tr.targ_std, tr.targ_mean


def evaluate(pred, true, ant):
    err = np.linalg.norm(pred - true, axis=1)
    multi, single = ant > 1, ant == 1
    return {'mae': float(err.mean()),
            'p50': float(np.median(err)),
            'multi_mae': float(err[multi].mean()),
            'single_mae': float(err[single].mean()),
            'n_multi': int(multi.sum()), 'n_single': int(single.sum())}


def main():
    ap = argparse.ArgumentParser(
        description='AoA validity masking across model families (A2).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python aoa_masking_across_models.py
  python aoa_masking_across_models.py --history 3
""")
    ap.add_argument('--history', type=int, default=5)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--single-ant-ratio', type=float, default=0.15)
    args = ap.parse_args()

    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'aoa_masking_across_models_{run_ts}')
    out_dir.mkdir(parents=True, exist_ok=True)

    log('loading...')
    data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
    data_dir = sorted(data_base.glob('sim_data_300users_*'))[-1]
    bs_pos = np.array(_read_bs_position_3d(data_dir))
    df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=args.seed,
                                     single_ant_ratio=args.single_ant_ratio)
    df, _, _ = make_unseen_user_split(df, 0.8, args.seed)

    def models():
        return {
            'knn': KNeighborsRegressor(n_neighbors=5, n_jobs=-1),
            'random_forest': RandomForestRegressor(
                n_estimators=150, max_features='sqrt', max_depth=16,
                min_samples_leaf=5, random_state=args.seed, n_jobs=-1),
            'xgboost': XGBRegressor(
                n_estimators=50, max_depth=5, learning_rate=0.15, subsample=0.8,
                colsample_bytree=0.8, random_state=args.seed, n_jobs=-1,
                tree_method='hist', multi_strategy='one_output_per_tree'),
        }

    results = {'meta': {'dataset': str(data_dir), 'h': args.history,
                        'seed': args.seed,
                        'reference_cnn': {'single': [33.607, 32.188],
                                          'multi': [15.408, 15.279]}}, 'arms': {}}

    arms = {}
    for masked in (False, True):
        name = 'masked' if masked else 'unmasked'
        t0 = time.time()
        X_tr, Y_tr, X_te, Y_te, ant, ts, tm = build_arm(df, args.history, masked, args.seed)
        log(f'{name}: {X_tr.shape[1]} features, built in {time.time()-t0:.1f}s')
        arms[name] = {}
        for mname, model in models().items():
            t1 = time.time()
            model.fit(X_tr, Y_tr)
            pred = model.predict(X_te) * ts + tm
            true = Y_te * ts + tm
            rec = evaluate(pred, true, ant)
            rec['fit_sec'] = round(time.time() - t1, 1)
            arms[name][mname] = rec
            log(f'  {mname:<14} MAE {rec["mae"]:6.3f} | multi {rec["multi_mae"]:6.3f} '
                f'| single {rec["single_mae"]:6.3f} | {rec["fit_sec"]}s')
        results['arms'][name] = arms[name]

    log('=' * 76)
    log(f'AoA MASKING EFFECT (h={args.history})')
    log('=' * 76)
    header = f'{"model":<15}{"overall":>22}{"multi-antenna":>24}{"single-antenna":>24}'
    log(header)
    log(f'{"":<15}{"unmask -> mask":>22}{"unmask -> mask":>24}{"unmask -> mask":>24}')
    log('-' * len(header))
    deltas = {}
    for mname in ('knn', 'random_forest', 'xgboost'):
        u, m = arms['unmasked'][mname], arms['masked'][mname]
        d = {k: round(100.0 * (u[k] - m[k]) / u[k], 2)
             for k in ('mae', 'multi_mae', 'single_mae')}
        deltas[mname] = d
        log(f'{mname:<15}'
            f'{u["mae"]:8.3f} ->{m["mae"]:7.3f} ({d["mae"]:+5.2f}%)'
            f'{u["multi_mae"]:9.3f} ->{m["multi_mae"]:7.3f} ({d["multi_mae"]:+5.2f}%)'
            f'{u["single_mae"]:9.3f} ->{m["single_mae"]:7.3f} ({d["single_mae"]:+5.2f}%)')
    results['deltas_pct'] = deltas

    n_single_better = sum(1 for d in deltas.values() if d['single_mae'] > 0)
    n_overall_better = sum(1 for d in deltas.values() if d['mae'] > 0)
    results['verdict'] = {
        'n_models': len(deltas),
        'n_single_ant_improved': n_single_better,
        'n_overall_improved': n_overall_better,
        'generalises': bool(n_single_better == len(deltas)),
    }
    log('-' * len(header))
    log(f'single-antenna improved in {n_single_better}/{len(deltas)} models | '
        f'overall improved in {n_overall_better}/{len(deltas)}')
    log('VERDICT: ' + ('masking GENERALISES beyond the 1D-CNN'
                       if n_single_better == len(deltas) else
                       'masking does NOT generalise - it is architecture-specific'))

    out = out_dir / 'aoa_masking_across_models_summary.json'
    out.write_text(json.dumps(results, indent=1), encoding='utf-8')
    log(f'saved -> {out}')


if __name__ == '__main__':
    sys.exit(main())
