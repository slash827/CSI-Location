# Feature Selection Analysis Results

## Date: November 6, 2025

## Summary

We created a comprehensive data generation and feature filtering pipeline similar to MATLAB experiments, tested multiple feature selection strategies, and discovered important insights about the dataset.

## Files Created

1. **`generate_and_filter_data.py`** - Complete pipeline for:
   - Loading CSI data from QuaDRiGa experiments
   - Analyzing feature importance (3 methods)
   - Filtering features based on importance
   - Generating reduced datasets
   - Visualizations and reports

2. **`compare_feature_selection.py`** - Automated comparison of:
   - 3 importance methods: mutual_info, f_test, random_forest
   - 8 feature counts: 10, 20, 30, 50, 75, 100, 150, 200
   - Total: 25 configurations tested

## Key Findings

### 🔍 Feature Selection Results

| Method | Best # Features | MAE (m) | R² | vs All Features |
|--------|----------------|---------|-----|-----------------|
| **Baseline (All)** | **771** | **28.24** | **0.2467** | **0.00 m** |
| Random Forest | 200 | 28.61 | 0.2326 | -0.37 m |
| Random Forest | 10-150 | 28.62 | 0.2298 | -0.38 m |
| Mutual Info | Any | 29.44 | 0.2029 | -1.20 m |
| F-Test | Any | 29.44 | 0.2029 | -1.20 m |

### ⚠️ Critical Insight

**Feature selection does NOT improve performance!**

- Using all 771 features: **28.24 m MAE**
- Best filtered (200 features): **28.61 m MAE** (worse)
- Most filtered configs: **29.44 m MAE** (worse)

### 📊 What This Means

The poor performance (28m vs expected 3-5m) is **NOT caused by**:
- ❌ Too many features (curse of dimensionality)
- ❌ Redundant/irrelevant features
- ❌ Feature noise

The real issues are likely:
1. **✅ Insufficient training data** (640 samples << 771 features)
   - Rule of thumb: need 10-100 samples per feature
   - We have: 0.83 samples per feature
   - Need: ~7,700-77,000 samples for 771 features

2. **✅ Model complexity mismatch**
   - Linear models too simple for CSI patterns
   - Random Forest overfits severely (train: 15.5m, val: 29.7m)
   - Need better regularization or different architectures

3. **✅ Data quality/diversity**
   - Only 20 trajectories in exp09
   - Limited spatial coverage
   - Possible channel correlation issues

## Feature Importance Analysis

### Mutual Information Method
- All RSS features have nearly identical importance (~1.055)
- Very little differentiation between features
- Top features: RSS_SC_27, RSS_SC_43, RSS_SC_28, etc.

### F-Test Method
- SINR features dominate (SINR_wb, SINR_SC_166, etc.)
- Many features have perfect score (1.0)
- Similar to mutual info - poor discrimination

### Random Forest Method (Best)
- More diverse importance scores (0.00004 - 0.0087)
- Top features span all groups:
  - SINR_SC_174 (0.0087)
  - H_MAG_SC_252 (0.0082)
  - RSS_SC_196 (0.0071)
  - H_MAG_SC_226 (0.0063)
- Shows better feature discrimination

## Generated Datasets

### dataset_top50
- **Features**: 50 (93.5% reduction)
- **Method**: Mutual Information
- **Location**: `output/generated_data/dataset_top50_*.npz`
- **Performance**: 29.44 m MAE (worse than baseline)

Files created:
- `dataset_top50_train.npz` - 640 samples × 50 features
- `dataset_top50_val.npz` - 160 samples × 50 features
- `dataset_top50_metadata.pkl` - Feature info
- `feature_importance_analysis.png` - Visualizations
- `generation_report.txt` - Detailed report

## Recommendations

### 🚀 Priority 1: Generate More Data

**ACTION**: Run MATLAB exp09 with more trajectories

```matlab
% In experiments/03_ue_movement/exp09_multi_trajectory.m
% Change:
n_trajectories = 500;  % Instead of 20
```

Expected output:
- **Training samples**: 32,000 (500 × 64)
- **Validation samples**: 8,000 (500 × 16)
- **Ratio**: 41 samples per feature (healthy!)

This should dramatically improve performance.

### 🔬 Priority 2: Try Advanced Models

Since linear models plateau at 28m MAE:

1. **Neural Networks** (PyTorch/TensorFlow)
   ```python
   # Enable in requirements.txt
   torch>=2.0.0
   ```
   
   Expected: 2-3m MAE (per LEVEL3_RESULTS_ANALYSIS.md)

2. **Gradient Boosting** (XGBoost/LightGBM)
   ```python
   # Enable in config.py
   BASELINE_MODELS['xgboost']['enabled'] = True
   ```

3. **Ensemble Methods**
   - Stack multiple models
   - Weighted averaging

### 🛠️ Priority 3: Feature Engineering

Instead of selection, try:
- **PCA/t-SNE** for dimensionality reduction
- **Polynomial features** for interaction terms
- **Domain-specific features**:
  - Phase differences between subcarriers
  - Frequency response derivatives
  - Spatial correlation metrics

### 📉 Priority 4: Regularization

For models that overfit:
- **Random Forest**: Reduce max_depth (try 5-8), increase min_samples_split
- **KNN**: Increase k (try k=10-20)
- **Ridge**: Increase alpha regularization

## Usage Examples

### Generate Filtered Dataset

```bash
# Top 50 features with mutual information
python generate_and_filter_data.py --method mutual_info --n_features 50 --output_name dataset_top50

# Top 100 features with random forest
python generate_and_filter_data.py --method random_forest --n_features 100 --output_name dataset_rf100

# Threshold-based selection
python generate_and_filter_data.py --method f_test --threshold 0.5 --output_name dataset_thresh
```

### Train with Filtered Data

```bash
# Use filtered dataset
python models/baseline_models.py --use_filtered dataset_top50

# Use original preprocessing
python models/baseline_models.py
```

### Compare Strategies

```bash
# Test all combinations
python compare_feature_selection.py
```

## Conclusion

**Feature selection is NOT the bottleneck.** The pipeline works perfectly, but the core issue is:
1. **Too little data** (640 samples)
2. **Too simple models** (linear regression)

**Next steps**: 
1. Generate 500-trajectory dataset (32,000 samples)
2. Implement neural networks
3. Re-test with larger dataset

Expected improvement: **28m → 3-5m MAE** 🎯

## Files Reference

### New Python Files
- `ml_training/generate_and_filter_data.py` - Main pipeline (460 lines)
- `ml_training/compare_feature_selection.py` - Strategy comparison (145 lines)

### Modified Files
- `ml_training/models/baseline_models.py` - Added `--use_filtered` argument

### Output Files
- `output/generated_data/dataset_top50_*.npz` - Filtered dataset
- `output/generated_data/feature_importance_analysis.png` - Visualizations
- `output/generated_data/generation_report.txt` - Detailed report
- `output/generated_data/feature_selection_comparison.csv` - Full results

---

**Status**: ✅ Feature pipeline complete, ready for large-scale data generation
