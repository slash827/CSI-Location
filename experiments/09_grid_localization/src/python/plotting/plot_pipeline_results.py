"""
Plot results from the new pipeline (pipeline_results.npz format)

This script generates visualizations for the grid localization pipeline results.
It works with the new .npz format instead of the old MATLAB .mat format.
"""

import sys
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

sns.set_style('whitegrid')


def load_results(results_dir):
    """Load results from pipeline_results.npz"""
    results_dir = Path(results_dir)
    
    # Load pipeline results
    npz_file = results_dir / 'pipeline_results.npz'
    if not npz_file.exists():
        raise FileNotFoundError(f"Results file not found: {npz_file}\n"
                              f"Make sure you're pointing to a results directory (exp13e_*), "
                              f"not a simulation data directory (sim_data_*).")
    
    # Load results (config is stored inside npz as JSON string)
    data = np.load(npz_file, allow_pickle=True)
    
    # Extract config from npz
    config_json_str = str(data['config'])
    config = json.loads(config_json_str)
    
    return data, config


def plot_spatial_layout(data, config, output_dir):
    """Plot spatial layout showing grid and base stations"""
    grid_size = config['grid']['size']
    spacing = config['grid']['spacing']
    grid_offset = config['grid']['grid_offset']
    
    # Generate grid positions
    grid_x = []
    grid_y = []
    for row in range(grid_size):
        for col in range(grid_size):
            grid_x.append(col * spacing + grid_offset[0])
            grid_y.append(row * spacing + grid_offset[1])
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Plot grid points
    ax.scatter(grid_x, grid_y, c='lightblue', s=200, marker='s', 
               edgecolors='blue', linewidths=2, alpha=0.6, label='Grid Points', zorder=2)
    
    # Add grid point numbers (1-indexed)
    for i, (x, y) in enumerate(zip(grid_x, grid_y)):
        ax.text(x, y, str(i+1), ha='center', va='center', fontsize=9, fontweight='bold')
    
    # Plot serving BS
    bs_pos = config['base_station']['position']
    ax.scatter(bs_pos[0], bs_pos[1], c='red', s=500, marker='^', 
               edgecolors='darkred', linewidths=3, label='Serving BS (Main)', zorder=3)
    ax.text(bs_pos[0], bs_pos[1] - 8, 'Main BS', ha='center', va='top', 
            fontsize=11, fontweight='bold', color='darkred',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='darkred', linewidth=2))
    
    # Plot interfering BSs if enabled
    if config['base_station']['interferers']['enabled']:
        interferer_positions = config['base_station']['interferers']['positions']
        if interferer_positions:
            interferer_x = [pos[0] for pos in interferer_positions]
            interferer_y = [pos[1] for pos in interferer_positions]
            ax.scatter(interferer_x, interferer_y, c='orange', s=400, marker='^', 
                       edgecolors='darkorange', linewidths=2, label='Interfering BSs', zorder=3)
            
            for i, (x, y) in enumerate(zip(interferer_x, interferer_y)):
                ax.text(x, y - 8, f'Interferer {i+1}', ha='center', va='top', 
                        fontsize=10, fontweight='bold', color='darkorange',
                        bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='darkorange', linewidth=1.5))
    
    # Draw coverage circle (optional visualization)
    circle_main = plt.Circle((bs_pos[0], bs_pos[1]), 100, color='red', fill=False, 
                             linestyle='--', linewidth=2, alpha=0.3, label='~100m radius')
    ax.add_patch(circle_main)
    
    # Formatting
    ax.set_xlabel('X Position (m)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Y Position (m)', fontsize=13, fontweight='bold')
    ax.set_title(f'Spatial Layout: {grid_size}x{grid_size} Grid with Base Stations\n{config["channel"]["scenario"]}', 
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=11, framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle=':')
    ax.set_aspect('equal', adjustable='box')
    
    # Set reasonable axis limits
    all_x = grid_x + [bs_pos[0]]
    all_y = grid_y + [bs_pos[1]]
    if config['base_station']['interferers']['enabled'] and config['base_station']['interferers']['positions']:
        all_x.extend([pos[0] for pos in config['base_station']['interferers']['positions']])
        all_y.extend([pos[1] for pos in config['base_station']['interferers']['positions']])
    
    margin = 20
    ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
    ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'spatial_layout.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("[OK] Created spatial_layout.png")


def extract_metrics_from_npz(data):
    """Extract available metrics from npz file"""
    metrics = []
    metric_display_names = []
    
    # Check which metrics are present
    for metric_key, display_name in [('rss', 'RSS'), ('sinr', 'SINR'), ('cqi', 'CQI')]:
        if f'{metric_key}_static_acc' in data:
            metrics.append(metric_key)
            metric_display_names.append(display_name)
    
    return metrics, metric_display_names


def plot_metrics_comparison(data, config, output_dir):
    """Compare accuracy and MAE across all metrics and history lengths"""
    metrics, metric_display_names = extract_metrics_from_npz(data)
    
    if not metrics:
        print("[WARNING] No metrics found in results file")
        return
    
    # Collect data for all metrics and history lengths
    static_acc = []
    trans_h1_acc = []
    trans_h2_acc = []
    trans_h3_acc = []
    
    static_mae = []
    trans_h1_mae = []
    trans_h2_mae = []
    trans_h3_mae = []
    
    for metric_key in metrics:
        static_acc.append(float(data[f'{metric_key}_static_acc']))
        static_mae.append(float(data[f'{metric_key}_static_mae']))
        
        # Check available history lengths
        if f'{metric_key}_trans_h1_acc' in data:
            trans_h1_acc.append(float(data[f'{metric_key}_trans_h1_acc']))
            trans_h1_mae.append(float(data[f'{metric_key}_trans_h1_mae']))
        else:
            trans_h1_acc.append(None)
            trans_h1_mae.append(None)
        
        if f'{metric_key}_trans_h2_acc' in data:
            trans_h2_acc.append(float(data[f'{metric_key}_trans_h2_acc']))
            trans_h2_mae.append(float(data[f'{metric_key}_trans_h2_mae']))
        else:
            trans_h2_acc.append(None)
            trans_h2_mae.append(None)
        
        if f'{metric_key}_trans_h3_acc' in data:
            trans_h3_acc.append(float(data[f'{metric_key}_trans_h3_acc']))
            trans_h3_mae.append(float(data[f'{metric_key}_trans_h3_mae']))
        else:
            trans_h3_acc.append(None)
            trans_h3_mae.append(None)
    
    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # ===== Accuracy Comparison =====
    x = np.arange(len(metrics))
    width = 0.18  # Narrower bars for 5 groups
    
    # Plot bars for each configuration
    bars_static = ax1.bar(x - 2*width, static_acc, width, label='Static', 
                          color='steelblue', alpha=0.8)
    
    if any(v is not None for v in trans_h1_acc):
        bars_h1 = ax1.bar(x - width, trans_h1_acc, width, label='Trans (h=1)', 
                         color='forestgreen', alpha=0.8)
    
    if any(v is not None for v in trans_h2_acc):
        bars_h2 = ax1.bar(x, trans_h2_acc, width, label='Trans (h=2)', 
                         color='mediumseagreen', alpha=0.8)
    
    if any(v is not None for v in trans_h3_acc):
        bars_h3 = ax1.bar(x + width, trans_h3_acc, width, label='Trans (h=3)', 
                         color='limegreen', alpha=0.8)
    
    # Best improvement bar
    best_acc = []
    for i in range(len(metrics)):
        vals = [static_acc[i]]
        if trans_h1_acc[i] is not None: vals.append(trans_h1_acc[i])
        if trans_h2_acc[i] is not None: vals.append(trans_h2_acc[i])
        if trans_h3_acc[i] is not None: vals.append(trans_h3_acc[i])
        best_acc.append(max(vals))
    
    bars_best = ax1.bar(x + 2*width, best_acc, width, label='Best', 
                       color='gold', alpha=0.8, edgecolor='orange', linewidth=2)
    
    ax1.set_xlabel('Metric', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Accuracy (%)', fontsize=13, fontweight='bold')
    ax1.set_title('Classification Accuracy Comparison', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metric_display_names, fontsize=12)
    ax1.legend(fontsize=10, loc='upper left')
    ax1.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bars in [bars_static, bars_best]:
        if bars:
            for bar in bars:
                if bar.get_height() > 0:
                    ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                            f'{bar.get_height():.1f}%', ha='center', va='bottom', 
                            fontsize=8, fontweight='bold')
    
    # Add improvement annotations
    for i in range(len(metrics)):
        improvement = best_acc[i] - static_acc[i]
        if improvement > 0:
            y_pos = best_acc[i] + 1
            ax1.text(x[i] + 2*width, y_pos, f'+{improvement:.1f}%',
                    ha='center', va='bottom', fontsize=9, fontweight='bold', 
                    color='darkgreen')
    
    # ===== MAE Comparison =====
    bars_mae_static = ax2.bar(x - 2*width, static_mae, width, label='Static', 
                              color='steelblue', alpha=0.8)
    
    if any(v is not None for v in trans_h1_mae):
        bars_mae_h1 = ax2.bar(x - width, trans_h1_mae, width, label='Trans (h=1)', 
                             color='forestgreen', alpha=0.8)
    
    if any(v is not None for v in trans_h2_mae):
        bars_mae_h2 = ax2.bar(x, trans_h2_mae, width, label='Trans (h=2)', 
                             color='mediumseagreen', alpha=0.8)
    
    if any(v is not None for v in trans_h3_mae):
        bars_mae_h3 = ax2.bar(x + width, trans_h3_mae, width, label='Trans (h=3)', 
                             color='limegreen', alpha=0.8)
    
    # Best (lowest) MAE bar
    best_mae = []
    for i in range(len(metrics)):
        vals = [static_mae[i]]
        if trans_h1_mae[i] is not None: vals.append(trans_h1_mae[i])
        if trans_h2_mae[i] is not None: vals.append(trans_h2_mae[i])
        if trans_h3_mae[i] is not None: vals.append(trans_h3_mae[i])
        best_mae.append(min(vals))
    
    bars_mae_best = ax2.bar(x + 2*width, best_mae, width, label='Best', 
                           color='gold', alpha=0.8, edgecolor='orange', linewidth=2)
    
    ax2.set_xlabel('Metric', fontsize=13, fontweight='bold')
    ax2.set_ylabel('MAE (meters)', fontsize=13, fontweight='bold')
    ax2.set_title('Mean Absolute Error Comparison', fontsize=14, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(metric_display_names, fontsize=12)
    ax2.legend(fontsize=10, loc='upper left')
    ax2.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bars in [bars_mae_static, bars_mae_best]:
        if bars:
            for bar in bars:
                if bar.get_height() > 0:
                    ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                            f'{bar.get_height():.2f}', ha='center', va='bottom', 
                            fontsize=8, fontweight='bold')
    
    # Add improvement annotations (negative = better for MAE)
    for i in range(len(metrics)):
        improvement = static_mae[i] - best_mae[i]  # Positive = improvement
        if improvement > 0:
            y_pos = max(static_mae[i], best_mae[i]) + 0.3
            ax2.text(x[i] + 2*width, y_pos, f'-{improvement:.2f}m',
                    ha='center', va='bottom', fontsize=9, fontweight='bold', 
                    color='darkgreen')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'metrics_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("[OK] Created metrics_comparison.png")


def plot_history_progression(data, config, output_dir):
    """Plot accuracy vs history length for each metric"""
    metrics, metric_display_names = extract_metrics_from_npz(data)
    
    if not metrics:
        print("[WARNING] No metrics found in results file")
        return
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Blue, Orange, Green
    markers = ['o', 's', '^']
    
    for idx, (metric_key, display_name) in enumerate(zip(metrics, metric_display_names)):
        # Collect data for this metric
        history_lengths = [0]  # 0 = static
        accuracies = [float(data[f'{metric_key}_static_acc'])]
        
        for h in [1, 2, 3]:
            key = f'{metric_key}_trans_h{h}_acc'
            if key in data:
                history_lengths.append(h)
                accuracies.append(float(data[key]))
        
        # Plot line
        ax.plot(history_lengths, accuracies, marker=markers[idx], 
               markersize=10, linewidth=2.5, label=display_name, 
               color=colors[idx], alpha=0.8)
        
        # Add value labels
        for h, acc in zip(history_lengths, accuracies):
            ax.text(h, acc + 0.5, f'{acc:.1f}%', ha='center', va='bottom',
                   fontsize=9, fontweight='bold', color=colors[idx])
    
    ax.set_xlabel('History Length', fontsize=13, fontweight='bold')
    ax.set_ylabel('Accuracy (%)', fontsize=13, fontweight='bold')
    ax.set_title('Accuracy vs History Length', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='lower right')
    ax.grid(True, alpha=0.3)
    ax.set_xticks([0, 1, 2, 3])
    ax.set_xticklabels(['Static', 'h=1', 'h=2', 'h=3'])
    
    plt.tight_layout()
    plt.savefig(output_dir / 'history_progression.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("[OK] Created history_progression.png")


def main():
    if len(sys.argv) < 2:
        print("Usage: python plot_pipeline_results.py <results_directory>")
        print("\nNote: Use results directory (exp13e_*), not simulation directory (sim_data_*)")
        sys.exit(1)
    
    results_dir = Path(sys.argv[1])
    
    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}")
        sys.exit(1)
    
    print(f"\n{'='*70}")
    print(f"Generating plots for: {results_dir.name}")
    print(f"{'='*70}\n")
    
    # Load data
    print("Loading results...")
    try:
        data, config = load_results(results_dir)
        grid_size = config['grid']['size']
        print(f"[OK] Loaded results for {grid_size}x{grid_size} grid\n")
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    
    # Generate plots
    print("Generating plots...")
    plot_spatial_layout(data, config, results_dir)
    plot_metrics_comparison(data, config, results_dir)
    plot_history_progression(data, config, results_dir)
    
    print(f"\n{'='*70}")
    print(f"[SUCCESS] All plots saved to: {results_dir}")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
