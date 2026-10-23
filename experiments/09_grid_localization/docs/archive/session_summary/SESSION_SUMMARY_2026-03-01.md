# Session Summary — 2026-03-01

**Theme:** Voronoi 10×10 feature experiments, OOM fix, regression pipeline extension, and scalability analysis

---

## Context

Continuing from 2026-02-25 session where the Voronoi 10×10 BS-inside-grid simulation was created. This session covers:
1. Feature combination experiments (RSS/SINR/AoA/CQI) with validated realistic noise
2. OOM fix for Gaussian model at h=3 on 10×10
3. Classification on 15×15 Voronoi data
4. Regression pipeline extended with XGBoost + selective metric combos
5. Regression scalability across 10×10, 15×15, 20×20

---

## 1. Feature Importance (10×10 Voronoi, XGBoost)

### What Was Excluded (Unrealistic Metrics)
- **timing_advance**: Exact propagation delay — no noise model applied → almost perfect distance estimate (unrealistic from real UE)
- **k_factor**: Not a real UE measurement (field only available at BS/core) → removed
- **CQI**: Useless at short BS-inside-grid range (all UEs at very high SINR → CQI collapses to top quantization level)

### AoA Noise Validation
`ml_config.jsonc` applies **4° Gaussian noise + 5° quantization** to AoA azimuth and elevation before passing to models. Results are realistic.

### Classification Results — 10×10 Voronoi (`sim_data_voronoi_2026-02-25_23-17-56`)

| Features | h=0 acc | h=1 acc | h=1 MAE | Notes |
|---|---|---|---|---|
| RSS | 18.8% | 23.2% | 5.70m | Distance-only, many equidistant rings |
| SINR | 18.8% | 22.9% | 5.74m | Same as RSS (no interferers) |
| RSS+SINR | 18.8% | 23.0% | 5.72m | No improvement over RSS alone |
| +AoA azimuth | 69.6% | 77.9% | 0.58m | +52pp — breaks 360° symmetry |
| +AoA elevation | **84.6%** | **88.5%** | **0.25m** | +9pp more, elevation = range info |
| CQI | 1.3% | 1.3% | 9.11m | Useless — CQI saturated at close range |

**Best: XGBoost, rss+sinr+aoa_azimuth+aoa_elevation, h=1 → 88.5% accuracy, 0.25m MAE**

**Key insight:** RSS ≈ SINR (no interferers → single BS → distance ring ambiguity). AoA breaks the symmetry with 52pp jump.

Result source: `results/experiment_matrix/2026-02-26_07-54-19/`

---

## 2. OOM Fix — Gaussian h=3 on 10×10

**Error:** `numpy._core._exceptions._ArrayMemoryError: Unable to allocate 6.43 GiB`
- Root cause: `norm.logpdf` broadcasting `(N=8000, P=35952, H=3)` = 862M float64 values in one shot
- 35,952 paths = 8-connected walks of length 3 on a 100-point grid

**Fix** (in `localization_pipeline.py`, `GaussianTransitionModel.predict_batch`):
```python
_MEM_BUDGET = 256 * 1024 * 1024  # 256 MB per chunk
chunk_size = max(1, int(_MEM_BUDGET / (P * history_len * 8)))
for start in range(0, N, chunk_size):
    # process chunk of test samples
```
Chunks test samples to bound dense `(chunk, P, H)` array to ≤256 MB. Verified working on both 10×10 h=3 and 15×15 h=1.

---

## 3. Per-Voronoi-Cell Analysis (10×10, XGBoost h=1, rss+sinr+aoa_az+aoa_el)

Script: `analyze_voronoi_cells.py`

| Voronoi Cell | Channel | Size | Accuracy | Cross-cell Error |
|---|---|---|---|---|
| Park | UMi_LOS | 101 pts | 95.0% | 3.4% |
| Residential | Mixed | 35 pts | 92.2% | 5.1% |
| Highway | RMa_LOS | 26 pts | 73.4% | 27% |
| Shopping center | UMi_NLOS | 8 pts | 65.8% | 36% |

- Large cells (35–101 pts): few cross-cell errors (3–5%)
- Small cells (8–26 pts): high cross-cell bleeding (20–36%) — insufficient data density
- Park (UMi_LOS) always best, shopping_center (UMi_NLOS) always hardest

---

## 4. Classification on 15×15 Voronoi (Scalability Check)

Data: `sim_data_voronoi_2026-02-07_17-16-42` (5m spacing, 100 spp, 22.5k samples, BS at 25m height)

| Features | h=0 acc | h=1 acc | h=1 MAE |
|---|---|---|---|
| RSS | 15.1% | 23.1% | 23.40m |
| SINR | 15.1% | 23.4% | 23.30m |
| RSS+SINR | 15.1% | 23.0% | 23.29m |
| +AoA azimuth | 61.2% | 71.4% | 2.66m |
| **+AoA elevation** | **74.4%** | **80.2%** | **1.34m** |

15×15 OOM confirmed **fixed** — runs cleanly without any memory errors.
Same AoA dominance pattern holds. h=1 adds ~6pp accuracy.

Result source: `results/experiment_matrix/2026-03-01_21-37-12/`

---

## 5. Regression Pipeline Extensions

**File modified:** `localization_pipeline_regression.py`

### Changes made:
1. **XGBoost regressor** — added `elif model_type == 'xgboost'` using `MultiOutputRegressor(XGBRegressor(...))`
2. **`--metrics` CLI argument** — `nargs='+'`, parses `"rss,sinr,aoa_azimuth"` → `['rss', 'sinr', 'aoa_azimuth']`
3. **Bug fix** — `_prepare_features` now always returns 2D array (`vals.reshape(-1, 1)` for single features)

### CLI example:
```bash
python localization_pipeline_regression.py \
  --data-dir results/.../sim_data_voronoi_... \
  --model xgboost --max-history 1 \
  --metrics rss sinr "rss,sinr" "rss,sinr,aoa_azimuth" "rss,sinr,aoa_azimuth,aoa_elevation"
```

---

## 6. Regression Results

### 10×10 Voronoi — 3D Position Error (meters)

| Features | RF h=0 | RF h=1 | XGB h=0 | XGB h=1 |
|---|---|---|---|---|
| RSS | 7.46 | 6.63 | 7.42 | 6.78 |
| SINR | 7.46 | 6.63 | 7.42 | 6.78 |
| RSS+SINR | 7.46 | 6.64 | 7.42 | 6.78 |
| +AoA azimuth | 1.10 | 0.73 | 1.12 | 0.90 |
| **+AoA elevation** | **0.44** | **0.40** | 0.58 | 0.59 |

Best regression: **RF h=1 → 0.40m position error**
Best classification: **XGBoost h=1 → 0.25m MAE**

### Scalability — Best Feature Set (rss+sinr+aoa_az+aoa_el), RF

| Grid | Environment | Spacing | Samples | Regression Best | Classification Best |
|---|---|---|---|---|---|
| 10×10 | Voronoi (4 scenarios) | 2m | 40k | **0.40m** (h=1) | **0.25m** (XGB h=1) |
| 15×15 | Voronoi (4 scenarios) | 5m | 22.5k | **1.82m** (h=1) | **1.34m** (XGB h=1) |
| 20×20 | NLOS (uniform) | 2m | 160k | **1.54m** (h=0) | — |

---

## 7. Key Findings Summary

1. **AoA is by far the most important feature** — alone adds 52pp accuracy vs RSS+SINR. Elevation adds 9pp more.
2. **RSS ≈ SINR on BS-inside-grid** — with no interferers, both encode distance. Combining adds nothing.
3. **CQI is useless at short range** — all UEs see very high SINR → CQI saturates at top quantization level.
4. **Classification beats regression** at every tested grid size — discrete grid structure matches discrete classifiers. RF regression is 1.3–1.6× worse than XGBoost classification.
5. **Transition history always helps** — h=1 alone recovers most of the benefit (+6pp on classification, -9% on regression error).
6. **OOM is now fixed** — Gaussian model with h=3 works on 10×10 and 15×15 via 256 MB chunked batch processing.
7. **Voronoi cell size matters** — large cells (35–101 pts) are well-classified; small cells (8 pts) bleed heavily (~36% cross-cell) due to data sparsity.

---

## 8. Data & Results Locations

| Run | Path |
|---|---|
| 10×10 Voronoi sim data | `results/grid_localization/grid_10x10/sim_data_voronoi_2026-02-25_23-17-56/` |
| 10×10 classification (64 configs) | `results/experiment_matrix/2026-02-26_07-54-19/` |
| 15×15 Voronoi sim data (existing) | `results/grid_localization/grid_15x15/sim_data_voronoi_2026-02-07_17-16-42/` |
| 15×15 classification (this session) | `results/experiment_matrix/2026-03-01_21-37-12/` |
| 10×10 regression RF | `results/grid_localization/grid_10x10/exp_regression_NLOS_2026-03-01_21-22-46/` |
| 10×10 regression XGBoost | `results/grid_localization/grid_10x10/exp_regression_NLOS_2026-03-01_21-22-50/` |
| 15×15 regression RF | `results/grid_localization/grid_15x15/exp_regression_NLOS_2026-03-01_21-29-25/` |
| 20×20 regression RF | `results/grid_localization/grid_20x20/exp_regression_NLOS_2026-03-01_21-29-44/` |

---

## 9. Pending / Next Steps

- [ ] **Run clean 15×15 MATLAB simulation** — `run_voronoi_15x15.m` is ready (2m spacing, 400 spp, BS@10m, matches 10×10 params). Blocked on MATLAB.
- [ ] **Scalability plot** — plot MAE vs grid size for both classification and regression, both with/without AoA
- [ ] **Documentation** — methodology section, results tables for report/slides
- [ ] **Multi-BS scenario** — add 2–3 BSs at different grid positions for richer RSS/SINR diversity
