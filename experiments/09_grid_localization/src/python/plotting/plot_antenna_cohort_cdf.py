"""
plot_antenna_cohort_cdf.py
--------------------------
Generates publication-quality Cumulative Distribution Function (CDF) visualization
comparing 2D positioning errors across hardware antenna cohorts (N=4, N=2, N=1)
on the realistic 300-user 5G NR deployment benchmark.

Saves to: docs/figures/antenna_cohort_error_cdf.png
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIGURES_DIR = PROJECT_ROOT / "docs" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = FIGURES_DIR / "antenna_cohort_error_cdf.png"

# Load precomputed test predictions
preds_file = PROJECT_ROOT / "experiments" / "09_grid_localization" / "scratch_test_preds.npz"
if not preds_file.exists():
    preds_file = Path("scratch_test_preds.npz")

if preds_file.exists():
    data = np.load(preds_file)
    preds_raw = data['preds_raw']
    targs = data['targs']
    n_ants = data['n_ants']
    errs_2d = np.linalg.norm(preds_raw - targs, axis=1)
else:
    raise FileNotFoundError(f"Could not find test predictions file: {preds_file}")

# Cohort masks
mask_4ant = (n_ants == 4)
mask_2ant = (n_ants == 2)
mask_multi = (n_ants > 1)
mask_1ant = (n_ants == 1)

errs_4ant = errs_2d[mask_4ant]
errs_2ant = errs_2d[mask_2ant]
errs_multi = errs_2d[mask_multi]
errs_1ant = errs_2d[mask_1ant]

# Setup figure with 2 subplots: Main CDF + Accuracy Reachability Bar Chart
fig, (ax_cdf, ax_bar) = plt.subplots(1, 2, figsize=(15, 6.5), dpi=300, gridspec_kw={'width_ratios': [2.2, 1.2]})

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']

# Helper to compute CDF
def get_cdf(errs):
    sorted_errs = np.sort(errs)
    cdf = np.arange(1, len(sorted_errs) + 1) / len(sorted_errs)
    return sorted_errs, cdf

# Plot CDFs
curves = [
    ("4-Antenna UEs (Flagship)", errs_4ant, "#08519c", "-", 2.5),
    ("2-Antenna UEs (Mid-Tier)", errs_2ant, "#3182bd", "--", 2.2),
    ("Combined Multi-Ant (85% share)", errs_multi, "#006d2c", "-", 3.0),
    ("1-Antenna UEs (IoT / Budget, 15%)", errs_1ant, "#de2d26", "-", 2.8),
    ("Overall Population (All UEs)", errs_2d, "#636363", ":", 2.0),
]

for label, err_cohort, color, ls, lw in curves:
    x_vals, y_vals = get_cdf(err_cohort)
    ax_cdf.plot(x_vals, y_vals * 100, label=f"{label} (Median: {np.median(err_cohort):.1f}m, MAE: {np.mean(err_cohort):.1f}m)",
                color=color, linestyle=ls, linewidth=lw)

# Reference lines
ax_cdf.axvline(10.0, color="#b30000", linestyle="--", alpha=0.7, lw=1.2)
ax_cdf.axvline(15.0, color="#e6550d", linestyle=":", alpha=0.7, lw=1.2)
ax_cdf.axhline(50.0, color="#525252", linestyle="--", alpha=0.5, lw=1.0)
ax_cdf.axhline(90.0, color="#525252", linestyle="--", alpha=0.5, lw=1.0)

# Annotations
ax_cdf.text(10.5, 8, "10m Target\n(3GPP Rel-16)", color="#b30000", fontsize=8.5, fontweight='bold')
ax_cdf.text(82, 51.5, "P50 (Median)", color="#525252", fontsize=8.5, va="bottom")
ax_cdf.text(82, 91.5, "P90 (90th %ile)", color="#525252", fontsize=8.5, va="bottom")

# Visual Callout on the Gap
ax_cdf.annotate(
    "2.3x Error Gap\nDue to Zero AoA\n(Radial smearing)",
    xy=(30.6, 50), xytext=(45, 30),
    arrowprops=dict(arrowstyle="->", color="#de2d26", lw=1.5),
    bbox=dict(boxstyle="round,pad=0.3", facecolor="#fee5d9", edgecolor="#de2d26", lw=0.8),
    fontsize=9, fontweight='bold', color="#a50f15"
)

ax_cdf.set_title("A: Cumulative Distribution Function (CDF) of Positioning Error", fontsize=13, fontweight='bold', pad=12)
ax_cdf.set_xlabel("2D Localization Error (meters)", fontsize=11, fontweight='semibold')
ax_cdf.set_ylabel("Cumulative Percentage of Steps (%)", fontsize=11, fontweight='semibold')
ax_cdf.set_xlim(0, 80)
ax_cdf.set_ylim(0, 102)
ax_cdf.grid(True, linestyle="--", alpha=0.5)
ax_cdf.legend(frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=9.2, loc="lower right")

# ─────────────────────────────────────────────────────────────────────────────
# Panel 2: Target Threshold Reachability Comparison (% of steps achieving target)
# ─────────────────────────────────────────────────────────────────────────────
thresholds = [10.0, 15.0, 20.0]
cohorts = [
    ("4-Antenna", errs_4ant, "#08519c"),
    ("2-Antenna", errs_2ant, "#3182bd"),
    ("Multi-Ant", errs_multi, "#006d2c"),
    ("1-Antenna", errs_1ant, "#de2d26")
]

x_indices = np.arange(len(thresholds))
bar_width = 0.18

for i, (c_name, c_errs, c_col) in enumerate(cohorts):
    pass_pcts = [np.mean(c_errs <= th) * 100 for th in thresholds]
    rects = ax_bar.bar(x_indices + (i - 1.5) * bar_width, pass_pcts, width=bar_width,
                       label=c_name, color=c_col, edgecolor="white", linewidth=0.8)
    for rect in rects:
        h = rect.get_height()
        ax_bar.text(rect.get_x() + rect.get_width() / 2.0, h + 1.0, f"{h:.0f}%",
                    ha='center', va='bottom', fontsize=8, fontweight='bold', color=c_col)

ax_bar.set_title("B: Accuracy Reachability by Tier", fontsize=13, fontweight='bold', pad=12)
ax_bar.set_xlabel("Target Accuracy Threshold", fontsize=11, fontweight='semibold')
ax_bar.set_ylabel("Percentage of Trajectory Steps (%)", fontsize=11, fontweight='semibold')
ax_bar.set_xticks(x_indices)
ax_bar.set_xticklabels([f"< {int(th)}m" for th in thresholds], fontsize=10, fontweight='semibold')
ax_bar.set_ylim(0, 95)
ax_bar.grid(True, axis='y', linestyle="--", alpha=0.5)
ax_bar.legend(frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=9, loc="upper left")

# Summary text at the bottom of Panel B
summary_box = (
    "Summary Findings:\n"
    "• Multi-Antenna: 34% of steps hit <10m; 60% hit <15m\n"
    "• 1-Antenna: Only 10% reach <10m due to missing AoA\n"
    "• Clean separation between smartphone & IoT physics"
)
ax_bar.text(0.5, -0.22, summary_box, transform=ax_bar.transAxes, fontsize=8.5,
            ha='center', va='top', bbox=dict(boxstyle='round,pad=0.5', facecolor='#f8f9fa', edgecolor='#b0bec5', alpha=0.95))

plt.tight_layout()
plt.savefig(OUT_PATH, dpi=300, bbox_inches='tight')
plt.close()

print(f"Per-Device Antenna CDF plot successfully generated at: {OUT_PATH}")
