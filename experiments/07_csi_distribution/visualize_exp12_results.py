"""
Visualize Experiment 12 Results: CSI Distribution Study
========================================================

This script creates three key visualizations from the exp12 results:
1. Heatmap of mean RSS across the grid
2. Heatmap of RSS standard deviation across the grid
3. Scatter plot of RSS vs distance from BS

Usage:
    python visualize_exp12_results.py

Requirements:
    - numpy
    - matplotlib
    - h5py (for loading MATLAB v7.3 .mat files)
    - scipy (for loading older MATLAB .mat files)

Author: CSI-Location Project
Date: November 27, 2025
"""

import numpy as np
import matplotlib.pyplot as plt
import h5py
from scipy.io import loadmat
from pathlib import Path
import sys

# Configuration
RESULTS_DIR = Path("../../results")
EXP_PREFIX = "exp12_"

def find_latest_exp12_results():
    """Find the most recent exp12 results directory."""
    exp_dirs = sorted(RESULTS_DIR.glob(f"{EXP_PREFIX}*"), reverse=True)
    
    if not exp_dirs:
        print(f"Error: No exp12 results found in {RESULTS_DIR}")
        sys.exit(1)
    
    return exp_dirs[0]

def load_experiment_data(results_dir):
    """Load statistics and grid info from experiment results."""
    print(f"Loading data from: {results_dir.name}")
    
    # Load statistics (MATLAB v7.3 format using h5py)
    stats_file = results_dir / "statistics" / "csi_statistics.mat"
    if not stats_file.exists():
        print(f"Error: Statistics file not found: {stats_file}")
        sys.exit(1)
    
    with h5py.File(str(stats_file), 'r') as f:
        # Access stats structure
        stats = f['stats']
        
        # Extract arrays (HDF5 format stores transposed)
        mean_rss = np.array(stats['mean_RSS']).T
        std_rss = np.array(stats['std_RSS']).T
        distance = np.array(stats['distance']).T
    
    # Load grid information (older MATLAB format)
    grid_file = results_dir / "data" / "grid_info.mat"
    if not grid_file.exists():
        print(f"Error: Grid info file not found: {grid_file}")
        sys.exit(1)
    
    # Try loading with scipy first (older format)
    try:
        grid_data = loadmat(str(grid_file))
        grid_info = grid_data['grid_info']
        
        x_coords = grid_info['x_coords'][0, 0]
        y_coords = grid_info['y_coords'][0, 0]
        bs_position = grid_info['bs_position'][0, 0].flatten()
    except NotImplementedError:
        # Fall back to h5py for v7.3 format
        with h5py.File(str(grid_file), 'r') as f:
            grid_info = f['grid_info']
            
            x_coords = np.array(grid_info['x_coords']).T
            y_coords = np.array(grid_info['y_coords']).T
            bs_position = np.array(grid_info['bs_position']).flatten()
    
    print(f"  Grid shape: {mean_rss.shape}")
    print(f"  BS position: ({bs_position[0]:.1f}, {bs_position[1]:.1f}, {bs_position[2]:.1f}) m")
    print(f"  RSS range: [{np.min(mean_rss):.2f}, {np.max(mean_rss):.2f}] dBm")
    print(f"  Std range: [{np.min(std_rss):.2f}, {np.max(std_rss):.2f}] dB")
    print(f"  Distance range: [{np.min(distance):.1f}, {np.max(distance):.1f}] m")
    
    return {
        'mean_rss': mean_rss,
        'std_rss': std_rss,
        'distance': distance,
        'x_coords': x_coords,
        'y_coords': y_coords,
        'bs_position': bs_position,
        'results_dir': results_dir
    }

def create_visualizations(data):
    """Create three key visualizations."""
    print("\nGenerating visualizations...")
    
    # Create figure with three subplots
    fig = plt.figure(figsize=(18, 5))
    
    # Get data
    mean_rss = data['mean_rss']
    std_rss = data['std_rss']
    distance = data['distance']
    x_coords = data['x_coords']
    y_coords = data['y_coords']
    bs_pos = data['bs_position']
    
    # Get coordinate vectors (1D arrays for axes)
    x_vec = x_coords[0, :]
    y_vec = y_coords[:, 0]
    
    # ==========================================
    # Plot 1: Mean RSS Heatmap
    # ==========================================
    ax1 = plt.subplot(1, 3, 1)
    
    im1 = ax1.imshow(mean_rss, 
                     extent=[x_vec[0], x_vec[-1], y_vec[0], y_vec[-1]],
                     origin='lower',
                     cmap='jet',
                     aspect='equal',
                     interpolation='bilinear')
    
    # Mark BS position
    ax1.plot(bs_pos[0], bs_pos[1], 'w^', markersize=15, 
             markeredgecolor='black', markeredgewidth=2,
             label='Base Station')
    
    # Colorbar
    cbar1 = plt.colorbar(im1, ax=ax1, label='RSS (dBm)')
    
    # Labels and title
    ax1.set_xlabel('X Position (m)', fontsize=12)
    ax1.set_ylabel('Y Position (m)', fontsize=12)
    ax1.set_title('Mean Received Signal Strength (RSS)', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3, linestyle='--')
    
    # ==========================================
    # Plot 2: RSS Std Dev Heatmap
    # ==========================================
    ax2 = plt.subplot(1, 3, 2)
    
    im2 = ax2.imshow(std_rss,
                     extent=[x_vec[0], x_vec[-1], y_vec[0], y_vec[-1]],
                     origin='lower',
                     cmap='hot',
                     aspect='equal',
                     interpolation='bilinear')
    
    # Mark BS position
    ax2.plot(bs_pos[0], bs_pos[1], 'c^', markersize=15,
             markeredgecolor='black', markeredgewidth=2,
             label='Base Station')
    
    # Colorbar
    cbar2 = plt.colorbar(im2, ax=ax2, label='RSS Std Dev (dB)')
    
    # Labels and title
    ax2.set_xlabel('X Position (m)', fontsize=12)
    ax2.set_ylabel('Y Position (m)', fontsize=12)
    ax2.set_title('RSS Standard Deviation (Variability)', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3, linestyle='--')
    
    # ==========================================
    # Plot 3: RSS vs Distance Scatter
    # ==========================================
    ax3 = plt.subplot(1, 3, 3)
    
    # Flatten arrays for scatter plot
    dist_flat = distance.flatten()
    mean_rss_flat = mean_rss.flatten()
    std_rss_flat = std_rss.flatten()
    
    # Scatter plot colored by std dev
    scatter = ax3.scatter(dist_flat, mean_rss_flat, 
                         c=std_rss_flat, 
                         cmap='viridis',
                         s=100,
                         alpha=0.7,
                         edgecolors='black',
                         linewidth=0.5)
    
    # Colorbar
    cbar3 = plt.colorbar(scatter, ax=ax3, label='RSS Std Dev (dB)')
    
    # Fit and plot trend line (polynomial degree 2)
    coeffs = np.polyfit(dist_flat, mean_rss_flat, 2)
    poly = np.poly1d(coeffs)
    dist_range = np.linspace(dist_flat.min(), dist_flat.max(), 100)
    ax3.plot(dist_range, poly(dist_range), 'r--', linewidth=2, 
             label=f'Fit: {coeffs[0]:.4f}d² + {coeffs[1]:.3f}d + {coeffs[2]:.2f}')
    
    # R² calculation
    residuals = mean_rss_flat - poly(dist_flat)
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((mean_rss_flat - np.mean(mean_rss_flat))**2)
    r_squared = 1 - (ss_res / ss_tot)
    
    # Labels and title
    ax3.set_xlabel('Distance from BS (m)', fontsize=12)
    ax3.set_ylabel('Mean RSS (dBm)', fontsize=12)
    ax3.set_title(f'RSS vs Distance (R² = {r_squared:.3f})', fontsize=14, fontweight='bold')
    ax3.legend(loc='upper right', fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    # Add text annotation about high variance
    textstr = f'Mean σ: {np.mean(std_rss_flat):.1f} dB\nRange: [{np.min(std_rss_flat):.1f}, {np.max(std_rss_flat):.1f}] dB'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax3.text(0.05, 0.05, textstr, transform=ax3.transAxes, fontsize=10,
             verticalalignment='bottom', bbox=props)
    
    # Overall title
    fig.suptitle('Experiment 12: CSI Distribution Analysis', 
                 fontsize=16, fontweight='bold', y=1.02)
    
    plt.tight_layout()
    
    return fig

def save_plots(fig, results_dir):
    """Save the figure to the results directory."""
    output_dir = results_dir / "plots"
    output_dir.mkdir(exist_ok=True)
    
    # Save as PNG
    output_file = output_dir / "exp12_summary_plots.png"
    fig.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved: {output_file}")
    
    # Also save in current directory for convenience
    local_file = Path("exp12_summary_plots.png")
    fig.savefig(local_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {local_file}")

def create_individual_plots(data):
    """Create individual high-resolution plots."""
    print("\nGenerating individual plots...")
    
    results_dir = data['results_dir']
    output_dir = results_dir / "plots"
    
    mean_rss = data['mean_rss']
    std_rss = data['std_rss']
    distance = data['distance']
    x_coords = data['x_coords']
    y_coords = data['y_coords']
    bs_pos = data['bs_position']
    
    x_vec = x_coords[0, :]
    y_vec = y_coords[:, 0]
    
    # Individual Plot 1: Mean RSS
    fig1, ax1 = plt.subplots(figsize=(10, 8))
    im1 = ax1.imshow(mean_rss, 
                     extent=[x_vec[0], x_vec[-1], y_vec[0], y_vec[-1]],
                     origin='lower',
                     cmap='jet',
                     aspect='equal',
                     interpolation='bilinear')
    ax1.plot(bs_pos[0], bs_pos[1], 'w^', markersize=20, 
             markeredgecolor='black', markeredgewidth=2.5,
             label='Base Station')
    cbar1 = plt.colorbar(im1, ax=ax1, label='RSS (dBm)', fraction=0.046)
    ax1.set_xlabel('X Position (m)', fontsize=14)
    ax1.set_ylabel('Y Position (m)', fontsize=14)
    ax1.set_title('Mean Received Signal Strength (RSS)', fontsize=16, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=12)
    ax1.grid(True, alpha=0.3, linestyle='--')
    plt.tight_layout()
    file1 = output_dir / "mean_rss_heatmap_python.png"
    fig1.savefig(file1, dpi=300, bbox_inches='tight')
    print(f"  ✓ {file1.name}")
    plt.close(fig1)
    
    # Individual Plot 2: Std RSS
    fig2, ax2 = plt.subplots(figsize=(10, 8))
    im2 = ax2.imshow(std_rss,
                     extent=[x_vec[0], x_vec[-1], y_vec[0], y_vec[-1]],
                     origin='lower',
                     cmap='hot',
                     aspect='equal',
                     interpolation='bilinear')
    ax2.plot(bs_pos[0], bs_pos[1], 'c^', markersize=20,
             markeredgecolor='black', markeredgewidth=2.5,
             label='Base Station')
    cbar2 = plt.colorbar(im2, ax=ax2, label='RSS Std Dev (dB)', fraction=0.046)
    ax2.set_xlabel('X Position (m)', fontsize=14)
    ax2.set_ylabel('Y Position (m)', fontsize=14)
    ax2.set_title('RSS Standard Deviation (Measurement Variability)', fontsize=16, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=12)
    ax2.grid(True, alpha=0.3, linestyle='--')
    
    # Add annotation about high variance finding
    textstr = f'Mean: {np.mean(std_rss):.1f} dB\nRange: [{np.min(std_rss):.1f}, {np.max(std_rss):.1f}] dB\n\n⚠ High variance indicates\nLOS/NLOS mixing'
    props = dict(boxstyle='round', facecolor='yellow', alpha=0.8)
    ax2.text(0.02, 0.98, textstr, transform=ax2.transAxes, fontsize=11,
             verticalalignment='top', bbox=props, family='monospace')
    
    plt.tight_layout()
    file2 = output_dir / "std_rss_heatmap_python.png"
    fig2.savefig(file2, dpi=300, bbox_inches='tight')
    print(f"  ✓ {file2.name}")
    plt.close(fig2)
    
    # Individual Plot 3: RSS vs Distance
    fig3, ax3 = plt.subplots(figsize=(12, 8))
    
    dist_flat = distance.flatten()
    mean_rss_flat = mean_rss.flatten()
    std_rss_flat = std_rss.flatten()
    
    scatter = ax3.scatter(dist_flat, mean_rss_flat, 
                         c=std_rss_flat, 
                         cmap='viridis',
                         s=150,
                         alpha=0.7,
                         edgecolors='black',
                         linewidth=0.8)
    
    cbar3 = plt.colorbar(scatter, ax=ax3, label='RSS Std Dev (dB)')
    
    # Fit polynomial
    coeffs = np.polyfit(dist_flat, mean_rss_flat, 2)
    poly = np.poly1d(coeffs)
    dist_range = np.linspace(dist_flat.min(), dist_flat.max(), 100)
    ax3.plot(dist_range, poly(dist_range), 'r--', linewidth=3, 
             label=f'Quadratic fit:\n{coeffs[0]:.4f}d² + {coeffs[1]:.3f}d + {coeffs[2]:.2f}')
    
    # R²
    residuals = mean_rss_flat - poly(dist_flat)
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((mean_rss_flat - np.mean(mean_rss_flat))**2)
    r_squared = 1 - (ss_res / ss_tot)
    
    ax3.set_xlabel('Distance from BS (m)', fontsize=14)
    ax3.set_ylabel('Mean RSS (dBm)', fontsize=14)
    ax3.set_title(f'Mean RSS vs Distance from Base Station (R² = {r_squared:.3f})', 
                  fontsize=16, fontweight='bold')
    ax3.legend(loc='upper right', fontsize=11)
    ax3.grid(True, alpha=0.3)
    
    # Detailed statistics annotation
    textstr = (f'Statistics:\n'
               f'  Points: {len(dist_flat)}\n'
               f'  Mean σ: {np.mean(std_rss_flat):.1f} dB\n'
               f'  σ range: [{np.min(std_rss_flat):.1f}, {np.max(std_rss_flat):.1f}] dB\n'
               f'  R²: {r_squared:.3f}\n\n'
               f'⚠ Low R² indicates distance alone\n'
               f'   cannot predict RSS reliably\n'
               f'   (LOS/NLOS is dominant factor)')
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.9)
    ax3.text(0.03, 0.03, textstr, transform=ax3.transAxes, fontsize=10,
             verticalalignment='bottom', bbox=props, family='monospace')
    
    plt.tight_layout()
    file3 = output_dir / "rss_vs_distance_python.png"
    fig3.savefig(file3, dpi=300, bbox_inches='tight')
    print(f"  ✓ {file3.name}")
    plt.close(fig3)

def main():
    """Main execution function."""
    print("="*60)
    print("Experiment 12 Visualization Script")
    print("="*60)
    
    # Find latest results
    results_dir = find_latest_exp12_results()
    
    # Load data
    data = load_experiment_data(results_dir)
    
    # Create combined visualization
    fig = create_visualizations(data)
    
    # Save combined plot
    save_plots(fig, results_dir)
    
    # Create individual high-res plots
    create_individual_plots(data)
    
    # Display
    print("\n" + "="*60)
    print("All visualizations generated successfully!")
    print("="*60)
    print("\nShowing plots... (close window to exit)")
    plt.show()

if __name__ == "__main__":
    main()
