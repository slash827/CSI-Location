"""
A4: Where does the tree-ensemble history curve actually turn?

Report section 5.4 shows the 1D-CNN and k-NN turning at h=10 while XGBoost keeps
improving (19.027 m at h=10, still falling). The claim there is hedged to "over the
range tested", which is honest but unsatisfying: the true optimum for tree
ensembles is unknown.

This pushes the window out to h=30. Note the feature count grows as 13(h+1)+3, so
h=30 means 406 flat features against 114k training rows - at some point
dimensionality rather than staleness becomes the binding constraint, and the
interesting question is which limit bites first.

Usage:
    python deep_history_sweep_trees.py
    python deep_history_sweep_trees.py --depths 5 10 15 20 30 40
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


def main():
    ap = argparse.ArgumentParser(
        description='Extend the tree-ensemble history sweep past h=10 (A4).')
    ap.add_argument('--depths', type=int, nargs='+', default=[0, 5, 10, 15, 20, 30])
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--single-ant-ratio', type=float, default=0.15)
    args = ap.parse_args()

    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'deep_history_sweep_trees_{run_ts}')
    out_dir.mkdir(parents=True, exist_ok=True)

    log('loading...')
    data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
    data_dir = sorted(data_base.glob('sim_data_300users_*'))[-1]
    bs_pos = np.array(_read_bs_position_3d(data_dir))
    df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=args.seed,
                                     single_ant_ratio=args.single_ant_ratio)
    df, _, _ = make_unseen_user_split(df, 0.8, args.seed)
    df_tr, df_te = df[df.split == 'train'], df[df.split == 'test']

    results = {'meta': {'dataset': str(data_dir), 'seed': args.seed,
                        'depths': args.depths}, 'sweep': {}}

    log(f'{"h":>4}{"feats":>8}{"n_train":>10}{"n_test":>9}{"MAE":>9}'
        f'{"multi":>9}{"single":>9}{"sec":>7}')
    log('-' * 66)
    for h in args.depths:
        t0 = time.time()
        tr = DerivedCSI1DDataset(df_tr, h=h)
        te = DerivedCSI1DDataset(df_te, h=h,
                                 sig_mean=tr.sig_mean, sig_std=tr.sig_std,
                                 stat_mean=tr.stat_mean, stat_std=tr.stat_std,
                                 targ_mean=tr.targ_mean, targ_std=tr.targ_std,
                                 speed_mean=tr.speed_mean, speed_std=tr.speed_std)
        X_tr, Y_tr, _ = flatten(tr)
        X_te, Y_te, ant = flatten(te)
        model = XGBRegressor(n_estimators=50, max_depth=5, learning_rate=0.15,
                             subsample=0.8, colsample_bytree=0.8,
                             random_state=args.seed, n_jobs=-1, tree_method='hist',
                             multi_strategy='one_output_per_tree')
        model.fit(X_tr, Y_tr)
        pred = model.predict(X_te) * tr.targ_std + tr.targ_mean
        true = Y_te * tr.targ_std + tr.targ_mean
        err = np.linalg.norm(pred - true, axis=1)
        multi, single = ant > 1, ant == 1
        rec = {'h': h, 'n_features': int(X_tr.shape[1]),
               'n_train': int(len(X_tr)), 'n_test': int(len(X_te)),
               'mae': float(err.mean()), 'p50': float(np.median(err)),
               'multi_mae': float(err[multi].mean()),
               'single_mae': float(err[single].mean()),
               'elapsed_sec': round(time.time() - t0, 1)}
        results['sweep'][f'h={h}'] = rec
        log(f'{h:>4}{rec["n_features"]:>8}{rec["n_train"]:>10}{rec["n_test"]:>9}'
            f'{rec["mae"]:>9.3f}{rec["multi_mae"]:>9.3f}{rec["single_mae"]:>9.3f}'
            f'{rec["elapsed_sec"]:>7.0f}')

    maes = [(h, results['sweep'][f'h={h}']['mae']) for h in args.depths]
    best_h, best_mae = min(maes, key=lambda t: t[1])
    base = results['sweep'][f'h={args.depths[0]}']['mae']
    results['verdict'] = {
        'best_h': best_h, 'best_mae': round(best_mae, 4),
        'gain_vs_first_pct': round(100.0 * (base - best_mae) / base, 2),
        'turned_within_range': bool(best_h != args.depths[-1]),
    }
    log('-' * 66)
    log(f'best depth h={best_h} at {best_mae:.3f} m '
        f'({100.0*(base-best_mae)/base:+.2f}% vs h={args.depths[0]})')
    log('curve turned within the tested range: '
        + ('YES' if best_h != args.depths[-1] else 'NO - still improving at the deepest window'))

    out = out_dir / 'deep_history_sweep_trees_summary.json'
    out.write_text(json.dumps(results, indent=1), encoding='utf-8')
    log(f'saved -> {out}')


if __name__ == '__main__':
    sys.exit(main())
