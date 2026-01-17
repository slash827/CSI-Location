# Common Commands - Grid Localization Pipeline

Quick reference for running the grid localization pipeline components.

## 📋 Table of Contents

- [Full Pipeline (Recommended)](#full-pipeline-recommended)
- [Individual Components](#individual-components)
  - [Data Generation (MATLAB)](#1-data-generation-matlab)
  - [Localization Pipeline (Python)](#2-localization-pipeline-python)
  - [Visualization (Python)](#3-visualization-python)
- [Common Scenarios](#common-scenarios)

---

## Full Pipeline (Recommended)

**Script:** `run_full_pipeline.py`  
**Description:** Orchestrates all steps: MATLAB data generation → Python localization → Plotting

### Basic Usage

```powershell
# Run complete pipeline with defaults (10x10 NLOS, 40k samples, Gaussian model)
python experiments\09_grid_localization\src\python\run_full_pipeline.py
```

### Custom Configurations

```powershell
# Generate 7x7 LOS grid with 20k samples
python experiments\09_grid_localization\src\python\run_full_pipeline.py --grid-size 7x7 --scenario LOS --n-samples 20000

# Use Random Forest model
python experiments\09_grid_localization\src\python\run_full_pipeline.py --model random_forest

# Test combined metrics (RSS+SINR fusion)
python experiments\09_grid_localization\src\python\run_full_pipeline.py --model random_forest --metrics RSS,SINR CQI

# 3x3 grid for quick testing
python experiments\09_grid_localization\src\python\run_full_pipeline.py --grid-size 3x3 --n-samples 5000
```

### Using Existing Data

```powershell
# Skip MATLAB, use existing simulation data
python experiments\09_grid_localization\src\python\run_full_pipeline.py --data-dir results\grid_localization\grid_10x10\sim_data_NLOS_2026-01-11_22-43-07

# Skip localization, only regenerate plots from existing results
python experiments\09_grid_localization\src\python\run_full_pipeline.py --results-dir results\grid_localization\grid_10x10\exp13e_NLOS_2026-01-12_07-40-39 --skip-pipeline

# Run localization only (no plots)
python experiments\09_grid_localization\src\python\run_full_pipeline.py --data-dir results\grid_localization\grid_10x10\sim_data_NLOS_2026-01-11_22-43-07 --skip-plots
```

---

## Individual Components

### 1. Data Generation (MATLAB)

**Script:** `generate_simulation_data.m`  
**Description:** Creates simulation data with user movement, channel models, and metrics (RSS/SINR/CQI)

```matlab
% In MATLAB - Run with default config (10x10 NLOS)
cd experiments/09_grid_localization/src/matlab
generate_simulation_data
```

```powershell
# From PowerShell - Custom configuration
matlab -batch "cd experiments/09_grid_localization; config.grid_size = '7x7'; config.scenario = 'LOS'; config.n_samples = 20000; generate_simulation_data(config);"
```

**Output:** Creates `results/grid_localization/grid_NxN/sim_data_SCENARIO_TIMESTAMP/`
- `simulation_data.mat` - Metrics, true locations, grid configuration
- `config.json` - Experiment configuration

---

### 2. Localization Pipeline (Python)

**Script:** `src/python/localization_pipeline.py`  
**Description:** Trains models and evaluates localization accuracy using different metrics and transition models

#### Basic Usage

```powershell
# Run with Gaussian models on RSS, SINR, CQI
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir results\grid_localization\grid_10x10\sim_data_NLOS_2026-01-11_22-43-07
```

#### Model Selection

```powershell
# Use Random Forest classifier
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir results\grid_localization\grid_10x10\sim_data_NLOS_2026-01-11_22-43-07 --model random_forest

# Use Gaussian models (default)
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir results\grid_localization\grid_10x10\sim_data_NLOS_2026-01-11_22-43-07 --model gaussian
```

#### Metric Selection

```powershell
# Test only RSS
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir <DATA_DIR> --metrics rss

# Test multiple individual metrics
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir <DATA_DIR> --metrics rss sinr cqi

# Test combined metrics (requires Random Forest)
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir <DATA_DIR> --model random_forest --metrics RSS,SINR RSS,CQI

# Mix of individual and combined
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir <DATA_DIR> --model random_forest --metrics rss RSS,SINR,CQI
```

#### History Length

```powershell
# Test transition models with different history lengths
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir <DATA_DIR> --max-history 3

# Only test static (no transition)
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir <DATA_DIR> --max-history 0
```

#### Other Options

```powershell
# Custom train/test split
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir <DATA_DIR> --test-ratio 0.3

# Specify output directory
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir <DATA_DIR> --output-dir my_custom_results
```

**Output:** Creates `results/grid_localization/grid_NxN/expXX_SCENARIO_TIMESTAMP/`
- `SUMMARY_REPORT.md` - Accuracy, MAE, timing summary
- `pipeline_results.npz` - Raw results for plotting

---

### 3. Visualization (Python)

**Script:** `src/python/plot_pipeline_results.py`  
**Description:** Generates comprehensive visualizations from pipeline results (new format)

```powershell
# Generate all plots from results directory
python experiments\09_grid_localization\src\python\plot_pipeline_results.py results\grid_localization\grid_10x10\exp13e_NLOS_2026-01-12_07-40-39
```

**Output:** Adds to results directory:
- `spatial_layout.png` - Grid and base station positions
- `metrics_comparison.png` - Accuracy and MAE comparison across all metrics and history lengths
- `history_progression.png` - Accuracy vs history length for each metric

**Note:** The old `plot_results.py` script only works with legacy MATLAB `.mat` format results.

---

## Common Scenarios

### Quick Test (3x3 Grid)

```powershell
# Fast test with small grid
python experiments\09_grid_localization\src\python\run_full_pipeline.py --grid-size 3x3 --n-samples 5000
```

### Standard Evaluation (10x10 NLOS)

```powershell
# Default configuration
python experiments\09_grid_localization\src\python\run_full_pipeline.py
```

### LOS vs NLOS Comparison

```powershell
# Generate LOS data
python experiments\09_grid_localization\src\python\run_full_pipeline.py --scenario LOS

# Generate NLOS data
python experiments\09_grid_localization\src\python\run_full_pipeline.py --scenario NLOS
```

### Gaussian vs Random Forest Comparison

```powershell
# Run Gaussian model
python experiments\09_grid_localization\src\python\run_full_pipeline.py --data-dir <DATA_DIR> --model gaussian

# Run Random Forest on same data
python experiments\09_grid_localization\src\python\run_full_pipeline.py --data-dir <DATA_DIR> --model random_forest
```

### Metric Fusion Analysis

```powershell
# Compare individual metrics vs combined (Random Forest only)
python experiments\09_grid_localization\src\python\run_full_pipeline.py --data-dir <DATA_DIR> --model random_forest --metrics rss sinr cqi RSS,SINR RSS,SINR,CQI
```

### Regenerate Plots Only

```powershell
# If you already ran the pipeline and just want new plots
python experiments\09_grid_localization\src\python\plot_pipeline_results.py results\grid_localization\grid_10x10\exp13e_NLOS_2026-01-12_07-40-39
```

### Batch Processing

```powershell
# Process multiple existing datasets
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir results\grid_localization\grid_7x7\sim_data_LOS_2026-01-09_16-09-49
python experiments\09_grid_localization\src\python\localization_pipeline.py --data-dir results\grid_localization\grid_10x10\sim_data_NLOS_2026-01-11_22-43-07

# Then plot each result
python experiments\09_grid_localization\src\python\plot_pipeline_results.py results\grid_localization\grid_7x7\exp13e_LOS_2026-01-09_16-09-49
python experiments\09_grid_localization\src\python\plot_pipeline_results.py results\grid_localization\grid_10x10\exp13e_NLOS_2026-01-12_07-40-39
```

---

## Parameter Quick Reference

### Data Generation Parameters
- `--grid-size`: Grid dimensions (e.g., `3x3`, `7x7`, `10x10`)
- `--scenario`: Channel model (`LOS` or `NLOS`)
- `--n-samples`: Number of trajectory samples (default: 40000)

### Localization Parameters
- `--model`: Model type (`gaussian` or `random_forest`)
- `--metrics`: Metrics to test (space-separated, comma for fusion)
- `--max-history`: Maximum transition history length (default: 3)
- `--test-ratio`: Test set percentage (default: 0.2)

### Pipeline Control
- `--data-dir`: Use existing data (skip MATLAB)
- `--results-dir`: Use existing results (skip localization)
- `--skip-pipeline`: Skip localization step
- `--skip-plots`: Skip visualization step

---

## Tips

1. **Always check the output directory path** - Results are timestamped
2. **Use `--data-dir` to reuse data** - Saves time when testing different models
3. **Start with 3x3 grids** - Fast iteration for debugging
4. **Random Forest requires more samples** - Use at least 10k samples
5. **Combined metrics only work with Random Forest** - Gaussian models support single metrics only
6. **Check SUMMARY_REPORT.md** - Contains accuracy, MAE, and timing information
7. **MAE is in meters** - Not grid points (after recent fix)

---

## Troubleshooting

### MATLAB Not Found
```powershell
# Add MATLAB to PATH or use full path
"C:\Program Files\MATLAB\R2023a\bin\matlab.exe" -batch "..."
```

### Unicode Errors in Reports
- Fixed in latest version (UTF-8 encoding)
- Reports now support ✓ and ✗ symbols

### Memory Issues with Large Grids
- Reduce `--n-samples` for 10x10 grids
- Use `--test-ratio 0.1` for smaller test sets

### Identical h=1, h=2, h=3 Results
- Known issue: GaussianTransitionModel training doesn't use full history yet
- Model architecture needs update to utilize multiple previous values
