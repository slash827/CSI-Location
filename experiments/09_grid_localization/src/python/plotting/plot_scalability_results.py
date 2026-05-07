"""
Scalability Plot: Classification vs Regression, with/without AoA.

Generates a publication-quality figure showing how localization MAE scales
with grid size for different feature sets and approaches.

Usage:
    python plot_scalability_results.py [--output-dir <path>]
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# ---------------------------------------------------------------------------
# Hardcoded results (collected from experiment CSVs and regression reports)
# ---------------------------------------------------------------------------

# NLOS single-scenario, XGBoost, RSS+SINR
# Source: results/experiment_matrix/scalability/ and scalability_static/
CLASSIF_NLOS_RSS_SINR = {
    'grid_sizes':   [3,    5,    7,    10,   15,   20],
    'n_points':     [9,    25,   49,   100,  225,  400],
    'h0_mae':       [1.28, 2.65, 3.96, 4.50, 8.87, 10.31],
    'hbest_mae':    [1.05, 1.89, 2.64, 2.64, 6.21,  7.50],
    'hbest_h':      [3,    3,    3,    3,    3,     2],
}

# Voronoi 4-scenario, XGBoost, RSS+SINR+AoAaz+AoAel (realistic 4°+5° noise)
# Source: results/experiment_matrix/2026-02-26_07-54-19/ (10x10, original)
#         results/experiment_matrix/2026-03-02_08-14-14/ (15x15, fixed: 4-type diversity)
#         results/experiment_matrix/2026-03-02_08-20-08/ (20x20, fixed: 4-type diversity)
# NOTE: 15x15/20x20 re-run after AreaGenerator fix (randperm instead of randi).
#       Fixed runs show 4 distinct area labels; residential→UMi_NLOS same as shopping_center.
CLASSIF_VORONOI_AOA = {
    'grid_sizes':   [10,    15,    20,   ],
    'n_points':     [100,   225,   400,  ],
    'h0_mae':       [0.338, 0.61,  1.11, ],
    'h1_mae':       [0.246, 0.46,  0.85, ],
}

# Voronoi 4-scenario, RandomForest, RSS+SINR+AoAaz+AoAel
# Source: regression reports (2026-03-02, fixed diversity)
#         10x10: exp_regression 2026-02-26 | 15x15: exp_regression 2026-03-02_08-14-33
#         20x20: exp_regression 2026-03-02_08-XX-XX (fixed)
REGRESSION_VORONOI_AOA = {
    'grid_sizes':   [10,    15,    20,   ],
    'n_points':     [100,   225,   400,  ],
    'h0_mae_3d':    [0.444, 0.748, 1.267,],
    'h1_mae_3d':    [0.395, 0.611, 0.984,],
}


def run_plot(output_dir: Path, include_new_15x15=None):
    """Generate scalability figure."""
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    fig.suptitle(
        'Localization Scalability: MAE vs Grid Size',
        fontsize=14, fontweight='bold', y=1.01
    )

    # colour + style palette
    COLOR_NLOS_H0    = '#9E9E9E'
    COLOR_NLOS_HBEST = '#1565C0'
    COLOR_AOA_H0     = '#EF6C00'
    COLOR_AOA_H1     = '#2E7D32'
    COLOR_REG_H0     = '#C62828'
    COLOR_REG_H1     = '#6A1B9A'

    MARKER_NLOS  = 's'
    MARKER_CLASS = 'o'
    MARKER_REG   = '^'

    # -----------------------------------------------------------------------
    # Panel 1 — Full range: NLOS RSS+SINR (all 6 grid sizes)
    # -----------------------------------------------------------------------
    ax = axes[0]
    ax.set_title('(a) NLOS Uniform — RSS+SINR', fontsize=11)

    gs = CLASSIF_NLOS_RSS_SINR['grid_sizes']
    np_pts = CLASSIF_NLOS_RSS_SINR['n_points']
    x_vals = np.array(gs)

    ax.plot(x_vals, CLASSIF_NLOS_RSS_SINR['h0_mae'],
            color=COLOR_NLOS_H0, marker=MARKER_NLOS, linewidth=2,
            markersize=7, label='Classification h=0 (static)', zorder=3)
    ax.plot(x_vals, CLASSIF_NLOS_RSS_SINR['hbest_mae'],
            color=COLOR_NLOS_HBEST, marker=MARKER_NLOS, linewidth=2,
            markersize=7, label='Classification h=best', zorder=3)

    # Annotate points with n_points
    for x, y, n in zip(x_vals, CLASSIF_NLOS_RSS_SINR['hbest_mae'], np_pts):
        ax.annotate(f'{n} pts', (x, y), textcoords='offset points',
                    xytext=(5, 5), fontsize=8, color=COLOR_NLOS_HBEST)

    ax.fill_between(x_vals, CLASSIF_NLOS_RSS_SINR['h0_mae'],
                    CLASSIF_NLOS_RSS_SINR['hbest_mae'],
                    alpha=0.12, color=COLOR_NLOS_HBEST, label='History benefit')

    ax.set_xlabel('Grid dimension (N×N)', fontsize=11)
    ax.set_ylabel('MAE (meters)', fontsize=11)
    ax.set_xticks(x_vals)
    ax.set_xticklabels([f'{g}×{g}' for g in gs])
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=9)
    ax.set_ylim(bottom=0)

    # -----------------------------------------------------------------------
    # Panel 2 — Voronoi: AoA features, classification vs regression
    # -----------------------------------------------------------------------
    ax = axes[1]
    ax.set_title('(b) Voronoi Mixed — Full AoA Features (4°+5° noise)', fontsize=11)

    gs_v  = np.array(CLASSIF_VORONOI_AOA['grid_sizes'])
    gs_r  = np.array(REGRESSION_VORONOI_AOA['grid_sizes'])

    ax.plot(gs_v, CLASSIF_VORONOI_AOA['h0_mae'],
            color=COLOR_AOA_H0, marker=MARKER_CLASS, linewidth=2,
            markersize=8, linestyle='--', label='Classification h=0', zorder=3)
    ax.plot(gs_v, CLASSIF_VORONOI_AOA['h1_mae'],
            color=COLOR_AOA_H1, marker=MARKER_CLASS, linewidth=2.5,
            markersize=8, label='Classification h=1', zorder=4)
    ax.plot(gs_r, REGRESSION_VORONOI_AOA['h0_mae_3d'],
            color=COLOR_REG_H0, marker=MARKER_REG, linewidth=2,
            markersize=8, linestyle='--', label='Regression h=0 (3D pos.)', zorder=3)
    ax.plot(gs_r, REGRESSION_VORONOI_AOA['h1_mae_3d'],
            color=COLOR_REG_H1, marker=MARKER_REG, linewidth=2.5,
            markersize=8, label='Regression h=1 (3D pos.)', zorder=4)

    # Annotate best values
    for x, y_c, y_r in zip(gs_v,
                            CLASSIF_VORONOI_AOA['h1_mae'],
                            REGRESSION_VORONOI_AOA['h1_mae_3d']):
        ax.annotate(f'{y_c:.2f}m', (x, y_c), textcoords='offset points',
                    xytext=(-30, 6), fontsize=9, color=COLOR_AOA_H1, fontweight='bold')
        ax.annotate(f'{y_r:.2f}m', (x, y_r), textcoords='offset points',
                    xytext=(-30, -14), fontsize=9, color=COLOR_REG_H1, fontweight='bold')

    # Optional: add new-15x15 data point once MATLAB sim is done
    if include_new_15x15:
        c_mae, r_mae = include_new_15x15
        ax.scatter([15], [c_mae], color=COLOR_AOA_H1, s=120, zorder=5,
                   marker='*', label=f'Classif h=1 (new 15×15 2m): {c_mae:.2f}m')
        ax.scatter([15], [r_mae], color=COLOR_REG_H1, s=120, zorder=5,
                   marker='*', label=f'Regression h=1 (new 15×15 2m): {r_mae:.2f}m')

    ax.set_xlabel('Grid dimension (N×N)', fontsize=11)
    ax.set_ylabel('MAE (meters)', fontsize=11)
    ax.set_xticks(gs_v)
    ax.set_xticklabels([f'{g}×{g}' for g in gs_v])
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=9)
    ax.set_ylim(bottom=0)

    # Note box
    note = ('Note: Voronoi env. has 4 distinct channel types\n'
            '(UMi_NLOS, UMi_LOS, RMa_LOS, Mixed).\n'
            'AoA: 4° Gaussian + 5° quantization noise.\n'
            'NLOS env. uses uniform UMa_NLOS.')
    ax.text(0.02, 0.97, note, transform=ax.transAxes, fontsize=7.5,
            verticalalignment='top', bbox=dict(boxstyle='round,pad=0.3',
                                               facecolor='lightyellow', alpha=0.8))

    plt.tight_layout()

    out_png = output_dir / 'scalability_classification_vs_regression.png'
    out_pdf = output_dir / 'scalability_classification_vs_regression.pdf'
    plt.savefig(out_png, dpi=150, bbox_inches='tight')
    plt.savefig(out_pdf, bbox_inches='tight')
    plt.close()

    print(f'[OK] Saved: {out_png}')
    print(f'[OK] Saved: {out_pdf}')

    # Also print summary table
    print('\n=== Summary Table ===')
    print(f'{"Grid":>6} {"Env":>12} {"Classif h=0 (MAE)":>20} {"Classif h=best":>16} {"Regress h=1":>13}')
    print('-' * 75)
    for i, (g, n) in enumerate(zip(CLASSIF_NLOS_RSS_SINR['grid_sizes'],
                                   CLASSIF_NLOS_RSS_SINR['n_points'])):
        row = f'{g}×{g} ({n:>3}pts)  {"NLOS RSS+SINR":>12}  {CLASSIF_NLOS_RSS_SINR["h0_mae"][i]:>7.2f}m (h=0){CLASSIF_NLOS_RSS_SINR["hbest_mae"][i]:>10.2f}m (h={CLASSIF_NLOS_RSS_SINR["hbest_h"][i]})           —'
        print(row)

    for i, g in enumerate(CLASSIF_VORONOI_AOA['grid_sizes']):
        c_h1 = CLASSIF_VORONOI_AOA['h1_mae'][i]
        c_h0 = CLASSIF_VORONOI_AOA['h0_mae'][i]
        r_h1 = REGRESSION_VORONOI_AOA['h1_mae_3d'][i]
        n    = CLASSIF_VORONOI_AOA['n_points'][i]
        print(f'{g}×{g} ({n:>3}pts)  {"Voronoi+AoA":>12}  {c_h0:>7.3f}m (h=0){c_h1:>10.3f}m (h=1)  {r_h1:>8.3f}m (h=1)')

    return out_png


def main():
    parser = argparse.ArgumentParser(description='Generate localization scalability plot')
    parser.add_argument('--output-dir', default=None,
                        help='Output directory (default: results/experiment_matrix/scalability_plots/)')
    parser.add_argument('--new-15x15-classif-mae', type=float, default=None,
                        help='New 15x15 clean classification MAE to overlay on panel (b)')
    parser.add_argument('--new-15x15-regress-mae', type=float, default=None,
                        help='New 15x15 clean regression MAE to overlay on panel (b)')
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = PROJECT_ROOT / 'results' / 'experiment_matrix' / 'scalability_plots'

    new_15x15 = None
    if args.new_15x15_classif_mae and args.new_15x15_regress_mae:
        new_15x15 = (args.new_15x15_classif_mae, args.new_15x15_regress_mae)

    run_plot(output_dir, include_new_15x15=new_15x15)


if __name__ == '__main__':
    main()
