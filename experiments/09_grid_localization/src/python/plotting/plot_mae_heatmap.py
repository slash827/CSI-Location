"""
Per-Grid-Point MAE Heatmap

Trains a model on the multi-user dataset, then computes per-grid-point MAE
on the test set and exports:
  - mae_heatmap_{exp}_{model}.csv   — grid_point_id, x, y, voronoi_cell_id, n_test, mae_m
  - mae_heatmap_{exp}_{model}.png   — scatter heatmap coloured by MAE, Voronoi boundaries

Supports multiple experiments in one run; produces a comparison subplot when
more than one experiment is given.

Usage:
  # Single experiment (default: BASE_A_H, xgboost):
  python plot_mae_heatmap.py --data-dir <path/to/sim_data_multi_user_*>

  # Compare BASE vs BASE_A_H side-by-side:
  python plot_mae_heatmap.py --data-dir <path> --experiments BASE BASE_A_H

  # Choose model and output dir:
  python plot_mae_heatmap.py --data-dir <path> --model rf --out-dir results/my_dir
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ── Shared utilities from the main pipeline ───────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from pipelines.multi_user_pipeline import (
    EXPERIMENTS,
    load_all_users,
    make_split,
    build_grid_lookup,
    build_history_features,
    build_delta_features,
    get_feature_cols,
    _read_bs_geometry,
)

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    from sklearn.ensemble import RandomForestClassifier
    HAS_RF = True
except ImportError:
    HAS_RF = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: Matplotlib not available — CSV will be written, PNG skipped")

RESULTS_ROOT = SCRIPT_DIR.parent.parent.parent.parent / 'results'

_EXP_REGISTRY = {e['key']: e for e in EXPERIMENTS}

CELL_COLORS = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']


# ─────────────────────────────────────────────────────────────────────────────
# Feature builder
# ─────────────────────────────────────────────────────────────────────────────

def build_features(df: pd.DataFrame, exp_def: dict) -> tuple[pd.DataFrame, list]:
    """Return (feat_df, feature_cols) for an experiment definition."""
    h     = exp_def['h']
    extra = exp_def.get('extra')
    aoa   = exp_def['aoa']
    mode  = exp_def['mode']

    if mode == 'delta':
        feat_df = build_delta_features(df, h=h, extra_cols=extra, include_aoa=aoa)
    else:
        feat_df = build_history_features(df, h=h, extra_cols=extra, include_aoa=aoa)

    feat_cols = get_feature_cols(h=h, extra_cols=extra, include_aoa=aoa, mode=mode)
    return feat_df, feat_cols


# ─────────────────────────────────────────────────────────────────────────────
# Per-grid-point MAE computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_per_point_mae(feat_df: pd.DataFrame,
                          feature_cols: list,
                          grid_lookup: dict,
                          model_name: str) -> pd.DataFrame:
    """
    Train model on train split, predict on test split, return per-grid-point
    DataFrame with columns: grid_point_id, x, y, voronoi_cell_id, n_test, mae_m.
    """
    label_col  = 'grid_point_id'
    train_mask = feat_df['split'] == 'train'
    test_mask  = feat_df['split'] == 'test'

    all_labels = sorted(feat_df[label_col].unique())
    label2idx  = {lbl: i for i, lbl in enumerate(all_labels)}
    idx2label  = {i: lbl for lbl, i in label2idx.items()}

    X_train = feat_df.loc[train_mask, feature_cols].values
    y_train = np.array([label2idx[l] for l in feat_df.loc[train_mask, label_col]])
    X_test  = feat_df.loc[test_mask,  feature_cols].values
    y_test  = feat_df.loc[test_mask,  label_col].values

    if model_name == 'xgboost':
        if not HAS_XGBOOST:
            raise ImportError("XGBoost not installed")
        model = XGBClassifier(
            n_estimators=50, max_depth=5, learning_rate=0.15,
            subsample=0.8, colsample_bytree=0.8,
            use_label_encoder=False, eval_metric='mlogloss',
            n_jobs=2, random_state=42, verbosity=0,
        )
    else:
        if not HAS_RF:
            raise ImportError("scikit-learn not installed")
        model = RandomForestClassifier(
            n_estimators=50, max_features='sqrt', max_depth=15,
            min_samples_leaf=20, n_jobs=1, random_state=42
        )

    model.fit(X_train, y_train)
    y_pred_idx  = model.predict(X_test)
    y_pred      = np.array([idx2label[i] for i in y_pred_idx])

    # Attach predictions to the test slice
    test_df = feat_df.loc[test_mask, [label_col, 'x_pos', 'y_pos', 'voronoi_cell_id']].copy()
    test_df = test_df.reset_index(drop=True)
    test_df['pred_grid_point_id'] = y_pred

    # Compute Euclidean error per sample
    def point_error(row):
        tx, ty = grid_lookup.get(int(row[label_col]),             (0.0, 0.0))
        px, py = grid_lookup.get(int(row['pred_grid_point_id']), (0.0, 0.0))
        return np.sqrt((tx - px) ** 2 + (ty - py) ** 2)

    test_df['error_m'] = test_df.apply(point_error, axis=1)

    # Aggregate per true grid point
    gp_stats = (
        test_df.groupby(label_col)
        .agg(
            x=('x_pos',           'mean'),
            y=('y_pos',           'mean'),
            voronoi_cell_id=('voronoi_cell_id', lambda s: int(s.mode()[0])),
            n_test=('error_m',    'count'),
            mae_m=('error_m',     'mean'),
        )
        .reset_index()
    )
    gp_stats = gp_stats.rename(columns={label_col: 'grid_point_id'})
    return gp_stats.sort_values('grid_point_id').reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Heatmap plotting
# ─────────────────────────────────────────────────────────────────────────────

def _draw_voronoi_background(ax, gp_df: pd.DataFrame, data_dir: Path = None):
    """Draw Voronoi cell background shading, boundaries, and BS markers."""
    from scipy.spatial.distance import cdist as _cdist

    cell_ids = sorted(gp_df['voronoi_cell_id'].unique())
    n_cells  = len(cell_ids)

    # Try to load voronoi_centers from .mat, fall back to centroid of grid points
    voronoi_centers = None
    if data_dir is not None:
        try:
            import scipy.io as _sio
            user1_candidates = sorted(data_dir.glob('user1_*.mat'))
            if user1_candidates:
                mat = _sio.loadmat(str(user1_candidates[0]),
                                   squeeze_me=True, struct_as_record=False)
                if 'voronoi_centers' in mat:
                    vc = np.array(mat['voronoi_centers'], dtype=float)
                    voronoi_centers = vc.reshape(-1, 2) if vc.ndim == 1 else vc
        except Exception:
            pass

    if voronoi_centers is None or len(voronoi_centers) != n_cells:
        voronoi_centers = np.array([
            [gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'x'].mean(),
             gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'y'].mean()]
            for cid in cell_ids
        ])

    pad  = 1.5
    x_min, x_max = gp_df['x'].min() - pad, gp_df['x'].max() + pad
    y_min, y_max = gp_df['y'].min() - pad, gp_df['y'].max() + pad
    xx, yy = np.meshgrid(np.linspace(x_min, x_max, 400),
                         np.linspace(y_min, y_max, 400))
    mesh_pts      = np.column_stack([xx.ravel(), yy.ravel()])
    mesh_cell_idx = np.argmin(_cdist(mesh_pts, voronoi_centers),
                              axis=1).reshape(xx.shape)

    cell_cmap = mcolors.ListedColormap(CELL_COLORS[:n_cells])
    ax.pcolormesh(xx, yy, mesh_cell_idx, cmap=cell_cmap, alpha=0.12,
                  vmin=-0.5, vmax=n_cells - 0.5, shading='auto', zorder=0)
    ax.contour(xx, yy, mesh_cell_idx, levels=np.arange(0.5, n_cells),
               colors='#555555', linewidths=1.2, zorder=1, alpha=0.7)

    # Cell centroid labels
    for i, cid in enumerate(cell_ids):
        color = CELL_COLORS[i % len(CELL_COLORS)]
        cx = gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'x'].mean()
        cy = gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'y'].mean()
        ax.text(cx, cy, f'C{cid}', ha='center', va='center',
                fontsize=9, fontweight='bold', color=color, zorder=8, alpha=0.5)

    # BS and interferer markers (auto-detected from config)
    if data_dir is not None:
        bs_xy, ibs_xys = _read_bs_geometry(data_dir)
        if bs_xy is not None:
            ax.scatter([bs_xy[0]], [bs_xy[1]], marker='^', s=250, c='blue',
                       zorder=6, edgecolors='white', linewidths=1.5, label='Serving BS')
        if ibs_xys:
            ax.scatter([p[0] for p in ibs_xys], [p[1] for p in ibs_xys],
                       marker='x', s=130, c='red', zorder=6, linewidths=2,
                       label='Interferers')
        if bs_xy is not None or ibs_xys:
            ax.legend(fontsize=8, loc='upper left')

    return x_min, x_max, y_min, y_max


def plot_single_heatmap(ax, gp_stats: pd.DataFrame,
                        title: str,
                        vmin: float, vmax: float,
                        data_dir: Path = None) -> object:
    """Draw MAE heatmap on a given Axes. Returns scatter for colorbar."""
    _draw_voronoi_background(ax, gp_stats, data_dir)

    sc = ax.scatter(
        gp_stats['x'], gp_stats['y'],
        c=gp_stats['mae_m'],
        cmap='RdYlGn_r',    # red = high error, green = low error
        vmin=vmin, vmax=vmax,
        s=70, alpha=0.95, edgecolors='k', linewidths=0.3, zorder=5,
    )
    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.set_xlabel('X (m)', fontsize=9)
    ax.set_ylabel('Y (m)', fontsize=9)
    ax.set_aspect('equal')
    ax.tick_params(labelsize=8)
    return sc


def _adaptive_vmax(values) -> float:
    """Colormap ceiling scaled to data distribution.

    max(p90, median * 4) keeps high-accuracy experiments (e.g. BASE_A_H,
    mean~0.27 m) on a tight 0–~0.8 m scale instead of being compressed by
    a few outliers onto a 0–15 m shared scale.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr) & (arr >= 0)]
    if len(arr) == 0:
        return 1.0
    return float(max(np.percentile(arr, 90), np.median(arr) * 4))


def save_heatmap_image(results_map: dict,
                       model_name: str,
                       out_dir: Path,
                       data_dir: Path = None):
    """
    results_map: {exp_key: gp_stats_df}
    Produces one PNG per experiment (each with its own adaptive scale) +
    a comparison PNG (independent colorbars per subplot) if len > 1.
    """
    if not HAS_MATPLOTLIB:
        return

    # Per-experiment adaptive scale so high-accuracy plots aren't flattened
    vmaxes = {k: _adaptive_vmax(df['mae_m'].values) for k, df in results_map.items()}

    # Individual plots
    for exp_key, gp_stats in results_map.items():
        vmax = vmaxes[exp_key]
        fig, ax = plt.subplots(figsize=(7, 7))
        overall_mae = gp_stats['mae_m'].mean()
        sc = plot_single_heatmap(
            ax, gp_stats,
            title=f'MAE per grid point — {exp_key} ({model_name})\n'
                  f'Overall MAE = {overall_mae:.3f} m',
            vmin=0.0, vmax=vmax,
            data_dir=data_dir,
        )
        plt.colorbar(sc, ax=ax, label='MAE (m)', shrink=0.85)
        fig.tight_layout()
        fname = out_dir / f'mae_heatmap_{exp_key}_{model_name}.png'
        fig.savefig(fname, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  Saved: {fname}")

    # Comparison plot — independent colorbars per subplot so each experiment
    # uses its own scale (experiments span very different error regimes)
    if len(results_map) > 1:
        n = len(results_map)
        ncols = min(n, 3)
        nrows = (n + ncols - 1) // ncols
        fig, axes = plt.subplots(nrows, ncols,
                                 figsize=(6.5 * ncols, 6.5 * nrows),
                                 squeeze=False)
        axes_flat = axes.ravel()

        for i, (exp_key, gp_stats) in enumerate(results_map.items()):
            ax = axes_flat[i]
            overall_mae = gp_stats['mae_m'].mean()
            sc = plot_single_heatmap(
                ax, gp_stats,
                title=f'{exp_key}  (MAE={overall_mae:.3f} m)',
                vmin=0.0, vmax=vmaxes[exp_key],
                data_dir=data_dir,
            )
            plt.colorbar(sc, ax=ax, label='MAE (m)', shrink=0.85)

        for j in range(i + 1, len(axes_flat)):
            axes_flat[j].set_visible(False)

        fig.suptitle(f'MAE Heatmap Comparison — {model_name}\n'
                     f'(independent colour scales per subplot)',
                     fontsize=12, fontweight='bold')
        fig.tight_layout()
        fname = out_dir / f'mae_heatmap_comparison_{model_name}.png'
        fig.savefig(fname, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  Saved: {fname}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    all_exp_keys = [e['key'] for e in EXPERIMENTS]

    parser = argparse.ArgumentParser(
        description='Per-grid-point MAE heatmap for the multi-user 15x15 experiment.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python plot_mae_heatmap.py --data-dir results/grid_localization/grid_15x15/sim_data_multi_user_*/
  python plot_mae_heatmap.py --data-dir <path> --experiments BASE BASE_A_H BASE_A_H_dp
  python plot_mae_heatmap.py --data-dir <path> --model rf --out-dir results/my_dir
""",
    )
    parser.add_argument('--data-dir', required=True, type=Path,
                        help='Directory containing user*.mat files')
    parser.add_argument('--out-dir', type=Path,
                        default=RESULTS_ROOT / 'multi_user_voronoi_15x15',
                        help='Output directory (default: results/multi_user_voronoi_15x15)')
    parser.add_argument('--experiments', nargs='+', default=['BASE_A_H'],
                        choices=all_exp_keys, metavar='EXP',
                        help=f'Experiment(s) to plot. Choices: {all_exp_keys}')
    parser.add_argument('--model', choices=['xgboost', 'rf'], default='xgboost',
                        help='Model to use (default: xgboost)')
    args = parser.parse_args()

    if args.model == 'xgboost' and not HAS_XGBOOST:
        print("Error: XGBoost not installed. Use --model rf")
        sys.exit(1)

    csv_dir = args.out_dir / 'csvs'
    img_dir = args.out_dir / 'images' / 'mae'
    for d in (args.out_dir, csv_dir, img_dir):
        d.mkdir(parents=True, exist_ok=True)

    # ── Load & split data ──────────────────────────────────────────────────────
    print(f"Loading data from {args.data_dir} ...")
    df = load_all_users(args.data_dir)
    df = make_split(df, test_ratio=0.2)
    grid_lookup = build_grid_lookup(df)
    print(f"  {len(df):,} samples | {df['grid_point_id'].nunique()} grid points | "
          f"train={( df['split']=='train').sum():,} test={( df['split']=='test').sum():,}")

    # ── Run each requested experiment ─────────────────────────────────────────
    results_map = {}
    for exp_key in args.experiments:
        exp_def = _EXP_REGISTRY[exp_key]
        print(f"\n[{exp_key}] Building features ...")
        feat_df, feat_cols = build_features(df, exp_def)

        print(f"[{exp_key}] Training {args.model} ...")
        gp_stats = compute_per_point_mae(feat_df, feat_cols, grid_lookup, args.model)

        # Save CSV
        csv_path = csv_dir / f'mae_heatmap_{exp_key}_{args.model}.csv'
        gp_stats.to_csv(csv_path, index=False)
        print(f"  Saved CSV: {csv_path}")
        print(f"  Overall MAE: {gp_stats['mae_m'].mean():.3f} m  |  "
              f"Min: {gp_stats['mae_m'].min():.3f} m  "
              f"Max: {gp_stats['mae_m'].max():.3f} m")

        results_map[exp_key] = gp_stats

    # ── Produce PNG(s) ─────────────────────────────────────────────────────────
    print("\nGenerating heatmap image(s) ...")
    save_heatmap_image(results_map, args.model, img_dir, data_dir=args.data_dir)

    print("\nDone.")


if __name__ == '__main__':
    main()
