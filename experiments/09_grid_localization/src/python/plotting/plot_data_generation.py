"""
Plot Data Generation Metrics

This script generates visualizations for the simulation data immediately after generation.
It creates plots for metric distributions, spatial coverage, and walk path analysis.

Usage:
    python plot_data_generation.py <sim_data_directory>
"""

import sys
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy.io import loadmat
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.read_jsonc import read_jsonc

sns.set_style('whitegrid')
plt.rcParams['figure.max_open_warning'] = 50  # Suppress warnings for many plots


def load_simulation_data(data_dir):
    """Load simulation data from MATLAB .mat file"""
    data_dir = Path(data_dir)
    
    # Load raw simulation data
    sim_file = data_dir / 'simulation_data.mat'
    if not sim_file.exists():
        raise FileNotFoundError(f"Simulation data not found: {sim_file}")
    
    print(f"Loading simulation data from: {sim_file}")
    data = loadmat(str(sim_file), squeeze_me=True, struct_as_record=False)
    
    # Load configuration from data directory
    # Handle both old (config.json) and new (data_generation_config.jsonc) filenames
    config_file = data_dir / 'data_generation_config.jsonc'
    if not config_file.exists():
        config_file = data_dir / 'config.jsonc'
    if not config_file.exists():
        config_file = data_dir / 'config.json'
    config = read_jsonc(config_file) if config_file.suffix == '.jsonc' else json.load(open(config_file))
    
    return data, config


def plot_metric_distributions(metrics_data, config, output_dir):
    """Plot distributions of all available metrics"""
    
    # Determine available metrics
    available_metrics = []
    metric_info = {}
    
    if hasattr(metrics_data, 'rss_wb'):
        available_metrics.append('RSS')
        metric_info['RSS'] = {'data': metrics_data.rss_wb, 'unit': 'dBm', 'color': 'blue'}
    
    if hasattr(metrics_data, 'sinr_wb'):
        available_metrics.append('SINR')
        metric_info['SINR'] = {'data': metrics_data.sinr_wb, 'unit': 'dB', 'color': 'green'}
    
    if hasattr(metrics_data, 'cqi_wb'):
        available_metrics.append('CQI')
        metric_info['CQI'] = {'data': metrics_data.cqi_wb, 'unit': '', 'color': 'orange'}
    
    if hasattr(metrics_data, 'aoa_azimuth'):
        available_metrics.append('AoA Azimuth')
        metric_info['AoA Azimuth'] = {'data': metrics_data.aoa_azimuth, 'unit': '°', 'color': 'purple'}
    
    if hasattr(metrics_data, 'aoa_elevation'):
        available_metrics.append('AoA Elevation')
        metric_info['AoA Elevation'] = {'data': metrics_data.aoa_elevation, 'unit': '°', 'color': 'magenta'}
    
    if hasattr(metrics_data, 'timing_advance'):
        available_metrics.append('Timing Advance')
        metric_info['Timing Advance'] = {'data': metrics_data.timing_advance, 'unit': 'µs', 'color': 'brown'}
    
    n_metrics = len(available_metrics)
    
    # Create subplot grid
    n_cols = 3
    n_rows = (n_metrics + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 5 * n_rows))
    if n_rows == 1:
        axes = axes.reshape(1, -1)
    
    for idx, metric_name in enumerate(available_metrics):
        row = idx // n_cols
        col = idx % n_cols
        ax = axes[row, col]
        
        data = metric_info[metric_name]['data']
        unit = metric_info[metric_name]['unit']
        color = metric_info[metric_name]['color']
        
        # Histogram with KDE
        ax.hist(data, bins=50, density=True, alpha=0.6, color=color, edgecolor='black')
        
        # Add KDE overlay
        from scipy.stats import gaussian_kde
        if len(np.unique(data)) > 1:  # Only if not constant
            kde = gaussian_kde(data)
            x_range = np.linspace(data.min(), data.max(), 200)
            ax.plot(x_range, kde(x_range), linewidth=2, color='darkred', label='KDE')
        
        # Statistics text box
        stats_text = f'Mean: {np.mean(data):.2f}{unit}\nStd: {np.std(data):.2f}{unit}\nMin: {np.min(data):.2f}{unit}\nMax: {np.max(data):.2f}{unit}'
        ax.text(0.98, 0.97, stats_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        ax.set_xlabel(f'{metric_name} {f"({unit})" if unit else ""}', fontsize=12, fontweight='bold')
        ax.set_ylabel('Probability Density', fontsize=12)
        ax.set_title(f'{metric_name} Distribution', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
    
    # Hide unused subplots
    for idx in range(n_metrics, n_rows * n_cols):
        row = idx // n_cols
        col = idx % n_cols
        axes[row, col].axis('off')
    
    scenario = config['channel']['scenario']
    grid_size = config['grid']['size']
    fig.suptitle(f'Metric Distributions - {grid_size}x{grid_size} Grid - {scenario}', 
                 fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    output_file = output_dir / 'metric_distributions.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"[SAVED] {output_file}")
    plt.close()


def plot_walk_path_visualization(walk_path, grid_positions, config, output_dir):
    """Visualize the random walk path on the grid"""
    
    grid_size = config['grid']['size']
    walk_indices = walk_path.grid_point_indices
    
    # Create figure
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    
    # --- Left plot: Visit count heatmap ---
    ax = axes[0]
    
    # Count visits to each grid point
    visit_counts = np.bincount(walk_indices - 1, minlength=grid_size**2)
    visit_grid = visit_counts.reshape(grid_size, grid_size)
    
    # Plot heatmap
    im = ax.imshow(visit_grid, cmap='YlOrRd', aspect='auto', origin='lower')
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Visit Count', fontsize=12, fontweight='bold')
    
    # Add text annotations
    for i in range(grid_size):
        for j in range(grid_size):
            idx = i * grid_size + j
            text = ax.text(j, i, f'{visit_counts[idx]}', ha='center', va='center',
                          color='white' if visit_counts[idx] > visit_counts.max()/2 else 'black',
                          fontsize=9, fontweight='bold')
    
    ax.set_xlabel('Grid Column', fontsize=12, fontweight='bold')
    ax.set_ylabel('Grid Row', fontsize=12, fontweight='bold')
    ax.set_title(f'Visit Count Heatmap\n(Total: {len(walk_indices)} samples)', fontsize=13, fontweight='bold')
    ax.set_xticks(range(grid_size))
    ax.set_yticks(range(grid_size))
    
    # --- Right plot: Walk trajectory (first 1000 steps) ---
    ax = axes[1]
    
    # Extract positions (use jittered for actual trajectory)
    positions = walk_path.positions_jittered
    n_plot = min(1000, len(positions))
    
    # Plot trajectory
    ax.plot(positions[:n_plot, 0], positions[:n_plot, 1], 
            'b-', alpha=0.3, linewidth=0.5, label='Walk Path')
    ax.scatter(positions[0, 0], positions[0, 1], 
               c='green', s=200, marker='o', edgecolors='darkgreen', 
               linewidths=2, label='Start', zorder=5)
    ax.scatter(positions[n_plot-1, 0], positions[n_plot-1, 1], 
               c='red', s=200, marker='X', edgecolors='darkred', 
               linewidths=2, label='End (t=1000)', zorder=5)
    
    # Plot grid points
    ax.scatter(grid_positions[:, 0], grid_positions[:, 1], 
               c='lightgray', s=100, marker='s', alpha=0.5, 
               edgecolors='gray', linewidths=1, label='Grid Points', zorder=1)
    
    # Plot BS
    bs_pos = config['base_station']['position']
    ax.scatter(bs_pos[0], bs_pos[1], c='orange', s=300, marker='^', 
               edgecolors='darkorange', linewidths=2, label='Base Station', zorder=6)
    
    ax.set_xlabel('X Position (m)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Y Position (m)', fontsize=12, fontweight='bold')
    ax.set_title(f'Random Walk Trajectory\n(First {n_plot} steps)', fontsize=13, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal', adjustable='box')
    
    scenario = config['channel']['scenario']
    fig.suptitle(f'Walk Path Analysis - {grid_size}x{grid_size} Grid - {scenario}', 
                 fontsize=16, fontweight='bold')
    plt.tight_layout()
    
    output_file = output_dir / 'walk_path_analysis.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"[SAVED] {output_file}")
    plt.close()


def plot_spatial_coverage(walk_path, grid_positions, metrics_data, config, output_dir):
    """Plot spatial coverage and metric variations across grid"""
    
    grid_size = config['grid']['size']
    walk_indices = walk_path.grid_point_indices
    
    # Create figure with subplots for each metric
    metrics_to_plot = []
    if hasattr(metrics_data, 'rss_wb'):
        metrics_to_plot.append(('RSS', metrics_data.rss_wb, 'dBm', 'Blues'))
    if hasattr(metrics_data, 'sinr_wb'):
        metrics_to_plot.append(('SINR', metrics_data.sinr_wb, 'dB', 'Greens'))
    if hasattr(metrics_data, 'aoa_azimuth'):
        metrics_to_plot.append(('AoA Azimuth', metrics_data.aoa_azimuth, '°', 'Purples'))
    
    n_metrics = len(metrics_to_plot)
    n_cols = 3
    n_rows = (n_metrics + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 6 * n_rows))
    if n_rows == 1:
        axes = axes.reshape(1, -1)
    
    for idx, (metric_name, metric_data, unit, cmap) in enumerate(metrics_to_plot):
        row = idx // n_cols
        col = idx % n_cols
        ax = axes[row, col]
        
        # Compute average metric value at each grid point
        avg_metric = np.zeros(grid_size**2)
        for point_idx in range(grid_size**2):
            samples_at_point = metric_data[walk_indices == point_idx + 1]
            if len(samples_at_point) > 0:
                avg_metric[point_idx] = np.mean(samples_at_point)
        
        # Reshape to grid
        metric_grid = avg_metric.reshape(grid_size, grid_size)
        
        # Plot heatmap
        im = ax.imshow(metric_grid, cmap=cmap, aspect='auto', origin='lower')
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label(f'{metric_name} ({unit})', fontsize=11, fontweight='bold')
        
        # Add text annotations
        for i in range(grid_size):
            for j in range(grid_size):
                idx_flat = i * grid_size + j
                text = ax.text(j, i, f'{avg_metric[idx_flat]:.1f}', ha='center', va='center',
                              color='white' if avg_metric[idx_flat] > (avg_metric.max() + avg_metric.min())/2 else 'black',
                              fontsize=8)
        
        ax.set_xlabel('Grid Column', fontsize=11, fontweight='bold')
        ax.set_ylabel('Grid Row', fontsize=11, fontweight='bold')
        ax.set_title(f'Average {metric_name} per Grid Point', fontsize=12, fontweight='bold')
        ax.set_xticks(range(grid_size))
        ax.set_yticks(range(grid_size))
    
    # Hide unused subplots
    for idx in range(n_metrics, n_rows * n_cols):
        row = idx // n_cols
        col = idx % n_cols
        axes[row, col].axis('off')
    
    scenario = config['channel']['scenario']
    fig.suptitle(f'Spatial Metric Distribution - {grid_size}x{grid_size} Grid - {scenario}', 
                 fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    output_file = output_dir / 'spatial_coverage.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"[SAVED] {output_file}")
    plt.close()


def plot_temporal_evolution(metrics_data, config, output_dir):
    """Plot temporal evolution of metrics (first 2000 samples)"""
    
    n_samples = min(2000, len(metrics_data.rss_wb))
    time_steps = np.arange(n_samples)
    
    # Determine available metrics
    metrics_to_plot = []
    if hasattr(metrics_data, 'rss_wb'):
        metrics_to_plot.append(('RSS', metrics_data.rss_wb[:n_samples], 'dBm', 'blue'))
    if hasattr(metrics_data, 'sinr_wb'):
        metrics_to_plot.append(('SINR', metrics_data.sinr_wb[:n_samples], 'dB', 'green'))
    if hasattr(metrics_data, 'aoa_azimuth'):
        metrics_to_plot.append(('AoA Azimuth', metrics_data.aoa_azimuth[:n_samples], '°', 'purple'))
    if hasattr(metrics_data, 'timing_advance'):
        metrics_to_plot.append(('Timing Advance', metrics_data.timing_advance[:n_samples], 'µs', 'brown'))
    
    n_metrics = len(metrics_to_plot)
    
    fig, axes = plt.subplots(n_metrics, 1, figsize=(16, 3 * n_metrics), sharex=True)
    if n_metrics == 1:
        axes = [axes]
    
    for idx, (metric_name, metric_data, unit, color) in enumerate(metrics_to_plot):
        ax = axes[idx]
        
        ax.plot(time_steps, metric_data, color=color, alpha=0.7, linewidth=0.8)
        ax.set_ylabel(f'{metric_name} ({unit})', fontsize=11, fontweight='bold')
        ax.set_title(f'{metric_name} Temporal Evolution', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Add running average
        window = 50
        if len(metric_data) >= window:
            running_avg = np.convolve(metric_data, np.ones(window)/window, mode='valid')
            ax.plot(time_steps[window-1:], running_avg, color='red', linewidth=2, 
                   label=f'{window}-sample MA')
            ax.legend(loc='upper right')
    
    axes[-1].set_xlabel('Sample Index', fontsize=12, fontweight='bold')
    
    scenario = config['channel']['scenario']
    grid_size = config['grid']['size']
    fig.suptitle(f'Temporal Metric Evolution - {grid_size}x{grid_size} Grid - {scenario}', 
                 fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    output_file = output_dir / 'temporal_evolution.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"[SAVED] {output_file}")
    plt.close()


def plot_grid_bs_map(grid_positions, config, output_dir):
    """Plot a map showing the grid and all base station locations"""
    
    grid_size = config['grid']['size']
    
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    
    # Plot grid points
    ax.scatter(grid_positions[:, 0], grid_positions[:, 1], 
               c='lightblue', s=150, marker='s', alpha=0.7, 
               edgecolors='darkblue', linewidths=1.5, label='Grid Points', zorder=2)
    
    # Draw grid boundary
    x_min, x_max = grid_positions[:, 0].min(), grid_positions[:, 0].max()
    y_min, y_max = grid_positions[:, 1].min(), grid_positions[:, 1].max()
    margin = config['grid']['spacing']
    
    from matplotlib.patches import Rectangle
    grid_rect = Rectangle((x_min - margin/2, y_min - margin/2), 
                          x_max - x_min + margin, 
                          y_max - y_min + margin,
                          linewidth=2, edgecolor='darkblue', 
                          facecolor='none', linestyle='--', 
                          label='Grid Boundary', zorder=1)
    ax.add_patch(grid_rect)
    
    # Plot main base station
    bs_pos = config['base_station']['position']
    ax.scatter(bs_pos[0], bs_pos[1], c='red', s=500, marker='^', 
               edgecolors='darkred', linewidths=3, label='Main BS', zorder=5)
    
    # Add BS label with height
    ax.text(bs_pos[0], bs_pos[1] - 3, f'Main BS\n({bs_pos[0]}, {bs_pos[1]}, {bs_pos[2]}m)', 
            ha='center', va='top', fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='red', alpha=0.3))
    
    # Calculate and display distance from main BS to grid center
    grid_center = np.mean(grid_positions, axis=0)
    dist_to_center = np.sqrt((bs_pos[0] - grid_center[0])**2 + (bs_pos[1] - grid_center[1])**2)
    ax.plot([bs_pos[0], grid_center[0]], [bs_pos[1], grid_center[1]], 
            'r--', alpha=0.5, linewidth=1.5, zorder=1)
    mid_x, mid_y = (bs_pos[0] + grid_center[0])/2, (bs_pos[1] + grid_center[1])/2
    ax.text(mid_x, mid_y, f'{dist_to_center:.1f}m', 
            ha='center', va='bottom', fontsize=9, color='red', fontweight='bold')
    
    # Plot interfering base stations if enabled
    if config['base_station']['interferers']['enabled']:
        interferer_positions = config['base_station']['interferers']['positions']
        colors = ['orange', 'purple', 'green', 'brown', 'pink']  # Support up to 5 interferers
        
        for idx, int_pos in enumerate(interferer_positions):
            color = colors[idx % len(colors)]
            ax.scatter(int_pos[0], int_pos[1], c=color, s=400, marker='v', 
                      edgecolors='black', linewidths=2, 
                      label=f'Interferer {idx+1}', zorder=4)
            
            # Add interferer label
            ax.text(int_pos[0], int_pos[1] - 3, f'Int-{idx+1}\n({int_pos[0]}, {int_pos[1]}, {int_pos[2]}m)', 
                   ha='center', va='top', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.4', facecolor=color, alpha=0.3))
            
            # Calculate and display distance from interferer to grid center
            dist_int_to_center = np.sqrt((int_pos[0] - grid_center[0])**2 + 
                                        (int_pos[1] - grid_center[1])**2)
            ax.plot([int_pos[0], grid_center[0]], [int_pos[1], grid_center[1]], 
                   color=color, linestyle=':', alpha=0.4, linewidth=1.5, zorder=1)
    
    # Mark grid center
    ax.scatter(grid_center[0], grid_center[1], c='yellow', s=200, marker='*', 
              edgecolors='black', linewidths=2, label='Grid Center', zorder=3)
    
    # Set labels and title
    ax.set_xlabel('X Position (m)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Y Position (m)', fontsize=13, fontweight='bold')
    ax.set_title(f'Grid and Base Station Layout Map\n{grid_size}x{grid_size} Grid', 
                fontsize=15, fontweight='bold')
    ax.legend(loc='best', fontsize=11, framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_aspect('equal', adjustable='box')
    
    # Add info box with grid details
    info_text = f'Grid Size: {grid_size}x{grid_size}\n'
    info_text += f'Grid Spacing: {config["grid"]["spacing"]}m\n'
    info_text += f'Grid Offset: {config["grid"]["grid_offset"]}\n'
    info_text += f'UE Height: {config["grid"]["ue_height"]}m\n'
    info_text += f'BS Height: {bs_pos[2]}m'
    
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='left',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    
    output_file = output_dir / 'grid_bs_layout_map.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"[SAVED] {output_file}")
    plt.close()


def main():
    if len(sys.argv) != 2:
        print("Usage: python plot_data_generation.py <sim_data_directory>")
        sys.exit(1)
    
    data_dir = Path(sys.argv[1])
    
    if not data_dir.exists():
        print(f"Error: Directory not found: {data_dir}")
        sys.exit(1)
    
    print(f"\n{'='*70}")
    print(f"DATA GENERATION VISUALIZATION")
    print(f"{'='*70}")
    print(f"Data directory: {data_dir}\n")
    
    # Load data
    data, config = load_simulation_data(data_dir)
    
    # Create output directory for plots
    output_dir = data_dir / 'plots'
    output_dir.mkdir(exist_ok=True)
    
    print(f"Generating plots...\n")
    
    # Generate all plots
    print("[1/6] Plotting metric distributions...")
    plot_metric_distributions(data['metrics'], config, output_dir)
    
    print("[2/6] Plotting walk path analysis...")
    plot_walk_path_visualization(data['walk_path'], data['config'].grid_positions, 
                                  config, output_dir)
    
    print("[3/6] Plotting spatial coverage...")
    plot_spatial_coverage(data['walk_path'], data['config'].grid_positions, 
                          data['metrics'], config, output_dir)
    
    print("[4/6] Plotting temporal evolution...")
    plot_temporal_evolution(data['metrics'], config, output_dir)
    
    print("[5/6] Plotting grid and base station layout map...")
    plot_grid_bs_map(data['config'].grid_positions, config, output_dir)
    
    print("\n" + "="*70)
    print(f"All plots saved to: {output_dir}")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
