# Copilot Session Log — February 22-23, 2026

**Environment:** Windows, VS Code + GitHub Copilot (Claude Opus 4.6)  
**Python:** 3.13.0 (venv at `experiments/09_grid_localization/.venv/`)  
**Continuing from:** Claude Code session on separate PC (2026-02-21)

---

## Session Goals
1. Continue the CSI-location experiment on a different PC
2. Fix data paths (simulation data at project root, scripts expected relative paths)
3. Re-run experiment matrix to regenerate CSVs/reports/plots not copied from other PC
4. Optimize slow code for faster iteration

---

## What Was Done

### 1. Project Setup on New Machine

**Problem:** Scripts used relative paths that didn't match where data was stored.  
Data lives at `<project_root>/results/grid_localization/` but scripts expected paths relative to their own location.

**Fix:** Added `PROJECT_ROOT` constant to all 4 Python scripts using `Path(__file__).resolve().parent.parent.parent.parent.parent`:
- `localization_pipeline.py`
- `run_experiment_matrix.py`
- `run_full_pipeline.py`
- `localization_pipeline_regression.py`

**Venv Setup:**
```powershell
cd experiments/09_grid_localization
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Updated `requirements.txt` to include: scikit-learn>=1.0.0, xgboost>=1.5.0, pandas>=1.3.0

---

### 2. Performance Optimization — Batch Prediction (~1000× speedup)

**Problem:** Experiment matrix took 8+ hours for 71 configs on 7×7 grid.  
Root cause: Per-sample `predict()` calls in evaluation loops.

**Analysis of bottlenecks:**
- Gaussian h=3: ~10 minutes per config (nested neighbor path enumeration)
- Random Forest: ~153 seconds per config (per-sample `predict_proba()`)
- XGBoost: ~12 seconds per config
- MLP: ~1 second per config

#### Solution A: GaussianTransitionModel Vectorization

Added `_build_path_arrays()` method during training:
- Pre-enumerates ALL valid h-step paths as numpy arrays
- For 7×7 grid: h=1 → 168 paths, h=2 → 596 paths, h=3 → 2,144 paths

Added `predict_batch()` method:
- Builds delta matrix for all test samples at once: shape `(N, h)`
- Broadcasts `norm.logpdf` across `(N, P, h)` tensor in one call
- Aggregates path scores per grid point with vectorized max

**Result:** h=3 went from ~10 minutes to **1.75 seconds** (~300-500× speedup).

#### Solution B: BaseSklearnModel Batch Prediction

Added `predict_batch()` to `BaseSklearnModel`:
- Builds all feature vectors in a loop (fast — just array ops)
- Calls `classifier.predict(X)` **once** instead of N times
- Returns predictions directly (no need for posterior → argmax)

Added `predict_batch()` override to `XGBoostModel`:
- Same approach but adds `_label_offset` back (XGBoost uses 0-indexed labels)

**Results (verified — batch vs loop produce identical predictions):**
| Model | Per-sample | Batch | Speedup |
|-------|-----------|-------|---------|
| Random Forest | 175.6s | 0.107s | **1,647×** |
| XGBoost | 7.8s | 0.110s | **71×** |
| MLP | ~1s | ~0.05s | ~20× |

#### Solution C: evaluate_static() Batch Path

Updated `evaluate_static()` to check for `predict_batch` method, same as `evaluate_transition()`.

**Net impact:** Full 7×7 matrix (71 configs) runs in ~10 minutes instead of 8+ hours.

---

### 3. Bug Fixes

#### Config Counter Mismatch (75 vs 71)
**Problem:** `run_experiment_matrix.py` counted 75 total configs but only 71 ran.  
**Cause:** The counting loop didn't skip Gaussian + multi-metric (RSS+SINR) combos, but the execution loop did.  
**Fix:** Added `if algo == 'gaussian' and isinstance(metric_spec, list): continue` to the counting loop.

#### Matplotlib Tk/Tcl Error
**Problem:** `plot_comparison_results.py` failed with `_tkinter.TclError: Can't find a usable init.tcl`.  
**Cause:** Python 3.13 venv doesn't have Tk installed.  
**Fix:** Added `matplotlib.use('Agg')` before importing pyplot for headless rendering.

#### Timing Display
**Problem:** Console output only showed `train_time` (misleading — 0.2s for Gaussian while eval took minutes).  
**Fix:** Updated to show both: `(train=0.1s eval=1.6s)`.

---

### 4. Experiment Runs

#### Run 1: Core 7×7 (Re-run with optimizations)
- **Command:**
  ```powershell
  python run_experiment_matrix.py --data-dir "$root\results\grid_localization\grid_7x7\sim_data_NLOS_2026-01-14_23-34-46" --output-dir "$root\results\experiment_matrix\core_7x7" --algorithms gaussian random_forest xgboost mlp --metrics rss sinr "RSS,SINR" --max-history 3 --feature-modes raw smart --split-method temporal
  ```
- **Result:** 71/71 configs completed, all eval times sub-second
- **Output:**
  - `results/experiment_matrix/core_7x7/experiment_results.csv`
  - `results/experiment_matrix/core_7x7/COMPARISON_REPORT.md`
  - `results/experiment_matrix/core_7x7/transition_impact.png`
  - `results/experiment_matrix/core_7x7/algorithm_comparison.png`
  - `results/experiment_matrix/core_7x7/feature_mode_comparison.png`

#### Run 2: Multi-Grid Scalability (Batch A — no MLP on large grids)
- **Decision:** Skip MLP for 10×10, 15×15, 20×20 grids (MLP training takes hours on large datasets)
- **Batch A:** All 6 grids × (Gaussian + RF + XGBoost) — 300 configs
- **Batch B (pending):** 3×3, 5×5, 7×7 × MLP — 21 configs
- **Status:** Running

---

### 5. Key Results (7×7 Grid)

#### Accuracy — RSS+SINR, raw features
| Algorithm | h=0 (Static) | h=1 | h=2 | h=3 | Improvement |
|-----------|-------------|-----|-----|-----|-------------|
| Gaussian  | 10.9% | 14.3% | 15.2% | 15.5% | **+4.7%** |
| RF        | 28.0% | 38.3% | 42.6% | 43.6% | **+15.6%** |
| XGBoost   | 26.8% | 38.7% | 43.5% | 45.4% | **+18.6%** |
| MLP       | 24.8% | 36.9% | 38.6% | 41.6% | **+16.8%** |

#### MAE (meters) — RSS+SINR, raw features
| Algorithm | h=0 | h=1 | h=2 | h=3 | Improvement |
|-----------|-----|-----|-----|-----|-------------|
| Gaussian  | 5.03 | 4.50 | 4.40 | 4.37 | **-13.0%** |
| RF        | 3.90 | 2.92 | 2.64 | 2.51 | **-35.7%** |
| XGBoost   | 3.93 | 2.89 | 2.56 | 2.39 | **-39.1%** |
| MLP       | 4.16 | 2.98 | 2.82 | 2.62 | **-36.9%** |

**Key observation:** Raw features consistently outperform smart features on 7×7 grid.

---

## Files Modified

| File | Changes |
|------|---------|
| `src/python/localization_pipeline.py` | PROJECT_ROOT, GaussianTransitionModel batch predict, BaseSklearnModel batch predict, XGBoostModel batch predict, evaluate_static batch, evaluate_transition batch |
| `src/python/run_experiment_matrix.py` | PROJECT_ROOT import, config counter fix, timing display fix |
| `src/python/run_full_pipeline.py` | PROJECT_ROOT, results_base path |
| `src/python/localization_pipeline_regression.py` | PROJECT_ROOT, output_dir path, fixed duplicate import |
| `src/python/plot_comparison_results.py` | Matplotlib Agg backend |
| `requirements.txt` | Added scikit-learn, xgboost, pandas |

---

## Next Steps
1. Wait for scalability Batch A to complete
2. Run scalability Batch B (MLP on small grids)
3. Merge CSV results and generate scalability plots
4. Update TASKS.md with fresh scalability numbers
5. Phase 4: Documentation & CEVA preparation
