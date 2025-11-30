# Experiment 13: Urban Mixed Indoor/Outdoor Large-Scale Dataset

## 🎯 Overview

This experiment generates a **realistic urban scenario dataset** combining indoor and outdoor environments for robust CSI-based localization. It represents the most comprehensive and realistic dataset in this project, scaling up to city-block size with hybrid base station deployment.

## 🏙️ Key Features

### Scale & Coverage
- **Area**: 300m × 300m (9 hectares) - **14× larger than exp11**
- **Samples**: 200,000 total (160K train, 40K validation) - **5× more than exp11**
- **Trajectories**: 2000 diverse movement patterns
- **Samples per trajectory**: 100 (longer paths for larger area)

### Realistic Urban Deployment
- **Frequency**: 3.0 GHz (5G mid-band with better penetration)
- **Subcarriers**: 2048 (finer frequency resolution)
- **Bandwidth**: 100 MHz
- **Base Stations**: 6 BSs with hybrid deployment
  - 2 Macro BSs (rooftop, 25m height, 35 dBm)
  - 2 Outdoor Small Cells (street poles, 10m height, 30 dBm)
  - 2 Indoor Small Cells (ceiling mounted, 6m height, 27 dBm)

### Environmental Zones
Samples are randomly assigned to zones based on realistic distribution:
- **Outdoor Open** (40%): Streets, plazas → Mostly LOS
- **Outdoor Obstructed** (15%): Trees, vehicles → Light NLOS
- **Indoor Light** (25%): Glass buildings, malls → Moderate NLOS
- **Indoor Heavy** (20%): Concrete buildings → Heavy NLOS

### Advanced Features
- **Variable UE Heights**: 0.8-1.8m (realistic user positions)
- **Zone-based NLOS**: Propagation conditions match environment type
- **Stop-and-Go Trajectories**: New pattern simulating shopping/browsing behavior
- **8 Trajectory Types**: Linear, circular, zigzag, random walk, grid, spiral, figure-8, stop-and-go

## 📊 Dataset Characteristics

### Feature Dimensions
- **Total features**: ~24,579 per sample
  - 3 wideband features (CQI, RSRP, SINR)
  - 24,576 per-subcarrier features (2048 × 6 BSs × 2 types: RSS, H_mag)

### Metadata Tracked
- Zone type (outdoor_open/obstructed, indoor_light/heavy)
- NLOS condition (pure_los, light/moderate/heavy NLOS)
- UE height (0.8-1.8m)
- Scenario name (3GPP propagation model)

## 🚀 Quick Start

### Prerequisites
1. MATLAB with QuaDRiGa installed
2. Utility functions in `utils/` directory
3. Sufficient disk space (~5-8 GB for dataset)
4. 2-3 hours runtime

### Running the Experiment

**🐛 RECOMMENDED: Start with Debug Mode**

Before running the full 2-3 hour generation, test with a quick 1-2 minute run:

```matlab
% 1. Enable debug mode
% Edit config_urban_dataset.m and set:
config.DEBUG_MODE = true;  % Line ~10

% 2. Run quick test
cd experiments/06_urban_scenario
exp13_urban_dataset  % Takes 1-2 minutes, generates 200 samples

% 3. If successful, disable debug mode for full run
% Edit config_urban_dataset.m and set:
config.DEBUG_MODE = false;

% 4. Run full generation
exp13_urban_dataset  % Takes 2-3 hours, generates 200K samples
```

**Debug Mode vs Production:**
| Mode | Trajectories | Samples/traj | Total | Time |
|------|--------------|--------------|-------|------|
| Debug | 10 | 20 | 200 | 1-2 min |
| Production | 2000 | 100 | 200K | 2-3 hrs |

### Monitoring Progress
The script provides detailed progress updates:
- Trajectory generation progress bar
- CSI simulation updates every 20 trajectories
- Estimated time remaining
- Current processing rate

## 📁 Output Structure

```
results/exp13_YYYY-MM-DD_HH-MM-SS/
├── dataset/
│   ├── train_data.mat          # 160,000 training samples
│   ├── val_data.mat            # 40,000 validation samples
│   └── metadata.mat            # Zone, NLOS, height metadata
├── trajectories/
│   └── trajectory_*.png        # Sample trajectory plots
├── analysis/
│   └── zone_nlos_analysis.png  # Zone/NLOS distribution analysis
└── experiment_report.txt       # Complete experiment summary
```

## 📈 Expected Results

### Dataset Statistics
- **Training**: 160,000 samples
- **Validation**: 40,000 samples
- **Spatial coverage**: 300×300m with good distribution
- **Feature count**: 24,579 per sample

### Zone Distribution (Approximate)
- Outdoor Open: ~80,000 samples (40%)
- Indoor Light: ~50,000 samples (25%)
- Outdoor Obstructed: ~30,000 samples (15%)
- Indoor Heavy: ~40,000 samples (20%)

### NLOS Distribution (Zone-weighted)
- Pure LOS: ~35-40% (mostly outdoor open)
- Light NLOS: ~20-25% (outdoor obstructed + some indoor)
- Moderate NLOS: ~25-30% (mostly indoor light)
- Heavy NLOS: ~15-20% (mostly indoor heavy)

## 🎯 Comparison with Previous Experiments

| Aspect | exp10 (LOS) | exp11 (NLOS) | exp13 (Urban) |
|--------|-------------|--------------|---------------|
| **Area** | 80×80m | 80×80m | **300×300m** |
| **Samples** | 40K | 40K | **200K** |
| **BSs** | 4 (corners) | 4 (corners) | **6 (hybrid)** |
| **Frequency** | 3.5 GHz | 3.5 GHz | **3.0 GHz** |
| **Subcarriers** | 1024 | 1024 | **2048** |
| **Features** | 3,075 | 12,291 | **24,579** |
| **Environment** | Pure LOS | Mixed NLOS | **Zone-based** |
| **UE Height** | 1.5m fixed | 1.5m fixed | **0.8-1.8m variable** |
| **Realism** | Basic | Enhanced | **Production-grade** |

## 🔬 Use Cases

### 1. Production ML Training
Train state-of-the-art models with sufficient data:
- Deep CNNs (200K samples enable complex architectures)
- Transformer-based models
- Ensemble methods

### 2. Robustness Testing
Evaluate model performance across conditions:
- Indoor vs outdoor accuracy
- LOS vs NLOS performance
- Height sensitivity analysis

### 3. Transfer Learning
Use as pre-training dataset for:
- Smaller deployment-specific datasets
- Different frequency bands
- Different BS configurations

### 4. Real-World Deployment Simulation
Most realistic dataset for:
- Shopping malls
- Airport terminals
- Large office complexes
- Mixed urban environments

## ⚙️ Configuration

All parameters are in `config_urban_dataset.m`:

### Key Configuration Parameters
```matlab
% Scenario size
config.scenario.bounds = struct(...
    'x_min', 0, 'x_max', 300, ...
    'y_min', 0, 'y_max', 300);

% BS positions and types
config.bs.positions = [
    50,  50,  25;    % Macro BS 1
    250, 250, 25;    % Macro BS 2
    150, 75,  10;    % Outdoor Small Cell 1
    150, 225, 10;    % Outdoor Small Cell 2
    75,  150, 6;     % Indoor Small Cell 1
    225, 150, 6];    % Indoor Small Cell 2

% Zone distribution
config.zone_distribution = struct(...
    'outdoor_open', 0.40, ...
    'outdoor_obstructed', 0.15, ...
    'indoor_light', 0.25, ...
    'indoor_heavy', 0.20);

% Variable UE height
config.ue.height_min = 0.8;
config.ue.height_max = 1.8;
```

## 📊 Visualization Tools

### BS Placement Visualization
```matlab
visualize_bs_placement
```
Generates:
- BS locations on 300×300m map
- Coverage circles for each BS type
- Zone type illustrations
- Detailed BS specifications

### Post-Generation Analysis
The experiment automatically generates:
- Zone distribution histograms
- NLOS condition distributions
- UE height distribution
- Spatial coverage maps
- RSRP analysis by zone/NLOS

## ⚠️ Important Notes

### Runtime Considerations
- **Estimated time**: 2-3 hours
- **Progress updates**: Every 20 trajectories
- **Save frequency**: Incremental during generation
- **Memory**: ~8-10 GB RAM recommended

### Disk Space
- **Raw dataset**: ~5-8 GB
- **Plots**: ~100-200 MB
- **Total**: ~6-9 GB

### Computational Requirements
- MATLAB R2019b or newer
- QuaDRiGa 2.4.0 or newer
- Multi-core CPU recommended (simulation is partially parallelizable)

## 🐛 Troubleshooting

### Issue: Out of memory
**Solution**: Reduce `n_trajectories` to 1000 or lower in config file

### Issue: QuaDRiGa errors
**Solution**: Ensure QuaDRiGa is properly installed and added to MATLAB path

### Issue: Slow simulation
**Solution**: 
- Reduce `config.output.plot_frequency` to 200 or 500
- Set `config.output.generate_plots = false` for faster run

### Issue: Missing trajectory functions
**Solution**: Ensure all `generate_*.m` files are in the experiment directory

## 🎯 Next Steps

After generating this dataset:

1. **Train Advanced Models**
   ```matlab
   cd ../../ml_training/experiments/neural_networks/training_scripts
   python train_improved_cnn.py --dataset exp13
   ```

2. **Compare Performance**
   - Compare exp13 vs exp11 (zone-based vs uniform NLOS)
   - Analyze indoor vs outdoor accuracy
   - Study impact of variable UE height

3. **Zone-Specific Analysis**
   - Train separate models per zone
   - Analyze which zones are hardest to localize
   - Optimize BS placement based on results

4. **Real-World Validation**
   - Use as baseline for real measurement campaigns
   - Transfer learning to deployment-specific data

## 📚 References

- Exp10: LOS baseline (80×80m, 4 BSs, 40K samples)
- Exp11: NLOS enhanced (80×80m, 4 BSs, mixed NLOS, 40K samples)
- Exp13: Urban scale (300×300m, 6 BSs, zone-based, 200K samples) ← **You are here**

## 📝 Citation

When using this dataset in publications:
```
Urban Mixed Indoor/Outdoor CSI Dataset (exp13)
300m × 300m area, 6 hybrid BSs, 200K samples
Zone-based propagation: 3GPP 38.901 LOS/NLOS/InH
3.0 GHz, 2048 subcarriers, variable UE heights
```

---

**Status**: ✅ Ready for use  
**Version**: 1.0  
**Last Updated**: November 25, 2025  
**Estimated Runtime**: 2-3 hours  
**Expected Output**: 200K samples, ~6-9 GB
