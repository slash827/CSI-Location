# Experiment 08: Static vs Random Walk CSI Comparison

## Objective

This experiment investigates whether a UE that travels from point A to point B achieves the same CSI in point B as a UE that was simply placed at point B from the start (i.e., without any movement history).

## Hypothesis

In a static channel model without temporal correlation, the CSI at any location should be independent of how the UE arrived at that location. This experiment tests this by comparing:

1. **Static Simulation**: 9 UEs placed simultaneously on a 3×3 grid (100 repetitions)
2. **Random Walk Simulation**: Single UE performing a random walk on the same grid (900 steps)

## Grid Configuration

```
(0,2) -- (1,2) -- (2,2)
  |        |        |
(0,1) -- (1,1) -- (2,1)
  |        |        |
(0,0) -- (1,0) -- (2,0)
```

- Grid size: 2m × 2m
- Points: 9 (3×3 arrangement)
- Spacing: 1 meter between adjacent points

## Simulations

### Simulation 1: Static Grid (exp13a_static_grid.m)
- Place 9 identical UEs at all grid points simultaneously
- All UEs have the same device configuration
- Repeat 100 times to build distribution
- Record full CSI data for all points
- Output saved to: `results/exp13a_<timestamp>/`

### Simulation 2: Random Walk (exp13b_random_walk.m)
- Single UE starts at a random grid point
- Performs 900 steps (moves only to adjacent cells - up/down/left/right)
- Records CSI at each visited location
- On average, visits each point ~100 times
- Output saved to: `results/exp13b_<timestamp>/`

## Analysis (analyze_static_vs_walk.py)

The Python analysis script compares:

1. **CSI Differences Distribution**:
   - Static: Difference between adjacent points in same simulation run
   - Walk: Difference between consecutive steps when moving between adjacent points

2. **Statistical Tests**:
   - Kolmogorov-Smirnov test
   - Mann-Whitney U test
   - Welch's t-test
   - Cohen's d effect size

3. **CSI Features Compared**:
   - Channel magnitude (|H|)
   - Channel phase (∠H)
   - RSS (Received Signal Strength)
   - SINR
   - CQI
   - Path loss
   - Delay spread

## Expected Output

If the channel model has no memory/history:
- The distributions should be statistically similar
- K-S test should not reject null hypothesis

If the channel model has temporal correlation:
- Walk differences might show different distribution
- Adjacent steps in walk could be more correlated

## Files

- `exp13a_static_grid.m` - Static grid simulation (MATLAB/QuaDRiGa)
- `exp13b_random_walk.m` - Random walk simulation (MATLAB/QuaDRiGa)
- `analyze_static_vs_walk.py` - Analysis and comparison (Python)
- `README.md` - This file

## Running the Experiment

1. Run MATLAB simulations:
   ```matlab
   cd experiments/08_static_vs_walk
   exp13a_static_grid
   exp13b_random_walk
   ```

2. Run Python analysis:
   ```bash
   cd experiments/08_static_vs_walk
   python analyze_static_vs_walk.py
   ```

## Requirements

- MATLAB with QuaDRiGa
- Python 3.8+ with: numpy, scipy, matplotlib, seaborn
