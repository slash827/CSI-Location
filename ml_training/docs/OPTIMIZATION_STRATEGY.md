# Optimization Strategy - Summary

**Date**: November 7, 2025  
**Status**: ✅ Running optimized hyperparameter experiments  
**Goal**: Improve beyond 20.10m MAE baseline without feature selection

---

## 🎯 Current Situation

### Baseline Performance (All 3,075 features)
- **Best Model**: Random Forest
- **Val MAE**: 20.10 m
- **Val R²**: 0.609
- **Training Time**: 38.9s

### Feature Selection Experiment Results
| Method | Features | Val MAE | Result |
|--------|----------|---------|--------|
| Mutual Info (500) | 500 | 31.15 m | ❌ Failed (-55%) |
| Mutual Info (2000) | 2,000 | 20.16 m | ✅ Nearly same |
| PCA (364) | 364 | 25.21 m | ⚠️ Worse (-25%) |

**Conclusion**: Most features ARE important! Feature selection doesn't help much for this problem.

---

## 💡 New Strategy: Hyperparameter Optimization

### Why Focus on Hyperparameters Instead of Feature Selection?

1. **Features are all informative** - 84% reduction (3075→500) destroyed performance
2. **Faster than feature selection** - No need for 500s mutual info computation
3. **Better models > fewer features** - 39s training isn't that bad
4. **Room for improvement** - Current RF uses conservative hyperparameters

---

## 🧪 Experiments Running Now

### Running: `run_optimized_models.py`

**Models Being Tested:**

#### 1. Random Forest - 4 Versions

**V1 (Baseline - Current Config)**
```python
n_estimators: 50
max_depth: 15
max_features: 'sqrt'
```
- Expected: 20.10m MAE (same as current)
- Training time: ~16s

**V2 (More Trees, Deeper)**
```python
n_estimators: 100
max_depth: 25
max_features: 'sqrt'
```
- Expected: 18-20m MAE
- Training time: ~35-40s
- Rationale: More trees reduce variance, deeper trees capture complex patterns

**V3 (Balanced)**
```python
n_estimators: 75
max_depth: 20
max_features: 'sqrt'
```
- Expected: 19-20m MAE
- Training time: ~25-30s
- Rationale: Middle ground between speed and accuracy

**V4 (Max Capacity - May Overfit)**
```python
n_estimators: 100
max_depth: 30
min_samples_split: 3
min_samples_leaf: 1
max_features: 'sqrt'
```
- Expected: 17-22m MAE (high variance)
- Training time: ~40-50s
- Rationale: Maximum model capacity, might overfit but worth trying

---

#### 2. XGBoost - 3 Versions

**V1 (Conservative)**
```python
n_estimators: 100
max_depth: 6
learning_rate: 0.1
```
- Expected: 18-20m MAE
- Training time: ~60-90s
- Rationale: Safe defaults, gradual learning

**V2 (Aggressive - More Iterations)**
```python
n_estimators: 200
max_depth: 8
learning_rate: 0.05
```
- Expected: 17-19m MAE
- Training time: ~120-180s
- Rationale: More trees + deeper + slower learning = better convergence

**V3 (Balanced)**
```python
n_estimators: 150
max_depth: 7
learning_rate: 0.075
```
- Expected: 17-20m MAE
- Training time: ~90-150s
- Rationale: Sweet spot between v1 and v2

---

## 📊 Expected Outcomes

### Optimistic Scenario 🎉
```
Best Model: XGBoost V2 or RF V2
Val MAE: 17-18 m
Improvement: 10-15% over baseline
Training time: 40-180s (acceptable)
```

### Realistic Scenario ✅
```
Best Model: XGBoost V3 or RF V3
Val MAE: 18-20 m
Improvement: 0-10% over baseline
Training time: 25-150s
```

### Pessimistic Scenario ⚠️
```
Best Model: RF V1 (current baseline)
Val MAE: 20.10 m
Improvement: 0%
Conclusion: Current hyperparameters already optimal
```

---

## 🔄 Next Steps Based on Results

### If XGBoost Wins (Expected)

1. **Further tune XGBoost**:
   - Try max_depth: 9, 10
   - Try n_estimators: 250, 300
   - Tune subsample, colsample_bytree

2. **Ensemble approaches**:
   ```python
   final_pred = 0.6 * xgb_pred + 0.4 * rf_pred
   ```
   Expected: 16-18m MAE

### If Random Forest Wins

1. **Try even more trees**:
   - n_estimators: 150, 200
   - May hit diminishing returns

2. **Tune other parameters**:
   - min_samples_split: 2, 3, 4
   - max_features: 'sqrt', 'log2', 0.3

### If No Improvement

1. **Neural Networks** (as planned):
   - MLP architecture
   - Expected: 15-18m MAE
   - Timeline: 1 week

2. **Feature Engineering**:
   - Polynomial features
   - Interaction terms
   - Domain-specific features

---

## ⏱️ Timeline

### Current Experiment
- **Start**: ~21:30
- **Duration**: ~15-25 minutes
- **ETA**: ~21:50-22:00

### Results Analysis
- **Duration**: 10 minutes
- View model_comparison.txt
- Identify best configuration

### Follow-up (if needed)
- **Fine-tuning**: 30-60 minutes
- **Ensemble**: 15-30 minutes
- **Total**: 1-2 hours

---

## 💭 Key Insights

### What We Learned

1. **Feature selection failed** because:
   - CSI features are highly interactive
   - Spatial triangulation needs all 4 BSs
   - Frequency diversity is critical
   - Mutual information can't see feature interactions

2. **2,000 features worked** because:
   - Still keeps 65% of frequency information
   - Preserves most spatial patterns
   - Good speed/accuracy trade-off

3. **All features are important** because:
   - Each subcarrier probes different multipath
   - Channel magnitude patterns are spatial fingerprints
   - Removing 84% = destroying the signal

### Implications for Future Work

1. **Don't over-optimize speed**:
   - 39s training is totally acceptable
   - Accuracy > speed for research
   - Can optimize inference later if needed

2. **Trust domain knowledge**:
   - Wireless channels need frequency diversity
   - Can't just rely on ML feature selection
   - Physics matters!

3. **Tree models are strong baselines**:
   - Random Forest: simple, robust, fast
   - XGBoost: better accuracy, more complex
   - Hard to beat with neural networks

---

## 🎯 Success Metrics

| Metric | Baseline | Target | Stretch Goal |
|--------|----------|--------|--------------|
| Val MAE | 20.10 m | < 19 m | < 17 m |
| Val R² | 0.609 | > 0.65 | > 0.70 |
| Training Time | 39s | < 180s | < 60s |
| Overfitting Gap | 9.2 m | < 10 m | < 7 m |

---

## 📝 Documentation

### Files Created Today

1. **run_optimized_models.py** - Hyperparameter tuning experiments
2. **FEATURE_SELECTION_FAILURE_ANALYSIS.md** - Why 500 features failed
3. **NEURAL_NETWORK_PLAN.md** - Future neural network roadmap
4. **OPTIMIZATION_STRATEGY.md** - This file

### Results Will Be Saved To

```
ml_training/results/optimized_YYYY-MM-DD_HH-MM-SS/
├── config.json                      # Experiment configuration
├── model_comparison.txt             # All model results
└── models/
    ├── random_forest_v1_model.pkl
    ├── random_forest_v2_model.pkl
    ├── random_forest_v3_model.pkl
    ├── random_forest_v4_model.pkl
    ├── xgboost_v1_x_model.pkl
    ├── xgboost_v1_y_model.pkl
    ├── xgboost_v2_x_model.pkl
    ├── xgboost_v2_y_model.pkl
    ├── xgboost_v3_x_model.pkl
    └── xgboost_v3_y_model.pkl
```

---

**Status**: ⏳ Experiment running... Check results in ~20 minutes!
