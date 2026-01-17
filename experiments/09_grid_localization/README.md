# Experiment 09: Grid Localization (Static vs Transition-Based)

## Overview

This experiment investigates whether incorporating **movement history** (previous location) improves localization accuracy compared to using only **current CSI measurements**.

**Research Question:** Does adding delta (Δ) information improve localization accuracy?
- Accuracy(RSS_current, RSS_previous) > Accuracy(RSS_current) ???

## Experimental Design

### Fair Comparison
Both methods solve the **same problem**: Predict which of the N grid points the UE is located at.

#### Method 1: Static Classification (Baseline)
- Input: RSS_current
- Output: Predicted location (1 to N)
- Approach: Maximum Likelihood with Gaussian distributions

#### Method 2: Transition-Based Classification
- Input: RSS_current + RSS_previous
- Output: Predicted location (1 to N)
- Approach: Maximum Likelihood with spatial constraint
  - Only considers valid transitions (adjacent grid points)
  - Uses max-over-neighbors for stronger spatial constraint

### Key Innovation
Previous location provides a **spatial constraint**: the UE can only move to adjacent grid points. This should help disambiguate similar CSI patterns.

## Grid Configuration

Example 3×3 Grid:
```
7 - 8 - 9
|   |   |
4 - 5 - 6
|   |   |
1 - 2 - 3
```

- Configurable grid sizes: 3×3, 5×5, 8×8, 10×10, 15×15, 20×20
- Spacing: 2.0 meters (default)
- Height: 1.5 meters
- Position jitter: ±0.1 meters

## Movement Model

### Random Walk
- UE moves randomly between adjacent grid points
- Each step: uniformly random selection from valid neighbors
- Step duration: spacing / speed = 2.0m / 1.5m/s = 1.33 seconds
- Total steps: Scaled with grid size (e.g., 30,000 for 5×5)

### Channel Scenarios
- **LOS:** `3GPP_38.901_UMa_LOS`
- **NLOS:** `3GPP_38.901_UMa_NLOS`

## Metrics

### Accuracy
Percentage of correct predictions: `Correct / Total × 100%`

### Mean Absolute Error (MAE)
Average localization error in grid points using Manhattan distance:
```
MAE = mean(|true_row - pred_row| + |true_col - pred_col|)
```

**Example:**
- True location: Point 5 (row=2, col=2) on 3×3 grid
- Predicted: Point 2 (row=1, col=2)
- Error: |2-1| + |2-2| = 1 grid point

## Files

### Main Experiment
- **exp13e_corrected_fair_comparison.m** - Main experiment script
  - Configurable grid size, spacing, steps, scenario
  - Runs both static and transition-based classification
  - Saves results to `results/grid_localization/grid_NxN/`

### Support Scripts
- **generate_corrected_report.m** - Generates markdown summary report
- **compute_delta_likelihood.m** - Helper function (legacy, not currently used)
- **reorganize_results.m** - Migrates old results to new directory structure
- **run_from_config.m** - Reproduces experiment from saved JSON config

### Documentation
- **RESULTS_REORGANIZATION.md** - Details on new results directory structure
- **SCALING_TEST_PLAN.md** - Guide for testing different grid sizes
- **New_experiment_13e.md** - Original experiment design notes

## Usage

### Configuration

All experiment parameters are defined in **`config.json`**. Edit this file to customize:

```json
{
  "grid": {
    "size": 3,              // Grid size (NxN)
    "spacing": 2.0,         // Meters between points
    "ue_height": 1.5        // UE antenna height
  },
  "movement": {
    "n_steps": 10000,       // Random walk steps
    "ue_speed": 1.5         // UE speed in m/s
  },
  "channel": {
    "scenario": "3GPP_38.901_UMa_LOS",  // LOS or NLOS
    "center_frequency": 3e9,
    "bandwidth": 1e8,
    "n_subcarriers": 256
  }
}
```

**Benefits:**
- ✅ No need to edit MATLAB code
- ✅ Configuration automatically copied to results
- ✅ Easy to reproduce experiments
- ✅ Simple parameter sweeps

### Quick Start
```matlab
% 1. Edit configs/config.json with desired parameters
% 2. Run experiment
cd experiments/09_grid_localization/src/matlab
generate_simulation_data

% Results will be saved to:
% results/grid_localization/grid_NxN/sim_data_SCENARIO_YYYY-MM-DD_HH-MM-SS/
```

Or use the full Python pipeline:
```powershell
python experiments\09_grid_localization\src\python\run_full_pipeline.py
```

### Plotting

Plots are **automatically generated** using Python after the experiment completes.

**Generated Plots:**
1. **spatial_layout.png** - Grid and base station positions
2. **metrics_comparison.png** - Accuracy and MAE across all metrics and history lengths
3. **history_progression.png** - Accuracy vs history length for each metric

**Requirements:**
```bash
pip install numpy matplotlib seaborn scipy
```

**Manual plotting:**
```bash
python experiments\09_grid_localization\src\python\plot_pipeline_results.py results\grid_localization\grid_3x3\exp_*
```

### Migrate Old Results
```matlab
cd experiments/09_grid_localization/archived/matlab
reorganize_results  % Moves exp13* folders to grid_localization/grid_NxN/
```

### Reproduce Previous Experiment
```matlab
cd experiments/09_grid_localization/src/matlab
run_from_config('../../../results/grid_localization/grid_3x3/exp_*/experiment_config.json')
```

## Results Directory Structure
```
results/
└── grid_localization/
    ├── grid_3x3/
    │   ├── exp13e_corrected_2026-01-08_10-30-15/
    │   │   ├── experiment_config.json          # All parameters (JSON)
    │   │   ├── corrected_comparison_results.mat # Full results (MATLAB)
    │   │   └── CORRECTED_SUMMARY_REPORT.md     # Human-readable summary
    │   └── ...
    ├── grid_5x5/
    ├── grid_10x10/
    └── grid_20x20/
```

## Expected Results

### Hypothesis 1: Improvement Increases with Grid Size ✓
As the number of classes increases, static RSS becomes less discriminative, making spatial constraints more valuable.

**Prediction:**
- 3×3 (9 classes): +1-2% improvement
- 5×5 (25 classes): +3-5% improvement
- 10×10 (100 classes): +5-10% improvement

### Hypothesis 2: LOS vs NLOS Behavior
- **LOS:** High baseline accuracy, modest improvement
- **NLOS:** Low baseline accuracy, potentially larger relative improvement

## Key Findings

### Corrected vs Original Experiment
The original exp13e had a critical flaw: it compared two **different problems**:
- Static: 9-class classification (which point?)
- Transition: 24-class classification (which edge?)

This corrected version ensures both methods solve the **same problem**, making the comparison fair.

### Implementation Details
1. **No Delta Variance Amplification:** Uses RSS_previous directly instead of computing delta
2. **Spatial Constraint:** Only considers transitions between adjacent points
3. **Max-Over-Neighbors:** Uses maximum likelihood across all valid (current, previous) pairs
4. **Train/Test Split:** 80/20 split ensures unbiased evaluation

## Configuration Parameters

### Channel Parameters
- Center frequency: 3 GHz
- Bandwidth: 100 MHz
- Subcarriers: 256
- BS position: [0, 0, 25] meters

### Movement Parameters
- UE speed: 1.5 m/s
- Step duration: spacing / speed
- Starting point: Center of grid
- Random seed: 42 (for reproducibility)

### Training Parameters
- Train/test ratio: 80/20
- Classification: Maximum Likelihood
- Model: Gaussian distributions per location

## Computational Considerations

### Runtime (approximate)
- 3×3, 10k steps: ~2-3 minutes
- 5×5, 30k steps: ~6-8 minutes
- 10×10, 120k steps: ~25-30 minutes
- 20×20, 500k steps: ~2-3 hours

### Memory Usage
- Dominated by channel matrix storage
- ~2 MB per 10,000 snapshots
- 20×20 with 500k steps: ~100 MB

## References

- QuaDRiGa v2.x: Channel model implementation
- 3GPP 38.901: Channel model specifications (UMa scenarios)
- Original experiments: `experiments/08_static_vs_walk/`

## Version History

- **v1.0 (exp13e_corrected):** Fair comparison with RSS_previous approach
- **Previous (exp13a-13d):** Exploratory experiments in 08_static_vs_walk/
- **Legacy (exp13e_transition_based):** Original unfair comparison (archived)

---

*Last Updated: January 8, 2026*
