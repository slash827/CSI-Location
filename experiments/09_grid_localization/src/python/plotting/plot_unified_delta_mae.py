"""
plot_unified_delta_mae.py
-------------------------
Dual-panel figure showing the accuracy gain from transition history across every
model family, as a function of history depth h.

Panel A: absolute 2D MAE against h.
Panel B: the same curves normalised to each family's own h=0 baseline, which is
the comparison the universality claim actually rests on - families start from very
different baselines, so only the relative change is comparable across them.

The curves are read from a `history_sweep_all_models_summary.json` produced by
`experiments_ablation/history_sweep_all_models.py`, so every curve comes from one
protocol: the Campaign B disjoint-user split, 2D MAE, identical features and
identical early stopping for all seven families.

    Earlier versions of this script hardcoded four curves drawn from three
    different experiments. The GRU curve in particular came from a single-user
    exploration with a chronological split, which interleaves test samples between
    training samples along one walk; it read 8.5 m and a -50% gain where the
    disjoint-user protocol gives 18.5 m. Those numbers are not comparable with the
    rest and must not come back.

Usage:
    python plot_unified_delta_mae.py --summary <path to summary json>
    python plot_unified_delta_mae.py            # newest summary under results/
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = Path(__file__).resolve().parents[5]
FIGURES_DIR = PROJECT_ROOT / "docs" / "figures"

# one visual identity per family, stable across regenerations
STYLE = {
    "knn":            dict(color="#8c564b", marker="v", linestyle=(0, (3, 1, 1, 1)), lw=2.0),
    "random_forest":  dict(color="#7570b3", marker="^", linestyle="-.", lw=2.2),
    "xgboost":        dict(color="#d95f02", marker="s", linestyle="--", lw=2.2),
    "cnn":            dict(color="#1f77b4", marker="o", linestyle="-",  lw=2.5),
    "gru":            dict(color="#2ca02c", marker="D", linestyle=":",  lw=2.5),
    "cnn_attn":       dict(color="#e7298a", marker="P", linestyle="-",  lw=2.2),
    "mask_aware_cnn": dict(color="#17becf", marker="X", linestyle="--", lw=2.2),
}
DISPLAY = {
    "knn": "k-NN (instance-based)",
    "random_forest": "Random Forest (bagged trees)",
    "xgboost": "XGBoost (boosted trees)",
    "cnn": "1D-CNN (convolutional)",
    "gru": "GRU (recurrent)",
    "cnn_attn": "CNN + attention",
    "mask_aware_cnn": "Mask-aware CNN",
}
ORDER = ["knn", "random_forest", "xgboost", "cnn", "gru", "cnn_attn", "mask_aware_cnn"]


def find_latest_summary():
    base = REPO_ROOT / "results" / "notebook_experiments" / "multi_user_poc"
    cands = sorted(base.glob("history_sweep_all_models_*/history_sweep_all_models_summary.json"))
    if not cands:
        raise FileNotFoundError(
            "No history_sweep_all_models_summary.json found. Run "
            "experiments_ablation/history_sweep_all_models.py first, or pass --summary.")
    return cands[-1]


def main():
    ap = argparse.ArgumentParser(
        description="Universal delta-MAE history curves, all model families.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python plot_unified_delta_mae.py
  python plot_unified_delta_mae.py --summary results/.../history_sweep_all_models_summary.json
""")
    ap.add_argument('--summary', type=Path, default=None,
                    help='history_sweep_all_models_summary.json (default: newest)')
    ap.add_argument('--out', type=Path,
                    default=FIGURES_DIR / "universal_delta_mae_history_curves.png")
    args = ap.parse_args()

    summary_path = args.summary or find_latest_summary()
    data = json.loads(Path(summary_path).read_text(encoding='utf-8'))
    depths = np.array(data['meta']['depths'])
    spacing = data['meta'].get('grid_spacing_m', 4.0)
    summary = data['summary']
    models = [m for m in ORDER if m in summary] + [m for m in summary if m not in ORDER]

    args.out.parent.mkdir(parents=True, exist_ok=True)

    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6.8), dpi=300)

    # the region every family's optimum falls in, read from the data
    best_hs = [summary[m]['best_h'] for m in models]
    lo_h, hi_h = min(best_hs), max(best_hs)

    # ── Panel A: absolute MAE ────────────────────────────────────────────────
    for name in models:
        s = summary[name]
        maes = np.array([s['mae_by_depth'][f'h{h}'] for h in depths])
        st = STYLE.get(name, dict(color="#666666", marker="o", linestyle="-", lw=2.0))
        ax1.plot(depths, maes, label=DISPLAY.get(name, name), color=st['color'],
                 marker=st['marker'], markersize=7, linestyle=st['linestyle'],
                 linewidth=st['lw'], zorder=4)

    ax1.set_title("A: Absolute positioning error vs. history depth",
                  fontsize=13, fontweight='bold', pad=12)
    ax1.set_xlabel("Transition history depth ($h$ previous steps)",
                   fontsize=11, fontweight='semibold')
    ax1.set_ylabel("2D mean absolute error (m)", fontsize=11, fontweight='semibold')
    ax1.set_xticks(depths)
    ax1.set_xticklabels([f"h={h}\n({spacing * h:.0f} m of path)" for h in depths], fontsize=9)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=9, loc="upper right")

    ax1.annotate(
        "$v \\approx \\Delta r / \\Delta t$ becomes computable\n"
        "displacement constrains the ring",
        xy=(1, max(summary[m]['mae_by_depth']['h1'] for m in models)),
        xytext=(1.6, ax1.get_ylim()[1] - 0.12 * np.ptp(ax1.get_ylim())),
        arrowprops=dict(arrowstyle="->", color="#333333", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff9e6", edgecolor="#e0c068", lw=0.8),
        fontsize=8.5)

    # ── Panel B: normalised gain ─────────────────────────────────────────────
    for name in models:
        s = summary[name]
        dpct = np.array([s['delta_pct_by_depth'][f'h{h}'] for h in depths])
        st = STYLE.get(name, dict(color="#666666", marker="o", linestyle="-", lw=2.0))
        ax2.plot(depths, dpct,
                 label=f"{DISPLAY.get(name, name)}: {-s['gain_pct']:.1f}% at h={s['best_h']}",
                 color=st['color'], marker=st['marker'], markersize=7,
                 linestyle=st['linestyle'], linewidth=st['lw'], zorder=4)

    ax2.axhline(0, color="gray", linestyle="--", alpha=0.7, lw=1)
    if hi_h > lo_h:
        ax2.axvspan(lo_h - 0.4, hi_h + 0.4, color="#e6f2ff", alpha=0.6, zorder=0,
                    label=f"optima, h={lo_h}–{hi_h} ({spacing * lo_h:.0f}–{spacing * hi_h:.0f} m of path)")

    ax2.set_title("B: Relative gain vs. each family's own snapshot baseline (h=0)",
                  fontsize=13, fontweight='bold', pad=12)
    ax2.set_xlabel("Transition history depth ($h$ previous steps)",
                   fontsize=11, fontweight='semibold')
    ax2.set_ylabel("Change in MAE vs. h=0 (%)  [lower is better]",
                   fontsize=11, fontweight='semibold')
    ax2.set_xticks(depths)
    ax2.set_xticklabels([f"h={h}\n({spacing * h:.0f} m of path)" for h in depths], fontsize=9)
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=8.5, loc="lower left")

    v = data['verdict']
    props = dict(boxstyle='round,pad=0.5', facecolor='#f8f9fa', edgecolor='#b0bec5', alpha=0.95)
    ax2.text(0.97, 0.06,
             f"{v['n_improved']}/{v['n_models']} families improve with history\n"
             f"gains span {v['gain_min_pct']:.1f}% to {v['gain_max_pct']:.1f}%\n"
             f"one protocol: disjoint-user split, {data['meta']['n_test_users']} unseen test users",
             transform=ax2.transAxes, fontsize=8.5, verticalalignment='bottom',
             horizontalalignment='right', bbox=props)

    fig.suptitle("Transition history helps every model family "
                 "(Campaign B, 300 users, single macro cell)",
                 fontsize=14, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(args.out, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Figure saved to: {args.out}")
    print(f"     built from: {summary_path}")


if __name__ == '__main__':
    main()
