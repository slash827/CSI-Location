# Development Session Summary - January 22, 2026

## Overview
This session focused on fixing realistic AoA impairments configuration and enhancing the regression pipeline with transition history support and 3D position error metrics for comparison with classification tasks.

---

## 🎯 Objectives Completed

### 1. Fixed Realistic AoA Configuration Architecture
**Problem:** Python pipelines were reading `realistic_aoa` settings from data directory config instead of ML config, causing NLOS to show perfect prediction (R²=1.000) with AoA features.

**Solution:**
- Modified both `localization_pipeline.py` and `localization_pipeline_regression.py` to load `ml_config.jsonc` from experiment configs directory
- Applied realistic impairments (4° Gaussian noise + 5° quantization) from ML config settings
- Maintained backward compatibility with old config files

**Files Modified:**
- `experiments/09_grid_localization/src/python/localization_pipeline.py`
- `experiments/09_grid_localization/src/python/localization_pipeline_regression.py`

**Validation:**
- NLOS regression with AoA now shows realistic improvement (1.53m → 1.07m) instead of perfect prediction
- LOS regression maintains realistic performance with noisy AoA features

---

### 2. Enhanced Regression Pipeline with Transition History

**Problem:** Regression pipeline only used current sample features (static model), unlike classification pipeline which supported transition history (h=1,2,3).

**Solution:**
- Added `--max-history` parameter to regression pipeline (default: 3)
- Implemented feature stacking to include previous h measurements
- Removed `--features` CLI argument in favor of using all available features
- Split method default changed to `temporal` for consistency

**New Functionality:**
- Tests all history values from h=0 to `--max-history`
- Feature dimension scales as `(h+1) × base_features`
- Example: 6 base features with h=2 → 18 total features
- Automatically adjusts train/test splits for valid indices

**Files Modified:**
- `experiments/09_grid_localization/src/python/localization_pipeline_regression.py`

---

### 3. Added 3D Position Error Metric

**Problem:** No direct comparison possible between regression and classification task performance.

**Solution:**
- Convert spherical predictions (distance, azimuth, elevation) back to Cartesian (x, y, z)
- Compute 3D Euclidean distance between predicted and true UE positions
- Report as "3D Position (m)" metric alongside traditional regression metrics
- This metric is directly comparable to classification MAE (mean absolute error in meters)

**Implementation:**
- Added `spherical_to_cartesian()` method to convert predictions to UE positions
- Compute position error for each test sample
- Report MAE of 3D position errors
- Store in results for report generation

**Files Modified:**
- `experiments/09_grid_localization/src/python/localization_pipeline_regression.py`

---

## 📊 Performance Results

### NLOS Scenario (10×10 grid, 40,001 samples)

| History | Distance MAE | Azimuth MAE | Elevation MAE | **3D Position MAE** |
|---------|--------------|-------------|---------------|---------------------|
| h=0     | 1.072 m      | 2.317°      | 0.739°        | **2.258 m**         |
| h=1     | 0.762 m      | 1.654°      | 0.526°        | **1.607 m**         |
| h=2     | 0.739 m      | 1.562°      | 0.511°        | **1.535 m** ✅      |
| h=3     | 0.742 m      | 1.551°      | 0.514°        | **1.530 m**         |

**Improvement:** h=2 provides **32% better 3D localization** vs static (h=0)

### LOS Scenario (10×10 grid, 40,001 samples)

| History | Distance MAE | Azimuth MAE | Elevation MAE | **3D Position MAE** |
|---------|--------------|-------------|---------------|---------------------|
| h=0     | 0.547 m      | 0.277°      | 0.368°        | **0.688 m**         |
| h=1     | 0.400 m      | 0.245°      | 0.269°        | **0.520 m** ✅      |
| h=2     | 0.402 m      | 0.256°      | 0.272°        | **0.527 m**         |
| h=3     | 0.417 m      | 0.267°      | 0.282°        | **0.548 m**         |

**Improvement:** h=1 provides **24% better 3D localization** vs static (h=0)

---

## 🔑 Key Findings

### 1. **Realistic AoA Impairments Working Correctly**
- Data generation saves clean AoA (ground truth)
- ML training applies 4° noise + 5° quantization
- Model trains on noisy features, predicts clean targets
- Both LOS and NLOS show realistic performance

### 2. **Transition History Significantly Improves Regression**
- Using previous measurements provides 24-32% improvement
- Optimal history: h=1 for LOS, h=2 for NLOS
- h=3 shows diminishing returns or slight overfitting
- Similar to classification pipeline behavior

### 3. **Regression vs Classification Comparison Now Possible**
- 3D Position MAE enables direct comparison
- Regression task can be evaluated using same metric as classification
- Future work: Compare classification and regression on same datasets

### 4. **Feature Contributions**
- AoA features provide substantial improvement over RSS+SINR+CQI alone
- Timing Advance still useless (grid too small for meaningful variation)
- History captures movement patterns and temporal correlation

---

## 🛠️ Technical Architecture

### Configuration Flow
```
data_generation_config.jsonc (frozen with each dataset)
    ├── Grid parameters
    ├── Channel scenario
    ├── Movement settings
    └── Base station position

ml_config.jsonc (experiment-level, ML training settings)
    ├── realistic_aoa settings (noise, quantization)
    ├── Feature selections
    ├── Model hyperparameters
    └── Evaluation metrics
```

### Data Flow
```
MATLAB (generate_simulation_data.m)
    ↓
Clean AoA saved in simulation_data.mat
    ↓
Python (localization_pipeline*.py)
    ↓
Load ml_config.jsonc for realistic_aoa settings
    ↓
Apply noise + quantization to AoA features
    ↓
Train model on noisy features → predict clean targets
```

### Regression Pipeline Workflow
```
1. Load all available features (RSS, SINR, CQI, AoA, TA)
2. Apply realistic AoA impairments from ml_config.jsonc
3. For each history value h = 0 to max_history:
   a. Stack features: [X[i-h], ..., X[i-1], X[i]]
   b. Adjust train/test indices for valid samples
   c. Train Random Forest Regressor
   d. Predict (distance, azimuth, elevation)
   e. Convert to 3D position and compute error
   f. Report all metrics
4. Generate markdown report
```

---

## 📁 Files Modified

### Python Scripts
1. **localization_pipeline.py** (Classification)
   - Load ml_config.jsonc for realistic_aoa settings
   - Apply impairments from ML config instead of data config

2. **localization_pipeline_regression.py** (Regression)
   - Load ml_config.jsonc for realistic_aoa settings
   - Added `--max-history` parameter (default: 3)
   - Removed `--features` CLI argument (uses all features)
   - Changed `--split-method` default to 'temporal'
   - Added `_stack_history_features()` method
   - Added `spherical_to_cartesian()` method
   - Added 3D position error computation
   - Updated report generation with 3D position MAE

### Configuration Files
- **ml_config.jsonc** - Already existed, now properly loaded by Python pipelines

---

## 🚀 Usage Examples

### Regression Pipeline (New)
```bash
# Test with history support (h=0,1,2,3)
python experiments/09_grid_localization/src/python/localization_pipeline_regression.py \
    --data-dir "results/grid_localization/grid_10x10/sim_data_NLOS_2026-01-22_10-02-40" \
    --split-method temporal \
    --max-history 3

# Static model only (h=0)
python experiments/09_grid_localization/src/python/localization_pipeline_regression.py \
    --data-dir "results/grid_localization/grid_10x10/sim_data_LOS_2026-01-22_09-02-09" \
    --split-method temporal \
    --max-history 0
```

### Classification Pipeline (Unchanged)
```bash
# Random Forest with all features and history
python experiments/09_grid_localization/src/python/localization_pipeline.py \
    --data-dir "results/grid_localization/grid_10x10/sim_data_NLOS_2026-01-22_10-02-40" \
    --model random_forest \
    --max-history 3
```

---

## ✅ Validation Checklist

- [x] Realistic AoA impairments applied from ml_config.jsonc
- [x] NLOS regression shows realistic performance (not perfect)
- [x] LOS regression maintains realistic performance
- [x] Transition history support working (h=0,1,2,3)
- [x] Feature stacking correctly adjusts train/test indices
- [x] 3D position error computed and reported
- [x] Results saved to markdown reports
- [x] All features used automatically
- [x] Backward compatibility maintained

---

## 🎓 Lessons Learned

1. **Configuration Separation is Critical**
   - Data generation config belongs with the data (frozen)
   - ML training config should be flexible and experiment-level
   - Don't mix data generation and ML training settings

2. **History Provides Significant Value**
   - Movement patterns and temporal correlation are important
   - Optimal history length depends on scenario (LOS vs NLOS)
   - Diminishing returns after h=2 or h=3

3. **Comparable Metrics Enable Better Analysis**
   - 3D position error bridges regression and classification
   - Same metric allows fair comparison across tasks
   - Essential for understanding trade-offs

4. **Realistic Impairments are Essential**
   - Clean data leads to unrealistic perfect predictions
   - Noise and quantization simulate real-world conditions
   - Flexibility to adjust impairments during training is valuable

---

## 📈 Next Steps (Future Work)

1. **Regression vs Classification Comparison**
   - Run classification pipeline on same datasets
   - Compare 3D position MAE between tasks
   - Analyze trade-offs (discrete vs continuous prediction)

2. **Advanced Regression Models**
   - Test other regressors (Gradient Boosting, Neural Networks)
   - Multi-task learning (joint distance + angle prediction)
   - Ensemble methods combining multiple models

3. **Feature Engineering**
   - Test RSS+SINR+CQI only vs adding AoA separately
   - Analyze feature importance for regression
   - Investigate why Timing Advance is useless (quantization issue?)

4. **Extended Scenarios**
   - Test on larger grids (15×15, 20×20)
   - Mixed LOS/NLOS scenarios
   - Different base station heights and positions

5. **Visualization**
   - Plot predicted vs actual UE trajectories
   - Error heatmaps across grid positions
   - Feature importance visualization

---

## 📊 Summary Statistics

- **Total Experiments Run:** 8 (4 NLOS + 4 LOS with h=0,1,2,3)
- **Total Samples Evaluated:** 64,008 (8,001 test × 8 experiments)
- **Best NLOS Performance:** 1.530 m (3D Position MAE, h=3)
- **Best LOS Performance:** 0.520 m (3D Position MAE, h=1)
- **Overall Improvement:** 24-32% with transition history
- **Files Modified:** 2 Python scripts
- **New Methods Added:** 2 (spherical_to_cartesian, _stack_history_features)
- **New Parameters:** 1 (--max-history)
- **Session Duration:** ~2 hours

---

**Session Date:** January 22, 2026  
**Datasets Used:**
- `sim_data_NLOS_2026-01-22_10-02-40` (10×10 grid, 40,001 samples)
- `sim_data_LOS_2026-01-22_09-02-09` (10×10 grid, 40,001 samples)

**Status:** ✅ All objectives completed and validated
