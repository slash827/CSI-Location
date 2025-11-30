# Recovery from OOM Error (40% Complete)

## Current Situation
- You have ~40,000 samples completed (40% of 100K)
- Out of memory error occurred
- Data is in workspace variables but not saved

## Recovery Steps

### Option 1: Save What You Have (RECOMMENDED)
1. In the MATLAB workspace where the error occurred, run:
   ```matlab
   save_partial_progress
   ```
   This saves your 40K samples to `*_partial.mat` files

2. The fix has been applied (using `single` precision instead of `double`)
   - This reduces memory by 50%

3. Update config to generate remaining 60K samples in append mode:
   ```matlab
   % In config_urban_dataset.m:
   config.APPEND_MODE = true;
   config.APPEND_TO_DIR = 'exp13_2025-11-26_XXXXX';  % Your directory
   config.n_trajectories = 600;  % Remaining trajectories
   ```

4. Before running, manually rename the partial files:
   ```matlab
   % In MATLAB or PowerShell:
   movefile('results/exp13_*/dataset/train_data_partial.mat', 'results/exp13_*/dataset/train_data.mat');
   movefile('results/exp13_*/dataset/val_data_partial.mat', 'results/exp13_*/dataset/val_data.mat');
   movefile('results/exp13_*/dataset/metadata_partial.mat', 'results/exp13_*/dataset/metadata.mat');
   ```

5. Run exp13_urban_dataset again (will append remaining 60K)

### Option 2: Reduce Dataset Size
If memory is still an issue, reduce to 50K total samples:
```matlab
% In config_urban_dataset.m:
config.n_trajectories = 500;  % 50K samples total
config.APPEND_MODE = false;
```
Run fresh (starts over, but completes successfully)

### Option 3: Reduce Subcarrier Resolution
Edit config to use fewer subcarriers:
```matlab
config.scenario.n_subcarriers = 1024;  % Half the resolution
```
This reduces memory by another 50%

## Memory Optimization Applied
- Changed per-subcarrier features from `double` (8 bytes) to `single` (4 bytes)
- Memory reduction: ~50%
- Should now handle 100K samples without OOM

## What Was the Problem?
- 2048 subcarriers × 6 BSs × 3 features = 36,864 values per sample
- At double precision: 36,864 × 8 bytes = 295 KB per sample
- For 100K samples: ~29.5 GB just for per-subcarrier data
- Single precision: ~14.8 GB (fits in typical RAM)
