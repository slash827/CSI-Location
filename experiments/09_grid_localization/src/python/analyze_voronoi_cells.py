"""
Per-Voronoi-Cell Error Analysis

Runs a specified model on simulation data and computes:
  - Per-cell accuracy and MAE
  - Fraction of errors that land *outside* the true cell (cross-cell errors)
  - Cell-level confusion matrix (n_cells x n_cells)
  - Spatial heatmap of per-grid-point accuracy overlaid on Voronoi boundaries

Usage:
    python analyze_voronoi_cells.py --data-dir <path>
    python analyze_voronoi_cells.py --data-dir <path> --algorithm random_forest --history 2

Defaults: XGBoost, rss+sinr+aoa_azimuth+aoa_elevation, h=1 (best from experiments)
"""

import argparse
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from pathlib import Path
from scipy.spatial.distance import cdist

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent))
from localization_pipeline import (
    SimulationData, DataSplitter, XGBoostModel, RandomForestModel,
    Evaluator, PROJECT_ROOT
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def assign_grid_points_to_cells(grid_positions_2d, voronoi_centers):
    """Assign each grid point to its nearest Voronoi cell (1-indexed)."""
    dists = cdist(grid_positions_2d, voronoi_centers)   # (n_points, n_cells)
    return np.argmin(dists, axis=1) + 1                  # 1-indexed


def run_model(data, metric_spec, algorithm, history_length):
    """Train model and return (predictions, true_labels, valid_test_indices)."""
    # Build metric matrix
    if isinstance(metric_spec, list):
        metric_values = np.column_stack([data.metrics[m.lower()] for m in metric_spec])
    else:
        metric_values = data.metrics[metric_spec.lower()]
    if metric_values.ndim == 1:
        metric_values = metric_values.reshape(-1, 1)

    splitter = DataSplitter(test_ratio=0.2, split_method='temporal')

    is_transition = history_length > 0
    if is_transition:
        train_indices, test_indices = splitter.split_transition(data.n_samples, history_length)
    else:
        train_indices, test_indices = splitter.split_static(data.n_samples)

    if algorithm == 'xgboost':
        model = XGBoostModel(use_transition=is_transition, history_length=history_length,
                             n_estimators=100, feature_mode='raw', n_jobs=4)
    else:
        model = RandomForestModel(use_transition=is_transition, history_length=history_length,
                                  n_estimators=100, feature_mode='raw', n_jobs=-1)

    model.train(metric_values, data.true_locations, train_indices, data.n_points)
    predictions, valid_mask = model.predict_batch(metric_values, test_indices)

    valid_test_indices = test_indices[valid_mask]
    true_labels = np.array([data.true_locations[i] for i in valid_test_indices])

    return np.array(predictions), true_labels, valid_test_indices


# ---------------------------------------------------------------------------
# Per-cell statistics
# ---------------------------------------------------------------------------

def compute_cell_stats(predictions, true_labels, valid_test_indices,
                       voronoi_cell_idx, grid_point_cells,
                       grid_positions, cell_names, cell_scenarios):
    """
    Returns a dict-of-lists with per-cell metrics.

    Fields:
      cell_idx, cell_name, scenario,
      n_samples, accuracy, mae_m,
      within_cell_errors, cross_cell_errors, cross_cell_error_frac
    """
    n_cells = len(cell_names)

    # True cell for each test sample — use grid-point-based assignment
    # (cleaner than walk-based voronoi_cell_idx for cell analysis)
    true_cells = grid_point_cells[true_labels - 1]   # 1-indexed labels → 0-indexed
    pred_cells = grid_point_cells[predictions - 1]

    stats = {k: [] for k in ['cell_idx', 'cell_name', 'scenario',
                               'n_samples', 'accuracy', 'mae_m',
                               'n_correct', 'n_within_cell_error', 'n_cross_cell_error',
                               'cross_cell_error_frac']}

    for c in range(1, n_cells + 1):
        mask = true_cells == c
        if not mask.any():
            continue

        preds_c  = predictions[mask]
        truths_c = true_labels[mask]
        pred_cells_c = pred_cells[mask]

        n = mask.sum()
        correct_mask = preds_c == truths_c
        n_correct = correct_mask.sum()

        # MAE in metres
        pred_pos  = grid_positions[preds_c  - 1, :2]
        true_pos  = grid_positions[truths_c - 1, :2]
        mae = float(np.mean(np.linalg.norm(pred_pos - true_pos, axis=1)))

        # Error breakdown
        error_mask = ~correct_mask
        n_errors   = error_mask.sum()
        cross_cell = (pred_cells_c[error_mask] != c).sum() if n_errors > 0 else 0
        within_cell = n_errors - cross_cell

        stats['cell_idx'].append(c)
        stats['cell_name'].append(cell_names[c - 1] if c - 1 < len(cell_names) else f'cell_{c}')
        stats['scenario'].append(cell_scenarios[c - 1] if c - 1 < len(cell_scenarios) else '')
        stats['n_samples'].append(int(n))
        stats['accuracy'].append(float(n_correct / n * 100))
        stats['mae_m'].append(mae)
        stats['n_correct'].append(int(n_correct))
        stats['n_within_cell_error'].append(int(within_cell))
        stats['n_cross_cell_error'].append(int(cross_cell))
        stats['cross_cell_error_frac'].append(float(cross_cell / n_errors * 100) if n_errors > 0 else 0.0)

    return stats


def build_cell_confusion_matrix(predictions, true_labels, grid_point_cells, n_cells):
    """n_cells x n_cells matrix: [true_cell, pred_cell] = count."""
    true_cells = grid_point_cells[true_labels  - 1]
    pred_cells = grid_point_cells[predictions  - 1]
    cm = np.zeros((n_cells, n_cells), dtype=int)
    for tc, pc in zip(true_cells, pred_cells):
        cm[tc - 1, pc - 1] += 1
    return cm


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

CELL_COLORS = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']


def plot_cell_stats(stats, out_path):
    """Bar chart: accuracy and cross-cell error fraction per cell."""
    n = len(stats['cell_idx'])
    labels = [f"Cell {stats['cell_idx'][i]}\n{stats['cell_name'][i]}" for i in range(n)]
    x = np.arange(n)
    w = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    bars1 = ax1.bar(x, stats['accuracy'], w, label='Accuracy', color=CELL_COLORS[:n])
    ax1.set_xlabel('Voronoi Cell')
    ax1.set_ylabel('Accuracy (%)')
    ax1.set_title('Per-Cell Classification Accuracy')
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.set_ylim(0, 105)
    for bar, v in zip(bars1, stats['accuracy']):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f'{v:.1f}%', ha='center', va='bottom', fontsize=9)

    bars2 = ax2.bar(x, stats['cross_cell_error_frac'], w, color=CELL_COLORS[:n])
    ax2.set_xlabel('Voronoi Cell')
    ax2.set_ylabel('Cross-cell errors / total errors (%)')
    ax2.set_title('Fraction of Errors That Cross Cell Boundary')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=9)
    ax2.set_ylim(0, 105)
    for bar, v in zip(bars2, stats['cross_cell_error_frac']):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f'{v:.1f}%', ha='center', va='bottom', fontsize=9)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [plot] {out_path}')


def plot_cell_confusion_matrix(cm, cell_names, cell_labels, out_path):
    """Normalised (row = true cell) confusion matrix."""
    n = cm.shape[0]
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True).clip(min=1)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    for ax, data, title, fmt in [
        (ax1, cm,      'Counts',       'd'),
        (ax2, cm_norm, 'Row-normalised', '.2f'),
    ]:
        im = ax.imshow(data, cmap='Blues', vmin=0)
        plt.colorbar(im, ax=ax, fraction=0.046)
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(cell_labels, fontsize=9)
        ax.set_yticklabels(cell_labels, fontsize=9)
        ax.set_xlabel('Predicted cell')
        ax.set_ylabel('True cell')
        ax.set_title(title)
        thresh = data.max() / 2
        for i in range(n):
            for j in range(n):
                v = data[i, j]
                txt = (f'{int(v)}' if fmt == 'd' else f'{v:.2f}')
                ax.text(j, i, txt, ha='center', va='center', fontsize=9,
                        color='white' if v > thresh else 'black')

    fig.suptitle('Cell-Level Confusion Matrix', fontsize=13)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [plot] {out_path}')


def plot_spatial_accuracy(grid_positions, grid_point_cells, predictions, true_labels,
                          voronoi_centers, cell_names, bs_position, out_path):
    """Spatial heatmap of per-grid-point accuracy with Voronoi cell segmentation."""
    n_points = len(grid_positions)
    n_cells  = voronoi_centers.shape[0]

    # Per-grid-point accuracy and MAE
    per_point_acc = np.full(n_points, np.nan)
    per_point_mae = np.full(n_points, np.nan)
    for pt in range(1, n_points + 1):
        mask = true_labels == pt
        if mask.sum() == 0:
            continue
        correct = (predictions[mask] == pt).mean() * 100
        pred_pos  = grid_positions[predictions[mask] - 1, :2]
        true_pos  = grid_positions[pt - 1, :2]
        mae = np.mean(np.linalg.norm(pred_pos - true_pos, axis=1))
        per_point_acc[pt - 1] = correct
        per_point_mae[pt - 1] = mae

    # ---------------------------------------------------------------
    # Build Voronoi segmentation background via nearest-centre mesh
    # ---------------------------------------------------------------
    pad = 1.5
    x_min, x_max = grid_positions[:, 0].min() - pad, grid_positions[:, 0].max() + pad
    y_min, y_max = grid_positions[:, 1].min() - pad, grid_positions[:, 1].max() + pad
    xx, yy = np.meshgrid(np.linspace(x_min, x_max, 400),
                         np.linspace(y_min, y_max, 400))
    mesh_pts = np.column_stack([xx.ravel(), yy.ravel()])
    mesh_cell_idx = np.argmin(cdist(mesh_pts, voronoi_centers), axis=1).reshape(xx.shape)
    cell_cmap = mcolors.ListedColormap(CELL_COLORS[:n_cells])

    # Centroid of each cell's grid points (for centering labels inside the region)
    cell_centroids = []
    for ci in range(n_cells):
        pts = grid_positions[grid_point_cells == ci + 1, :2]   # grid_point_cells is 1-indexed
        cell_centroids.append(pts.mean(axis=0) if len(pts) > 0 else voronoi_centers[ci])

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for ax, values, cmap, label, title in [
        (axes[0], per_point_acc, 'RdYlGn', 'Accuracy (%)',   'Per-grid-point accuracy'),
        (axes[1], per_point_mae, 'RdYlGn_r', 'MAE (m)',      'Per-grid-point MAE'),
    ]:
        # --- Voronoi cell segmentation: filled regions + boundary lines ---
        ax.pcolormesh(xx, yy, mesh_cell_idx, cmap=cell_cmap, alpha=0.15,
                      vmin=-0.5, vmax=n_cells - 0.5, shading='auto', zorder=0)
        ax.contour(xx, yy, mesh_cell_idx, levels=np.arange(0.5, n_cells),
                   colors='#555555', linewidths=1.5, zorder=1, alpha=0.8)

        # --- Per-grid-point scatter (accuracy / MAE colouring) ---
        sc = ax.scatter(grid_positions[:, 0], grid_positions[:, 1],
                        c=values, cmap=cmap, s=120, edgecolors='k', linewidths=0.3,
                        vmin=np.nanmin(values), vmax=np.nanmax(values), zorder=3)
        plt.colorbar(sc, ax=ax, label=label, fraction=0.046)

        # --- Cell labels centred inside each Voronoi region ---
        for ci in range(n_cells):
            color = CELL_COLORS[ci % len(CELL_COLORS)]
            name  = cell_names[ci] if ci < len(cell_names) else f'cell_{ci+1}'
            cx, cy = cell_centroids[ci]
            ax.text(cx, cy, name, ha='center', va='center',
                    fontsize=9, fontweight='bold', color=color, zorder=8,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              alpha=0.65, edgecolor=color, linewidth=1.2))

        # --- BS marker ---
        ax.scatter(bs_position[0], bs_position[1], marker='^', s=300,
                   c='black', edgecolors='white', linewidths=1.5, zorder=6, label='BS')

        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_title(title)
        ax.set_aspect('equal')
        ax.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [plot] {out_path}')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Per-Voronoi-cell error analysis')
    parser.add_argument('--data-dir', required=True,
                        help='Path to simulation_data directory')
    parser.add_argument('--algorithm', default='xgboost',
                        choices=['xgboost', 'random_forest'])
    parser.add_argument('--metrics', default='rss,sinr,aoa_azimuth,aoa_elevation',
                        help='Comma-separated metric names')
    parser.add_argument('--history', type=int, default=1,
                        help='Transition history length (0 = static)')
    args = parser.parse_args()

    data_path = Path(args.data_dir)
    metric_spec = [m.strip() for m in args.metrics.split(',')]
    metric_label = '+'.join(metric_spec)

    print('=' * 60)
    print('VORONOI CELL ANALYSIS')
    print('=' * 60)
    print(f'Data:      {data_path}')
    print(f'Algorithm: {args.algorithm}')
    print(f'Metrics:   {metric_label}')
    print(f'History:   h={args.history}')
    print()

    # ------------------------------------------------------------------
    # Load data
    # ------------------------------------------------------------------
    data = SimulationData(str(data_path))

    import scipy.io as sio
    raw = sio.loadmat(str(data_path / 'simulation_data.mat'), simplify_cells=True)
    wp  = raw['walk_path']
    cfg = raw['config']

    voronoi_cell_idx  = np.array(wp['voronoi_cell_idx']).flatten()   # (n_samples,)
    voronoi_centers   = np.array(wp['voronoi_centers'])               # (n_cells, 2)
    voronoi_names     = list(wp.get('voronoi_names', []))
    voronoi_scenarios = list(wp.get('voronoi_scenarios', []))
    grid_positions    = np.array(cfg['grid_positions'])               # (n_points, 3)
    bs_position       = np.array(cfg['bs_position']).flatten()

    n_cells = voronoi_centers.shape[0]
    if not voronoi_names:
        voronoi_names = [f'cell_{i+1}' for i in range(n_cells)]

    # Short labels for plots: "cell_1\nhighway"
    cell_labels = [f'C{i+1}\n{voronoi_names[i]}' for i in range(n_cells)]

    # Assign each grid point to its Voronoi cell
    grid_point_cells = assign_grid_points_to_cells(
        grid_positions[:, :2], voronoi_centers
    )   # (n_points,) — 1-indexed cell number for each grid point

    print(f'Grid: {int(cfg["grid_size"])}x{int(cfg["grid_size"])}  '
          f'({data.n_points} points,  {data.n_samples} samples)')
    print(f'Voronoi cells: {n_cells}')
    for i in range(n_cells):
        pts_in_cell = (grid_point_cells == i + 1).sum()
        name = voronoi_names[i] if i < len(voronoi_names) else '?'
        scen = voronoi_scenarios[i] if i < len(voronoi_scenarios) else '?'
        print(f'  Cell {i+1}: {name:20s}  {scen:40s}  ({pts_in_cell} grid points)')
    print()

    # ------------------------------------------------------------------
    # Run model
    # ------------------------------------------------------------------
    print(f'Running {args.algorithm} ({metric_label}, h={args.history})...')
    predictions, true_labels, valid_test_indices = run_model(
        data, metric_spec, args.algorithm, args.history
    )
    overall_acc = (predictions == true_labels).mean() * 100
    pred_pos  = grid_positions[predictions  - 1, :2]
    true_pos  = grid_positions[true_labels - 1, :2]
    overall_mae = np.mean(np.linalg.norm(pred_pos - true_pos, axis=1))
    print(f'  Overall accuracy: {overall_acc:.1f}%   MAE: {overall_mae:.2f}m')
    print()

    # ------------------------------------------------------------------
    # Per-cell statistics
    # ------------------------------------------------------------------
    stats = compute_cell_stats(
        predictions, true_labels, valid_test_indices,
        voronoi_cell_idx, grid_point_cells,
        grid_positions, voronoi_names, voronoi_scenarios
    )

    print('Per-cell results:')
    header = f"{'Cell':>4}  {'Name':20s}  {'N':>6}  {'Acc%':>6}  {'MAE(m)':>7}  {'Within-cell err':>16}  {'Cross-cell err':>14}  {'Cross%':>7}"
    print(header)
    print('-' * len(header))
    for i in range(len(stats['cell_idx'])):
        line = (f"{stats['cell_idx'][i]:>4}  "
                f"{stats['cell_name'][i]:20s}  "
                f"{stats['n_samples'][i]:>6}  "
                f"{stats['accuracy'][i]:>6.1f}  "
                f"{stats['mae_m'][i]:>7.2f}  "
                f"{stats['n_within_cell_error'][i]:>7} / {stats['n_samples'][i] - stats['n_correct'][i]:<6}  "
                f"{stats['n_cross_cell_error'][i]:>14}  "
                f"{stats['cross_cell_error_frac'][i]:>7.1f}%")
        print(line)
    print()

    # ------------------------------------------------------------------
    # Cell confusion matrix
    # ------------------------------------------------------------------
    cm = build_cell_confusion_matrix(predictions, true_labels, grid_point_cells, n_cells)
    print('Cell confusion matrix (rows=true, cols=predicted):')
    header_cm = '       ' + '  '.join(f'C{c+1}' for c in range(n_cells))
    print(header_cm)
    for i in range(n_cells):
        row = f'  C{i+1}   ' + '  '.join(f'{cm[i,j]:>3}' for j in range(n_cells))
        print(row)
    print()

    # ------------------------------------------------------------------
    # Save outputs
    # ------------------------------------------------------------------
    out_dir = data_path / f'cell_analysis_{args.algorithm}_h{args.history}'
    out_dir.mkdir(exist_ok=True)

    # CSV
    import csv
    csv_path = out_dir / 'per_cell_stats.csv'
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(stats.keys()))
        writer.writeheader()
        for i in range(len(stats['cell_idx'])):
            writer.writerow({k: stats[k][i] for k in stats})
    print(f'  [csv]  {csv_path}')

    # Plots
    plot_cell_stats(stats, out_dir / 'cell_accuracy_and_cross_errors.png')
    plot_cell_confusion_matrix(cm, voronoi_names, cell_labels,
                               out_dir / 'cell_confusion_matrix.png')
    plot_spatial_accuracy(grid_positions, grid_point_cells, predictions, true_labels,
                          voronoi_centers, voronoi_names, bs_position,
                          out_dir / 'spatial_accuracy_map.png')

    print(f'\nAll outputs saved to: {out_dir}')


if __name__ == '__main__':
    main()
