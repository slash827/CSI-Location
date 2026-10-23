# Common Commands - Grid Localization Pipeline

Quick reference for running the grid localization pipeline components.

## 📋 Table of Contents

- [Configuration](#configuration)
- [Data Generation](#data-generation-matlab)
- [Classification Pipeline](#classification-pipeline-python)
- [Regression Pipeline](#regression-pipeline-python)
- [Visualization](#visualization)
- [Common Scenarios](#common-scenarios)

---

## Configuration

Two separate config files:
- **`configs/data_generation_config.jsonc`** - Data generation parameters (grid, channel, movement)
- **`configs/ml_config.jsonc`** - ML training parameters (features, models, realistic AoA impairments)

The data generation config is automatically copied with each dataset for reproducibility.

---

## Data Generation (MATLAB)

**Script:** `src/matlab/generate_simulation_data.m`  
**Config:** `configs/data_generation_config.jsonc`

Generates simulation data with UE movement, channel models, and metrics (RSS, SINR, CQI, AoA, Timing Advance).

### From MATLAB

```matlab
cd experiments/09_grid_localization/src/matlab
generate_simulation_data
```

### From PowerShell

```powershell
# Generate data with current config
cd D:\gilad\projects\Academy\CSI-Location
matlab -batch "cd experiments/09_grid_localization/src/matlab; generate_simulation_data"
```

### Configuration

Edit `configs/data_generation_config.jsonc`:
- `grid.size` - Grid dimensions (e.g., 3, 7, 10)
- `channel.scenario` - `3GPP_38.901_UMa_LOS` or `3GPP_38.901_UMa_NLOS`
- `movement.steps_per_point` - Samples per grid point (default: 400)
- `grid.neighbor_connectivity` - 4 (straight) or 8 (includes diagonals)
- `output.auto_run_pipeline` - Auto-run Python pipeline after generation (default: false)

**Output:** Creates `results/grid_localization/grid_NxN/sim_data_SCENARIO_TIMESTAMP/`
- `simulation_data.mat` - Metrics, walk path, grid config
- `data_generation_config.jsonc` - Copy of generation parameters
- `plots/` - Auto-generated visualization plots

---

## Classification Pipeline (Python)

**Script:** `src/python/localization_pipeline.py`  
**Task:** Predict which grid point the UE is at

### Basic Usage

```powershell
# Run with Random Forest on RSS, SINR, CQI
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir results\grid_localization\grid_10x10\sim_data_NLOS_2026-01-22_10-02-40 --model random_forest --metrics rss,sinr,cqi
```

### With AoA and Timing Advance

```powershell
# Use all available features (realistic AoA noise applied from ml_config.jsonc)
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir <DATA_DIR> --model random_forest --metrics rss,sinr,cqi,aoa_azimuth,aoa_elevation,timing_advance
```

### Data Split Methods

```powershell
# Temporal split (prevent data leakage, recommended)
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir <DATA_DIR> --split-method temporal --model random_forest --metrics rss,sinr,cqi

# Random split
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir <DATA_DIR> --split-method random --model random_forest --metrics rss,sinr,cqi
```

### Model Options

```powershell
# Random Forest (best for multiple features)
--model random_forest

# Gaussian models (static and transition-based)
--model gaussian --max-history 3
```

**Output:** Creates `results/grid_localization/grid_NxN/exp_classification_SCENARIO_TIMESTAMP/`
- `SUMMARY_REPORT.md` - Accuracy, MAE, confusion matrices
- `*.png` - Plots and visualizations

---

## Regression Pipeline (Python)

**Script:** `src/python/localization_pipeline_regression.py`  
**Task:** Predict distance, azimuth, and elevation to BS (continuous values)

### Basic Usage

```powershell
# Regression with RSS, SINR, CQI only (no AoA as features)
python experiments\09_grid_localization\src\python\localization_pipeline_regression.py --data-dir results\grid_localization\grid_10x10\sim_data_LOS_2026-01-22_09-02-09 --split-method temporal --features rss,sinr,cqi
```

### With Noisy AoA as Features

```powershell
# Using noisy AoA measurements to predict clean position
# Note: Realistic AoA impairments applied from ml_config.jsonc
python experiments\09_grid_localization\src\python\localization_pipeline_regression.py --data-dir <DATA_DIR> --split-method temporal --features rss,sinr,cqi,aoa_azimuth,aoa_elevation
```

### Multiple Feature Sets

```powershell
# Test multiple feature combinations
python experiments\09_grid_localization\src\python\localization_pipeline_regression.py --data-dir <DATA_DIR> --split-method temporal --features rss,sinr,cqi rss,sinr,cqi,timing_advance
```

**Output:** Creates `results/grid_localization/grid_NxN/exp_regression_SCENARIO_TIMESTAMP/`
- `REGRESSION_REPORT.md` - MAE, RMSE, R² for distance, azimuth, elevation
- Target predictions vs ground truth

---

## Visualization

### Data Generation Plots (Automatic)

Generated automatically after data generation (if `output.generate_plots: true`):
- `metric_distributions.png` - Histograms and KDE for all metrics
- `walk_path_analysis.png` - Heatmap and trajectory
- `spatial_coverage.png` - Metric values per grid point
- `temporal_evolution.png` - Time series with moving average

### Manual Plot Generation

```powershell
# Regenerate data generation plots
python experiments\09_grid_localization\src\python\plot_data_generation.py "results\grid_localization\grid_10x10\sim_data_LOS_2026-01-22_09-02-09"
```

---

## Common Scenarios

### Quick Test (Generate LOS Data)

```powershell
# 1. Edit config: Set scenario to LOS, grid size to 10
# 2. Generate data
matlab -batch "cd experiments/09_grid_localization/src/matlab; generate_simulation_data"
```

### Classification with All Features

```powershell
# Use all available features including noisy AoA
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir results\grid_localization\grid_10x10\sim_data_LOS_2026-01-22_09-02-09 --split-method temporal --model random_forest --metrics rss,sinr,cqi,aoa_azimuth,aoa_elevation,timing_advance
```

### Regression: Predict Position from RSS/SINR/CQI

```powershell
# Predict distance + angles without using AoA as input
python experiments\09_grid_localization\src\python\localization_pipeline_regression.py --data-dir results\grid_localization\grid_10x10\sim_data_LOS_2026-01-22_09-02-09 --split-method temporal --features rss,sinr,cqi
```

### LOS vs NLOS Comparison

```powershell
# 1. Generate LOS data (edit config, set scenario to LOS)
matlab -batch "cd experiments/09_grid_localization/src/matlab; generate_simulation_data"

# 2. Generate NLOS data (edit config, set scenario to NLOS)
matlab -batch "cd experiments/09_grid_localization/src/matlab; generate_simulation_data"

# 3. Run regression on both
python experiments\09_grid_localization\src\python\localization_pipeline_regression.py --data-dir results\grid_localization\grid_10x10\sim_data_LOS_<TIMESTAMP> --split-method temporal --features rss,sinr,cqi

python experiments\09_grid_localization\src\python\localization_pipeline_regression.py --data-dir results\grid_localization\grid_10x10\sim_data_NLOS_<TIMESTAMP> --split-method temporal --features rss,sinr,cqi
```

### Test Different AoA Noise Levels

```powershell
# Edit configs/ml_config.jsonc:
#   "noise_std_deg": 2.0,  # Try 0, 2, 4, 6 degrees
#   "quantization_deg": 5.0

# Run classification with AoA features
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir <DATA_DIR> --split-method temporal --model random_forest --metrics aoa_azimuth,aoa_elevation
```

---

## Parameter Quick Reference

### Data Generation (`data_generation_config.jsonc`)
- `grid.size`: Grid dimensions (3, 7, 10)
- `grid.neighbor_connectivity`: 4 or 8 neighbors
- `channel.scenario`: LOS or NLOS
- `movement.steps_per_point`: Samples per grid point (default: 400)
- `output.auto_run_pipeline`: Run Python after generation (default: false)

### ML Training (`ml_config.jsonc`)
- `realistic_aoa.enabled`: Apply noise to AoA features (default: true)
- `realistic_aoa.noise_std_deg`: Gaussian noise std (default: 4.0°)
- `realistic_aoa.quantization_deg`: Quantization step (default: 5.0°)

### Classification Pipeline
- `--model`: `gaussian` or `random_forest`
- `--metrics`: Comma-separated feature list
- `--split-method`: `temporal` or `random`
- `--max-history`: History length for transition models (default: 3)

### Regression Pipeline
- `--features`: Comma-separated feature list (e.g., `rss,sinr,cqi`)
- `--split-method`: `temporal` or `random`
- `--model`: Currently only `random_forest`

---

## Available Features

| Feature | Description | Notes |
|---------|-------------|-------|
| `rss` | Received Signal Strength (dBm) | Wideband average |
| `sinr` | Signal-to-Interference-plus-Noise Ratio (dB) | Wideband average |
| `cqi` | Channel Quality Indicator | Quantized quality metric |
| `aoa_azimuth` | Angle of Arrival - Azimuth (degrees) | Clean in data, noisy in ML |
| `aoa_elevation` | Angle of Arrival - Elevation (degrees) | Clean in data, noisy in ML |
| `timing_advance` | Timing Advance (μs) | Usually constant on small grids |

---

## Tips

1. **Use temporal split** - Prevents data leakage from correlated consecutive samples
2. **Timing Advance is often useless** - Grid too small (18m range difference = 61ns)
3. **AoA data is clean** - Realistic impairments applied during ML training for flexibility
4. **Regression predicts clean targets** - Even when using noisy AoA as features
5. **Start with RSS,SINR,CQI** - Baseline features before adding AoA
6. **Compare classification vs regression** - Different approaches to localization
7. **Check `ml_config.jsonc` for AoA noise** - Can experiment without regenerating data

---

## Troubleshooting

### JSONC Comments Not Supported Error
- Fixed: Both MATLAB and Python now use custom JSONC parsers
- `read_jsonc.m` (MATLAB) and `read_jsonc.py` (Python)

### Config File Not Found
- Use `data_generation_config.jsonc` (renamed from `config.jsonc`)
- File automatically copied to each generated dataset

### AoA Perfect Fingerprinting (100% accuracy)
- Enable realistic impairments in `ml_config.jsonc`
- `realistic_aoa.enabled: true` applies 4° noise + 5° quantization

### Data Generation Fails with Path Warning
- Utils folder is now at workspace root (not experiment level)
- Script automatically fixes paths

---

## File Structure

```
experiments/09_grid_localization/
├── configs/
│   ├── data_generation_config.jsonc  # Data generation parameters
│   └── ml_config.jsonc                # ML training parameters
├── src/
│   ├── matlab/
│   │   ├── generate_simulation_data.m  # Data generation
│   │   └── read_jsonc.m                # JSONC parser
│   └── python/
│       ├── localization_pipeline.py           # Classification
│       ├── localization_pipeline_regression.py # Regression
│       ├── plot_data_generation.py            # Data viz
│       └── read_jsonc.py                      # JSONC parser
└── results/
    └── grid_localization/
        └── grid_10x10/
            ├── sim_data_LOS_<TIMESTAMP>/       # Generated data
            └── exp_regression_LOS_<TIMESTAMP>/  # ML results
```
