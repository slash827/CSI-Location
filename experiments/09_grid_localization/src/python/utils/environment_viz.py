import os
import sys
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.patches import Rectangle, Circle

def plot_environment_layout(bs_pos, interferers=None, grid_bounds=(5, 101, 5, 101), scenario_label="3GPP 38.901 UMi NLOS", save_path=None):
    """
    Plots a clean 2D spatial environment map showing:
    - Main Serving Base Station (gNodeB)
    - Interfering Base Stations
    - 25x25 Grid Footprint & Propagation Boundaries
    - Concentric Path Loss Distance Rings around Main BS
    - NO user walk trajectories (clutter-free)
    """
    fig, ax = plt.subplots(figsize=(11, 9.5))

    x_min, x_max, y_min, y_max = grid_bounds
    
    # Shade 25x25 Grid Footprint Region
    grid_rect = Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
                          linewidth=2.5, edgecolor='darkblue', facecolor='skyblue', alpha=0.18,
                          linestyle='--', label='25x25 Grid Footprint (5m - 101m)', zorder=2)
    ax.add_patch(grid_rect)
    
    # Plot Main Serving Base Station
    ax.scatter(bs_pos[0], bs_pos[1], color='crimson', s=550, marker='^', zorder=6,
               edgecolor='black', linewidth=1.5, label=f'Serving BS ({bs_pos[0]:.0f}m, {bs_pos[1]:.0f}m, {bs_pos[2]:.0f}m)')
    ax.text(bs_pos[0], bs_pos[1] - 4.5, f'Main BS\n({bs_pos[0]}m, {bs_pos[1]}m)', ha='center', va='top',
            fontsize=10, fontweight='bold', color='crimson',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='crimson', alpha=0.9))

    # Plot Concentric Distance Contour Rings from Main BS
    for r in [30, 60, 90, 120]:
        circle = Circle((bs_pos[0], bs_pos[1]), r, color='crimson', fill=False, linestyle=':', alpha=0.45, lw=1.3)
        ax.add_patch(circle)
        ax.text(bs_pos[0] - r/math.sqrt(2), bs_pos[1] - r/math.sqrt(2), f'{r}m', color='crimson', alpha=0.75, fontsize=9, fontweight='bold')

    # Plot Interfering Base Stations if provided
    if interferers is None:
        # Default standard 4-corner interfering BS topology in 3GPP simulations
        interferers = [[0, 0, 10], [200, 0, 10], [200, 200, 10], [0, 200, 10]]
        
    int_colors = ['darkorange', 'purple', 'forestgreen', 'chocolate']
    for idx, int_pos in enumerate(interferers):
        c = int_colors[idx % len(int_colors)]
        ax.scatter(int_pos[0], int_pos[1], color=c, s=400, marker='v', zorder=5,
                   edgecolor='black', linewidth=1.2, label=f'Interferer {idx+1} ({int_pos[0]}m, {int_pos[1]}m)')
        ax.text(int_pos[0], int_pos[1] + (5 if int_pos[1]==0 else -4), f'Int-{idx+1}', ha='center', va='bottom' if int_pos[1]==0 else 'top',
                fontsize=9, fontweight='bold', color=c,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=c, alpha=0.85))

    # Environment Info Box
    info_txt = (
        f"Propagation Scenario: {scenario_label}\n"
        f"Grid Dimension: 25x25 (625 Cells)\n"
        f"Grid Boundary: [{x_min}m, {x_max}m] x [{y_min}m, {y_max}m]\n"
        f"Base Station Height: {bs_pos[2]}m\n"
        f"Center Frequency: 3.0 GHz (5G NR Sub-6)"
    )
    ax.text(0.02, 0.98, info_txt, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='left',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.85, edgecolor='darkgoldenrod'))

    ax.set_xlim(-15, 215)
    ax.set_ylim(-15, 215)
    ax.set_xlabel('X Coordinate (meters)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Y Coordinate (meters)', fontsize=12, fontweight='bold')
    ax.set_title('5G NR Environment Layout: Base Stations & 25x25 Grid Footprint', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle=':')
    ax.legend(fontsize=9.5, loc='upper right', framealpha=0.9)
    ax.set_aspect('equal', adjustable='box')
    plt.tight_layout()

    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"[SAVED] Environment layout plot: {save_path}")
    
    return fig, ax


def analyze_distance_and_interference_errors(preds, targs, bs_pos, interferers=None):
    """
    Computes disaggregated MAE, P50 (Median), and P90 error stats binned by:
    1. Distance to Main Serving BS (<30m, 30-60m, 60-90m, >90m)
    2. Distance to Nearest Interfering BS (<50m, 50-100m, >100m)
    """
    errs = np.linalg.norm(preds - targs, axis=1)
    
    # Distance to Main BS (2D)
    dist_bs = np.linalg.norm(targs - bs_pos[:2], axis=1)
    
    if interferers is None:
        interferers = [[0, 0, 10], [200, 0, 10], [200, 200, 10], [0, 200, 10]]
    
    # Distance to Nearest Interfering BS
    int_dists = []
    for int_pos in interferers:
        d_i = np.linalg.norm(targs - np.array(int_pos[:2]), axis=1)
        int_dists.append(d_i)
    dist_nearest_int = np.min(np.column_stack(int_dists), axis=1)

    # 1. Main BS Distance Bins
    bs_bins = [
        ("< 30m from Main BS", dist_bs < 30),
        ("30m - 60m from Main BS", (dist_bs >= 30) & (dist_bs < 60)),
        ("60m - 90m from Main BS", (dist_bs >= 60) & (dist_bs < 90)),
        ("> 90m from Main BS", dist_bs >= 90)
    ]

    # 2. Interferer Distance Bins
    int_bins = [
        ("< 50m from Nearest Interferer (High Interference Zone)", dist_nearest_int < 50),
        ("50m - 100m from Nearest Interferer (Moderate Interference Zone)", (dist_nearest_int >= 50) & (dist_nearest_int < 100)),
        ("> 100m from Nearest Interferer (Low Interference Zone)", dist_nearest_int >= 100)
    ]

    results = {'bs_distance': [], 'interferer_distance': []}
    
    print("\n=== ERROR ANALYSIS BY DISTANCE TO MAIN BASE STATION ===")
    for label, mask in bs_bins:
        if np.any(mask):
            e_sub = errs[mask]
            mae = np.mean(e_sub)
            p50 = np.percentile(e_sub, 50)
            p90 = np.percentile(e_sub, 90)
            print(f"  {label:<32}: MAE = {mae:6.3f}m | Median = {p50:6.3f}m | P90 = {p90:6.3f}m | Samples = {mask.sum():5,}")
            results['bs_distance'].append({'bin': label, 'mae': mae, 'p50': p50, 'p90': p90, 'samples': int(mask.sum())})

    print("\n=== ERROR ANALYSIS BY DISTANCE TO NEAREST INTERFERING BS ===")
    for label, mask in int_bins:
        if np.any(mask):
            e_sub = errs[mask]
            mae = np.mean(e_sub)
            p50 = np.percentile(e_sub, 50)
            p90 = np.percentile(e_sub, 90)
            print(f"  {label:<55}: MAE = {mae:6.3f}m | Median = {p50:6.3f}m | P90 = {p90:6.3f}m | Samples = {mask.sum():5,}")
            results['interferer_distance'].append({'bin': label, 'mae': mae, 'p50': p50, 'p90': p90, 'samples': int(mask.sum())})

    return results


if __name__ == '__main__':
    bs_pos = [116.0, 116.0, 10.0]
    out_img = Path("C:/Users/gilad/.gemini/antigravity-ide/brain/b90924c7-9fdd-41b2-b6e8-198355c5aa66/env_layout_clean.png")
    plot_environment_layout(bs_pos, save_path=out_img)
