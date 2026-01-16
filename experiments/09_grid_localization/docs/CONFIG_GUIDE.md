# Configuration Guide

## Overview

The experiment is now configured via **`config.json`** instead of editing MATLAB code. This makes it easier to:
- Adjust parameters without touching code
- Reproduce experiments exactly
- Run parameter sweeps
- Share configurations

## Configuration File Structure

### Example: `config.json`

```json
{
  "experiment": {
    "name": "exp13e_corrected_fair_comparison",
    "description": "Static vs Transition-based localization comparison",
    "random_seed": 42
  },
  
  "grid": {
    "size": 3,
    "spacing": 2.0,
    "ue_height": 1.5,
    "grid_offset": [20, 0],
    "position_jitter": 0.1
  },
  
  "movement": {
    "n_steps": 10000,
    "ue_speed": 1.5,
    "starting_point": "center"
  },
  
  "channel": {
    "scenario": "3GPP_38.901_UMa_LOS",
    "center_frequency": 3e9,
    "bandwidth": 1e8,
    "n_subcarriers": 256
  },
  
  "base_station": {
    "position": [0, 0, 25],
    "tx_power_dbm": 30
  },
  
  "classification": {
    "test_ratio": 0.2,
    "metrics": ["RSS", "SINR", "CQI"]
  },
  
  "output": {
    "save_results": true,
    "generate_plots": true,
    "save_raw_data": true,
    "verbose": true
  }
}
```

## Parameter Reference

### experiment
- **name**: Experiment identifier
- **description**: Brief description
- **random_seed**: Seed for reproducibility (42 recommended)

### grid
- **size**: Grid dimension (N for N×N grid)
  - Small: 3 (9 points, ~2-3 min)
  - Medium: 5 (25 points, ~6-8 min)
  - Large: 10 (100 points, ~25-30 min)
  - Very Large: 20 (400 points, ~2-3 hours)
  
- **spacing**: Distance between adjacent points (meters)
  - Default: 2.0m
  - Larger spacing = larger coverage area
  
- **ue_height**: UE antenna height (meters)
  - Typical: 1.5m (handheld device)
  
- **grid_offset**: Grid center position [x, y] (meters)
  - Default: [20, 0] (20m from BS)
  
- **position_jitter**: Random position variation (meters)
  - Default: 0.1m (realistic positioning uncertainty)

### movement
- **n_steps**: Number of random walk steps
  - Recommendation: `size² × 1200` for ~1200 samples/point
  - 3×3: 10,000 steps
  - 5×5: 30,000 steps
  - 10×10: 120,000 steps
  
- **ue_speed**: UE movement speed (m/s)
  - Default: 1.5 m/s (walking speed)
  - Step duration = spacing / speed
  
- **starting_point**: Initial position
  - "center": Middle of grid (recommended)

### channel
- **scenario**: 3GPP channel model
  - LOS: `"3GPP_38.901_UMa_LOS"`
  - NLOS: `"3GPP_38.901_UMa_NLOS"`
  
- **center_frequency**: Carrier frequency (Hz)
  - Default: 3e9 (3 GHz)
  - Affects path loss and scattering
  
- **bandwidth**: Channel bandwidth (Hz)
  - Default: 1e8 (100 MHz)
  - More subcarriers = better frequency selectivity
  
- **n_subcarriers**: Number of OFDM subcarriers
  - Default: 256
  - Trade-off: accuracy vs computation time
  
- **interference_per_sc_dbm**: Interference level per subcarrier (dBm)
  - Default: -999 (no interference, RSS = SINR)
  - Recommended: -85 to -90 dBm for realistic scenario
  - Effect: SINR becomes different from RSS
  - Benefits: Captures signal quality, not just strength

### base_station
- **position**: BS location [x, y, z] (meters)
  - Default: [0, 0, 25] (25m height)
  
- **tx_power_dbm**: Transmit power (dBm)
  - Default: 30 dBm
  - Currently informational (not used in calculations)

### classification
- **test_ratio**: Fraction of data for testing
  - Default: 0.2 (80/20 train/test split)
  
- **metrics**: CSI metrics to evaluate
  - Default: ["RSS", "SINR", "CQI"]
  - Currently all three are computed

### output
- **save_results**: Save .mat file
  - Default: true
  
- **generate_plots**: Auto-generate Python plots
  - Default: true
  - Requires: Python with matplotlib, seaborn, scipy
  
- **save_raw_data**: Include full channel data
  - Default: true
  
- **verbose**: Print detailed progress
  - Default: true

## Common Configurations

### Quick Test (3×3, LOS)
```json
{
  "grid": {"size": 3, "spacing": 2.0},
  "movement": {"n_steps": 10000},
  "channel": {"scenario": "3GPP_38.901_UMa_LOS"}
}
```
**Runtime:** ~2-3 minutes

### Standard Experiment (5×5, LOS)
```json
{
  "grid": {"size": 5, "spacing": 2.0},
  "movement": {"n_steps": 30000},
  "channel": {"scenario": "3GPP_38.901_UMa_LOS"}
}
```
**Runtime:** ~6-8 minutes

### NLOS Challenge (5×5)
```json
{
  "grid": {"size": 5, "spacing": 2.0},
  "movement": {"n_steps": 30000},
  "channel": {"scenario": "3GPP_38.901_UMa_NLOS"}
}
```
**Runtime:** ~6-8 minutes
**Expected:** Lower accuracy, MAE impact more visible

### Large Scale (10×10, LOS)
```json
{
  "grid": {"size": 10, "spacing": 2.0},
  "movement": {"n_steps": 120000},
  "channel": {"scenario": "3GPP_38.901_UMa_LOS"}
}
```
**Runtime:** ~25-30 minutes
**Use case:** Test scaling behavior

## Workflow

### 1. Create Custom Config
```bash
cd experiments/09_grid_localization
cp config.json config_5x5_nlos.json
# Edit config_5x5_nlos.json
```

### 2. Update Default Config
```bash
# Replace config.json with your custom one
cp config_5x5_nlos.json config.json
```

### 3. Run Experiment
```matlab
cd experiments/09_grid_localization
run exp13e_corrected_fair_comparison
```

### 4. Results Location
```
results/grid_localization/grid_5x5/exp13e_corrected_YYYY-MM-DD_HH-MM-SS/
├── corrected_comparison_results.mat
├── experiment_config.json          ← Copy of config used
├── CORRECTED_SUMMARY_REPORT.md
├── confusion_matrices.png
├── spatial_error_map.png
├── metrics_comparison.png
├── visit_distribution.png
├── rss_distributions.png
└── summary_dashboard.png
```

## Tips

### Reproducibility
- Always set `random_seed` to a fixed value (e.g., 42)
- The config is automatically copied to results
- Use `run_from_config.m` to reproduce any experiment

### Parameter Sweeps
Create multiple config files:
```
config_3x3_los.json
config_3x3_nlos.json
config_5x5_los.json
config_5x5_nlos.json
```

Run batch:
```bash
for config in config_*.json; do
    cp $config config.json
    matlab -batch "cd experiments/09_grid_localization; exp13e_corrected_fair_comparison"
done
```

### Debugging
If experiment fails:
1. Check `config.json` syntax (valid JSON?)
2. Verify Python installation: `python --version`
3. Disable plotting: `"generate_plots": false`
4. Reduce grid size for faster testing

### Performance Tuning
- **Faster:** Reduce `n_subcarriers` (256 → 128)
- **More accurate:** Increase `n_steps`
- **Less memory:** Reduce `n_steps`
- **Skip plots:** Set `generate_plots: false`

---

*Always commit `config.json` to version control alongside your results!*
