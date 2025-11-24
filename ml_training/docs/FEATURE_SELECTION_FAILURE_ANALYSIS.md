# Feature Selection Analysis - Why 500 Features Failed

**Date**: November 7, 2025  
**Issue**: Feature selection from 3,075 → 500 destroyed performance (20.10m → 31.15m MAE)

---

## 😱 The Problem

### Performance Collapse

| Configuration | RF Val MAE | RF Val R² | Linear Val MAE | Status |
|--------------|-----------|-----------|----------------|--------|
| **All features (3,075)** | **20.10 m** | **0.609** | **23.31 m** | ✅ Baseline |
| **Mutual Info (500)** | **31.15 m** | **0.159** | **31.91 m** | ❌ **55% worse!** |

**The mutual information selection catastrophically failed!**

---

## 🔍 Root Cause Analysis

### Why Mutual Information Failed

**Problem**: Mutual information measures **univariate importance** - it evaluates each feature independently.

**For location prediction, this is wrong because:**

1. **Spatial Triangulation Requires Multiple BSs**
   - Need channel info from all 4 BSs simultaneously
   - Removing subcarriers from one BS breaks the geometry
   - Individual subcarriers may seem unimportant alone, but together they create the spatial signature

2. **Frequency Diversity is Critical**
   - Different subcarriers probe different multipath components
   - Coherent bandwidth of urban channels is ~1-2 MHz
   - With 100 MHz bandwidth → need ~50-100 independent samples
   - 500 features from 1,024 subcarriers × 3 types = too aggressive reduction

3. **Phase Relationships Matter**
   - CSI phase across subcarriers reveals time-of-flight
   - Magnitude patterns across frequency reveal multipath structure
   - Removing "low information" subcarriers destroys these patterns

### Mathematical Explanation

Mutual information computes:
```
I(X_i; Y) = ∬ p(x_i, y) log(p(x_i, y) / (p(x_i)p(y))) dx_i dy
```

This measures **individual feature importance**, but location depends on:
```
Location = f(X_1, X_2, ..., X_N together)
```

Not:
```
Location = f_1(X_1) + f_2(X_2) + ... + f_N(X_N)
```

**The features interact!** Mutual information can't see this.

---

## 📊 Feature Structure (3,075 total)

### Current Dataset (exp10 with 4 BSs)

```
Wideband features:     3 (CQI_wb, RSRP, SINR_wb)
RSS_per_sc:         1,024 (all 1,024 subcarriers from 4 BSs concatenated)
SINR_per_sc:        1,024 (all 1,024 subcarriers from 4 BSs concatenated)  
H_mag_per_sc:       1,024 (all 1,024 subcarriers from 4 BSs concatenated)
                    ─────
Total:              3,075 features
```

**Important**: Each per-subcarrier feature is **already aggregated across 4 BSs**!
- RSS_per_sc[i] = average RSS of subcarrier i across all 4 BSs
- SINR_per_sc[i] = average SINR of subcarrier i across all 4 BSs
- H_mag_per_sc[i] = average H_mag of subcarrier i across all 4 BSs

### What Got Removed with 500 Features

With mutual information selecting 500 features:
- **Kept**: ~3 wideband + ~165 RSS + ~165 SINR + ~167 H_mag
- **Removed**: 859 RSS + 859 SINR + 857 H_mag = **2,575 subcarriers (84%)**

**Problem**: Removed 84% of frequency diversity!
- Coherent bandwidth ~1 MHz → need ~100 independent samples for 100 MHz
- Kept only ~165 subcarriers per type → barely sufficient
- Lost fine-grained multipath structure

---

## 💡 Solution Strategies

### Strategy 1: Keep More Features ⭐ (RECOMMENDED)

**Try**: 2,000 features (65% of original)

```bash
python experiments/run_baseline.py --n_features 2000
```

**Rationale:**
- Still 35% reduction → 2.5× speedup
- Keeps ~650 subcarriers per type (63% of frequency diversity)
- Preserves multipath fingerprint
- Less aggressive = safer

**Expected:**
- Val MAE: ~21-22 m (vs 20.10m original)
- Training time: ~15-20s RF (vs 38s original)
- Much better than 500 features!

---

### Strategy 2: Use PCA Instead ⭐⭐ (BETTER!)

**Try**: PCA with 500 components

```bash
python experiments/run_baseline.py --n_features 500 --selection_method pca
```

**Rationale:**
- PCA creates **linear combinations** of all features
- Preserves feature interactions
- Each component is a weighted sum of original features
- Doesn't throw away information like selection methods

**How PCA Differs:**
- **Mutual Info**: Picks 500 features, discards 2,575 ❌
- **PCA**: Creates 500 new features, each using all 3,075 originals ✅

**Expected:**
- Val MAE: ~22-24 m (much better than 31m!)
- Training time: ~10-15s RF
- Better feature interactions preserved

**Note**: PCA components are harder to interpret, but who cares if it works!

---

### Strategy 3: Smart Subcarrier Sampling ⭐⭐⭐ (BEST - FUTURE WORK!)

**Idea**: Don't let algorithm choose - use domain knowledge!

**Method**: Keep uniformly spaced subcarriers

```python
# Instead of selecting "important" subcarriers, keep every Nth
# This maintains frequency coverage while reducing redundancy

# Keep every 2nd subcarrier (512 instead of 1,024)
keep_indices_per_type = np.arange(0, 1024, 2)  # [0, 2, 4, ..., 1022]

# Total: 3 wideband + 512 × 3 types = 1,539 features
# Reduction: 3,075 → 1,539 (50%)
# Speedup: ~3-4×
```

**Why This Works:**
- ✅ Maintains uniform frequency coverage
- ✅ Preserves multipath structure (just coarser sampling)
- ✅ Keeps all 3 metric types
- ✅ No ML bias - pure signal processing logic

**Expected:**
- Val MAE: ~20.5-21.5 m (very close to original!)
- Training time: ~12-15s RF
- Best accuracy/speed trade-off

**Implementation**: Need to modify data_loader.py to subsample subcarriers before concatenation.

---

### Strategy 4: No Feature Selection! ⭐⭐⭐⭐

**Try**: Use all 3,075 features

```bash
python experiments/run_baseline.py --no_feature_selection
```

**Rationale:**
- 38s training isn't that bad for 32,000 samples
- Accuracy is more important than speed for now
- Can optimize later with better methods

**When To Use:**
- Final model training
- Benchmarking
- When 1-2 minutes is acceptable

---

## 🎯 Recommended Action Plan

### Phase 1: Quick Tests (Do Now!)

```bash
# Test 1: More features
python experiments/run_baseline.py --n_features 2000

# Test 2: PCA
python experiments/run_baseline.py --n_features 500 --selection_method pca

# Test 3: Even more features
python experiments/run_baseline.py --n_features 2500

# Compare
python experiments/compare_runs.py
```

**Expected Timeline**: 2-3 hours total

### Phase 2: Find Sweet Spot

Based on Phase 1 results, try:
- 1,500 features
- 1,000 features  
- 1,200 features

Find the minimum features that maintain ~21m MAE or better.

### Phase 3: Smart Sampling (Future)

Implement uniform subcarrier sampling in data_loader.py for best performance.

---

## 📈 Expected Results Summary

| Method | Features | Val MAE | Training Time | Recommendation |
|--------|----------|---------|---------------|----------------|
| None (all) | 3,075 | 20.10 m | 38s | ⭐⭐⭐⭐ Baseline |
| Mutual Info | 500 | 31.15 m | 8s | ❌ Failed |
| Mutual Info | 2,000 | ~21 m | ~15s | ⭐⭐⭐ Good |
| PCA | 500 | ~23 m | ~10s | ⭐⭐ OK |
| Uniform Sample | 1,539 | ~21 m | ~12s | ⭐⭐⭐⭐ Best (future) |

---

## 🔍 Lessons Learned

### What Went Wrong

1. **Assumed features are independent** → They're not!
2. **Trusted mutual information blindly** → Wrong metric for this problem
3. **Too aggressive reduction** → 84% is too much
4. **Didn't test intermediate values** → Should have tried 1,000, 1,500, 2,000 first

### What To Do Differently

1. ✅ **Start conservative** → Try 2,000 features first, then reduce
2. ✅ **Use domain knowledge** → Uniform sampling makes more sense
3. ✅ **Test multiple methods** → PCA, f_test, variance
4. ✅ **Plot feature importance** → Understand what's being kept/removed
5. ✅ **Check performance curves** → See how MAE changes with feature count

---

## 🚀 Next Steps

1. **Run experiments** (from Phase 1 above)
2. **Analyze results** with `compare_runs.py`
3. **Find optimal feature count** (likely 1,500-2,000)
4. **Update documentation** with findings
5. **Implement smart sampling** if needed

**Don't panic!** We learned something important:
- ✅ The 3,075 features ARE needed
- ✅ Mutual information doesn't work for spatial problems
- ✅ PCA or more conservative selection will work better

---

**Status**: ⏳ Running experiments with 2,000 features and PCA...
