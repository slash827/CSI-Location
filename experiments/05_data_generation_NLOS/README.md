# Level 5: Large-Scale Data Generation - NLOS Scenarios

## 📊 Overview

This level focuses on generating **large-scale NLOS (Non-Line-of-Sight) datasets** for machine learning training. NLOS scenarios are critical for realistic indoor localization as they represent environments with obstacles, walls, and complex propagation paths.

## 🎯 Learning Objectives

By completing this level, you will:

- Generate large NLOS CSI datasets with diverse trajectories
- Understand NLOS channel characteristics and challenges
- Create realistic indoor propagation scenarios
- Build comprehensive training datasets for ML models
- Learn about NLOS detection and mitigation strategies

## 📁 Experiments

### Experiment 11: NLOS Dataset Generation
**File**: `exp11_nlos_dataset.m`  
**Configuration**: `config_nlos_dataset.m`  
**Time**: 2-3 hours  

#### What it does:
- Generates 500+ trajectories in **NLOS environments**
- Uses 3GPP indoor scenarios with obstacles
- Creates diverse movement patterns (linear, circular, zigzag, random walk, etc.)
- Produces 30,000+ training samples optimized for NLOS conditions

#### Key Parameters:
```matlab
Trajectories: 500+
Scenario: 3GPP_38.901_InH_NLOS (Indoor Hotspot NLOS)
Frequency: 3.5 GHz
Bandwidth: 100 MHz
Environment: Indoor with obstacles and walls
```

#### Output:
1. **Training Dataset**: ~32,000 NLOS samples
2. **Validation Dataset**: ~8,000 NLOS samples
3. **Features**: 771 per sample (3 wideband + 768 per-subcarrier)
4. **Trajectory Visualizations**: PNG/FIG plots
5. **Quality Reports**: Statistics and validation results

## 🔍 NLOS vs LOS Differences

### Channel Characteristics

| Property | LOS | NLOS |
|----------|-----|------|
| **Path Loss** | Lower | Higher (10-20 dB more) |
| **Multipath** | Few dominant paths | Many scattered paths |
| **Fading** | Rician distribution | Rayleigh distribution |
| **Variability** | More stable | Higher variance |
| **Delay Spread** | Small | Large |

### Impact on Localization

- **NLOS Error**: Can cause 5-20m positioning errors
- **Challenge**: Harder to distinguish nearby locations
- **Solution**: More training data + NLOS-aware features

## 🚀 Quick Start

### Prerequisites
- Completed Level 3 (UE Movement) experiments
- Completed Level 4 (LOS Data Generation)
- QuaDRiGa properly installed
- At least 2-3 hours available

### Running the Experiment

```matlab
% 1. Navigate to experiment folder
cd experiments/05_data_generation_NLOS

% 2. (Optional) Review/modify configuration
edit config_nlos_dataset.m

% 3. Run the experiment
exp11_nlos_dataset

% 4. Validate the dataset
validate_dataset
```

### Expected Runtime
- **500 trajectories** × 80 timesteps = 40,000 samples
- **Estimated time**: 2-3 hours
- Progress updates every 10 trajectories

## 📊 Dataset Statistics

### Expected Output
```
Training samples: ~32,000
Validation samples: ~8,000
Total samples: ~40,000
Features per sample: 771

Trajectory types:
  - Linear: 20%
  - Circular: 15%
  - Zigzag: 15%
  - Random Walk: 20%
  - Grid: 10%
  - Spiral: 10%
  - Figure-8: 10%
```

### Quality Metrics
- **Spatial Coverage**: >90% of environment
- **Distance Range**: 5-80m from BS
- **RSS Range**: -110 to -50 dBm (typical NLOS)
- **SINR Range**: -5 to 20 dB

## 📖 Documentation Files

### Main Documentation
- **`NLOS_QUICKSTART.md`**: Quick start guide
- **`NLOS_IMPLEMENTATION.md`**: Technical implementation details
- **`NLOS_SUMMARY.md`**: Project summary and results
- **`NLOS_DATASET_VALIDATION.md`**: Validation procedures

### Configuration
- **`config_nlos_dataset.m`**: All experiment parameters

## 🔧 Customization

### Adjust Dataset Size
```matlab
% In config_nlos_dataset.m
config.n_trajectories = 200;   % Faster (16,000 samples)
config.n_trajectories = 1000;  % Larger (80,000 samples)
```

### Change Trajectory Mix
```matlab
% Adjust trajectory distribution
config.trajectory_distribution = struct(...
    'linear', 0.30, ...      % More linear paths
    'random_walk', 0.30, ... % More random walks
    'circular', 0.10, ...
    'zigzag', 0.10, ...
    'grid', 0.10, ...
    'spiral', 0.05, ...
    'figure8', 0.05 ...
);
```

### Modify NLOS Severity
```matlab
% Stronger NLOS effects
config.scenario.type = '3GPP_38.901_InH_NLOS';  % Indoor NLOS
config.scenario.shadowing_std = 8;  % Higher shadowing (dB)

% Less severe NLOS
config.scenario.type = '3GPP_38.901_UMi_NLOS';  % Urban Micro NLOS
```

## 🎓 Key Concepts

### NLOS Propagation
- **Reflection**: Signals bounce off walls, furniture
- **Diffraction**: Signals bend around obstacles
- **Scattering**: Signals scatter from rough surfaces
- **Penetration**: Reduced through walls (10-30 dB loss)

### NLOS Detection
Indicators of NLOS conditions:
- High path loss (compared to free-space)
- Large delay spread
- Low Rice K-factor (< 0 dB)
- High channel variability

### Applications
1. **Indoor Localization**: Main use case
2. **NLOS Mitigation**: Identify and correct NLOS errors
3. **Hybrid LOS/NLOS Models**: Combine both datasets
4. **Scenario Classification**: Detect environment type

## 📈 Integration with ML Training

### After Dataset Generation

```bash
# 1. Navigate to ML training folder
cd ../../ml_training

# 2. Update dataset path in config
# Edit config.py: NLOS_DATASET_PATH = '../results/exp11_.../dataset'

# 3. Train models on NLOS data
python models/baseline_models.py --dataset nlos

# 4. Compare LOS vs NLOS performance
python analysis/compare_scenarios.py
```

### Expected Performance
- **NLOS MAE**: 8-15m (worse than LOS due to propagation)
- **Improvement**: With more data, can achieve 5-10m
- **Combined Dataset**: Mix LOS+NLOS for robustness

## ⚠️ Important Notes

### Computational Requirements
- **Long runtime**: 2-3 hours for 500 trajectories
- **Memory**: ~2-4 GB for complete dataset
- **Storage**: ~1-2 GB for saved results

### NLOS Challenges
- Higher positioning errors expected
- More training data needed than LOS
- Feature engineering more critical
- May need NLOS-specific algorithms

### Best Practices
1. **Start small**: Test with 50 trajectories first
2. **Validate frequently**: Check data quality
3. **Monitor progress**: Watch console output
4. **Save incrementally**: Don't lose hours of work
5. **Document parameters**: Note what worked

## 🎯 Completion Checklist

After running this experiment, you should have:

- [ ] Generated 30,000+ NLOS training samples
- [ ] Created 8,000+ NLOS validation samples
- [ ] Achieved >90% spatial coverage
- [ ] Validated dataset quality
- [ ] Saved all trajectory visualizations
- [ ] Documented experiment results
- [ ] Ready dataset for ML training

## 📚 Related Experiments

### Prerequisites
- **Exp01-03**: Basic QuaDRiGa concepts
- **Exp07-09**: Trajectory generation
- **Exp10**: LOS dataset generation (Level 4)

### Next Steps
- **Exp12**: CSI distribution study (Level 6)
- **Exp13+**: ML model training (Level 7)
- **Analysis**: Compare LOS vs NLOS performance

## 🆘 Troubleshooting

### Simulation Too Slow
- Reduce trajectories: `config.n_trajectories = 100`
- Reduce timesteps: `config.n_timesteps = 40`
- Disable plots: `config.output.generate_plots = false`

### High Path Loss Values
- Normal for NLOS! Expect -100 to -110 dBm
- Check BS power: `config.bs.tx_power_dbm`
- Verify scenario: `config.scenario.type`

### Low Spatial Coverage
- Increase random walk trajectories
- Expand area bounds
- Add more grid patterns

### Memory Issues
- Disable raw channel saving
- Process in smaller batches
- Use `-v7.3` MAT-file format

---

**Good luck with NLOS dataset generation!** 🚀

For questions, refer to:
- `NLOS_QUICKSTART.md` - Quick reference
- `NLOS_IMPLEMENTATION.md` - Technical details
- `docs/TECHNICAL_FAQ.md` - General FAQ
