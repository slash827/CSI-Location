# Session Summary — 2026-03-10

## Overview

This session covered two main themes:
1. **Documentation corrections** — fixing AoA multi-user results that had been recorded from an oracle (no-noise) run instead of the realistic noisy run
2. **Voronoi accuracy map visualisation** — designing and generating spatial accuracy heatmaps with Voronoi cell segmentation for both the single-user 10×10 and multi-user 15×15 experiments

---

## 1. Documentation Corrections

### Problem

The previously recorded AoA accuracy numbers in all documentation files (99.9% / 100% / 95.9%) were taken from an oracle run where no AoA noise was applied. The actual realistic runs (4°/5° std noise) produce substantially lower values. These inflated numbers misrepresented the multi-user experiment findings.

### Actual Noisy Results (from `results_summary.csv`)

| Metric | RF | XGBoost |
|---|---|---|
| E5 (static + AoA, h=0) | 77.3% / 0.555 m | 82.2% / 0.439 m |
| E6 (transitions + AoA, h=3) | 77.1% / 0.526 m | 83.6% / 0.388 m |
| E7 (transitions + AoA + device, h=3) | 79.3% / 0.471 m | 84.9% / 0.440 m |
| Cross-user E6 (U5 held out) | 72.8% / 0.643 m | 76.7% / 0.540 m |

### Files Corrected

- **`docs/METHODOLOGY_AND_RESULTS.md`**
  - Section 9 Key Finding #10: updated pooled and cross-user AoA numbers
  - Section 10.6 Key Findings 6–8: revised narrative (pooled accuracy is *below* per-device ceiling due to RSS/SINR heterogeneity penalising the channel-only models, not above it)
  - Data inventory: fixed "E6: 100.0%" entry
  - **Added Section 13**: consolidated comparison tables (5 sub-tables covering single-user classification, single-user regression, multi-user all experiments, AoA impact summary, grid-scale comparison)

- **`TASKS.md`**
  - Phase 6g table: corrected all four AoA experiment rows
  - Fixed key-findings bullets: revised "negligible impact" to "major impact"

- **`docs/PRESENTATION_SLIDES.md`**
  - Result 7 slide: replaced oracle-inflated framing with realistic pooled numbers
  - Cross-user table: expanded to show both RF and XGBoost accuracy
  - Summary finding #8: corrected numbers throughout

---

## 2. Voronoi Accuracy Map Visualisation

### Design

The visualisation approach adds three layers on top of the existing per-grid-point accuracy scatter plot:

1. **Cell background** — 400×400 meshgrid, each pixel assigned to nearest Voronoi centre via `cdist`, rendered with `pcolormesh(alpha=0.15)` using a `ListedColormap`
2. **Cell boundaries** — `ax.contour` at integer+0.5 levels on the integer cell-index mesh — draws exact Voronoi boundaries without requiring polygon clipping
3. **Centroid labels** — mean position of all grid points in each cell; rendered as `ax.text` with `boxstyle='round'` bbox for legibility

### 10×10 Single-User (analyze_voronoi_cells.py)

- Modified `plot_spatial_accuracy()` in `src/python/analyze_voronoi_cells.py`
- Added `import matplotlib.colors as mcolors` at module level
- Replaced star-marker + offset-annotation cell labels with centroid-based labels
- Verified output visually — confirmed correct segmentation

### 15×15 Multi-User (multi_user_pipeline.py)

- Rewrote `plot_voronoi_accuracy_map()` in `src/python/multi_user_pipeline.py`
- Added support for loading cell names and centres from an external reference simulation (`sim_data_voronoi_2026-03-02_08-12-13/simulation_data.mat`), since the flat multi-user `.mat` files do not contain `voronoi_names` or `voronoi_centers`
- Three-tier fallback for centres: caller override → mat file → mean-position derivation from DataFrame
- Three-tier fallback for names: caller parameter → mat file → `C{id}` generic labels
- Added `exp_key` parameter (default `'E2'`) to select which experiment result to plot
- Added `out_filename` parameter (default `'voronoi_accuracy_map.png'`) to allow saving distinct files per run

### Standalone Generation Script (gen_voronoi_map.py)

Created `src/python/gen_voronoi_map.py` — a standalone script that:
- Loads cell names and centres from the reference simulation mat file
- Builds feature sets once and reuses across models (avoids redundant history-stacking)
- Runs all desired model/experiment combinations
- Generates all output plots in a single invocation

Current configuration produces **4 plots**:

| Output file | Model | Experiment | Acc | MAE |
|---|---|---|---|---|
| `voronoi_accuracy_map_rf_E2.png` | RF | E2 (RSS+SINR, h=3) | 52.5% | 4.007 m |
| `voronoi_accuracy_map_rf_E5.png` | RF | E5 (RSS+SINR+AoA, h=0) | 77.3% | 0.555 m |
| `voronoi_accuracy_map_xgboost_E2.png` | XGBoost | E2 (RSS+SINR, h=3) | 50.4% | 4.526 m |
| `voronoi_accuracy_map_xgboost_E5.png` | XGBoost | E5 (RSS+SINR+AoA, h=0) | 82.2% | 0.439 m |

All output saved to: `results/multi_user_voronoi_15x15/`

---

## 3. Per-Cell Accuracy Analysis

Examining the XGBoost E2 results from `per_cell_breakdown.csv`:

| Cell | Propagation model | Accuracy | MAE | Notes |
|---|---|---|---|---|
| park | UMi_LOS | **62.6%** | 3.47 m | Only cell in northern half of grid |
| shopping_center | UMi_NLOS | 52.1% | 6.01 m | Adjacent to residential → mutual confusion |
| residential | UMi_NLOS | 45.7% | 6.04 m | Adjacent to shopping_center |
| **highway** | **RMa_LOS** | **37.9%** | 4.84 m | Worst: flat LOS fingerprint + interference zone |

### Why highway is worst (E2)

Two compounding causes:
1. **RMa_LOS = featureless fingerprint** — under Rural Macro LOS, the dominant signal is a single clean ray. No rich multipath means grid points 2 m apart look nearly identical to the classifier. In contrast, UMi_NLOS cells have dense scattering, giving each location a unique multipath pattern.
2. **Interference gradient overlap** — the serving BS is at `[19,19,10]` and interferer IBS-2 is at `[19,-11,10]`. The highway cell sits at `y ≈ 8`, squarely between them, creating ambiguous SINR fingerprints.

### AoA rescues highway (E5)

| Cell | E2 acc | E5 acc | Gain |
|---|---|---|---|
| highway | 37.9% | 76.5% | **+38.6 pp** |
| residential | 45.7% | 78.9% | +33.2 pp |
| shopping_center | 52.1% | 81.0% | +28.9 pp |
| park | 62.6% | 88.6% | +26.0 pp |

Highway benefits most from AoA — confirming that the angle dimension provides spatial diversity that RSS/SINR cannot in an RMa_LOS environment.

---

## 4. Experiment Design Reference (E1–E7)

| Exp | Features | History h | AoA | Device params |
|---|---|---|---|---|
| E1 | RSS + SINR | 0 | No | No |
| E2 | RSS + SINR stacked | 3 | No | No |
| E3 | E2 + device params | 3 | No | Yes (n_ant, gain, height) |
| E4 | E2 + user_id | 3 | No | Oracle identity |
| E5 | RSS + SINR + AoA | 0 | Yes | No |
| E6 | RSS + SINR + AoA stacked | 3 | Yes | No |
| E7 | E6 + device params | 3 | Yes | Yes |

The design is a 2×2 ablation (history × AoA) with E3/E4 probing heterogeneity corrections on E2, and E7 as the full-featured upper bound.

---

## Files Modified

| File | Change |
|---|---|
| `docs/METHODOLOGY_AND_RESULTS.md` | Corrected Sections 9, 10.6, data inventory; added Section 13 |
| `TASKS.md` | Corrected Phase 6g table and findings |
| `docs/PRESENTATION_SLIDES.md` | Corrected Result 7 slide and Summary |
| `src/python/analyze_voronoi_cells.py` | Rewrote `plot_spatial_accuracy()` with cell segmentation |
| `src/python/multi_user_pipeline.py` | Rewrote `plot_voronoi_accuracy_map()` with segmentation + `exp_key`/`out_filename` params |
| `src/python/gen_voronoi_map.py` | Created standalone 4-plot generation script |

## Outputs Generated

```
results/multi_user_voronoi_15x15/
  voronoi_accuracy_map_rf_E2.png
  voronoi_accuracy_map_rf_E5.png
  voronoi_accuracy_map_xgboost_E2.png
  voronoi_accuracy_map_xgboost_E5.png
  voronoi_accuracy_map.png          (XGBoost E2, from earlier run)
  voronoi_accuracy_map_E5.png       (XGBoost E5, from earlier run)
```
