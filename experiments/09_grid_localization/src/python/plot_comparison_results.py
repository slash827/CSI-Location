"""
Comparison Results Visualization

Generates publication-quality figures from experiment matrix results.
Reads experiment_results.csv and produces key figures for the thesis.

Usage:
    python plot_comparison_results.py --results-dir results/experiment_matrix_xxx
    python plot_comparison_results.py --csv results/experiment_results.csv
"""

import argparse
import csv
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def load_results(csv_path):
    """Load experiment results from CSV."""
    results = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            for key in ['accuracy', 'mae', 'train_time', 'eval_time', 'grid_size',
                       'history', 'n_test_samples']:
                if key in row and row[key]:
                    try:
                        row[key] = float(row[key])
                    except ValueError:
                        pass
            results.append(row)
    return results


def plot_transition_impact(results, output_dir, metric_filter=None, grid_filter=None):
    """THE KEY FIGURE: Accuracy vs history length, one line per algorithm.

    Shows that ALL algorithms improve with transition history.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Determine which metric/grid to use
    grids = sorted(set(r['grid'] for r in results))
    metrics = sorted(set(r['metric'] for r in results))
    algorithms = sorted(set(r['algorithm'] for r in results))

    # Use smart features if available, otherwise raw
    feature_modes = set(r['feature_mode'] for r in results)
    preferred_fm = 'smart' if 'smart' in feature_modes else 'raw'

    # Filter to one grid and metric for the main figure
    if grid_filter is None:
        grid_filter = grids[len(grids) // 2] if grids else None  # Pick middle grid
    if metric_filter is None:
        # Prefer combined metrics
        for m in metrics:
            if '+' in str(m):
                metric_filter = m
                break
        if metric_filter is None:
            metric_filter = metrics[0] if metrics else None

    colors = {'gaussian': '#1f77b4', 'random_forest': '#2ca02c',
              'xgboost': '#ff7f0e', 'mlp': '#d62728'}
    markers = {'gaussian': 'o', 'random_forest': 's', 'xgboost': '^', 'mlp': 'D'}
    algo_labels = {'gaussian': 'Gaussian', 'random_forest': 'Random Forest',
                   'xgboost': 'XGBoost', 'mlp': 'MLP'}

    # --- Left: Accuracy ---
    ax = axes[0]
    for algo in algorithms:
        history_acc = {}
        for r in results:
            if (r['algorithm'] == algo and r['grid'] == grid_filter
                    and r['metric'] == metric_filter):
                h = int(r['history'])
                fm = r['feature_mode']
                # For h=0, accept any feature_mode (it's static)
                # For h>0, prefer the specified feature mode
                if h == 0 or fm == preferred_fm or (algo == 'gaussian' and fm in ('raw', 'static')):
                    if h not in history_acc or r['accuracy'] > history_acc[h]:
                        history_acc[h] = r['accuracy']

        if not history_acc:
            continue

        hs = sorted(history_acc.keys())
        accs = [history_acc[h] for h in hs]
        ax.plot(hs, accs, marker=markers.get(algo, 'o'), color=colors.get(algo, 'gray'),
                label=algo_labels.get(algo, algo), linewidth=2, markersize=8)

    ax.set_xlabel('History Length (h)', fontsize=12)
    ax.set_ylabel('Accuracy (%)', fontsize=12)
    ax.set_title(f'Classification Accuracy vs History\n({grid_filter}, {metric_filter})', fontsize=13)
    ax.set_xticks(range(0, 4))
    ax.set_xticklabels(['Static', 'h=1', 'h=2', 'h=3'])
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    # --- Right: MAE ---
    ax = axes[1]
    for algo in algorithms:
        history_mae = {}
        for r in results:
            if (r['algorithm'] == algo and r['grid'] == grid_filter
                    and r['metric'] == metric_filter):
                h = int(r['history'])
                fm = r['feature_mode']
                if h == 0 or fm == preferred_fm or (algo == 'gaussian' and fm in ('raw', 'static')):
                    if h not in history_mae or r['mae'] < history_mae[h]:
                        history_mae[h] = r['mae']

        if not history_mae:
            continue

        hs = sorted(history_mae.keys())
        maes = [history_mae[h] for h in hs]
        ax.plot(hs, maes, marker=markers.get(algo, 'o'), color=colors.get(algo, 'gray'),
                label=algo_labels.get(algo, algo), linewidth=2, markersize=8)

    ax.set_xlabel('History Length (h)', fontsize=12)
    ax.set_ylabel('MAE (meters)', fontsize=12)
    ax.set_title(f'Position Error vs History\n({grid_filter}, {metric_filter})', fontsize=13)
    ax.set_xticks(range(0, 4))
    ax.set_xticklabels(['Static', 'h=1', 'h=2', 'h=3'])
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_file = output_dir / 'transition_impact.png'
    plt.savefig(out_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved: {out_file}")


def plot_algorithm_comparison(results, output_dir):
    """Grouped bar chart: static vs best-transition for each algorithm."""
    grids = sorted(set(r['grid'] for r in results))
    algorithms = sorted(set(r['algorithm'] for r in results))
    metrics = sorted(set(r['metric'] for r in results))

    # Pick the most common grid
    grid_counts = {}
    for r in results:
        grid_counts[r['grid']] = grid_counts.get(r['grid'], 0) + 1
    main_grid = max(grid_counts, key=grid_counts.get)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    algo_labels = {'gaussian': 'Gaussian', 'random_forest': 'RF',
                   'xgboost': 'XGBoost', 'mlp': 'MLP'}

    for ax_idx, target_metric in enumerate(metrics[:2]):  # First 2 metrics
        static_accs = []
        best_trans_accs = []
        algo_names = []

        for algo in algorithms:
            # Static accuracy
            static = [r for r in results
                     if r['algorithm'] == algo and r['grid'] == main_grid
                     and r['metric'] == target_metric and int(r['history']) == 0]
            if not static:
                continue

            static_acc = max(r['accuracy'] for r in static)

            # Best transition accuracy
            trans = [r for r in results
                    if r['algorithm'] == algo and r['grid'] == main_grid
                    and r['metric'] == target_metric and int(r['history']) > 0]
            best_trans_acc = max((r['accuracy'] for r in trans), default=static_acc)

            static_accs.append(static_acc)
            best_trans_accs.append(best_trans_acc)
            algo_names.append(algo_labels.get(algo, algo))

        if not algo_names:
            continue

        x = np.arange(len(algo_names))
        width = 0.35

        bars1 = axes[ax_idx].bar(x - width/2, static_accs, width, label='Static (h=0)',
                                  color='#4ECDC4', edgecolor='white')
        bars2 = axes[ax_idx].bar(x + width/2, best_trans_accs, width, label='Best Transition',
                                  color='#FF6B6B', edgecolor='white')

        # Add improvement annotations
        for i, (s, t) in enumerate(zip(static_accs, best_trans_accs)):
            imp = t - s
            if imp > 0:
                axes[ax_idx].annotate(f'+{imp:.1f}%',
                                       xy=(x[i] + width/2, t),
                                       ha='center', va='bottom', fontsize=9,
                                       fontweight='bold', color='darkred')

        axes[ax_idx].set_xlabel('Algorithm', fontsize=12)
        axes[ax_idx].set_ylabel('Accuracy (%)', fontsize=12)
        axes[ax_idx].set_title(f'{target_metric.upper()} - {main_grid}', fontsize=13)
        axes[ax_idx].set_xticks(x)
        axes[ax_idx].set_xticklabels(algo_names)
        axes[ax_idx].legend(fontsize=10)
        axes[ax_idx].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    out_file = output_dir / 'algorithm_comparison.png'
    plt.savefig(out_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved: {out_file}")


def plot_scalability(results, output_dir):
    """Accuracy vs grid size, showing the approach scales."""
    grids_set = sorted(set(int(r['grid_size']) for r in results))
    if len(grids_set) < 2:
        print("[SKIP] Scalability plot requires multiple grid sizes")
        return

    algorithms = sorted(set(r['algorithm'] for r in results))
    metrics = sorted(set(r['metric'] for r in results))

    # Pick one metric (prefer combined)
    target_metric = metrics[0]
    for m in metrics:
        if '+' in str(m):
            target_metric = m
            break

    colors = {'gaussian': '#1f77b4', 'random_forest': '#2ca02c',
              'xgboost': '#ff7f0e', 'mlp': '#d62728'}
    algo_labels = {'gaussian': 'Gaussian', 'random_forest': 'RF',
                   'xgboost': 'XGBoost', 'mlp': 'MLP'}

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Static vs best transition across grid sizes
    for line_type, ax_idx in [('static', 0), ('transition', 0), ('mae', 1)]:
        ax = axes[ax_idx]

        for algo in algorithms:
            x_vals = []
            y_vals = []

            for gs in grids_set:
                grid_str = f"{gs}x{gs}"
                if line_type == 'mae':
                    # Best transition MAE
                    trans = [r for r in results
                            if r['algorithm'] == algo and r['grid'] == grid_str
                            and r['metric'] == target_metric and int(r['history']) > 0]
                    if trans:
                        x_vals.append(gs)
                        y_vals.append(min(r['mae'] for r in trans))
                elif line_type == 'static':
                    static = [r for r in results
                             if r['algorithm'] == algo and r['grid'] == grid_str
                             and r['metric'] == target_metric and int(r['history']) == 0]
                    if static:
                        x_vals.append(gs)
                        y_vals.append(max(r['accuracy'] for r in static))
                else:  # transition
                    trans = [r for r in results
                            if r['algorithm'] == algo and r['grid'] == grid_str
                            and r['metric'] == target_metric and int(r['history']) > 0]
                    if trans:
                        x_vals.append(gs)
                        y_vals.append(max(r['accuracy'] for r in trans))

            if not x_vals:
                continue

            ls = '--' if line_type == 'static' else '-'
            label = f"{algo_labels.get(algo, algo)}"
            if ax_idx == 0:
                label += ' (static)' if line_type == 'static' else ' (trans)'

            ax.plot(x_vals, y_vals, marker='o', color=colors.get(algo, 'gray'),
                    label=label, linewidth=2, linestyle=ls)

    axes[0].set_xlabel('Grid Size', fontsize=12)
    axes[0].set_ylabel('Accuracy (%)', fontsize=12)
    axes[0].set_title(f'Scalability: Accuracy vs Grid Size\n({target_metric})', fontsize=13)
    axes[0].legend(fontsize=9, ncol=2)
    axes[0].grid(True, alpha=0.3)

    axes[1].set_xlabel('Grid Size', fontsize=12)
    axes[1].set_ylabel('MAE (meters)', fontsize=12)
    axes[1].set_title(f'Scalability: Position Error vs Grid Size\n({target_metric})', fontsize=13)
    axes[1].legend(fontsize=10)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    out_file = output_dir / 'scalability.png'
    plt.savefig(out_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved: {out_file}")


def plot_feature_mode_comparison(results, output_dir):
    """Compare raw stacking vs smart features."""
    # Filter to results that have both modes
    raw_results = [r for r in results if r['feature_mode'] == 'raw' and int(r['history']) > 0]
    smart_results = [r for r in results if r['feature_mode'] == 'smart' and int(r['history']) > 0]

    if not raw_results or not smart_results:
        print("[SKIP] Feature mode comparison requires both raw and smart results")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    algorithms = sorted(set(r['algorithm'] for r in raw_results + smart_results))
    algo_labels = {'gaussian': 'Gaussian', 'random_forest': 'RF',
                   'xgboost': 'XGBoost', 'mlp': 'MLP'}
    colors = {'gaussian': '#1f77b4', 'random_forest': '#2ca02c',
              'xgboost': '#ff7f0e', 'mlp': '#d62728'}

    # Pick one grid and metric
    grids = sorted(set(r['grid'] for r in raw_results))
    main_grid = grids[len(grids) // 2] if grids else grids[0]
    metrics = sorted(set(r['metric'] for r in raw_results))
    main_metric = metrics[0]
    for m in metrics:
        if '+' in str(m):
            main_metric = m
            break

    # Accuracy comparison
    for algo in algorithms:
        for mode, ls, label_suffix in [('raw', '--', 'raw'), ('smart', '-', 'smart')]:
            data_filtered = [r for r in results
                           if r['algorithm'] == algo and r['grid'] == main_grid
                           and r['metric'] == main_metric
                           and (r['feature_mode'] == mode or int(r['history']) == 0)]
            if not data_filtered:
                continue

            history_acc = {}
            for r in data_filtered:
                h = int(r['history'])
                if h == 0 or r['feature_mode'] == mode:
                    if h not in history_acc or r['accuracy'] > history_acc[h]:
                        history_acc[h] = r['accuracy']

            if not history_acc:
                continue

            hs = sorted(history_acc.keys())
            accs = [history_acc[h] for h in hs]
            axes[0].plot(hs, accs, marker='o', color=colors.get(algo, 'gray'),
                        label=f"{algo_labels.get(algo, algo)} ({label_suffix})",
                        linewidth=2, linestyle=ls, markersize=6)

    axes[0].set_xlabel('History Length', fontsize=12)
    axes[0].set_ylabel('Accuracy (%)', fontsize=12)
    axes[0].set_title(f'Raw vs Smart Features\n({main_grid}, {main_metric})', fontsize=13)
    axes[0].legend(fontsize=9, ncol=2)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xticks(range(4))
    axes[0].set_xticklabels(['Static', 'h=1', 'h=2', 'h=3'])

    # Training time comparison
    raw_times = {}
    smart_times = {}
    for r in results:
        if r['grid'] != main_grid or r['metric'] != main_metric:
            continue
        h = int(r['history'])
        if h == 0:
            continue
        algo = r['algorithm']
        key = (algo, h)
        if r['feature_mode'] == 'raw' and r.get('train_time'):
            raw_times[key] = float(r['train_time'])
        elif r['feature_mode'] == 'smart' and r.get('train_time'):
            smart_times[key] = float(r['train_time'])

    if raw_times and smart_times:
        common_keys = sorted(set(raw_times.keys()) & set(smart_times.keys()))
        if common_keys:
            labels = [f"{algo_labels.get(k[0], k[0])}\nh={k[1]}" for k in common_keys]
            raw_t = [raw_times[k] for k in common_keys]
            smart_t = [smart_times[k] for k in common_keys]

            x = np.arange(len(common_keys))
            width = 0.35
            axes[1].bar(x - width/2, raw_t, width, label='Raw', color='#4ECDC4')
            axes[1].bar(x + width/2, smart_t, width, label='Smart', color='#FF6B6B')
            axes[1].set_xlabel('Configuration', fontsize=12)
            axes[1].set_ylabel('Training Time (s)', fontsize=12)
            axes[1].set_title('Training Time: Raw vs Smart', fontsize=13)
            axes[1].set_xticks(x)
            axes[1].set_xticklabels(labels, fontsize=9)
            axes[1].legend()
            axes[1].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    out_file = output_dir / 'feature_mode_comparison.png'
    plt.savefig(out_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved: {out_file}")


def plot_heatmap(results, output_dir):
    """Grid-size vs history heatmap of accuracy/MAE."""
    grids = sorted(set(int(r['grid_size']) for r in results))
    if len(grids) < 2:
        print("[SKIP] Heatmap requires multiple grid sizes")
        return

    algorithms = sorted(set(r['algorithm'] for r in results))
    history_vals = sorted(set(int(r['history']) for r in results))

    # Pick best metric per config
    metrics = sorted(set(r['metric'] for r in results))
    target_metric = metrics[0]
    for m in metrics:
        if '+' in str(m):
            target_metric = m
            break

    # Create one heatmap per algorithm
    n_algos = min(len(algorithms), 4)
    fig, axes = plt.subplots(1, n_algos, figsize=(5 * n_algos, 5))
    if n_algos == 1:
        axes = [axes]

    algo_labels = {'gaussian': 'Gaussian', 'random_forest': 'Random Forest',
                   'xgboost': 'XGBoost', 'mlp': 'MLP'}

    for ax_idx, algo in enumerate(algorithms[:n_algos]):
        matrix = np.full((len(grids), len(history_vals)), np.nan)

        for r in results:
            if r['algorithm'] != algo or r['metric'] != target_metric:
                continue
            gi = grids.index(int(r['grid_size']))
            hi = history_vals.index(int(r['history']))
            acc = r['accuracy']
            if np.isnan(matrix[gi, hi]) or acc > matrix[gi, hi]:
                matrix[gi, hi] = acc

        im = axes[ax_idx].imshow(matrix, cmap='RdYlGn', aspect='auto',
                                  vmin=np.nanmin(matrix) if not np.all(np.isnan(matrix)) else 0,
                                  vmax=np.nanmax(matrix) if not np.all(np.isnan(matrix)) else 100)

        # Annotate cells
        for i in range(len(grids)):
            for j in range(len(history_vals)):
                if not np.isnan(matrix[i, j]):
                    axes[ax_idx].text(j, i, f'{matrix[i, j]:.1f}%',
                                       ha='center', va='center', fontsize=9)

        axes[ax_idx].set_xticks(range(len(history_vals)))
        axes[ax_idx].set_xticklabels([f'h={h}' for h in history_vals])
        axes[ax_idx].set_yticks(range(len(grids)))
        axes[ax_idx].set_yticklabels([f'{g}x{g}' for g in grids])
        axes[ax_idx].set_xlabel('History Length')
        axes[ax_idx].set_ylabel('Grid Size')
        axes[ax_idx].set_title(algo_labels.get(algo, algo))

    plt.suptitle(f'Accuracy Heatmap ({target_metric})', fontsize=14, y=1.02)
    plt.tight_layout()
    out_file = output_dir / 'accuracy_heatmap.png'
    plt.savefig(out_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved: {out_file}")


def main():
    parser = argparse.ArgumentParser(description='Plot experiment comparison results')
    parser.add_argument('--results-dir', help='Directory containing experiment_results.csv')
    parser.add_argument('--csv', help='Direct path to CSV file')
    parser.add_argument('--output-dir', help='Output directory for plots (defaults to results dir)')
    parser.add_argument('--metric', help='Filter to specific metric for transition impact plot')
    parser.add_argument('--grid', help='Filter to specific grid for transition impact plot')

    args = parser.parse_args()

    # Find CSV
    if args.csv:
        csv_path = Path(args.csv)
    elif args.results_dir:
        csv_path = Path(args.results_dir) / 'experiment_results.csv'
    else:
        parser.error("Either --results-dir or --csv is required")

    if not csv_path.exists():
        print(f"Error: CSV not found: {csv_path}")
        return

    output_dir = Path(args.output_dir) if args.output_dir else csv_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading results from: {csv_path}")
    results = load_results(csv_path)
    print(f"Loaded {len(results)} result entries")

    # Generate all plots
    plot_transition_impact(results, output_dir, metric_filter=args.metric, grid_filter=args.grid)
    plot_algorithm_comparison(results, output_dir)
    plot_scalability(results, output_dir)
    plot_feature_mode_comparison(results, output_dir)
    plot_heatmap(results, output_dir)

    print(f"\nAll plots saved to: {output_dir}")


if __name__ == '__main__':
    main()
