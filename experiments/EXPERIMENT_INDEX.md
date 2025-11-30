# Experiment Index

## 🎓 Progressive Learning Path

### 📚 Level 1: Basics (Start Here!)
**Location**: `experiments/01_basics/`  
**Time**: 30 minutes total  
**Goal**: Master QuaDRiGa fundamentals

| Experiment | Description | Time |
|------------|-------------|------|
| exp01_minimal_setup | Basic BS-UE link, CSI structure | 5 min |
| exp02_distance_comparison | Distance vs path loss | 10 min |
| exp03_los_vs_nlos | Obstacles and scattering | 10 min |

**✓ Completion criteria**: Understand CSI dimensions, path loss, LOS/NLOS

---

### 🔬 Level 2: Single UE Analysis
**Location**: `experiments/02_single_ue_analysis/`  
**Time**: 45 minutes total  
**Goal**: Master CSI metrics and frequency analysis

| Experiment | Description | Status |
|------------|-------------|--------|
| exp04_frequency_response | Time → Frequency domain | Coming soon |
| exp05_csi_metrics | RSS, SINR, CQI calculation | Coming soon |
| exp06_parameter_effects | Bandwidth, power effects | Coming soon |

**✓ Completion criteria**: Calculate metrics, understand frequency selectivity

---

### 🚗 Level 3: UE Movement
**Location**: `experiments/03_ue_movement/`  
**Time**: 60 minutes total  
**Goal**: Simulate trajectories and track CSI changes

| Experiment | Description | Status |
|------------|-------------|--------|
| exp07_simple_movement | Linear trajectory | Coming soon |
| exp08_trajectory_types | Multiple patterns | Coming soon |
| exp09_multi_trajectory | Batch generation | Coming soon |

**✓ Completion criteria**: Generate diverse trajectory datasets

---

### 📊 Level 4: Data Generation - LOS
**Location**: `experiments/04_data_generation_LOS/`  
**Time**: 2-3 hours  
**Goal**: Create large-scale ML training datasets with LOS conditions

| Experiment | Description | Status |
|------------|-------------|--------|
| exp10_large_dataset | Generate 500+ diverse LOS trajectories | ✅ Ready |
| validate_dataset | Verify data quality & coverage | ✅ Ready |

**✓ Completion criteria**: 
- 30,000+ training samples
- 8,000+ validation samples  
- 90%+ spatial coverage
- 7 trajectory types (linear, circular, zigzag, random_walk, grid, spiral, figure8)

---

### 📊 Level 5: Data Generation - NLOS
**Location**: `experiments/05_data_generation_NLOS/`  
**Time**: 2-3 hours  
**Goal**: Create large-scale ML training datasets with NLOS conditions

| Experiment | Description | Status |
|------------|-------------|--------|
| exp11_nlos_dataset | Generate 500+ diverse NLOS trajectories | ✅ Ready |
| validate_dataset | Verify data quality & coverage | ✅ Ready |

**✓ Completion criteria**: 
- 30,000+ training samples (NLOS scenarios)
- 8,000+ validation samples  
- 90%+ spatial coverage
- 7 trajectory types with realistic indoor propagation

---

### 📊 Level 6: Urban Scenario Generation
**Location**: `experiments/06_urban_scenario/`  
**Time**: 2-3 hours  
**Goal**: Generate production-scale urban dataset with indoor/outdoor mix

| Experiment | Description | Status |
|------------|-------------|--------|
| exp13_urban_dataset | 300×300m urban area, 6 BSs, 200K samples, zone-based NLOS | ✅ Ready |

**✓ Completion criteria**: 
- 200,000 samples with mixed indoor/outdoor environments
- Hybrid BS deployment (macro + outdoor + indoor small cells)
- Zone-based propagation (outdoor open/obstructed, indoor light/heavy)
- Variable UE heights (0.8-1.8m)
- Production-grade dataset for real-world deployment

---

### 📊 Level 7: CSI Distribution Study
**Location**: `experiments/07_csi_distribution/`  
**Time**: 1-2 hours  
**Goal**: Study statistical distribution of CSI at fixed locations

| Experiment | Description | Status |
|------------|-------------|--------|
| exp12_csi_distribution | CSI distribution on 20×20 grid, 100 samples/point | Coming soon |

**✓ Completion criteria**: 
- Understand CSI variability at fixed locations
- Characterize statistical properties (mean, variance)
- Generate spatial heatmaps of signal quality
- Study LOS/NLOS effects on CSI distributions

---

### 🧪 Level 8: Static vs Walk CSI Comparison
**Location**: `experiments/08_static_vs_walk/`  
**Time**: 1-2 hours  
**Goal**: Test if CSI at a location depends on UE movement history

| Experiment | Description | Status |
|------------|-------------|--------|
| exp08a_static_grid | 9 UEs on 3×3 grid, 100 repetitions | ✅ Ready |
| exp08b_random_walk | Single UE random walk, 900 steps | ✅ Ready |
| analyze_static_vs_walk.py | Statistical comparison (Python) | ✅ Ready |

**Hypothesis**: CSI at location B should be the same whether UE arrived from A or was placed directly at B.

**✓ Completion criteria**: 
- Compare CSI difference distributions (static vs walk)
- K-S test for distribution similarity
- Per-pair analysis for all adjacent grid points
- Determine if channel model has memory/temporal effects

---

### 🤖 Level 9: ML Training
**Location**: `experiments/09_ml_training/`  
**Time**: Ongoing  
**Goal**: Train and evaluate location prediction models

| Experiment | Description | Status |
|------------|-------------|--------|
| exp14_baseline_rf | Random Forest baseline | Coming soon |
| exp15_neural_network | Feedforward NN | Coming soon |
| exp16_lstm_temporal | LSTM for trajectories | Coming soon |
| exp17_model_comparison | Compare all models | Coming soon |

**✓ Completion criteria**: < 10m mean localization error

---

## 🚀 Quick Start

```matlab
% 1. Setup (do once)
addpath(genpath('utils'));
savepath;

% 2. Start with Level 1
cd experiments/01_basics
exp01_minimal_setup

% 3. Progress through experiments in order
```

## 📈 Your Progress

Track your learning:

- [ ] **Level 1 Complete**: Basics mastered
- [ ] **Level 2 Complete**: Metrics mastered  
- [ ] **Level 3 Complete**: Movement simulated
- [ ] **Level 4 Complete**: LOS dataset generated (500+ trajectories)
- [ ] **Level 5 Complete**: NLOS dataset generated (500+ trajectories)
- [ ] **Level 6 Complete**: Urban dataset generated (2000 trajectories, 200K samples)
- [ ] **Level 7 Complete**: CSI distributions characterized
- [ ] **Level 8 Complete**: Static vs Walk comparison analyzed
- [ ] **Level 9 Complete**: Model trained (< 10m error)
- [ ] **Project Complete**: Thesis written!

---

## 💡 Tips

1. **Don't skip levels** - Each builds on the previous
2. **Experiment with parameters** - Change values and observe
3. **Save your results** - Use `../../results/` folder
4. **Read the console output** - Explanations included
5. **Check plots** - Visual understanding is key

---

## 📚 Documentation

For detailed guides, see:
- `docs/SCRIPTS_EXPLAINED.md` - Complete script reference
- `docs/ML_LOCATION_PREDICTION_GUIDE.md` - ML project roadmap
- `docs/QUICK_REFERENCE.md` - Quick commands
- Each `experiments/XX_name/README.md` - Level-specific info

---

*Start your journey: `cd experiments/01_basics && exp01_minimal_setup`*
