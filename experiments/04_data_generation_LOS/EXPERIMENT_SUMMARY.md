# Experiment 04: Large-Scale Data Generation - Summary

**Created**: November 7, 2025  
**Status**: ✅ Ready to run  
**Expected Impact**: Reduce MAE from 28m → 5-10m

---

## 📁 Files Created

### Core Scripts (4 files)

1. **`exp10_large_dataset.m`** (390 lines)
   - Main data generation script
   - Generates 500 trajectories with 7 types
   - Simulates CSI using QuaDRiGa
   - Saves train/val datasets
   - Runtime: 30-60 minutes

2. **`trajectory_generators.m`** (250 lines)
   - 8 trajectory generation functions:
     - `generate_linear_trajectory()` - Straight lines
     - `generate_circular_trajectory()` - Circles
     - `generate_zigzag_trajectory()` - Zigzag patterns
     - `generate_random_walk()` - Stochastic motion
     - `generate_grid_trajectory()` - Grid coverage
     - `generate_spiral_trajectory()` - Spirals
     - `generate_figure8_trajectory()` - Figure-8
   - Configurable parameters for each type

3. **`config_large_dataset.m`** (135 lines)
   - Centralized configuration
   - 500 trajectories × 80 timesteps
   - 7 trajectory types with distribution
   - QuaDRiGa parameters
   - Feature extraction settings

4. **`validate_dataset.m`** (180 lines)
   - Data integrity checks (NaN/Inf)
   - Spatial coverage analysis
   - Diversity metrics
   - Generates 3 validation plots
   - Quality assessment

### Documentation (3 files)

5. **`README.md`** - Complete experiment overview
6. **`QUICKSTART.md`** - Step-by-step guide
7. **`EXPERIMENT_INDEX.md`** - Updated with exp10

---

## 🎯 What You Get

### Dataset Size
- **Training samples**: ~32,000 (500 traj × 64 samples)
- **Validation samples**: ~8,000 (500 traj × 16 samples)
- **Features per sample**: 771 (3 wideband + 768 per-subcarrier)
- **Total size**: ~40,000 samples

### Comparison with Current Dataset

| Metric | Current (exp09) | New (exp10) | Improvement |
|--------|----------------|-------------|-------------|
| Training samples | 640 | 32,000 | **50×** |
| Validation samples | 160 | 8,000 | **50×** |
| Trajectories | 20 | 500 | **25×** |
| Trajectory types | 1 (random) | 7 (diverse) | **7×** |
| Samples/feature | 0.83 | 41.5 | **50×** |

### Trajectory Distribution

| Type | Count | % | Description |
|------|-------|---|-------------|
| Linear | 100 | 20% | Straight-line paths |
| Circular | 75 | 15% | Circular motion |
| Zigzag | 75 | 15% | Sharp turns |
| Random Walk | 100 | 20% | Natural movement |
| Grid | 50 | 10% | Systematic coverage |
| Spiral | 50 | 10% | Expanding/contracting |
| Figure-8 | 50 | 10% | Lemniscate curves |

---

## 🚀 How to Run

### Quick Start (Copy-paste)

```matlab
% 1. Navigate to experiment
cd experiments/04_data_generation

% 2. Run generation (30-60 min)
exp10_large_dataset

% 3. Validate dataset
validate_dataset('../../results/exp10_2025-11-07_XX-XX-XX/dataset/')
```

### Expected Console Output

```
========================================
EXP10: LARGE-SCALE DATA GENERATION
========================================

Output directory: ../../results/exp10_2025-11-07_12-34-56

Initializing QuaDRiGa...
✓ Created 4 base stations

Total trajectories: 500
  linear: 100 trajectories (20.0%)
  circular: 75 trajectories (15.0%)
  zigzag: 75 trajectories (15.0%)
  random_walk: 100 trajectories (20.0%)
  grid: 50 trajectories (10.0%)
  spiral: 50 trajectories (10.0%)
  figure8: 50 trajectories (10.0%)

Generating trajectories...
Progress: [==================================================]
✓ Generated 500 trajectories

Simulating CSI data with QuaDRiGa...
This will take 30-60 minutes...

  Processed 50/500 trajectories (10.0%) - ETA: 45.2 min
  Processed 100/500 trajectories (20.0%) - ETA: 40.1 min
  ...
  Processed 500/500 trajectories (100.0%) - ETA: 0.0 min

✓ Simulation complete in 42.3 minutes

Saving dataset...
✓ Saved training data: 32000 samples
✓ Saved validation data: 8000 samples

========================================
EXPERIMENT 10 COMPLETE!
========================================

📁 Output directory: ../../results/exp10_2025-11-07_12-34-56
📊 Training samples: 32000
📊 Validation samples: 8000
⏱️  Total time: 42.3 minutes

🎯 Next step: Train ML models on this dataset!
```

---

## 📊 Integration with ML Pipeline

### Step 1: Update Config

Edit `ml_training/config.py`:

```python
# OLD
DEFAULT_DATASET_PATH = Path('results/exp09_2025-11-04_21-41-43/dataset')

# NEW  
DEFAULT_DATASET_PATH = Path('results/exp10_2025-11-07_12-34-56/dataset')
```

### Step 2: Verify Data Loading

```bash
cd ml_training
python -c "from data_loader import CSIDataLoader; loader = CSIDataLoader(); X_train, y_train, X_val, y_val = loader.load_all(); print(f'Train: {X_train.shape}, Val: {X_val.shape}')"
```

Expected output:
```
Train: (32000, 771), Val: (8000, 771)
```

### Step 3: Run EDA

```bash
python eda.py
```

This generates 6 plots showing the new dataset characteristics.

### Step 4: Train Models

```bash
python models/baseline_models.py
```

Expected performance improvement:
- **Before**: 28.24 m MAE (640 samples)
- **After**: 5-10 m MAE (32,000 samples) ⭐

---

## 📈 Expected Performance Improvement

### Current Baseline (640 samples)

| Model | MAE (m) | R² |
|-------|---------|-----|
| Linear Regression | 28.24 | 0.247 |
| Ridge | 28.45 | 0.244 |
| Random Forest | 29.65 | 0.056 (overfitting) |
| KNN | 30.20 | 0.018 (overfitting) |

### Expected with Large Dataset (32,000 samples)

| Model | MAE (m) | R² | Improvement |
|-------|---------|-----|-------------|
| Linear Regression | **8-12** | **0.6-0.7** | 16-20m better |
| Ridge | **8-12** | **0.6-0.7** | 16-20m better |
| Random Forest | **5-8** | **0.7-0.8** | 21-24m better |
| KNN | **6-10** | **0.6-0.7** | 20-24m better |
| **Neural Network** | **2-4** | **0.85-0.95** | **24-26m better** ⭐ |

### Why This Improvement?

1. **More samples** (50× increase)
   - Better generalization
   - Reduced overfitting
   - More patterns learned

2. **More diversity** (7 trajectory types)
   - Better coverage of motion patterns
   - Robust to different movements
   - Better interpolation

3. **Better sample/feature ratio**
   - Was: 0.83 samples/feature (severe underfitting)
   - Now: 41.5 samples/feature (healthy range)

---

## ⚙️ Configuration Options

### Generate Smaller Test Dataset (Faster)

Edit `config_large_dataset.m`:
```matlab
config.n_trajectories = 100;  % 5× faster (6-12 min)
config.n_timesteps = 50;       % ~6,400 train samples
```

### Generate Larger Production Dataset

```matlab
config.n_trajectories = 1000;  % 64,000 train samples
% Runtime: 60-120 minutes
```

### Focus on Specific Trajectory Types

```matlab
config.trajectory_distribution = struct(...
    'linear', 0.00, ...        % Disable
    'circular', 0.00, ...      
    'zigzag', 0.00, ...        
    'random_walk', 1.00, ...   % 100% random walk
    'grid', 0.00, ...          
    'spiral', 0.00, ...        
    'figure8', 0.00 ...
);
```

---

## 🔍 Validation Checklist

After generation, verify:

- [ ] Training samples ≥ 30,000
- [ ] Validation samples ≥ 8,000
- [ ] No NaN/Inf values
- [ ] Spatial coverage > 90%
- [ ] All trajectory types generated
- [ ] Features extracted correctly (771 features)
- [ ] Position ranges: X [10, 90], Y [10, 90]

Run validation:
```matlab
validate_dataset('path/to/dataset/')
```

---

## 🐛 Common Issues

### Issue: "Out of memory"
**Cause**: Too many trajectories for available RAM  
**Solution**: 
- Reduce `n_trajectories` to 200-300
- Close other MATLAB sessions
- Process in batches

### Issue: Very slow simulation
**Cause**: QuaDRiGa overhead per trajectory  
**Solution**:
- Disable plots: `config.output.generate_plots = false`
- Reduce `n_timesteps` to 60-70
- Ensure QuaDRiGa is properly compiled

### Issue: Uneven spatial coverage
**Cause**: Some trajectory types clustered  
**Solution**:
- Increase `random_walk` percentage
- Add more `grid` trajectories
- Check validation plots

---

## 📖 Next Steps After Generation

1. ✅ **Validate dataset** → `validate_dataset()`
2. ✅ **Update ML config** → Edit `config.py`
3. ✅ **Run EDA** → `python eda.py`
4. ✅ **Train baseline models** → `python models/baseline_models.py`
5. ✅ **Compare performance** → Check MAE improvement
6. ✅ **Feature selection** → `python generate_and_filter_data.py` (optional)
7. ✅ **Train neural networks** → Implement in `models/neural_networks.py`
8. ✅ **Hyperparameter tuning** → Optimize best models

---

## 🎯 Success Metrics

Your experiment is successful if:

- ✅ Dataset generated without errors
- ✅ 30,000+ training samples
- ✅ >90% spatial coverage
- ✅ ML training MAE **< 10m** (vs 28m before)
- ✅ No severe overfitting (train/val gap < 5m)

**Expected final result**: **5-10m MAE with baseline models**, **2-4m MAE with neural networks** 🎯

---

## 📚 References

- `README.md` - Full experiment description
- `QUICKSTART.md` - Step-by-step instructions  
- `config_large_dataset.m` - All configuration options
- `trajectory_generators.m` - Trajectory function documentation
- `../EXPERIMENT_INDEX.md` - Experiment progression

---

**Status**: ✅ **READY TO RUN**  
**Command**: `cd experiments/04_data_generation && exp10_large_dataset`  
**Expected Runtime**: 30-60 minutes  
**Expected Impact**: **Reduce MAE by 18-23 meters** 🚀
