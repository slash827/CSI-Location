# Results Directory Reorganization

## Overview
The results directory has been reorganized to better manage experiments with different grid sizes and provide better reproducibility.

## New Directory Structure

```
results/
└── grid_localization/
    ├── grid_3x3/
    │   ├── exp13e_corrected_2026-01-08_10-30-15/
    │   │   ├── experiment_config.json
    │   │   ├── corrected_comparison_results.mat
    │   │   └── CORRECTED_SUMMARY_REPORT.md
    │   ├── exp13e_corrected_2026-01-08_11-45-22/
    │   └── ...
    ├── grid_5x5/
    │   └── ...
    ├── grid_10x10/
    │   └── ...
    └── grid_20x20/
        └── ...
```

## Changes Made

### 1. Hierarchical Directory Structure
- **Base:** `results/grid_localization/`
- **Grid-specific:** `grid_NxN/` subdirectories for each grid size
- **Experiments:** Individual experiment runs within each grid subdirectory

**Benefits:**
- Easy comparison between different grid sizes
- Cleaner organization as experiments scale up
- Prevents cluttering of main results directory

### 2. Configuration JSON Export
Each experiment now saves a `experiment_config.json` file with all parameters:

```json
{
  "experiment_name": "exp13e_corrected_fair_comparison",
  "timestamp": "2026-01-08 10:30:15",
  "grid_size": 3,
  "spacing": 2.0,
  "ue_height": 1.5,
  "grid_offset": [20, 0],
  "position_jitter": 0.1,
  "n_steps": 30000,
  "ue_speed": 1.5,
  "step_duration": 1.333333,
  "center_frequency": 3000000000,
  "bandwidth": 100000000,
  "n_subcarriers": 256,
  "scenario": "3GPP_38.901_UMa_LOS",
  "bs_position": [0, 0, 25],
  "n_points": 9,
  "random_seed": 42,
  "test_ratio": 0.2
}
```

**Benefits:**
- Complete reproducibility of any experiment
- Easy parameter comparison between runs
- Machine-readable format for automated analysis
- Can be version-controlled separately

### 3. Mean Absolute Error (MAE) Metric
Added MAE calculation using Manhattan distance on the grid:

**Formula:** `MAE = mean(|true_row - pred_row| + |true_col - pred_col|)`

**Example:**
- True location: Point 5 (row=2, col=2) on 3×3 grid
- Predicted: Point 2 (row=1, col=2)
- Error: |2-1| + |2-2| = 1 grid point

**Benefits:**
- Provides continuous error metric (not just binary correct/incorrect)
- More informative for near-miss predictions
- Useful for understanding error distribution
- Complements accuracy percentage

### 4. Enhanced Summary Output
The console and markdown reports now include both accuracy and MAE:

```
=== ACCURACY ===
Metric     | Static       | Transition      | Improvement
----------------------------------------------------------
RSS        |     87.40% |        88.50% |      +1.10%
SINR       |     85.20% |        86.10% |      +0.90%
CQI        |     84.80% |        85.60% |      +0.80%

=== MEAN ABSOLUTE ERROR (grid points) ===
Metric     | Static       | Transition      | Improvement
----------------------------------------------------------
RSS        |      0.234 |           0.198 |      +0.036
SINR       |      0.289 |           0.251 |      +0.038
CQI        |      0.301 |           0.267 |      +0.034
```

**Note:** For MAE, positive improvement means transition method **reduces** error (lower is better).

## Migration Scripts

### Reorganize Existing Results
To move existing experiment folders to the new structure:

```matlab
cd experiments/08_static_vs_walk
reorganize_results
```

This script:
1. Scans `results/` for `exp13*` folders
2. Reads `grid_size` from each config file
3. Creates appropriate `grid_NxN/` subdirectories
4. Moves folders to correct locations
5. Skips folders that are already moved

### Reproduce an Experiment
To exactly reproduce an experiment from its config:

```matlab
cd experiments/08_static_vs_walk
run_from_config('../../results/grid_localization/grid_3x3/exp_*/experiment_config.json')
```

This loads the JSON config and reruns the simulation with identical parameters.

## Backwards Compatibility

The changes are backwards compatible:
- Old result folders can be migrated using `reorganize_results.m`
- The experiment script automatically creates the new directory structure
- Existing analysis scripts can still read `.mat` files from new locations

## Files Modified

### Core Experiment Script
- `exp13e_corrected_fair_comparison.m`
  - Updated output directory logic
  - Added MAE calculation
  - Added JSON config export
  - Enhanced console output

### Report Generator
- `generate_corrected_report.m`
  - Added MAE table to markdown report
  - Reformatted for better readability

### New Utility Scripts
- `reorganize_results.m` - Migrate existing results
- `run_from_config.m` - Reproduce experiments from JSON

## Usage Examples

### Run New Experiment
```matlab
% In exp13e_corrected_fair_comparison.m, set:
config.grid_size = 5;
config.n_steps = 30000;
config.scenario = '3GPP_38.901_UMa_LOS';

% Run the script - results will automatically go to:
% results/grid_localization/grid_5x5/exp13e_corrected_YYYY-MM-DD_HH-MM-SS/
```

### Compare Grid Sizes
```matlab
% After running experiments with different grid sizes:
grid_3x3_results = load('results/grid_localization/grid_3x3/exp_*/corrected_comparison_results.mat');
grid_5x5_results = load('results/grid_localization/grid_5x5/exp_*/corrected_comparison_results.mat');

% Compare accuracies
fprintf('3×3 RSS: %.2f%%\n', grid_3x3_results.results.rss.static_acc);
fprintf('5×5 RSS: %.2f%%\n', grid_5x5_results.results.rss.static_acc);
```

### Batch Processing
```matlab
% Process all experiments in a grid size
grid_dir = 'results/grid_localization/grid_3x3';
exp_folders = dir(fullfile(grid_dir, 'exp13e_*'));

for i = 1:length(exp_folders)
    config_path = fullfile(grid_dir, exp_folders(i).name, 'experiment_config.json');
    cfg = jsondecode(fileread(config_path));
    fprintf('%s: Grid=%dx%d, Steps=%d\n', exp_folders(i).name, ...
            cfg.grid_size, cfg.grid_size, cfg.n_steps);
end
```

## Best Practices

1. **Always check the JSON config** before reproducing to ensure parameters are as expected
2. **Use consistent naming** - keep grid_size in experiment config accurate
3. **Document variations** - if you modify parameters, note it in commit messages
4. **Archive old runs** - move completed experiment batches to archive folders
5. **Compare within grid sizes first** - don't compare 3×3 directly to 10×10

## Next Steps

1. Run `reorganize_results.m` to migrate existing folders
2. Test new experiment with current config
3. Verify JSON export contains all expected parameters
4. Run scaling experiments (3×3 → 5×5 → 8×8 → 10×10)
5. Use MAE to understand where misclassifications occur (adjacent vs far)
