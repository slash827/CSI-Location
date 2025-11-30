# Experiment 13: Quick Start Guide

## 📡 Base Station Configuration

### BS Placement Overview (300m × 300m Area)

```
                    300m
     ┌──────────────────────────────────┐
     │                                  │
     │         BS4 (150, 225, 10m)     │  ← North outdoor small cell
     │              ▪                   │
     │                                  │
 300m│  BS5                    BS6     │
     │  (75,150,6m)         (225,150,6m)│  ← Indoor small cells (center)
     │     ●                    ●       │
     │                                  │
     │         BS3 (150, 75, 10m)      │  ← South outdoor small cell
     │              ▪                   │
     │                                  │
     │  BS1                    BS2     │
     │  (50,50,25m)         (250,250,25m)│  ← Macro BSs (corners)
     │     ▲                    ▲       │
     └──────────────────────────────────┘
          0                           300m

Legend:
  ▲ = Macro BS (25m height, 35 dBm)
  ▪ = Outdoor Small Cell (10m height, 30 dBm)
  ● = Indoor Small Cell (6m height, 27 dBm)
```

### Detailed BS Specifications

| ID | Type | Position (x,y,z) | Height | Power | Coverage |
|----|------|------------------|--------|-------|----------|
| BS1 | Macro | (50, 50, 25)m | 25m | 35 dBm | ~150m radius |
| BS2 | Macro | (250, 250, 25)m | 25m | 35 dBm | ~150m radius |
| BS3 | Outdoor Small | (150, 75, 10)m | 10m | 30 dBm | ~80m radius |
| BS4 | Outdoor Small | (150, 225, 10)m | 10m | 30 dBm | ~80m radius |
| BS5 | Indoor Small | (75, 150, 6)m | 6m | 27 dBm | ~50m radius |
| BS6 | Indoor Small | (225, 150, 6)m | 6m | 27 dBm | ~50m radius |

## 🎯 Key Features

### Scenario Configuration
- **Area**: 300m × 300m (9 hectares)
- **Frequency**: 3.0 GHz (5G mid-band)
- **Bandwidth**: 100 MHz
- **Subcarriers**: 2048
- **Subcarrier Spacing**: 48.83 kHz

### Dataset Scale
- **Trajectories**: 2000
- **Samples per trajectory**: 100
- **Total samples**: 200,000 (160K train, 40K validation)

### Environment Zones
| Zone | Percentage | NLOS Tendency |
|------|-----------|---------------|
| Outdoor Open | 40% | Mostly LOS (80% LOS, 20% light NLOS) |
| Indoor Light | 25% | Moderate NLOS (70% moderate, 20% heavy) |
| Indoor Heavy | 20% | Heavy NLOS (90% heavy, 10% moderate) |
| Outdoor Obstructed | 15% | Light NLOS (60% light, 20% LOS) |

### Trajectory Types Distribution
| Type | Count | Percentage |
|------|-------|-----------|
| Linear | 500 | 25% |
| Random Walk | 500 | 25% |
| Zigzag | 300 | 15% |
| Circular | 200 | 10% |
| Stop-and-Go | 200 | 10% |
| Grid | 100 | 5% |
| Spiral | 100 | 5% |
| Figure-8 | 100 | 5% |

## 🚀 Running the Experiment

### Step 0: Debug Mode (Recommended First Run!)
Before running the full 2-3 hour generation, test with debug mode:

1. **Open `config_urban_dataset.m`**
2. **Set `config.DEBUG_MODE = true`** (line ~10)
3. **Run the experiment** - takes only 1-2 minutes!

```matlab
% In config_urban_dataset.m:
config.DEBUG_MODE = true;  % Enable debug mode

% Then run:
cd experiments/06_urban_scenario
exp13_urban_dataset

% Output: 🐛 DEBUG MODE: Running quick test
%         - Trajectories: 10 (instead of 2000)
%         - Samples/traj: 20 (instead of 100)
%         - Total samples: ~200 (instead of 200K)
%         - Estimated time: 1-2 minutes
```

This generates a **tiny dataset (200 samples)** to verify:
- ✅ No errors
- ✅ Proper BS configuration
- ✅ Zone assignment working
- ✅ Data saving correctly

### Step 1: Production Run
Once debug run succeeds:

1. **Set `config.DEBUG_MODE = false`** in config file
2. **Run the full experiment**

```matlab
cd experiments/06_urban_scenario
exp13_urban_dataset  % Now runs full 200K sample generation
```

### Expected Runtime
- **Trajectory generation**: ~5 minutes
- **CSI simulation**: ~2-3 hours
- **Analysis & saving**: ~5-10 minutes
- **Total**: ~2.5-3.5 hours

### Auto-Save & Resume Feature ⚡
The experiment automatically saves checkpoints:
- **Every 50 trajectories** processed
- **Every 30 minutes** of runtime
- If interrupted (crash/sleep), simply **re-run the script** - it will resume from the last checkpoint!

```matlab
% If interrupted, just run again - it will resume automatically
exp13_urban_dataset
% Output: ⚠️  Found existing checkpoint! Loading...
%         ✓ Resuming from trajectory 450/2000
```

To **start fresh** (delete checkpoint):
```matlab
delete('results/exp13_*/dataset/checkpoint.mat')
exp13_urban_dataset
```

### Progress Monitoring
You'll see:
```
========================================
EXP13: URBAN MIXED SCENARIO GENERATION
========================================

Generating trajectories...
Progress: [==================================================]
✓ Generated 2000 trajectories

Simulating CSI data with zone-based NLOS...
This will take 2-3 hours...

  Processed 20/2000 trajectories (1.0%) - Elapsed: 1.2 min, ETA: 118.8 min
  Processed 40/2000 trajectories (2.0%) - Elapsed: 2.4 min, ETA: 117.6 min
  💾 Saving checkpoint at trajectory 50...
  ✓ Checkpoint saved
  Processed 60/2000 trajectories (3.0%) - Elapsed: 3.6 min, ETA: 116.4 min
  ...
```

**Checkpoints saved every**:
- 50 trajectories completed
- 30 minutes elapsed (whichever comes first)

## 📊 Expected Output

### File Structure
```
results/exp13_YYYY-MM-DD_HH-MM-SS/
├── dataset/
│   ├── train_data.mat      (~4 GB)
│   ├── val_data.mat        (~1 GB)
│   └── metadata.mat        (~200 MB)
├── trajectories/
│   └── trajectory_*.png    (every 100th)
├── analysis/
│   └── zone_nlos_analysis.png
└── experiment_report.txt
```

### Dataset Files Content

**train_data.mat** (160,000 samples):
- `CQI_wb`: Wideband CQI
- `RSRP`: Reference Signal Received Power
- `SINR_wb`: Wideband SINR
- `RSS_per_sc`: RSS per subcarrier [12288 × 160000]
- `SINR_per_sc`: SINR per subcarrier [12288 × 160000]
- `H_mag_per_sc`: Channel magnitude per subcarrier [12288 × 160000]
- `positions_x`, `positions_y`: Ground truth positions

**metadata.mat**:
- `train_zones`: Zone type (1-4) for each sample
- `train_nlos_conditions`: NLOS type (1-4) for each sample
- `train_scenarios`: 3GPP scenario name per sample
- `train_ue_heights`: UE height (0.8-1.8m) per sample
- (Same for validation)

## 🎓 Next Steps After Generation

### 1. Verify Dataset Quality
```matlab
% Check spatial coverage
load('results/exp13_*/dataset/train_data.mat');
figure;
scatter(positions_x, positions_y, 1, '.');
title('Spatial Coverage');
```

### 2. Train ML Models
```python
cd ../../ml_training/experiments/neural_networks/training_scripts
python train_improved_cnn.py --dataset exp13
```

### 3. Analyze Results
- Compare exp13 (urban) vs exp11 (NLOS) vs exp10 (LOS)
- Analyze zone-specific performance
- Study impact of variable UE height

## ⚠️ Troubleshooting

### Memory Issues
If you run out of memory:
1. Reduce `config.n_trajectories` from 2000 to 1000
2. Or reduce `config.n_timesteps` from 100 to 80

### Slow Simulation
To speed up:
1. Set `config.output.generate_plots = false`
2. Increase `config.output.plot_frequency` to 500
3. Use a machine with more CPU cores

### QuaDRiGa Errors
Ensure QuaDRiGa is properly installed:
```matlab
which qd_layout  % Should show QuaDRiGa path
```

## 📈 Comparison with Previous Experiments

| Feature | exp10 | exp11 | **exp13** |
|---------|-------|-------|-----------|
| Area | 80×80m | 80×80m | **300×300m** ✨ |
| BSs | 4 corners | 4 corners | **6 hybrid** ✨ |
| Samples | 40K | 40K | **200K** ✨ |
| Frequency | 3.5 GHz | 3.5 GHz | **3.0 GHz** |
| Subcarriers | 1024 | 1024 | **2048** ✨ |
| Environment | Pure LOS | Mixed NLOS | **Zone-based** ✨ |
| UE Height | 1.5m fixed | 1.5m fixed | **0.8-1.8m variable** ✨ |
| Features | 3,075 | 12,291 | **24,579** ✨ |
| Runtime | 10 min | 15 min | **2-3 hours** |
| Storage | 500 MB | 800 MB | **~6 GB** |

✨ = Enhanced in exp13

## 🎯 Dataset Realism Features

This dataset simulates:
- ✅ Real urban block (300×300m)
- ✅ Hybrid BS deployment (macro + small cells)
- ✅ Mixed indoor/outdoor propagation
- ✅ Variable user heights (sitting/standing)
- ✅ Realistic movement patterns (including stop-and-go)
- ✅ Zone-appropriate NLOS conditions
- ✅ Production-scale sample count (200K)

---

**Ready to generate? Run**: `exp13_urban_dataset`  
**Estimated time**: 2-3 hours  
**Output**: 200K samples, ~6 GB dataset
