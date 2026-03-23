# Multi-User Heterogeneous Environment Experiment

## Context
I have an existing QuaDRiGa-based CSI localization project with:
- A working Voronoi heterogeneous environment (AreaGenerator.m) 
  with multiple scenario types (shopping, office, residential, park)
- Single-user transition-based fingerprinting experiments on grids up to 15×15
- Established MATLAB→Python pipeline via scipy.io
- Proven results: transition history (h=1..4) consistently improves 
  localization accuracy over static fingerprinting (h=0)

The project already has working code for data generation, feature engineering, 
and ML training. This experiment extends it to multi-user heterogeneous settings.

## Objective
Extend the simulation to 5 users moving simultaneously on a 15×15 Voronoi grid, 
with each user representing a different device profile. The core research 
hypothesis to validate: **transition-based features are robust to user/device 
heterogeneity, while static features (h=0) degrade**.

---

## Part 1: MATLAB — Multi-User Data Generation

Extend the existing AreaGenerator-based simulation to generate 5 users.

### Network Setup (CRITICAL — do not change)
- **1 serving base station** (inside or near center of grid) — this is the 
  ONLY source used for localization
- **2-3 interfering base stations** outside the grid — they exist ONLY to 
  create realistic SINR variation (interference), their individual signals 
  are NOT used as features
- Frequency: 3.5 GHz, 64-antenna Massive MIMO on serving BS
- Features extracted: RSS and SINR from serving BS only

This is intentional: we want fingerprinting from a single BS, NOT 
triangulation. Using multiple BS signals would trivialize the problem.

### Voronoi Environment
- 15×15 grid with Voronoi tessellation (use existing AreaGenerator.m)
- Each Voronoi cell has a different 3GPP scenario 
  (e.g., InH_Shopping, UMi_Street, Indoor_Office, UMa_Open)
- Users can transition between cells (cross-cell movement is allowed 
  and expected)

### Device Profiles (5 users)
Generate a separate simulation run per user with these profiles:

| User | Description      | rx_antennas | antenna_gain_db | ue_height_m |
|------|-----------------|-------------|-----------------|-------------|
| U1   | Flagship A      | 4           | 0.0             | 1.5         |
| U2   | Mid-range       | 2           | -2.0            | 1.5         |
| U3   | Budget/Old      | 1           | -4.0            | 1.5         |
| U4   | Flagship B      | 4           | 0.0             | 1.5         |
| U5   | Tablet/IoT      | 2           | -1.0            | 0.9         |

U1 and U4 share the same device parameters but different random walk seeds — 
this isolates device effect from trajectory randomness.

### Data to Save (per user)
Save a .mat file per user containing:
- `rss`: [N×1] from serving BS only
- `sinr`: [N×1] from serving BS only  
- `x_pos`, `y_pos`: [N×1] ground truth coordinates
- `grid_point_id`: [N×1] nearest grid point index (1..225)
- `voronoi_cell_id`: [N×1] which Voronoi cell the user is in
- `step_index`: [N×1] chronological step number (critical for train/test split)
- `user_id`: scalar (1..5)
- `device_profile`: struct with n_antennas, antenna_gain_db, ue_height_m

Naming: `user1_voronoi_15x15.mat`, ..., `user5_voronoi_15x15.mat`

---

## Part 2: Python — Feature Engineering & Training

### Data Loading
Load all 5 .mat files and combine into a single DataFrame with columns:
`user_id, step_index, x_pos, y_pos, grid_point_id, voronoi_cell_id,
rss, sinr, n_antennas, antenna_gain_db, ue_height`

### Train/Test Split (NO DATA LEAKAGE)
Split **per user chronologically** — never random split:
- For each user independently: first 80% of steps → train, last 20% → test
- The split must be on `step_index` order, NOT shuffled
- This simulates: model trained on early trajectories, tested on later movement
- Verify split integrity: assert no step_index overlap between train/test 
  for the same user

### Feature Sets to Compare
Build 4 feature sets:

**F1 — Static baseline (h=0):**
`[rss, sinr]`

**F2 — Transitions only (h=1..4), raw stacking:**
For history length h, stack: `[rss_t, sinr_t, rss_t-1, sinr_t-1, ..., rss_t-h, sinr_t-h]`
Use h=3 as primary (best from previous experiments).

**F3 — Transitions + device info (continuous):**
F2 features + `[n_antennas, antenna_gain_db, ue_height]`

**F4 — Transitions + device category (categorical):**
F2 features + `user_id` as integer (represents known device type)

### Models
Run RF and XGBoost only (skip Gaussian — memory issues at this scale).
Use same hyperparameters as previous experiments for consistency.

### Experiments Matrix
Run all combinations and report results:

| Experiment | Features | Models | Purpose |
|------------|----------|--------|---------|
| E1 | F1 (h=0) | RF, XGB | Baseline — static, no device info |
| E2 | F2 (h=3) | RF, XGB | Core hypothesis — transitions only |
| E3 | F3 (h=3) | RF, XGB | Do continuous device params help? |
| E4 | F4 (h=3) | RF, XGB | Does knowing device category help? |

### Metrics (per experiment, per model)
- **Overall**: Accuracy (%), MAE (meters)
- **Per-user breakdown**: accuracy and MAE for each of the 5 users separately
  — this reveals which device profiles benefit most from transitions
- **Per-Voronoi-cell breakdown**: accuracy per cell 
  — this reveals which environments benefit most
- **Cross-user analysis**: does the model trained on U1..U4 generalize to U5?
  (one additional train/test split where U5 is fully held out)

### Key Visualizations
1. Bar chart: Accuracy comparison across E1..E4, grouped by model
2. Per-user accuracy heatmap: users × experiments
3. Voronoi map colored by per-cell accuracy (show where the model struggles)
4. Confusion matrix for best model (E2 or E3)
5. Learning curve: accuracy vs. history length h=0..4 (for best model)

### Output Files
Save to `results/multi_user_voronoi_15x15/`:
- `results_summary.csv` — all metrics in one table
- `per_user_breakdown.csv`
- `per_cell_breakdown.csv`  
- All plots as PNG
- `experiment_config.json` — all parameters for reproducibility

---

## Critical Requirements

1. **No data leakage**: split is strictly chronological per user. 
   Add explicit assertions to verify this before training.

2. **Single BS features only**: RSS and SINR from serving BS only. 
   Do NOT include per-interferer measurements as features.

3. **Voronoi cell membership**: when a user moves across a cell boundary, 
   the scenario changes mid-trajectory — this should be preserved naturally 
   by the simulation, not smoothed out.

4. **Raw feature stacking** (not deltas/trends): previous experiments 
   consistently showed raw stacking outperforms engineered features 
   by 2-8pp. Keep this approach.

5. **Consistent random seeds**: document all seeds for reproducibility. 
   U1 and U4 must differ ONLY in their random walk seed.

6. **Before training**: print a data summary showing sample counts per user, 
   per Voronoi cell, and class distribution — to catch any imbalance issues 
   before wasting compute.