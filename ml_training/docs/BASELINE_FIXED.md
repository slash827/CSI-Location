# ✅ Baseline Models Fixed and Running!

## Issues Fixed

### 1. Import Errors ✅
**Problem:** `ModuleNotFoundError: No module named 'data_loader'`

**Solution:** Added parent directory to Python path in `baseline_models.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### 2. Multi-output Error ✅
**Problem:** `ValueError: Multioutput not supported in max_error`

**Solution:** Removed `max_error()` from sklearn metrics and calculated separate max errors for X and Y coordinates.

### 3. Missing Import ✅
**Problem:** `OUTPUT_DIR` not imported

**Solution:** Added `OUTPUT_DIR` to imports from `config.py`

## Current Status ✅

Baseline models are **WORKING** and trained successfully!

### Results Summary

| Model | Val MAE | Val RMSE | Val R² | Training Time |
|-------|---------|----------|--------|---------------|
| **Linear** | **28.24 m** | 31.01 m | 0.2467 | 0.09 s |
| Ridge | 28.45 m | 31.10 m | 0.2439 | 0.03 s |
| Random Forest | 29.65 m | 34.60 m | 0.0556 | 11.13 s |
| KNN | 30.20 m | 35.33 m | 0.0182 | 0.00 s |

**Best Model:** Linear Regression (28.24m MAE)

## Performance Analysis

### Why Not 3-5m as Expected?

The current results (~28m MAE) are much worse than expected (3-5m). Possible reasons:

1. **Too many features (771)**: May cause overfitting or noise
2. **Feature selection needed**: Some features might be irrelevant
3. **Hyperparameter tuning**: Default settings may not be optimal
4. **Dataset size**: 640 samples might be too small for 771 features
5. **Outlier removal was too aggressive**: Now disabled

### Observable Issues

1. **Random Forest overfitting**: 
   - Training MAE: 15.54m ✓ Good
   - Validation MAE: 29.65m ✗ Poor
   - Gap indicates overfitting

2. **KNN perfect training, poor validation**:
   - Training MAE: 0.00m (memorizing data)
   - Validation MAE: 30.20m (can't generalize)

3. **Linear models perform best**:
   - Less overfitting
   - More stable generalization

## Next Steps to Improve

### 1. Try Different Feature Sets

```python
# Edit data_loader.py call:

# Option A: Only RSS (simplest)
X_train, y_train, X_val, y_val = loader.load_all(feature_groups=['wideband'])

# Option B: RSS + per-subcarrier
X_train, y_train, X_val, y_val = loader.load_all(
    feature_groups=['wideband', 'rss_per_sc']
)

# Option C: All CSI features
X_train, y_train, X_val, y_val = loader.load_all(
    feature_groups=['wideband', 'h_mag_per_sc']
)
```

### 2. Enable Feature Selection

Edit `config.py`:
```python
FEATURE_SELECTION = {
    'enabled': True,
    'method': 'mutual_info',
    'n_features': 50,  # Reduce from 771 to 50
}
```

### 3. Tune Random Forest

Edit `config.py`:
```python
BASELINE_MODELS['random_forest']['params'] = {
    'n_estimators': 200,
    'max_depth': 10,  # Reduce from 20 to prevent overfitting
    'min_samples_split': 10,  # Increase from 5
    'min_samples_leaf': 5,  # Add this
    'n_jobs': -1,
    'random_state': 42
}
```

### 4. Generate More Data

Run `exp09` in MATLAB with more trajectories:
```matlab
n_trajectories = 500;  % Instead of 20
n_snapshots_per_traj = 50;
% = 25,000 samples instead of 800
```

## How to Run

### Quick Test
```powershell
cd ml_training
python models\baseline_models.py --use_processed
```

### Full Pipeline
```powershell
python models\baseline_models.py
# This will preprocess + train
```

### With Different Features
Modify the code temporarily or create a new script.

## Files Created

✅ **Trained Models** (4 files):
- `output/saved_models/linear_model.pkl`
- `output/saved_models/ridge_model.pkl`
- `output/saved_models/random_forest_model.pkl`
- `output/saved_models/knn_model.pkl`

✅ **Processed Data**:
- `output/processed_data/processed_train.npz`
- `output/processed_data/processed_val.npz`
- `output/processed_data/preprocessor.pkl`

✅ **Results**:
- `output/results/baseline_comparison.txt`

## Summary

✅ **Baseline models are WORKING!**  
⚠️ **Performance needs improvement (28m vs expected 3-5m)**  
🎯 **Next: Try feature selection and hyperparameter tuning**

The pipeline is functional end-to-end. Now you can experiment with different configurations to improve performance!

---

**Status:** Fixed and Running ✅  
**Date:** November 6, 2025  
**Next:** Feature engineering and tuning
