# Level 4: Large-Scale Data Generation - LOS Scenarios

## Overview

This experiment focuses on generating large, diverse CSI datasets with **Line-of-Sight (LOS) conditions** for machine learning training. The goal is to create 30,000+ samples with various trajectory types to improve model generalization.

## Motivation

Current baseline models achieve **28m MAE** with only 640 training samples. Analysis showed:
- Feature selection doesn't help (all 771 features needed)
- Insufficient data: 0.83 samples per feature (need 10-100×)
- Models overfit severely (Random Forest, KNN)

**Solution**: Generate 500+ trajectories with diverse movement patterns.

## Trajectory Types

### 1. Linear Paths
- Straight-line motion in various directions
- Different speeds and distances
- Covers basic movement patterns

### 2. Circular Paths
- Clockwise and counter-clockwise
- Various radii and angular speeds
- Tests rotational invariance

### 3. Zigzag Paths
- Sharp directional changes
- Different amplitudes and frequencies
- Challenging for prediction models

### 4. Random Walk
- Stochastic movement patterns
- Natural human-like motion
- High diversity

### 5. Grid Pattern
- Systematic coverage of area
- Consistent spacing
- Good for interpolation testing

### 6. Spiral Paths
- Expanding/contracting spirals
- Combined radial and angular motion
- Complex trajectory patterns

## Files

### Main Scripts

1. **`exp10_large_dataset.m`** - Main generation script
   - Generates 500+ trajectories
   - Multiple trajectory types
   - Saves to dataset format

2. **`trajectory_generators.m`** - Trajectory generation functions
   - `generate_linear_trajectory()`
   - `generate_circular_trajectory()`
   - `generate_zigzag_trajectory()`
   - `generate_random_walk()`
   - `generate_grid_trajectory()`
   - `generate_spiral_trajectory()`

3. **`validate_dataset.m`** - Validation script
   - Check data quality
   - Verify coverage
   - Generate statistics

### Supporting Scripts

4. **`config_large_dataset.m`** - Configuration parameters
5. **`plot_trajectories.m`** - Visualization utilities

## Expected Output

### Dataset Size
- **Training samples**: ~32,000 (500 trajectories × 64 samples)
- **Validation samples**: ~8,000 (500 trajectories × 16 samples)
- **Features**: 771 (3 wideband + 768 per-subcarrier)

### Performance Target
- Current: **28.24 m MAE**
- Expected: **5-10 m MAE** (with more data)
- Goal: **<3 m MAE** (with neural networks)

## Usage

### Quick Start

```matlab
% Run main generation script
cd experiments/04_data_generation_LOS
exp10_large_dataset

% Expected runtime: 30-60 minutes
```

### Custom Configuration

```matlab
% Edit config_large_dataset.m
n_trajectories = 500;        % Total trajectories
trajectory_types = {...      % Types to generate
    'linear', 'circular', 'zigzag', 
    'random_walk', 'grid', 'spiral'
};
```

### Validation

```matlab
% After generation, validate dataset
validate_dataset('results/exp10_*/dataset/')
```

## Output Structure

```
results/
  exp10_YYYY-MM-DD_HH-MM-SS/
    dataset/
      train_data.mat          % Training set (32,000 samples)
      val_data.mat            % Validation set (8,000 samples)
    trajectories/             % Visualization plots
      trajectory_000.png
      trajectory_001.png
      ...
    experiment_report.txt     % Summary statistics
    trajectory_summary.png    % All trajectories overlay
```

## Integration with ML Pipeline

### After Generation

```bash
# 1. Update config.py to point to new dataset
cd ml_training
# Edit config.py: DEFAULT_DATASET_PATH = 'results/exp10_..../dataset'

# 2. Inspect new dataset
python eda.py

# 3. Train baseline models
python models/baseline_models.py

# 4. Expected improvement: 28m → 5-10m MAE
```

## Timeline

1. **Script Development**: 1-2 hours
2. **Data Generation**: 30-60 minutes (MATLAB)
3. **Validation**: 5-10 minutes
4. **ML Training**: 10-15 minutes
5. **Analysis**: 15-20 minutes

**Total**: ~2-3 hours

## Next Steps

1. ✅ Create generation scripts
2. ⏳ Run data generation (exp10)
3. ⏳ Validate dataset quality
4. ⏳ Train ML models on new data
5. ⏳ Compare with baseline results
6. ⏳ Iterate if needed

---

**Status**: Ready for implementation
**Expected Impact**: Reduce MAE from 28m to 5-10m
