# Experiment Level 3: UE Movement

## 🎯 Learning Goals
- Simulate moving UE
- Track CSI changes over time
- Observe spatial correlation
- Generate trajectory datasets

## 📝 Experiments

### exp07_simple_movement.m ✅
**Duration:** 20 minutes  
**Topics:**
- Linear trajectory with constant velocity
- CSI evolution over time
- RSS, SINR, CQI vs position
- Spatial correlation analysis

**Key Outputs:**
- Trajectory visualization
- Metrics vs distance plots
- Time series evolution
- Correlation distance measurement

**What You'll Learn:**
- CSI changes smoothly with position
- RSS is strong distance indicator
- Spatial correlation exists (~10-20m)
- Tracking is feasible

---

### exp08_trajectory_types.m ✅
**Duration:** 25 minutes  
**Topics:**
- Three trajectory types: Linear, Circular, Random Walk
- Pattern-specific CSI characteristics
- Variability analysis
- Statistical comparison

**Key Outputs:**
- Multi-trajectory visualization
- Distance profile comparison
- RSS/SINR/CQI distributions
- Variability and autocorrelation

**What You'll Learn:**
- Different patterns show different CSI signatures
- Linear: Monotonic, predictable (good for testing)
- Circular: Stable RSS, tests angular effects
- Random: Most realistic, higher variability
- Need diverse training data for robust ML

---

### exp09_multi_trajectory.m ✅
**Duration:** 30-60 minutes  
**Topics:**
- Large-scale dataset generation (configurable size)
- Multiple trajectory types (50% random, 30% linear, 20% curved)
- Feature extraction at scale
- Train/validation split (80/20)

**Key Outputs:**
- `train_data.mat`: Training dataset with all features
- `val_data.mat`: Validation dataset
- `metadata.mat`: Dataset configuration
- Spatial coverage visualization
- Feature distribution analysis

**Dataset Structure:**
```matlab
train_data/val_data:
  - positions_x, positions_y (ground truth)
  - distances (to BS)
  - RSS_wb, SINR_wb, CQI_wb (wideband features)
  - RSS_per_sc, SINR_per_sc (per-subcarrier, 256 values)
  - H_mag_per_sc (channel magnitude, 256 values)
  - trajectory_id, snapshot_id (metadata)
```

**What You'll Learn:**
- Dataset generation pipeline
- Feature engineering best practices
- Train/val splitting strategies
- Dataset quality assessment
- Ready for ML training!

---

## 🚀 Prerequisites

Complete **01_basics/** and **02_single_ue_analysis/**

## 📚 Key Concepts

- **Track API**: Time-consistent channels
- **Snapshots**: Channel at discrete time points
- **Spatial correlation**: Nearby positions = similar CSI

## ➡️ Next Level

Ready for data generation:
**experiments/04_data_generation/**
