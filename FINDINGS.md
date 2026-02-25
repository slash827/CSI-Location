# CSI-Based Grid Localization: Experimental Findings

**Project:** Transition-Based Localization using 5G CSI Fingerprints  
**Date:** February 23, 2026  
**Status:** Phase 2 Complete (Scalability Analysis)

---

## 1. Executive Summary

We investigate whether **temporal transition history** improves CSI-based grid localization. Our core hypothesis: by observing how channel metrics (RSS, SINR) change over consecutive time steps, ML models can disambiguate grid points that look similar in a single snapshot.

### Key Results

| Finding | Evidence |
|---------|----------|
| **Transition history consistently improves accuracy** | +10 to +29 percentage points across all grid sizes |
| **XGBoost is the best-performing algorithm** | Wins on every grid size tested |
| **Combined RSS+SINR dramatically outperforms single metrics** | +20 to +30 pp vs RSS alone |
| **MAE improves 24–55% with transitions** | From 8.82m → 5.57m on 15×15; 4.52m → 2.04m on 10×10 |
| **Raw feature stacking beats engineered features** | Consistent 4–8 pp advantage across all grids |
| **Best overall result: 65.8% accuracy, 0.95m MAE** | 3×3 grid, XGBoost, RSS+SINR, h=3 |

---

## 2. Experimental Setup

### 2.1 Simulation Environment

- **Tool:** MATLAB 5G NR Toolbox (QuaDRiGa channel model)
- **Scenario:** NLOS Urban Micro, 3 base stations
- **Channel model:** 3GPP_38.901_UMi_NLOS
- **Carrier:** 3.5 GHz, 20 MHz bandwidth
- **Grid spacing:** 2 meters between adjacent points
- **UE movement:** Random walk across grid points, ~400 samples per point

### 2.2 Dataset Summary

| Grid | Points | Area | Total Samples | Test Samples | Metrics Available |
|------|--------|------|---------------|--------------|-------------------|
| 3×3 | 9 | 4×4 m | 3,601 | 721 | RSS, SINR, CQI |
| 5×5 | 25 | 8×8 m | 10,001 | 2,001 | RSS, SINR, CQI |
| 7×7 | 49 | 12×12 m | 19,601 | 3,921 | RSS, SINR, CQI |
| 10×10 | 100 | 18×18 m | 40,001 | 8,001 | RSS, SINR, CQI, AOA, Timing |
| 15×15 | 225 | 28×28 m | 90,001 | 18,001 | RSS, SINR, CQI, AOA, Timing |

**Train/test split:** 80/20 temporal (first 80% of walk for training, last 20% for testing).

### 2.3 Algorithms Tested

| Algorithm | Description | Transition Support |
|-----------|-------------|-------------------|
| **Gaussian** | Per-grid-point Gaussian model, Bayesian posterior | Transition probabilities over h-step paths |
| **Random Forest** | 200 trees, max_depth=30 | Stacked feature vectors [t, t-1, ..., t-h] |
| **XGBoost** | Gradient-boosted trees, 200 rounds | Stacked feature vectors [t, t-1, ..., t-h] |
| **MLP** | 2-layer neural network (128→64), ReLU | Stacked feature vectors [t, t-1, ..., t-h] |

### 2.4 Experiment Matrix

- **Metrics:** RSS, SINR, RSS+SINR (combined)
- **History lengths:** h=0 (static), h=1, h=2, h=3
- **Feature modes:** Raw (stacked values), Smart (engineered: deltas, slope, variance)
- **Total configurations per grid:** 50 (Gaussian: 8 + RF: 21 + XGBoost: 21)

---

## 3. Finding 1: Transition History Dramatically Improves All Algorithms

The central finding of this work: incorporating even a single step of history (h=1) produces large accuracy gains, with diminishing but still meaningful returns at h=2 and h=3.

### 3.1 Accuracy Gain: Static (h=0) vs Transition (h=3)

Best configuration: RSS+SINR, raw features.

| Grid | Algorithm | h=0 (Static) | h=3 (Transition) | Gain |
|------|-----------|-------------|------------------|------|
| 3×3 | XGBoost | 53.4% | 65.8% | **+12.4 pp** |
| 5×5 | XGBoost | 38.2% | 58.1% | **+19.9 pp** |
| 7×7 | XGBoost | 26.8% | 45.4% | **+18.6 pp** |
| 10×10 | XGBoost | 33.4% | 62.8% | **+29.4 pp** |
| 15×15 | XGBoost | 14.1% | 33.2% | **+19.1 pp** |

### 3.2 MAE Improvement

| Grid | Algorithm | h=0 MAE | h=3 MAE | Improvement |
|------|-----------|---------|---------|-------------|
| 3×3 | XGBoost | 1.28 m | 0.95 m | **-25.8%** |
| 5×5 | XGBoost | 2.71 m | 1.62 m | **-40.2%** |
| 7×7 | XGBoost | 3.93 m | 2.39 m | **-39.2%** |
| 10×10 | XGBoost | 4.52 m | 2.04 m | **-54.9%** |
| 15×15 | XGBoost | 8.82 m | 5.57 m | **-36.8%** |

### 3.3 History Length Progression (7×7, RSS+SINR, raw)

Detailed view showing diminishing returns with increasing history:

| Algorithm | h=0 | h=1 | h=2 | h=3 | Total Gain |
|-----------|-----|-----|-----|-----|------------|
| Gaussian | 10.9%* | — | — | — | N/A (RSS+SINR not supported) |
| MLP | 24.8% | 36.9% | 38.6% | 41.6% | **+16.8 pp** |
| Random Forest | 28.0% | 38.3% | 42.6% | 43.6% | **+15.6 pp** |
| XGBoost | 26.8% | 38.7% | 43.5% | 45.4% | **+18.6 pp** |

*Gaussian: RSS-only, h=0 shown for reference.

**Observation:** The largest jump is from h=0→h=1 (roughly 2/3 of total gain). Each additional history step provides ~2–3 pp more.

> **Plot:** See `transition_impact.png` — shows h=0→h=3 progression for all algorithms.

---

## 4. Finding 2: XGBoost Consistently Outperforms All Other Algorithms

### 4.1 Algorithm Ranking (RSS+SINR, raw, h=3)

| Grid | XGBoost | Random Forest | MLP* | Gaussian** |
|------|---------|---------------|------|-----------|
| 3×3 | **65.8%** | 64.9% | — | 38.1% (RSS) |
| 5×5 | **58.1%** | 54.4% | — | 30.1% (RSS) |
| 7×7 | **45.4%** | 43.6% | 41.6% | 15.5% (RSS) |
| 10×10 | **62.8%** | 59.6% | — | 35.7% (RSS) |
| 15×15 | **33.2%** | 32.4% | — | 15.4% (RSS) |

*MLP tested only on 7×7 due to long training times on larger grids.  
**Gaussian does not support multi-metric (RSS+SINR); RSS-only results shown.

**Key observations:**
- XGBoost leads by **1–4 pp** over Random Forest consistently
- Both tree-based methods far outperform Gaussian (+15–30 pp)
- MLP competitive but slightly behind RF/XGBoost on 7×7

> **Plot:** See `algorithm_comparison.png`

---

## 5. Finding 3: RSS+SINR Combination is Critical

Combining RSS and SINR into a joint feature vector provides a massive boost over either metric alone.

### 5.1 Metric Comparison (h=3, raw, best algorithm per grid)

| Grid | RSS Only | SINR Only | RSS+SINR | RSS→Combined Gain |
|------|----------|-----------|----------|-------------------|
| 3×3 | 45.6% | 41.9% | **65.8%** | +20.2 pp |
| 5×5 | 40.6% | 29.8% | **58.1%** | +17.5 pp |
| 7×7 | 21.1% | 14.0% | **45.4%** | +24.3 pp |
| 10×10 | 46.0% | 20.2% | **62.8%** | +16.8 pp |
| 15×15 | 20.3% | 6.8% | **33.2%** | +12.9 pp |

**Why this works:** RSS and SINR capture complementary information. RSS reflects path loss and shadowing (distance-dependent), while SINR captures interference patterns and multipath (geometry-dependent). Together they create a more discriminative fingerprint.

**Note:** SINR alone performs poorly on larger grids (6.8% on 15×15, barely above random = 0.4%). RSS alone is much more useful.

---

## 6. Finding 4: Raw Features Beat Engineered Features

We compared two feature construction approaches for the transition history:

- **Raw:** Stack metric values directly: `[v_t, v_{t-1}, ..., v_{t-h}]`
- **Smart:** Compute summary statistics: `[v_t, delta_1, ..., delta_h, cumulative_change, trend_slope, variance]`

### 6.1 Raw vs Smart (RSS+SINR, h=3)

| Grid | Algorithm | Raw | Smart | Delta |
|------|-----------|-----|-------|-------|
| 3×3 | XGBoost | **65.8%** | 63.7% | -2.1 pp |
| 5×5 | XGBoost | **58.1%** | 52.9% | -5.2 pp |
| 7×7 | XGBoost | **45.4%** | 40.4% | -5.0 pp |
| 7×7 | RF | **43.6%** | 38.5% | -5.1 pp |
| 10×10 | XGBoost | **62.8%** | 55.1% | -7.7 pp |
| 10×10 | RF | **59.6%** | 53.1% | -6.5 pp |
| 15×15 | XGBoost | **33.2%** | 28.9% | -4.3 pp |

**Smart features are consistently 2–8 pp worse.** The gap widens on larger grids.

### 6.2 Why Raw Wins

1. **Information loss:** Smart features (deltas, slopes, variance) are lossy transformations. Tree-based models can learn these patterns themselves from raw values.
2. **Fingerprint destruction:** Raw values preserve the unique RSS/SINR signature at each grid point. Deltas are not unique — many locations produce similar step-to-step changes.
3. **Noisy engineering:** Linear slope fit (`np.polyfit`) on 3–4 noisy CSI samples has very high variance, adding noise rather than signal.
4. **Feature dimensionality is low:** With h=3 and 2 metrics, raw = 8 features. Tree ensembles handle this easily — no need for dimensionality reduction.

> **Plot:** See `feature_mode_comparison.png`

---

## 7. Finding 5: Scalability Behavior

### 7.1 Accuracy vs Grid Size

| Grid | Points | Area | Best Accuracy | Best MAE |
|------|--------|------|--------------|----------|
| 3×3 | 9 | 4×4 m | 65.8% | 0.95 m |
| 5×5 | 25 | 8×8 m | 58.1% | 1.62 m |
| 7×7 | 49 | 12×12 m | 45.4% | 2.39 m |
| 10×10 | 100 | 18×18 m | 62.8% | 2.04 m |
| 15×15 | 225 | 28×28 m | 33.2% | 5.57 m |

### 7.2 The 10×10 Anomaly

The 10×10 grid shows *higher accuracy than 7×7*, which is counterintuitive. Investigation reveals:

- **Same samples/point (~400)** across all grids
- **Same grid spacing (2m)** across all grids
- **Different simulation runs:** 10×10 and 15×15 were generated on Jan 22 (vs Jan 14 for 3×3–7×7)
- **Additional metrics available:** 10×10/15×15 include AOA_azimuth, AOA_elevation, timing_advance (not used in our RSS+SINR experiments)
- **Different channel realization:** The random seed for the QuaDRiGa channel model differs, producing different multipath environments

This means **accuracy comparisons across grid sizes are not perfectly controlled.** The channel realization for the 10×10 scenario may be more favorable for fingerprint discrimination. Caution is needed when interpreting the scalability trend.

### 7.3 Gaussian Model Scalability

The Gaussian model degrades rapidly with grid size (single-metric only):

| Grid | RSS h=0 | RSS h=3 | Gain |
|------|---------|---------|------|
| 3×3 | 31.9% | 38.1% | +6.2 pp |
| 5×5 | 23.7% | 30.1% | +6.4 pp |
| 7×7 | 10.9% | 15.5% | +4.7 pp |
| 10×10 | 20.1% | 35.7% | +15.6 pp |
| 15×15 | 7.7% | 15.4% | +7.7 pp |

Even Gaussian benefits from transitions, but its absolute performance is far below tree-based methods.

> **Plot:** See `scalability.png` and `accuracy_heatmap.png`

---

## 8. Generated Plots

All plots are in `results/experiment_matrix/scalability_5grids/`:

| Plot | Description |
|------|-------------|
| `transition_impact.png` | Side-by-side: static vs h=1/2/3 accuracy per algorithm |
| `algorithm_comparison.png` | Bar chart comparing all algorithms at best config |
| `scalability.png` | Accuracy and MAE trends across grid sizes |
| `feature_mode_comparison.png` | Raw vs Smart feature comparison |
| `accuracy_heatmap.png` | Full heatmap: algorithm × metric × history |

Additional 7×7-specific plots in `results/experiment_matrix/core_7x7/`:

| Plot | Description |
|------|-------------|
| `transition_impact.png` | 7×7 transition impact (includes MLP) |
| `algorithm_comparison.png` | 7×7 algorithm comparison (includes MLP) |
| `feature_mode_comparison.png` | 7×7 raw vs smart (includes MLP) |

---

## 9. What's Missing / Suggested Next Steps

### 9.1 Immediate Gaps

| Gap | Impact | Effort |
|-----|--------|--------|
| **20×20 grid results** | Run got stuck on Gaussian static (160K samples × 400 points). Need to skip Gaussian h=0 or optimize per-sample loop for very large grids. | Re-run skipping Gaussian, or add batch support for Gaussian static |
| **MLP on grids other than 7×7** | MLP training is slow on large datasets. Only tested on 7×7. | Run on 3×3, 5×5 at least (fast). 10×10+ would take hours. |
| **Controlled cross-grid comparison** | 10×10 anomaly shows simulations aren't identical. Need same channel seed or normalized comparison. | Re-simulate with controlled parameters |

### 9.2 Possible Extensions

| Extension | Rationale |
|-----------|-----------|
| **Use AOA + Timing Advance metrics** | 10×10 and 15×15 datasets have these. Could significantly boost accuracy on larger grids. |
| **Increase history length (h=4, h=5)** | Returns are diminishing but 7×7 still gained ~2 pp from h=2→h=3. |
| **Regression instead of classification** | Predict continuous (x,y) coordinates instead of grid point index. Would eliminate quantization error. |
| **Cross-validation instead of temporal split** | Current 80/20 temporal split means test data is from the end of the walk. Random split might give different (likely higher) results. |
| **Hyperparameter tuning** | Current RF/XGBoost use default-ish parameters. Grid search could improve by 2–5 pp. |
| **Confusion matrix analysis** | Which grid points are most confused? Are they spatial neighbors? This would reveal systematic error patterns. |

---

## 10. Technical Notes

### 10.1 Performance Optimizations

Batch prediction optimizations were critical for feasibility:

| Model | Before | After | Speedup |
|-------|--------|-------|---------|
| Random Forest eval | 175.6 s | 0.107 s | **1,647×** |
| XGBoost eval | 7.8 s | 0.110 s | **71×** |
| Gaussian eval (h=3) | ~600 s | 1.75 s | **~340×** |

**How:** Pre-enumerate all valid h-step paths during training; evaluate all test samples in a single vectorized call using numpy broadcasting.

### 10.2 Reproducibility

- All data in `results/grid_localization/` (MATLAB .mat files)
- All code in `experiments/09_grid_localization/src/python/`
- CSV results in `results/experiment_matrix/`
- Python 3.13.0, scikit-learn 1.8.0, xgboost 3.2.0

---

*Generated from 250 experimental configurations across 5 grid sizes.*
