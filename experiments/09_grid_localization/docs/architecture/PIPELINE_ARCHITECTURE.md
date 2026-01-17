# Grid Localization Pipeline - Architecture Update

**Date:** January 9, 2026

## Overview

The grid localization codebase has been refactored into a modular, maintainable architecture that separates simulation (MATLAB/QuaDRiGa) from analysis (Python). This enables faster iteration on ML models without re-running expensive channel simulations.

---

## Architecture

### Old Architecture (exp13e)
```
exp13e_corrected_fair_comparison.m
    ├── Generate simulation data (QuaDRiGa)
    ├── Train/test split
    ├── Train statistical models
    ├── Evaluate models
    ├── Generate reports
    └── Call Python for plotting
```
**Problem:** Monolithic, hard to experiment with different models

### New Architecture
```
generate_simulation_data.m (MATLAB)
    └── Outputs: simulation_data.mat + config.json
              ↓
localization_pipeline.py (Python)
    ├── Load simulation data
    ├── Train/test split
    ├── Train models (modular, easy to extend)
    ├── Evaluate models
    └── Generate reports
```
**Benefits:**
- ✅ Separation of concerns
- ✅ Reuse simulation data (no re-simulation needed)
- ✅ Easy to add ML models
- ✅ Fast iteration on analysis

---

## File Structure

### Core Scripts

| File | Language | Purpose |
|:-----|:---------|:--------|
| `config.json` | JSON | Experiment configuration |
| `generate_simulation_data.m` | MATLAB | QuaDRiGa simulation only |
| `localization_pipeline.py` | Python | Main analysis pipeline |
| `fusion_experiments.py` | Python | Test RSS+SINR fusion strategies |
| `plot_results.py` | Python | Visualization |

### Legacy Scripts (still functional)

| File | Purpose |
|:-----|:--------|
| `exp13e_corrected_fair_comparison.m` | Old monolithic script (still works) |

---

## Usage

### 1. Generate Simulation Data (MATLAB + Python)

```bash
# Run from project root:
matlab -batch "cd experiments/09_grid_localization; generate_simulation_data"
```

**What it does:**
1. Loads `config.json`
2. Runs QuaDRiGa channel simulation
3. Saves `simulation_data.mat` with metrics (RSS, SINR, CQI)
4. Automatically calls Python pipeline
5. Outputs to: `results/grid_localization/grid_NxN/sim_data_LOS_YYYY-MM-DD_HH-MM-SS/`

**Output structure:**
```
results/grid_localization/grid_5x5/sim_data_LOS_2026-01-09_16-30-00/
├── simulation_data.mat        # Raw simulation data (MATLAB)
├── config.json                # Copy of configuration
├── pipeline_results.npz       # Analysis results (Python)
└── SUMMARY_REPORT.md          # Results summary
```

---

### 2. Re-analyze Existing Data (Python Only)

No need to re-run the expensive simulation! Just load existing data and try different approaches:

```bash
python experiments/09_grid_localization/localization_pipeline.py \
    --data-dir results/grid_localization/grid_5x5/sim_data_LOS_2026-01-09_16-30-00
```

**Options:**
```bash
# Custom test ratio
--test-ratio 0.3

# Different max history length
--max-history 5

# Test only specific metrics
--metrics rss sinr

# Custom output directory
--output-dir results/my_experiment
```

---

### 3. Test Fusion Strategies (Python)

Combine RSS and SINR for improved accuracy:

```bash
python experiments/09_grid_localization/fusion_experiments.py \
    results/grid_localization/grid_5x5/sim_data_LOS_2026-01-09_16-30-00
```

**What it does:**
- Tests multiple fusion methods:
  - Posterior multiplication (α = 0.3, 0.5, 0.7)
  - Weighted average (different weights)
  - Bivariate Gaussian (joint RSS, SINR)
- Compares to individual metrics
- Shows which fusion method works best

---

### 4. Generate Plots (Python)

```bash
python experiments/09_grid_localization/plot_results.py \
    results/grid_localization/grid_5x5/sim_data_LOS_2026-01-09_16-30-00
```

**Generates:**
- `spatial_layout.png` - Grid and BS positions
- `confusion_matrices.png` - Static vs transition (all history lengths)
- `spatial_error_map.png` - Error distribution across grid
- `metrics_comparison.png` - RSS vs SINR vs CQI
- `summary_dashboard.png` - Overview

---

## Configuration (`config.json`)

### Key Parameters

```json
{
  "grid": {
    "size": 5,                    // NxN grid
    "spacing": 2.0               // Meters between points
  },
  
  "movement": {
    "steps_per_point": 400,      // NEW: Scales with grid size
    // "n_steps": 10000           // LEGACY: Still supported
  },
  
  "classification": {
    "max_history_length": 3,     // NEW: Test h=1,2,3
    "test_ratio": 0.2
  },
  
  "base_station": {
    "interferers": {
      "enabled": true,           // Multi-BS for RSS≠SINR
      "positions": [
        [150, 0, 25],
        [-150, 0, 25],
        [0, 150, 25]
      ]
    }
  }
}
```

### Backward Compatibility

- **`n_steps` vs `steps_per_point`:** If both present, `steps_per_point` takes precedence
- **`max_history_length`:** Optional, defaults to 3
- All old configs still work!

---

## Adding New Models (For Developers)

The new architecture makes it easy to add ML models:

### 1. Create a new model class

```python
# In localization_pipeline.py

class MyMLModel(LocalizationModel):
    def __init__(self, params):
        self.model = SomeMLModel(**params)
        self.name = "My ML Model"
    
    def train(self, metric_values, true_locations, train_indices, n_points):
        # Training logic
        X_train = ...
        y_train = ...
        self.model.fit(X_train, y_train)
    
    def predict(self, metric_value):
        # Return probability distribution over locations
        probabilities = self.model.predict_proba([metric_value])[0]
        return probabilities
    
    def get_name(self):
        return self.name
```

### 2. Use it in pipeline

```python
# In Pipeline.run()
ml_model = MyMLModel(params={'learning_rate': 0.01})
ml_model.train(metric_values, true_locations, train_indices, n_points)
results = Evaluator.evaluate_static(ml_model, metric_values, true_locations, test_indices)
```

That's it! The evaluation infrastructure is already there.

---

## Workflow Examples

### Experiment 1: Quick test on 3x3 grid

```bash
# 1. Edit config.json: set size=3, steps_per_point=200
# 2. Run simulation
matlab -batch "cd experiments/09_grid_localization; generate_simulation_data"
# → Fast! Only 1800 samples (3×3×200)
```

### Experiment 2: Try different fusion weights

```bash
# No re-simulation needed!
python fusion_experiments.py results/grid_localization/grid_5x5/sim_data_LOS_2026-01-09_16-30-00
```

### Experiment 3: Test ML model on existing data

```python
# Create your model, then:
python localization_pipeline.py --data-dir <existing_sim_data> --model ml
```

---

## Data Format

### `simulation_data.mat` (MATLAB)

```matlab
metrics.rss_wb     % [N×1] RSS values in dBm
metrics.sinr_wb    % [N×1] SINR values in dB  
metrics.cqi_wb     % [N×1] CQI values

walk_path.grid_point_indices    % [N×1] True locations (1-indexed)
walk_path.positions             % [N×3] XYZ positions
walk_path.positions_jittered    % [N×3] With jitter applied

config.n_points          % Number of grid points
config.grid_positions    % [n_points×3] Grid layout
config.neighbors         % {n_points} Adjacency list
```

### `pipeline_results.npz` (Python)

```python
import numpy as np
data = np.load('pipeline_results.npz')

# Access results
rss_static_acc = data['rss_static_acc']        # Static accuracy
rss_trans_h1_acc = data['rss_trans_h1_acc']    # Transition h=1 accuracy
rss_static_cm = data['rss_static_cm']          # Confusion matrix
```

---

## Migration Guide

### From exp13e to new pipeline:

| Old | New |
|:----|:----|
| Run `exp13e_corrected_fair_comparison.m` | Run `generate_simulation_data.m` |
| Results in `exp13e_LOS_*/` | Results in `sim_data_LOS_*/` |
| Re-run MATLAB to try new approach | Just run Python script again |
| Hard to add ML models | Easy: inherit `LocalizationModel` |

### Can I still use exp13e?

**Yes!** The old script still works and is untouched. Use it if you need it, but consider migrating to the new pipeline for better maintainability.

---

## Performance Notes

- **Simulation time:** ~30-60 seconds (5×5 grid, 10k samples)
- **Python pipeline:** ~5-10 seconds
- **Re-analysis:** ~5 seconds (no MATLAB needed!)

---

## Troubleshooting

### Error: "simulation_data.mat not found"
- Make sure you ran `generate_simulation_data.m` first
- Check that the data directory path is correct

### Error: "MATLAB error Exit Status"
- Check MATLAB path includes QuaDRiGa
- Verify `config.json` is valid JSON

### Python import errors
- Install dependencies: `pip install numpy scipy matplotlib`

---

## Summary

**Old way:** Run MATLAB → wait → get results → want to try different approach → re-run MATLAB → wait...

**New way:** Run MATLAB once → save data → Python experiment 1 → Python experiment 2 → Python experiment 3... (fast!)

This architecture enables rapid experimentation and makes it easy to add machine learning models in the future.
