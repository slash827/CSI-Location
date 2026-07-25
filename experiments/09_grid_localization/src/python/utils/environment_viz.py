import os
import sys
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.patches import Rectangle, Circle
from scipy.spatial import Voronoi, voronoi_plot_2d

def plot_environment_layout(bs_pos, interferers=None, grid_bounds=(5, 101, 5, 101), voronoi_cells=None, scenario_label="3GPP 38.901 Mixed UMi", save_path=None):
    """
    Plots a 2D spatial environment map showing:
    - Main Serving Base Station (gNodeB)
    - Pushed Interfering Base Stations
    - 25x25 Grid Footprint & Propagation Boundaries
    - Voronoi Propagation Areas (LOS vs NLOS Areas: Highway, Park, Shopping Center, Residential)
    - Concentric Path Loss Distance Rings
    """
    fig, ax = plt.subplots(figsize=(11.5, 9.5))

    x_min, x_max, y_min, y_max = grid_bounds
    
    # Shade 25x25 Grid Footprint Region
    grid_rect = Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
                          linewidth=2.5, edgecolor='darkblue', facecolor='none',
                          linestyle='--', label='25x25 Grid Footprint (5m - 101m)', zorder=3)
    ax.add_patch(grid_rect)

    # Render Voronoi Propagation Areas (LOS vs NLOS) if provided
    if voronoi_cells is None:
        voronoi_cells = [
            {"center": [35.0, 15.0], "scenario": "LOS", "name": "Highway (LOS)"},
            {"center": [95.0, 15.0], "scenario": "NLOS", "name": "Shopping Center (NLOS)"},
            {"center": [75.0, 5.0],  "scenario": "NLOS", "name": "Residential (NLOS)"},
            {"center": [60.0, 90.0], "scenario": "LOS", "name": "Park (LOS)"}
        ]

    # Create 2D Voronoi Cell Background Heatmap
    gx = np.linspace(x_min, x_max, 150)
    gy = np.linspace(y_min, y_max, 150)
    GX, GY = np.meshgrid(gx, gy)
    grid_pts = np.column_stack([GX.ravel(), GY.ravel()])

    centers = np.array([c['center'] for c in voronoi_cells])
    cell_types = [1 if c['scenario']=='LOS' else 0 for c in voronoi_cells]

    # Assign grid points to nearest Voronoi center
    dists = np.linalg.norm(grid_pts[:, None, :] - centers[None, :, :], axis=2)
    nearest_idx = np.argmin(dists, axis=1)
    grid_scenarios = np.array([cell_types[i] for i in nearest_idx]).reshape(150, 150)

    # Plot Background Propagation Map (Green = LOS, Light Salmon = NLOS)
    cmap = matplotlib.colors.ListedColormap(['#ffcccc', '#ccffcc'])
    ax.imshow(grid_scenarios, extent=(x_min, x_max, y_min, y_max), origin='lower', cmap=cmap, alpha=0.35, zorder=1)

    # Mark Voronoi Area Centers & Labels
    for c in voronoi_cells:
        color = 'darkgreen' if c['scenario'] == 'LOS' else 'darkred'
        ax.scatter(c['center'][0], c['center'][1], color=color, s=180, marker='P', zorder=4, edgecolor='black', linewidth=1)
        ax.text(c['center'][0], c['center'][1] + 3, f"{c['name']}", color=color, fontsize=10, fontweight='bold', ha='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=color, alpha=0.9))

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

    # Plot Interfering Base Stations (Pushed SW & S)
    if interferers is None:
        interferers = [[-60, 53, 10], [53, -60, 10]]
        
    int_colors = ['darkorange', 'purple']
    labels = ['IBS-1 (West Pushed -60m)', 'IBS-2 (South Pushed -60m)']
    
    for idx, int_pos in enumerate(interferers):
        c = int_colors[idx % len(int_colors)]
        lbl = labels[idx] if idx < len(labels) else f'Interferer {idx+1}'
        ax.scatter(int_pos[0], int_pos[1], color=c, s=400, marker='v', zorder=5,
                   edgecolor='black', linewidth=1.2, label=f'{lbl} ({int_pos[0]}m, {int_pos[1]}m)')
        ax.text(int_pos[0], int_pos[1] + (5 if int_pos[1]<0 else -4), f'IBS-{idx+1}', ha='center', va='bottom' if int_pos[1]<0 else 'top',
                fontsize=9, fontweight='bold', color=c,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=c, alpha=0.85))

    # Environment Info Box
    info_txt = (
        f"Propagation Scenario: {scenario_label}\n"
        f"Green Regions: Line-of-Sight (LOS)\n"
        f"Red Regions: Non-Line-of-Sight (NLOS)\n"
        f"Grid Dimension: 25x25 (625 Cells)\n"
        f"Interferers: Pushed Outward (-60m)\n"
        f"Center Frequency: 3.0 GHz (5G NR Sub-6)"
    )
    ax.text(0.02, 0.98, info_txt, transform=ax.transAxes, fontsize=9.5,
            verticalalignment='top', horizontalalignment='left',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.9, edgecolor='darkgoldenrod'))

    ax.set_xlim(-75, 135)
    ax.set_ylim(-75, 135)
    ax.set_xlabel('X Coordinate (meters)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Y Coordinate (meters)', fontsize=12, fontweight='bold')
    ax.set_title('5G NR Environment Layout: Voronoi LOS/NLOS Propagation Map & Cell Towers', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle=':')
    ax.legend(fontsize=9, loc='upper right', framealpha=0.9)
    ax.set_aspect('equal', adjustable='box')
    plt.tight_layout()

    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"[SAVED] Environment layout plot: {save_path}")
    
    return fig, ax


def analyze_distance_and_interference_errors(preds, targs, bs_pos, interferers=None, report_dir=None):
    """
    Computes disaggregated MAE, P50 (Median), and P90 error stats binned by:
    1. Distance to Main Serving BS (<30m, 30-60m, 60-90m, >90m)
    2. Distance to Nearest Interfering BS (<50m, 50-100m, >100m)
    3. LOS vs NLOS Propagation Areas (Voronoi Areas)
    Saves a comprehensive Markdown report to report_dir if specified.
    """
    errs = np.linalg.norm(preds - targs, axis=1)
    
    # Distance to Main BS (2D)
    dist_bs = np.linalg.norm(targs - bs_pos[:2], axis=1)
    
    if interferers is None:
        interferers = [[-60, 53, 10], [53, -60, 10]]
    
    # Distance to Nearest Interfering BS
    int_dists = []
    for int_pos in interferers:
        d_i = np.linalg.norm(targs - np.array(int_pos[:2]), axis=1)
        int_dists.append(d_i)
    dist_nearest_int = np.min(np.column_stack(int_dists), axis=1)

    # Voronoi Propagation Areas Classification
    voronoi_cells = [
        {"center": [35.0, 15.0], "scenario": "LOS", "name": "Highway (LOS)"},
        {"center": [95.0, 15.0], "scenario": "NLOS", "name": "Shopping Center (NLOS)"},
        {"center": [75.0, 5.0],  "scenario": "NLOS", "name": "Residential (NLOS)"},
        {"center": [60.0, 90.0], "scenario": "LOS", "name": "Park (LOS)"}
    ]
    centers = np.array([c['center'] for c in voronoi_cells])
    dists_v = np.linalg.norm(targs[:, None, :] - centers[None, :, :], axis=2)
    nearest_v_idx = np.argmin(dists_v, axis=1)
    is_los = np.array([voronoi_cells[i]['scenario'] == 'LOS' for i in nearest_v_idx])

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

    # 3. LOS / NLOS Bins
    propagation_bins = [
        ("Line-of-Sight (LOS) Areas (Highway & Park)", is_los),
        ("Non-Line-of-Sight (NLOS) Areas (Shopping & Residential)", ~is_los)
    ]

    results = {'bs_distance': [], 'interferer_distance': [], 'propagation': []}
    
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

    print("\n=== ERROR ANALYSIS BY PROPAGATION CONDITION (LOS VS NLOS) ===")
    for label, mask in propagation_bins:
        if np.any(mask):
            e_sub = errs[mask]
            mae = np.mean(e_sub)
            p50 = np.percentile(e_sub, 50)
            p90 = np.percentile(e_sub, 90)
            print(f"  {label:<55}: MAE = {mae:6.3f}m | Median = {p50:6.3f}m | P90 = {p90:6.3f}m | Samples = {mask.sum():5,}")
            results['propagation'].append({'bin': label, 'mae': mae, 'p50': p50, 'p90': p90, 'samples': int(mask.sum())})

    # Generate Markdown Report if report_dir is specified
    if report_dir:
        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "spatial_environment_and_interference_report.md"
        
        md_lines = [
            "# 5G NR Spatial Environment & Interference Error Analysis Report",
            "",
            "## 1. Network Topology & Base Station Configuration",
            f"- **Serving Main BS Position:** `[{bs_pos[0]}, {bs_pos[1]}, {bs_pos[2]}] meters`",
            "- **IBS-1 (West Pushed):** `[-60, 53, 10] meters`",
            "- **IBS-2 (South Pushed):** `[53, -60, 10] meters`",
            "- **Grid Area:** 25x25 Grid Footprint `[5m, 101m] x [5m, 101m]`",
            "",
            "## 2. Line-of-Sight (LOS) vs Non-Line-of-Sight (NLOS) Area Breakdown",
            "| Propagation Area | Samples | 2D MAE (m) | Median Error P50 (m) | 90th Percentile P90 (m) |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ]
        for row in results['propagation']:
            md_lines.append(f"| **{row['bin']}** | {row['samples']:,} | **{row['mae']:.3f}** | {row['p50']:.3f} | {row['p90']:.3f} |")

        md_lines.extend([
            "",
            "## 3. Distance to Main Base Station Breakdown",
            "| Distance Bin | Samples | 2D MAE (m) | Median Error P50 (m) | 90th Percentile P90 (m) |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ])
        for row in results['bs_distance']:
            md_lines.append(f"| **{row['bin']}** | {row['samples']:,} | **{row['mae']:.3f}** | {row['p50']:.3f} | {row['p90']:.3f} |")
            
        md_lines.extend([
            "",
            "## 4. Distance to Nearest Interfering Base Station Breakdown",
            "| Interference Zone | Samples | 2D MAE (m) | Median Error P50 (m) | 90th Percentile P90 (m) |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ])
        for row in results['interferer_distance']:
            md_lines.append(f"| **{row['bin']}** | {row['samples']:,} | **{row['mae']:.3f}** | {row['p50']:.3f} | {row['p90']:.3f} |")
            
        report_path.write_text("\n".join(md_lines), encoding='utf-8')
        print(f"[SAVED] Report written to: {report_path}")

    return results


if __name__ == '__main__':
    bs_pos = [116.0, 116.0, 10.0]
    out_img = Path("C:/Users/gilad/.gemini/antigravity-ide/brain/b90924c7-9fdd-41b2-b6e8-198355c5aa66/env_layout_voronoi_los_nlos.png")
    plot_environment_layout(bs_pos, save_path=out_img)
