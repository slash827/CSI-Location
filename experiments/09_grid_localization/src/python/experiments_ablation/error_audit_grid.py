"""
Audit of accuracy and MAE on the 15x15 controlled grid (instructor requests M1, M2, M3, M4).

Re-trains XGBoost (same settings as multi_user_pipeline.py) for a few experiments on one
simulation, keeps the per-sample predictions and reports
  * accuracy, MAE, and the identity  MAE = (1 - accuracy) x mean error of the wrong predictions;
  * how far the wrong predictions are (histogram, share within 1, 2, 3 cells);
  * MAE averaged per grid point (every cell weighted equally) next to the usual sample-weighted MAE;
  * a map of the mean error per grid point.

Usage (from the repository root):
    .venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/error_audit_grid.py \
        --data-dir results/grid_localization/grid_15x15/sim_data_ne_bs_<ts> \
        --out-dir results/error_audit/grid_ne_rmalos --n-jobs 4
    ... --experiments BASE_H3 BASE_A_H3 BASE --history 3
"""
import argparse
import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'src' / 'python'))

import pipelines.multi_user_pipeline as mu  # noqa: E402

# name -> (include AoA, history depth is the --history argument unless 0)
EXPS = {'BASE': (False, False), 'BASE_H3': (False, True), 'BASE_A': (True, False), 'BASE_A_H3': (True, True)}


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def main():
    ap = argparse.ArgumentParser(
        description='Accuracy/MAE audit with per-sample predictions on the 15x15 grid.',
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('Usage')[1])
    ap.add_argument('--data-dir', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--experiments', nargs='+', choices=list(EXPS), default=['BASE_H3', 'BASE_A_H3'])
    ap.add_argument('--history', type=int, default=3)
    ap.add_argument('--n-jobs', type=int, default=4)
    args = ap.parse_args()

    mu.N_JOBS = args.n_jobs
    data_dir, out = Path(args.data_dir), Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    df = mu.make_split(mu.load_all_users(data_dir, sinr_dependent_aoa=True))
    lookup = mu.build_grid_lookup(df)
    spacing = mu.get_grid_spacing(data_dir)
    labels = sorted(df['grid_point_id'].unique())
    l2i = {l: i for i, l in enumerate(labels)}
    i2l = np.array(labels)
    xy = np.array([lookup[int(l)] for l in labels])
    report = {}
    fig_h, axes_h = plt.subplots(1, len(args.experiments), figsize=(3.4 * len(args.experiments), 2.8), sharey=True)
    fig_m, axes_m = plt.subplots(1, len(args.experiments), figsize=(3.4 * len(args.experiments), 3.2), sharey=True)
    axes_h, axes_m = np.atleast_1d(axes_h), np.atleast_1d(axes_m)
    for k, exp in enumerate(args.experiments):
        aoa, hist = EXPS[exp]
        h = args.history if hist else 0
        feat = mu.build_history_features(df, h, include_aoa=aoa)
        cols = mu.get_feature_cols(h, include_aoa=aoa)
        tr, te = feat['split'] == 'train', feat['split'] == 'test'
        clf = mu.get_model('xgboost', len(labels))
        clf.fit(feat.loc[tr, cols].values.astype(np.float32), feat.loc[tr, 'grid_point_id'].map(l2i).values)
        pred = i2l[clf.predict(feat.loc[te, cols].values.astype(np.float32))]
        true = feat.loc[te, 'grid_point_id'].values
        t_xy = np.array([lookup[int(i)] for i in true])
        p_xy = np.array([lookup[int(i)] for i in pred])
        err = np.linalg.norm(t_xy - p_xy, axis=1)
        wrong = err > 0
        acc, mae = float((~wrong).mean()), float(err.mean())
        # per-grid-point (equal weight) MAE
        per_cell = np.array([err[true == l].mean() if (true == l).any() else np.nan for l in labels])
        r = {
            'h': h, 'n_test': int(len(err)), 'accuracy': acc, 'mae_m': mae,
            'mean_error_of_wrong_m': float(err[wrong].mean()),
            'identity_mae_equals_(1-acc)*wrong': float((1 - acc) * err[wrong].mean()),
            'share_exact': acc,
            'share_within_1_cell': float((err <= spacing * np.sqrt(2) + 1e-6).mean()),
            'share_within_2_cells': float((err <= 2 * spacing * np.sqrt(2) + 1e-6).mean()),
            'share_within_3_cells': float((err <= 3 * spacing * np.sqrt(2) + 1e-6).mean()),
            'median_m': float(np.median(err)), 'p90_m': float(np.percentile(err, 90)),
            'mae_per_grid_point_equal_weight_m': float(np.nanmean(per_cell)),
            'test_rows_per_cell_min_max': [int(np.bincount(pd_ids := np.searchsorted(i2l, true)).min()),
                                           int(np.bincount(pd_ids).max())],
        }
        report[exp] = r
        log(f'{exp}: acc {100 * acc:.1f}%  MAE {mae:.2f} m  wrong-only {r["mean_error_of_wrong_m"]:.2f} m  '
            f'(1-acc)*wrong {r["identity_mae_equals_(1-acc)*wrong"]:.2f} m  equal-weight MAE {r["mae_per_grid_point_equal_weight_m"]:.2f} m')
        ax = axes_h[k]
        ax.hist(err, bins=np.arange(0, 36, 2), color='#2a78d6')
        ax.set_title(f'{exp}: {100 * acc:.0f}% exact, MAE {mae:.1f} m', fontsize=8)
        ax.set_xlabel('position error (m)')
        sc = axes_m[k].scatter(xy[:, 0], xy[:, 1], c=per_cell, s=38, marker='s', cmap='viridis', vmin=0, vmax=12)
        axes_m[k].set_aspect('equal')
        axes_m[k].set_title(f'{exp}: mean error per grid point', fontsize=8)
    axes_h[0].set_ylabel('test samples')
    fig_m.colorbar(sc, ax=axes_m, label='mean error (m)', shrink=0.8)
    fig_h.savefig(out / 'error_histogram.png', dpi=160, bbox_inches='tight')
    fig_m.savefig(out / 'error_map_per_grid_point.png', dpi=160, bbox_inches='tight')
    (out / 'audit.json').write_text(json.dumps(
        {'data_dir': str(data_dir), 'spacing_m': spacing, 'model': 'xgboost', 'results': report}, indent=2))
    log(f'wrote {out}')


if __name__ == '__main__':
    main()
