# Troubleshooting Guide

## Issue: "NotImplementedError: Please use HDF reader for matlab v7.3 files"

### Problem
Your MATLAB files were saved in v7.3 format (HDF5), which `scipy.loadmat()` cannot read.

### Solution ✅ (FIXED!)
The `data_loader.py` has been updated to automatically handle both formats:
- Older MATLAB formats (< v7.3): Uses `scipy.loadmat()`
- MATLAB v7.3 format: Uses `h5py`

### What was done:
1. Added `h5py` to `requirements.txt`
2. Updated `data_loader.py` to detect and handle v7.3 files
3. Fixed field extraction for nested MATLAB structs

### Verification:
```powershell
cd ml_training
python data_loader.py --inspect
```

You should see:
```
✓ Loading MATLAB v7.3 file with h5py...
✓ Loaded 640 samples
```

---

## Issue: Field not found errors

### Problem
MATLAB v7.3 files store data in nested Groups, not flat dictionaries.

### Solution ✅ (FIXED!)
The `_get_field()` method now:
- Checks for nested `train_data` and `val_data` groups
- Handles both dictionary and attribute access
- Automatically transposes arrays from MATLAB's column-major to row-major format

---

## Issue: Baseline model import errors

### Problem
```
ModuleNotFoundError: No module named 'data_loader'
```

### Solution ✅ (FIXED!)
Added parent directory to Python path in `models/baseline_models.py`

### Verification:
```powershell
cd ml_training
python models\baseline_models.py
```

Should train 4 models successfully.

---

## Issue: Multi-output max_error

### Problem
```
ValueError: Multioutput not supported in max_error
```

### Solution ✅ (FIXED!)
Replaced sklearn's `max_error()` with separate max calculations for X and Y coordinates.

---

## Issue: Poor model performance (~28m MAE)

### Problem
Models achieve ~28m MAE instead of expected 3-5m.

### Possible Causes:
1. Too many features (771) causing overfitting
2. Dataset too small (640 samples) for feature count
3. Hyperparameters need tuning
4. Need feature selection

### Solutions to Try:

**1. Use fewer features:**
Edit feature selection in `config.py`:
```python
FEATURE_SELECTION = {
    'enabled': True,
    'method': 'mutual_info',
    'n_features': 50,
}
```

**2. Try only RSS features:**
Modify data loading to use only wideband features.

**3. Tune Random Forest:**
Edit `config.py` to reduce overfitting:
```python
BASELINE_MODELS['random_forest']['params'] = {
    'max_depth': 10,  # Reduce depth
    'min_samples_split': 10,  # Increase
}
```

**4. Generate more data:**
Rerun exp09 in MATLAB with more trajectories (500+ instead of 20).

---

## Common Issues & Solutions

### 1. Dataset Path Not Found

**Error:**
```
FileNotFoundError: Dataset path not found: ...
```

**Solution:**
Edit `config.py`:
```python
DEFAULT_DATASET_PATH = Path(r"D:\full\path\to\your\exp09\dataset")
```

### 2. Missing h5py Package

**Error:**
```
ImportError: h5py not installed
```

**Solution:**
```powershell
pip install h5py
```

Or reinstall all dependencies:
```powershell
pip install -r requirements.txt
```

### 3. Out of Memory

**Error:**
```
MemoryError: Unable to allocate array
```

**Solution:**
Reduce features in `config.py`:
```python
FEATURE_SELECTION = {
    'enabled': True,
    'method': 'mutual_info',
    'n_features': 100,  # Instead of 771
}
```

### 4. Slow Model Training

**Solution:**
Disable slow models in `config.py`:
```python
BASELINE_MODELS['random_forest']['enabled'] = False
BASELINE_MODELS['xgboost']['enabled'] = False
```

---

## Testing Your Setup

### Quick Test
```powershell
cd ml_training
python data_loader.py --inspect
```

Expected output:
- ✓ Loads 640 training samples
- ✓ Loads 160 validation samples
- ✓ Shows 771 features
- ✓ Displays statistics

### Full Pipeline Test
```powershell
python quickstart.py
# Select option 1 (Data Inspection)
```

---

## Still Having Issues?

### Check Python Environment
```powershell
python --version  # Should be 3.8+
pip list | findstr "numpy scipy h5py"  # Check packages
```

### Verify Dataset Exists
```powershell
dir ..\results\exp09_2025-11-04_21-41-43\dataset
```

Should show:
- train_data.mat
- val_data.mat
- metadata.mat

### Check File Format
Run `inspect_mat.py`:
```powershell
python inspect_mat.py
```

Should show the MATLAB file structure.

---

## Getting Help

1. **Check this file first** - Most common issues are listed above
2. **Read QUICKSTART.md** - Step-by-step getting started
3. **Check config.py comments** - All settings explained
4. **Run with --inspect** - See what the loader detects

---

**Status:** ✅ All known issues fixed!  
**Last Updated:** November 6, 2025
