"""
BS Placement Comparison — Center BS vs NE BS

Loads saved CSVs from both placement experiments and generates:
  accuracy_comparison.png     — grouped bar chart, core experiments × model × placement
  aoa_gain_comparison.png     — AoA gain vs history gain side-by-side
  mae_heatmap_comparison.png  — spatial MAE scatter maps, shared scale per row
  comparison_summary.csv      — merged table with Δ columns

Usage:
  python compare_placements.py
  python compare_placements.py \\
    --center-dir results/multi_user_voronoi_15x15 \\
    --ne-dir     results/ne_bs_voronoi_15x15 \\
    --out-dir    results/placement_comparison
"""
import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

CORE_EXPERIMENTS = ['BASE', 'BASE_H', 'BASE_A', 'BASE_A_H']
MODELS = ['xgboost', 'rf']

_COLOR_CENTER = '#2196F3'
_COLOR_NE = '#FF5722'


def _load_summary(results_dir: Path) -> pd.DataFrame:
    p = results_dir / 'csvs' / 'results_summary.csv'
    if not p.exists():
        raise FileNotFoundError(f"Results not found: {p}")
    return pd.read_csv(p)


def _load_mae_heatmap(results_dir: Path, experiment: str, model: str = 'xgboost') -> pd.DataFrame | None:
    p = results_dir / 'csvs' / f'mae_heatmap_{experiment}_{model}.csv'
    return pd.read_csv(p) if p.exists() else None


def _bs_position(data_dir: Path | None):
    """Return (x, y) of the serving BS from the simulation data directory, or None."""
    if data_dir is None or not data_dir.exists():
        return None
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from pipelines.multi_user_pipeline import _read_bs_geometry
        bs_xy, _ = _read_bs_geometry(data_dir)
        return bs_xy
    except Exception:
        pass
    return None


# ── plot helpers ─────────────────────────────────────────────────────────────

def plot_accuracy_comparison(center: pd.DataFrame, ne: pd.DataFrame, out_dir: Path):
    fig, axes = plt.subplots(1, len(MODELS), figsize=(6 * len(MODELS), 5), sharey=True)

    x = np.arange(len(CORE_EXPERIMENTS))
    w = 0.35

    for ax, model in zip(axes, MODELS):
        c_idx = center[center['model'] == model].set_index('experiment')['accuracy_%']
        n_idx = ne[ne['model'] == model].set_index('experiment')['accuracy_%']

        c_vals = [c_idx.get(exp, np.nan) for exp in CORE_EXPERIMENTS]
        n_vals = [n_idx.get(exp, np.nan) for exp in CORE_EXPERIMENTS]

        bars_c = ax.bar(x - w / 2, c_vals, w, label='Center BS', color=_COLOR_CENTER, alpha=0.85)
        bars_n = ax.bar(x + w / 2, n_vals, w, label='NE BS',     color=_COLOR_NE,    alpha=0.85)

        for bar, val in [(b, v) for b, v in zip(list(bars_c) + list(bars_n),
                                                  c_vals + n_vals)]:
            if not np.isnan(val):
                ax.text(bar.get_x() + bar.get_width() / 2, val + 0.8,
                        f'{val:.1f}', ha='center', va='bottom', fontsize=7.5, fontweight='bold')

        ax.set_xticks(x)
        ax.set_xticklabels(CORE_EXPERIMENTS, rotation=20, ha='right')
        ax.set_title(model.upper(), fontsize=13, fontweight='bold')
        ax.set_ylabel('Accuracy (%)')
        ax.set_ylim(0, 108)
        ax.legend(loc='upper left', fontsize=9)
        ax.grid(axis='y', alpha=0.3)

    fig.suptitle('BS Placement Comparison — Classification Accuracy',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    out_path = out_dir / 'accuracy_comparison.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[OK] {out_path}')


def plot_gain_comparison(center: pd.DataFrame, ne: pd.DataFrame, out_dir: Path):
    """Side-by-side bar charts: AoA gain and history gain per model × placement."""
    gain_specs = [
        ('AoA Gain\n(BASE_A_H − BASE_H)', 'BASE_A_H', 'BASE_H'),
        ('History Gain\n(BASE_H − BASE)',  'BASE_H',   'BASE'),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))

    bar_labels = ['Center\nXGBoost', 'Center\nRF', 'NE\nXGBoost', 'NE\nRF']
    bar_colors  = [_COLOR_CENTER, _COLOR_CENTER, _COLOR_NE, _COLOR_NE]
    bar_hatches = ['', '//', '', '//']

    for ax, (title, exp_hi, exp_lo) in zip(axes, gain_specs):
        vals = []
        for df in [center, ne]:
            for model in MODELS:
                mdf = df[df['model'] == model].set_index('experiment')['accuracy_%']
                vals.append(mdf.get(exp_hi, np.nan) - mdf.get(exp_lo, np.nan))

        bars = ax.bar(bar_labels, vals, color=bar_colors,
                      hatch=bar_hatches, edgecolor='white', linewidth=1.2, alpha=0.85)
        for bar, v in zip(bars, vals):
            if not np.isnan(v):
                ax.text(bar.get_x() + bar.get_width() / 2, v + 0.3,
                        f'+{v:.1f} pp', ha='center', va='bottom',
                        fontsize=9, fontweight='bold')

        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_ylabel('Accuracy gain (pp)')
        finite = [v for v in vals if not np.isnan(v)]
        ax.set_ylim(0, (max(finite) if finite else 40) * 1.3)
        ax.grid(axis='y', alpha=0.3)
        ax.tick_params(axis='x', labelsize=9)

    fig.suptitle('Gain Attribution: AoA vs History — Center BS vs NE BS',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    out_path = out_dir / 'aoa_gain_comparison.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[OK] {out_path}')


def plot_mae_comparison(center: pd.DataFrame, ne: pd.DataFrame, out_dir: Path):
    """Bar chart of MAE per core experiment × model × placement (lower = better)."""
    fig, axes = plt.subplots(1, len(MODELS), figsize=(6 * len(MODELS), 5), sharey=True)

    x = np.arange(len(CORE_EXPERIMENTS))
    w = 0.35

    for ax, model in zip(axes, MODELS):
        c_idx = center[center['model'] == model].set_index('experiment')['mae_m']
        n_idx = ne[ne['model'] == model].set_index('experiment')['mae_m']

        c_vals = [c_idx.get(exp, np.nan) for exp in CORE_EXPERIMENTS]
        n_vals = [n_idx.get(exp, np.nan) for exp in CORE_EXPERIMENTS]

        bars_c = ax.bar(x - w / 2, c_vals, w, label='Center BS', color=_COLOR_CENTER, alpha=0.85)
        bars_n = ax.bar(x + w / 2, n_vals, w, label='NE BS',     color=_COLOR_NE,    alpha=0.85)

        for bar, val in [(b, v) for b, v in zip(list(bars_c) + list(bars_n),
                                                  c_vals + n_vals)]:
            if not np.isnan(val):
                ax.text(bar.get_x() + bar.get_width() / 2, val + 0.05,
                        f'{val:.2f}', ha='center', va='bottom', fontsize=7.5, fontweight='bold')

        ax.set_xticks(x)
        ax.set_xticklabels(CORE_EXPERIMENTS, rotation=20, ha='right')
        ax.set_title(model.upper(), fontsize=13, fontweight='bold')
        ax.set_ylabel('MAE (m)  ↓ lower is better')
        finite = [v for v in c_vals + n_vals if not np.isnan(v)]
        ax.set_ylim(0, max(finite) * 1.2 if finite else 10)
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(axis='y', alpha=0.3)

    fig.suptitle('BS Placement Comparison — Mean Absolute Error',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    out_path = out_dir / 'mae_comparison.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[OK] {out_path}')


def plot_mae_gain_comparison(center: pd.DataFrame, ne: pd.DataFrame, out_dir: Path):
    """Side-by-side bar charts: AoA MAE reduction and history MAE reduction per placement."""
    gain_specs = [
        ('AoA MAE Reduction\n(BASE_H − BASE_A_H)', 'BASE_H', 'BASE_A_H'),
        ('History MAE Reduction\n(BASE − BASE_H)',  'BASE',   'BASE_H'),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))

    bar_labels  = ['Center\nXGBoost', 'Center\nRF', 'NE\nXGBoost', 'NE\nRF']
    bar_colors  = [_COLOR_CENTER, _COLOR_CENTER, _COLOR_NE, _COLOR_NE]
    bar_hatches = ['', '//', '', '//']

    for ax, (title, exp_hi_mae, exp_lo_mae) in zip(axes, gain_specs):
        vals = []
        for df in [center, ne]:
            for model in MODELS:
                mdf = df[df['model'] == model].set_index('experiment')['mae_m']
                # reduction = positive when the second exp has lower MAE
                vals.append(mdf.get(exp_hi_mae, np.nan) - mdf.get(exp_lo_mae, np.nan))

        bars = ax.bar(bar_labels, vals, color=bar_colors,
                      hatch=bar_hatches, edgecolor='white', linewidth=1.2, alpha=0.85)
        for bar, v in zip(bars, vals):
            if not np.isnan(v):
                ax.text(bar.get_x() + bar.get_width() / 2, v + 0.02,
                        f'−{v:.2f} m', ha='center', va='bottom',
                        fontsize=9, fontweight='bold')

        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_ylabel('MAE reduction (m)  ↑ larger is better')
        finite = [v for v in vals if not np.isnan(v)]
        ax.set_ylim(0, (max(finite) if finite else 5) * 1.3)
        ax.grid(axis='y', alpha=0.3)
        ax.tick_params(axis='x', labelsize=9)

    fig.suptitle('MAE Gain Attribution: AoA vs History — Center BS vs NE BS',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    out_path = out_dir / 'mae_gain_comparison.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[OK] {out_path}')


def plot_mae_heatmap_comparison(center_dir: Path, ne_dir: Path, out_dir: Path,
                                center_data_dir: Path | None = None,
                                ne_data_dir: Path | None = None,
                                experiments: tuple = ('BASE_H', 'BASE_A_H')):
    """Scatter MAE maps, 2 rows × 2 columns (experiment × placement), shared scale per row."""
    n_rows = len(experiments)
    fig, axes = plt.subplots(n_rows, 2, figsize=(13, 5.5 * n_rows))
    if n_rows == 1:
        axes = axes[None, :]

    bs_center = _bs_position(center_data_dir)
    bs_ne     = _bs_position(ne_data_dir)

    for row, exp in enumerate(experiments):
        c_df = _load_mae_heatmap(center_dir, exp)
        n_df = _load_mae_heatmap(ne_dir, exp)

        # Shared vmax for this row (95th percentile across both placements)
        all_maes = []
        for df in [c_df, n_df]:
            if df is not None:
                all_maes.extend(df['mae_m'].dropna().tolist())
        vmax = float(np.percentile(all_maes, 95)) if all_maes else 10.0

        for col, (df, label, bs_pos) in enumerate([
            (c_df, 'Center BS', bs_center),
            (n_df, 'NE BS',     bs_ne),
        ]):
            ax = axes[row, col]
            if df is None:
                ax.text(0.5, 0.5, 'No data', ha='center', va='center',
                        transform=ax.transAxes, fontsize=12)
                ax.set_title(f'{exp} — {label}', fontweight='bold')
                continue

            sc = ax.scatter(df['x'], df['y'], c=df['mae_m'], cmap='RdYlGn_r',
                            s=130, vmin=0, vmax=vmax, edgecolors='none', zorder=2)
            cbar = plt.colorbar(sc, ax=ax)
            cbar.set_label('MAE (m)')

            if bs_pos is not None:
                ax.scatter([bs_pos[0]], [bs_pos[1]], marker='^', s=160,
                           color='black', edgecolors='white', linewidths=1.5,
                           zorder=5, label='Serving BS')
                ax.legend(loc='lower right', fontsize=8)

            ax.set_title(f'{exp} — {label}', fontweight='bold')
            ax.set_xlabel('X (m)')
            ax.set_ylabel('Y (m)')
            ax.set_aspect('equal')
            ax.grid(alpha=0.2)

        # Shared scale note
        axes[row, 0].set_title(
            f'{experiments[row]} — Center BS  (scale 0–{vmax:.1f} m)', fontweight='bold')
        axes[row, 1].set_title(
            f'{experiments[row]} — NE BS  (scale 0–{vmax:.1f} m)', fontweight='bold')

    fig.suptitle('Spatial MAE Comparison — XGBoost (shared colour scale per row)',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    out_path = out_dir / 'mae_heatmap_comparison.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[OK] {out_path}')


def save_comparison_summary(center: pd.DataFrame, ne: pd.DataFrame, out_dir: Path):
    c = (center[center['experiment'].isin(CORE_EXPERIMENTS)]
         [['model', 'experiment', 'accuracy_%', 'mae_m']].copy())
    n = (ne[ne['experiment'].isin(CORE_EXPERIMENTS)]
         [['model', 'experiment', 'accuracy_%', 'mae_m']].copy())

    merged = c.merge(n, on=['model', 'experiment'], suffixes=('_center', '_ne'))
    merged['delta_acc_pp'] = (merged['accuracy_%_ne'] - merged['accuracy_%_center']).round(2)
    merged['delta_mae_m']  = (merged['mae_m_ne']      - merged['mae_m_center']).round(3)

    # Sort by model then experiment order
    exp_order = {e: i for i, e in enumerate(CORE_EXPERIMENTS)}
    merged['_ord'] = merged['experiment'].map(exp_order)
    merged = merged.sort_values(['model', '_ord']).drop(columns='_ord')

    out_path = out_dir / 'comparison_summary.csv'
    merged.round(3).to_csv(out_path, index=False)
    print(f'[OK] {out_path}')

    # Print a readable table
    print('\nComparison summary (XGBoost):')
    xgb = merged[merged['model'] == 'xgboost'][
        ['experiment', 'accuracy_%_center', 'accuracy_%_ne', 'delta_acc_pp',
         'mae_m_center', 'mae_m_ne', 'delta_mae_m']
    ].to_string(index=False)
    print(xgb)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args():
    parser = argparse.ArgumentParser(
        description='Compare center BS vs NE BS placement experiments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python compare_placements.py
  python compare_placements.py \\
    --center-dir results/multi_user_voronoi_15x15 \\
    --ne-dir     results/ne_bs_voronoi_15x15 \\
    --out-dir    results/placement_comparison
""")
    parser.add_argument('--center-dir', default=str(PROJECT_ROOT / 'results' / 'multi_user_voronoi_15x15'),
                        help='Results directory for the center-BS experiment')
    parser.add_argument('--ne-dir', default=str(PROJECT_ROOT / 'results' / 'ne_bs_voronoi_15x15'),
                        help='Results directory for the NE-BS experiment')
    parser.add_argument('--out-dir', default=str(PROJECT_ROOT / 'results' / 'placement_comparison'),
                        help='Output directory for comparison plots and CSV')
    parser.add_argument('--center-data-dir', default=None,
                        help='(optional) Simulation data dir for center BS — enables BS markers')
    parser.add_argument('--ne-data-dir', default=None,
                        help='(optional) Simulation data dir for NE BS — enables BS markers')
    return parser.parse_args()


def main():
    args = _parse_args()
    center_dir = Path(args.center_dir)
    ne_dir     = Path(args.ne_dir)
    out_dir    = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f'Center BS : {center_dir}')
    print(f'NE BS     : {ne_dir}')
    print(f'Output    : {out_dir}\n')

    center = _load_summary(center_dir)
    ne     = _load_summary(ne_dir)

    plot_accuracy_comparison(center, ne, out_dir)
    plot_gain_comparison(center, ne, out_dir)
    plot_mae_comparison(center, ne, out_dir)
    plot_mae_gain_comparison(center, ne, out_dir)
    center_data = Path(args.center_data_dir) if args.center_data_dir else None
    ne_data     = Path(args.ne_data_dir)     if args.ne_data_dir     else None
    plot_mae_heatmap_comparison(center_dir, ne_dir, out_dir,
                                center_data_dir=center_data, ne_data_dir=ne_data)
    save_comparison_summary(center, ne, out_dir)

    print(f'\n[OK] All outputs written to {out_dir}')


if __name__ == '__main__':
    main()
