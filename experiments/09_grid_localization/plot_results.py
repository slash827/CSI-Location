"""
Grid Localization Results Visualization

Generates comprehensive plots for static vs transition-based localization experiments.
Called from MATLAB after experiment completion.

Usage from MATLAB:
    system('python plot_results.py <results_dir>');
"""

import sys
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy.io import loadmat

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def load_results(results_dir):
    """Load experiment results from MATLAB .mat file"""
    results_dir = Path(results_dir)
    mat_file = results_dir / 'corrected_comparison_results.mat'
    
    if not mat_file.exists():
        raise FileNotFoundError(f"Results file not found: {mat_file}")
    
    data = loadmat(str(mat_file), squeeze_me=True, struct_as_record=False)
    
    # Load config
    config_file = results_dir / 'experiment_config.json'
    with open(config_file, 'r') as f:
        config_json = json.load(f)
    
    # Flatten config structure for easier access
    # Handle both new (steps_per_point) and legacy (n_steps) config formats
    grid_size = config_json['grid']['size']
    if 'steps_per_point' in config_json['movement']:
        steps_per_point = config_json['movement']['steps_per_point']
        n_steps = steps_per_point * grid_size * grid_size
    elif 'n_steps' in config_json['movement']:
        n_steps = config_json['movement']['n_steps']
    else:
        n_steps = 0  # fallback if neither exists
    
    config = {
        'grid_size': grid_size,
        'spacing': config_json['grid']['spacing'],
        'scenario': config_json['channel']['scenario'],
        'n_steps': n_steps,
        'grid_offset': config_json['grid']['grid_offset'],
        'bs_position': config_json['base_station']['position'],
        'interferers_enabled': config_json['base_station']['interferers']['enabled'],
        'interferer_positions': config_json['base_station']['interferers']['positions'] if config_json['base_station']['interferers']['enabled'] else []
    }
    
    return data, config


def plot_confusion_matrices(data, config, output_dir):
    """Plot confusion matrices for static and transition methods"""
    grid_size = config['grid_size']
    results = data['results']
    
    # Get RSS results (primary metric)
    rss_results = results.rss
    cm_static = rss_results.cm_static
    cm_transition = rss_results.cm_transition
    
    # Check if cm_transition is a list/array (multiple history lengths) or single matrix
    # MATLAB cell arrays become numpy object arrays with shape (n,)
    is_multi_history = (isinstance(cm_transition, np.ndarray) and 
                       cm_transition.dtype == object and 
                       len(cm_transition.shape) == 1)
    
    if is_multi_history:
        # Multiple history lengths - plot all of them
        n_history = len(cm_transition)
        fig, axes = plt.subplots(1, n_history + 1, figsize=(6 * (n_history + 1), 6))
        
        # Static confusion matrix
        cm_static_norm = cm_static / cm_static.sum(axis=1, keepdims=True) * 100
        sns.heatmap(cm_static_norm, annot=True, fmt='.1f', cmap='Blues', 
                    ax=axes[0], vmin=0, vmax=100, cbar_kws={'label': 'Percentage (%)'})
        axes[0].set_title(f'Static Classification\nAccuracy: {rss_results.static_acc:.2f}%', 
                          fontsize=14, fontweight='bold')
        axes[0].set_xlabel('Predicted Location', fontsize=12)
        axes[0].set_ylabel('True Location', fontsize=12)
        
        # Transition confusion matrices for each history length
        for h_idx in range(n_history):
            cm_h = cm_transition[h_idx]
            cm_h_norm = cm_h / cm_h.sum(axis=1, keepdims=True) * 100
            acc_h = rss_results.transition_acc[h_idx]
            improvement = acc_h - rss_results.static_acc
            
            sns.heatmap(cm_h_norm, annot=True, fmt='.1f', cmap='Greens', 
                        ax=axes[h_idx + 1], vmin=0, vmax=100, cbar_kws={'label': 'Percentage (%)'})
            axes[h_idx + 1].set_title(f'Transition (h={h_idx+1})\nAccuracy: {acc_h:.2f}% ({improvement:+.2f}%)', 
                          fontsize=14, fontweight='bold')
            axes[h_idx + 1].set_xlabel('Predicted Location', fontsize=12)
            axes[h_idx + 1].set_ylabel('True Location', fontsize=12)
    else:
        # Single confusion matrix (old format)
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Normalize to percentages
        cm_static_norm = cm_static / cm_static.sum(axis=1, keepdims=True) * 100
        cm_transition_norm = cm_transition / cm_transition.sum(axis=1, keepdims=True) * 100
        
        # Static confusion matrix
        sns.heatmap(cm_static_norm, annot=True, fmt='.1f', cmap='Blues', 
                    ax=axes[0], vmin=0, vmax=100, cbar_kws={'label': 'Percentage (%)'})
        axes[0].set_title(f'Static Classification\nAccuracy: {rss_results.static_acc:.2f}%', 
                          fontsize=14, fontweight='bold')
        axes[0].set_xlabel('Predicted Location', fontsize=12)
        axes[0].set_ylabel('True Location', fontsize=12)
        
        # Transition confusion matrix
        improvement = rss_results.transition_acc - rss_results.static_acc
        sns.heatmap(cm_transition_norm, annot=True, fmt='.1f', cmap='Greens', 
                    ax=axes[1], vmin=0, vmax=100, cbar_kws={'label': 'Percentage (%)'})
        axes[1].set_title(f'Transition-Based Classification\nAccuracy: {rss_results.transition_acc:.2f}% ({improvement:+.2f}%)', 
                          fontsize=14, fontweight='bold')
        axes[1].set_xlabel('Predicted Location', fontsize=12)
        axes[1].set_ylabel('True Location', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'confusion_matrices.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("[OK] Created confusion_matrices.png")


def plot_spatial_error_map(data, config, output_dir):
    """Plot spatial distribution of localization errors"""
    grid_size = config['grid_size']
    results = data['results']
    rss_results = results.rss
    
    # Calculate per-location error rates
    cm_static = rss_results.cm_static
    cm_transition_orig = rss_results.cm_transition
    
    # Use first history length if cm_transition is a list or numpy object array
    if isinstance(cm_transition_orig, np.ndarray) and cm_transition_orig.dtype == object:
        cm_transition = cm_transition_orig[0]  # Use h=1 for spatial error map
    elif isinstance(cm_transition_orig, (list, tuple)):
        cm_transition = cm_transition_orig[0]
    else:
        cm_transition = cm_transition_orig
    
    # Verify it's a 2D matrix
    if len(cm_transition.shape) != 2:
        print(f"Warning: cm_transition has shape {cm_transition.shape}, skipping spatial error map")
        return
    
    # Error rate = (total - correct) / total
    static_errors = np.zeros(grid_size * grid_size)
    transition_errors = np.zeros(grid_size * grid_size)
    
    for i in range(grid_size * grid_size):
        total_static = cm_static[i, :].sum()
        total_transition = cm_transition[i, :].sum()
        
        if total_static > 0:
            static_errors[i] = (total_static - cm_static[i, i]) / total_static * 100
        if total_transition > 0:
            transition_errors[i] = (total_transition - cm_transition[i, i]) / total_transition * 100
    
    # Reshape to grid
    static_grid = static_errors.reshape(grid_size, grid_size)
    transition_grid = transition_errors.reshape(grid_size, grid_size)
    improvement_grid = static_grid - transition_grid
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # Static errors
    im1 = axes[0].imshow(static_grid, cmap='Reds', origin='lower', vmin=0, vmax=100)
    axes[0].set_title('Static Method\nError Rate per Location', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Grid X', fontsize=12)
    axes[0].set_ylabel('Grid Y', fontsize=12)
    plt.colorbar(im1, ax=axes[0], label='Error Rate (%)')
    
    # Add text annotations
    for i in range(grid_size):
        for j in range(grid_size):
            text = axes[0].text(j, i, f'{static_grid[i, j]:.1f}',
                               ha="center", va="center", color="black", fontsize=10)
    
    # Transition errors
    im2 = axes[1].imshow(transition_grid, cmap='Greens_r', origin='lower', vmin=0, vmax=100)
    axes[1].set_title('Transition Method\nError Rate per Location', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('Grid X', fontsize=12)
    axes[1].set_ylabel('Grid Y', fontsize=12)
    plt.colorbar(im2, ax=axes[1], label='Error Rate (%)')
    
    for i in range(grid_size):
        for j in range(grid_size):
            text = axes[1].text(j, i, f'{transition_grid[i, j]:.1f}',
                               ha="center", va="center", color="black", fontsize=10)
    
    # Improvement (positive = transition better)
    max_abs = max(abs(improvement_grid.min()), abs(improvement_grid.max()))
    im3 = axes[2].imshow(improvement_grid, cmap='RdYlGn', origin='lower', 
                        vmin=-max_abs, vmax=max_abs)
    axes[2].set_title('Improvement\n(Positive = Transition Better)', fontsize=14, fontweight='bold')
    axes[2].set_xlabel('Grid X', fontsize=12)
    axes[2].set_ylabel('Grid Y', fontsize=12)
    plt.colorbar(im3, ax=axes[2], label='Error Reduction (%)')
    
    for i in range(grid_size):
        for j in range(grid_size):
            color = 'black' if abs(improvement_grid[i, j]) < max_abs * 0.5 else 'white'
            text = axes[2].text(j, i, f'{improvement_grid[i, j]:+.1f}',
                               ha="center", va="center", color=color, fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'spatial_error_map.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("[OK] Created spatial_error_map.png")


def plot_metrics_comparison(data, config, output_dir):
    """Compare accuracy and MAE across all metrics"""
    results = data['results']
    
    metrics = ['RSS', 'SINR', 'CQI']
    metric_fields = ['rss', 'sinr', 'cqi']
    
    static_acc = []
    transition_acc = []
    static_mae = []
    transition_mae = []
    
    for field in metric_fields:
        metric_data = getattr(results, field)
        static_acc.append(metric_data.static_acc)
        # Use first history length if transition_acc is an array
        trans_acc = metric_data.transition_acc
        transition_acc.append(trans_acc[0] if isinstance(trans_acc, (list, np.ndarray)) else trans_acc)
        static_mae.append(metric_data.mae_static)
        # Use first history length if mae_transition is an array
        trans_mae = metric_data.mae_transition
        transition_mae.append(trans_mae[0] if isinstance(trans_mae, (list, np.ndarray)) else trans_mae)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Accuracy comparison
    x = np.arange(len(metrics))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, static_acc, width, label='Static', color='steelblue', alpha=0.8)
    bars2 = ax1.bar(x + width/2, transition_acc, width, label='Transition', color='forestgreen', alpha=0.8)
    
    ax1.set_xlabel('Metric', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Classification Accuracy Comparison', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics)
    ax1.legend(fontsize=11)
    ax1.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
    
    # MAE comparison
    bars3 = ax2.bar(x - width/2, static_mae, width, label='Static', color='steelblue', alpha=0.8)
    bars4 = ax2.bar(x + width/2, transition_mae, width, label='Transition', color='forestgreen', alpha=0.8)
    
    ax2.set_xlabel('Metric', fontsize=12, fontweight='bold')
    ax2.set_ylabel('MAE (grid points)', fontsize=12, fontweight='bold')
    ax2.set_title('Mean Absolute Error Comparison', fontsize=14, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(metrics)
    ax2.legend(fontsize=11)
    ax2.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars and percentage improvement
    for i, bars in enumerate([bars3, bars4]):
        for j, bar in enumerate(bars):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.3f}', ha='center', va='bottom', fontsize=9)
    
    # Add improvement percentage labels between bars
    for j in range(len(metrics)):
        if static_mae[j] > 0:
            improvement_pct = (static_mae[j] - transition_mae[j]) / static_mae[j] * 100
            y_pos = max(static_mae[j], transition_mae[j]) * 1.05
            color = 'green' if improvement_pct > 0 else 'red'
            ax2.text(x[j], y_pos, f'{improvement_pct:+.1f}%',
                    ha='center', va='bottom', fontsize=9, fontweight='bold', color=color)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'metrics_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("[OK] Created metrics_comparison.png")


def plot_visit_distribution(data, config, output_dir):
    """Plot random walk visit distribution across grid points"""
    grid_size = config['grid_size']
    walk_path = data['walk_path']
    
    # Count visits
    visit_counts = np.bincount(walk_path.astype(int) - 1, minlength=grid_size*grid_size)
    visit_grid = visit_counts.reshape(grid_size, grid_size)
    
    fig, ax = plt.subplots(figsize=(8, 7))
    
    im = ax.imshow(visit_grid, cmap='viridis', origin='lower')
    ax.set_title(f'Random Walk Visit Distribution\nTotal Steps: {len(walk_path)-1}', 
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('Grid X', fontsize=12)
    ax.set_ylabel('Grid Y', fontsize=12)
    plt.colorbar(im, ax=ax, label='Number of Visits')
    
    # Add text annotations
    for i in range(grid_size):
        for j in range(grid_size):
            text = ax.text(j, i, f'{int(visit_grid[i, j])}',
                          ha="center", va="center", 
                          color="white" if visit_grid[i, j] > visit_grid.max()/2 else "black",
                          fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'visit_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("[OK] Created visit_distribution.png")


def plot_rss_distributions(data, config, output_dir):
    """Plot RSS distributions per grid location"""
    grid_size = config['grid_size']
    walk_path = data['walk_path'].astype(int)
    rss_values = data['metrics'].RSS_wb
    
    # Collect RSS per location
    rss_per_location = []
    for loc in range(1, grid_size*grid_size + 1):
        mask = (walk_path == loc)
        rss_per_location.append(rss_values[mask])
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    positions = np.arange(1, grid_size*grid_size + 1)
    bp = ax.boxplot(rss_per_location, positions=positions, widths=0.6,
                     patch_artist=True, showfliers=False)
    
    # Color boxes
    for patch in bp['boxes']:
        patch.set_facecolor('lightblue')
        patch.set_alpha(0.7)
    
    ax.set_xlabel('Grid Location', fontsize=12, fontweight='bold')
    ax.set_ylabel('RSS (dB)', fontsize=12, fontweight='bold')
    ax.set_title('RSS Distribution per Grid Location', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    # Add mean values
    means = [np.mean(rss) for rss in rss_per_location]
    ax.plot(positions, means, 'ro-', label='Mean', linewidth=2, markersize=6)
    ax.legend(fontsize=11)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'rss_distributions.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("[OK] Created rss_distributions.png")


def plot_summary_dashboard(data, config, output_dir):
    """Create a comprehensive summary dashboard"""
    results = data['results']
    rss_results = results.rss
    grid_size = config['grid_size']
    
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # Title
    fig.suptitle(f'Grid Localization Experiment Summary\n{grid_size}x{grid_size} Grid, {config["scenario"]}',
                 fontsize=16, fontweight='bold')
    
    # 1. Confusion matrices (top row)
    cm_static = rss_results.cm_static
    cm_transition = rss_results.cm_transition
    
    # Handle cm_transition as numpy object array (use first history length for summary)
    if isinstance(cm_transition, np.ndarray) and cm_transition.dtype == object:
        cm_transition = cm_transition[0]
    
    cm_static_norm = cm_static / cm_static.sum(axis=1, keepdims=True) * 100
    cm_transition_norm = cm_transition / cm_transition.sum(axis=1, keepdims=True) * 100
    
    ax1 = fig.add_subplot(gs[0, 0])
    sns.heatmap(cm_static_norm, annot=grid_size<=5, fmt='.0f', cmap='Blues', 
                ax=ax1, vmin=0, vmax=100, cbar_kws={'label': '%'})
    ax1.set_title(f'Static: {rss_results.static_acc:.1f}%', fontweight='bold')
    ax1.set_xlabel('Predicted')
    ax1.set_ylabel('True')
    
    ax2 = fig.add_subplot(gs[0, 1])
    sns.heatmap(cm_transition_norm, annot=grid_size<=5, fmt='.0f', cmap='Greens', 
                ax=ax2, vmin=0, vmax=100, cbar_kws={'label': '%'})
    trans_acc = rss_results.transition_acc[0] if isinstance(rss_results.transition_acc, (list, np.ndarray)) else rss_results.transition_acc
    improvement = trans_acc - rss_results.static_acc
    ax2.set_title(f'Transition: {trans_acc:.1f}% ({improvement:+.1f}%)', 
                  fontweight='bold')
    ax2.set_xlabel('Predicted')
    ax2.set_ylabel('True')
    
    # 2. Metrics comparison (top right)
    ax3 = fig.add_subplot(gs[0, 2])
    metrics = ['RSS', 'SINR', 'CQI']
    static_accs = [results.rss.static_acc, 
                   results.sinr.static_acc, 
                   results.cqi.static_acc]
    # Use first history length for each metric
    rss_trans = results.rss.transition_acc
    sinr_trans = results.sinr.transition_acc
    cqi_trans = results.cqi.transition_acc
    trans_accs = [
        rss_trans[0] if isinstance(rss_trans, (list, np.ndarray)) else rss_trans,
        sinr_trans[0] if isinstance(sinr_trans, (list, np.ndarray)) else sinr_trans,
        cqi_trans[0] if isinstance(cqi_trans, (list, np.ndarray)) else cqi_trans
    ]
    
    x = np.arange(len(metrics))
    width = 0.35
    ax3.bar(x - width/2, static_accs, width, label='Static', color='steelblue', alpha=0.7)
    ax3.bar(x + width/2, trans_accs, width, label='Transition', color='forestgreen', alpha=0.7)
    ax3.set_ylabel('Accuracy (%)')
    ax3.set_title('All Metrics', fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(metrics, rotation=0)
    ax3.legend(fontsize=9)
    ax3.grid(axis='y', alpha=0.3)
    
    # 3. Visit distribution (middle left)
    ax4 = fig.add_subplot(gs[1, 0])
    walk_path = data['walk_path'].astype(int)
    visit_counts = np.bincount(walk_path - 1, minlength=grid_size*grid_size)
    visit_grid = visit_counts.reshape(grid_size, grid_size)
    im4 = ax4.imshow(visit_grid, cmap='viridis', origin='lower')
    ax4.set_title('Visit Distribution', fontweight='bold')
    plt.colorbar(im4, ax=ax4, fraction=0.046, pad=0.04)
    
    # 4. Spatial errors (middle center & right)
    static_errors = np.zeros(grid_size * grid_size)
    for i in range(grid_size * grid_size):
        total = cm_static[i, :].sum()
        if total > 0:
            static_errors[i] = (total - cm_static[i, i]) / total * 100
    static_grid = static_errors.reshape(grid_size, grid_size)
    
    ax5 = fig.add_subplot(gs[1, 1])
    im5 = ax5.imshow(static_grid, cmap='Reds', origin='lower', vmin=0, vmax=100)
    ax5.set_title('Static Error Rate (%)', fontweight='bold')
    plt.colorbar(im5, ax=ax5, fraction=0.046, pad=0.04)
    
    transition_errors = np.zeros(grid_size * grid_size)
    for i in range(grid_size * grid_size):
        total = cm_transition[i, :].sum()
        if total > 0:
            transition_errors[i] = (total - cm_transition[i, i]) / total * 100
    transition_grid = transition_errors.reshape(grid_size, grid_size)
    
    ax6 = fig.add_subplot(gs[1, 2])
    im6 = ax6.imshow(transition_grid, cmap='Greens_r', origin='lower', vmin=0, vmax=100)
    ax6.set_title('Transition Error Rate (%)', fontweight='bold')
    plt.colorbar(im6, ax=ax6, fraction=0.046, pad=0.04)
    
    # 5. RSS distributions (bottom row, spanning all columns)
    ax7 = fig.add_subplot(gs[2, :])
    rss_values = data['metrics'].RSS_wb
    rss_per_location = []
    for loc in range(1, grid_size*grid_size + 1):
        mask = (walk_path == loc)
        rss_per_location.append(rss_values[mask])
    
    positions = np.arange(1, grid_size*grid_size + 1)
    bp = ax7.boxplot(rss_per_location, positions=positions, widths=0.6,
                      patch_artist=True, showfliers=False)
    for patch in bp['boxes']:
        patch.set_facecolor('lightblue')
        patch.set_alpha(0.7)
    
    means = [np.mean(rss) for rss in rss_per_location]
    ax7.plot(positions, means, 'ro-', label='Mean', linewidth=2, markersize=4)
    ax7.set_xlabel('Grid Location')
    ax7.set_ylabel('RSS (dB)')
    ax7.set_title('RSS Distribution per Location', fontweight='bold')
    ax7.legend(fontsize=9)
    ax7.grid(axis='y', alpha=0.3)
    
    plt.savefig(output_dir / 'summary_dashboard.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("[OK] Created summary_dashboard.png")


def plot_spatial_layout(data, config, output_dir):
    """Plot spatial layout showing grid and base stations"""
    grid_size = config['grid_size']
    spacing = config['spacing']
    grid_offset = config['grid_offset']
    
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
    
    # Add grid point numbers
    for i, (x, y) in enumerate(zip(grid_x, grid_y)):
        ax.text(x, y, str(i+1), ha='center', va='center', fontsize=9, fontweight='bold')
    
    # Plot serving BS
    bs_pos = config['bs_position']
    ax.scatter(bs_pos[0], bs_pos[1], c='red', s=500, marker='^', 
               edgecolors='darkred', linewidths=3, label='Serving BS (Main)', zorder=3)
    ax.text(bs_pos[0], bs_pos[1] - 8, 'Main BS', ha='center', va='top', 
            fontsize=11, fontweight='bold', color='darkred',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='darkred', linewidth=2))
    
    # Plot interfering BSs if enabled
    if config['interferers_enabled'] and config['interferer_positions']:
        interferer_x = [pos[0] for pos in config['interferer_positions']]
        interferer_y = [pos[1] for pos in config['interferer_positions']]
        ax.scatter(interferer_x, interferer_y, c='orange', s=400, marker='^', 
                   edgecolors='darkorange', linewidths=2, label='Interfering BSs', zorder=3)
        
        for i, (x, y) in enumerate(zip(interferer_x, interferer_y)):
            ax.text(x, y - 8, f'Interferer {i+1}', ha='center', va='top', 
                    fontsize=10, fontweight='bold', color='darkorange',
                    bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='darkorange', linewidth=1.5))
    
    # Draw coverage circles (optional visualization)
    circle_main = plt.Circle((bs_pos[0], bs_pos[1]), 100, color='red', fill=False, 
                             linestyle='--', linewidth=2, alpha=0.3, label='~100m radius')
    ax.add_patch(circle_main)
    
    # Formatting
    ax.set_xlabel('X Position (m)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Y Position (m)', fontsize=13, fontweight='bold')
    ax.set_title(f'Spatial Layout: {grid_size}x{grid_size} Grid with Base Stations\n{config["scenario"]}', 
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=11, framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle=':')
    ax.set_aspect('equal', adjustable='box')
    
    # Set reasonable axis limits
    all_x = grid_x + [bs_pos[0]]
    all_y = grid_y + [bs_pos[1]]
    if config['interferers_enabled'] and config['interferer_positions']:
        all_x.extend([pos[0] for pos in config['interferer_positions']])
        all_y.extend([pos[1] for pos in config['interferer_positions']])
    
    margin = 20
    ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
    ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'spatial_layout.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("[OK] Created spatial_layout.png")


def main():
    if len(sys.argv) < 2:
        print("Usage: python plot_results.py <results_directory>")
        sys.exit(1)
    
    results_dir = Path(sys.argv[1])
    
    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"Generating plots for: {results_dir.name}")
    print(f"{'='*60}\n")
    
    # Load data
    print("Loading results...")
    data, config = load_results(results_dir)
    print(f"[OK] Loaded results for {config['grid_size']}x{config['grid_size']} grid\n")
    
    # Generate all plots
    print("Generating plots...")
    plot_spatial_layout(data, config, results_dir)
    plot_confusion_matrices(data, config, results_dir)
    plot_spatial_error_map(data, config, results_dir)
    plot_metrics_comparison(data, config, results_dir)
    plot_visit_distribution(data, config, results_dir)
    plot_rss_distributions(data, config, results_dir)
    plot_summary_dashboard(data, config, results_dir)
    
    print(f"\n{'='*60}")
    print(f"[SUCCESS] All plots saved to: {results_dir}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
