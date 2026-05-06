# Claude Code Prompt — Experiment Extension

## Context

This is an extension of an existing multi-user heterogeneous localization experiment.
The pipeline is in `src/python/multi_user_pipeline.py`. Data is already generated
in `results/multi_user_voronoi_15x15/`.

## Experiment Naming Convention

| Index | Name | Features | h | AoA | Extra |
|-------|------|----------|---|-----|-------|
| E1  | `BASE`        | RSS+SINR     | 0 | No  | — |
| E2  | `BASE_dp`     | RSS+SINR     | 0 | No  | device params |
| E3  | `BASE_uid`    | RSS+SINR     | 0 | No  | user ID |
| E4  | `BASE_H`      | RSS+SINR     | 3 | No  | — |
| E5  | `BASE_H_dp`   | RSS+SINR     | 3 | No  | device params |
| E6  | `BASE_H_uid`  | RSS+SINR     | 3 | No  | user ID |
| E7  | `BASE_A`      | RSS+SINR+AoA | 0 | Yes | — |
| E8  | `BASE_A_dp`   | RSS+SINR+AoA | 0 | Yes | device params |
| E9  | `BASE_A_uid`  | RSS+SINR+AoA | 0 | Yes | user ID |
| E10 | `BASE_A_H`    | RSS+SINR+AoA | 3 | Yes | — |
| E11 | `BASE_A_H_dp` | RSS+SINR+AoA | 3 | Yes | device params |

**Legend:** BASE = RSS+SINR, A = AoA (4° noise + 5° quantization),
H = history absolute stacking h=3, dp = device params
(n_antennas, antenna_gain_db, ue_height), uid = user_id integer.

**Old → new name mapping:**

| Old | New |
|-----|-----|
| E1 | `BASE` (E1) |
| E2 | `BASE_H` (E4) |
| E3 | `BASE_H_dp` (E5) |
| E4 | `BASE_H_uid` (E6) |
| E5 | `BASE_A` (E7) |
| E6 | `BASE_A_H` (E10) |
| E7 | `BASE_A_H_dp` (E11) |

---

## Step 1: Rename Existing Results

Before running any new experiments, rename all old experiment name occurrences
(E1–E7 string values) to the new names in:

1. `results/multi_user_voronoi_15x15/results_summary.csv` — `experiment` column
2. `results/multi_user_voronoi_15x15/per_user_breakdown.csv` — same
3. `results/multi_user_voronoi_15x15/per_cell_breakdown.csv` — same
4. Experiment name constants in `src/python/multi_user_pipeline.py`
5. Regenerate all existing plots using the renamed CSVs (do not re-train)

After renaming, assert that `results_summary.csv` contains exactly these
experiment names: BASE, BASE_H, BASE_H_dp, BASE_H_uid, BASE_A, BASE_A_H,
BASE_A_H_dp — and nothing else before new experiments are added.

---

## Step 2: Add Missing Static Baselines (E2, E3, E8, E9)

Run 4 new experiments using existing multi-user data. Do NOT regenerate
simulation data. Load from existing `.mat` files for all 5 users.

**E2 — `BASE_dp`:**
features = [rss, sinr, n_antennas, antenna_gain_db, ue_height], h=0

**E3 — `BASE_uid`:**
features = [rss, sinr, user_id], h=0

**E8 — `BASE_A_dp`:**
features = [rss, sinr, aoa_az_noisy, aoa_el_noisy, n_antennas, antenna_gain_db, ue_height], h=0

**E9 — `BASE_A_uid`:**
features = [rss, sinr, aoa_az_noisy, aoa_el_noisy, user_id], h=0

Run both RF and XGBoost. Same chronological 80/20 split per user as all existing
experiments. Also run cross-user variant (train U1–U4, test U5 held out) for each.

Append results to all three CSVs.

---

## Step 3: Delta vs. Absolute A/B Comparison

### 3a — Implement delta feature builder

Add `build_delta_features(df, h, base_metrics)` to the pipeline:

```python
def build_delta_features(df, h, base_metrics):
    """
    Feature vector:
      - Columns 0..D-1:     current absolute values m_t
      - Columns D..2D-1:    first differences m_t - m_{t-1}
      - Columns 2D..3D-1:   first differences m_{t-1} - m_{t-2}
      - ... up to h differences
    Shape: (N, D*(h+1)) — same as absolute stacking.
    Rows with insufficient history are dropped.
    """
```

### 3b — Run delta variants (both RF and XGBoost)

| Delta name | Absolute equivalent |
|------------|---------------------|
| `BASE_H_delta`      | `BASE_H` (E4) |
| `BASE_H_dp_delta`   | `BASE_H_dp` (E5) |
| `BASE_A_H_delta`    | `BASE_A_H` (E10) |
| `BASE_A_H_dp_delta` | `BASE_A_H_dp` (E11) |

Append to all result CSVs.

### 3c — Data volume sweep

For `BASE_H` and `BASE_H_delta` only, run at 4 training fractions:
`[0.10, 0.25, 0.50, 1.00]`.

Apply the fraction AFTER the chronological 80/20 split, taking the first X%
of the training portion only. Never touch the test set. Assert this before
every training call.

Save to: `results/multi_user_voronoi_15x15/data_volume_sweep.csv`
Columns: experiment, model, data_fraction, accuracy, mae

---

## Step 4: Environmental Variability Experiment

### 4a — MATLAB: generate 3 runs for U1

Generate 3 simulation runs for U1 (4 antennas, 0 dB, 1.5m height) on the same
15×15 Voronoi grid, varying only the QuaDRiGa random seed:

| Run | Seed | Output file |
|-----|------|-------------|
| env_run_1 | 101 | `user1_env1_voronoi_15x15.mat` |
| env_run_2 | 102 | `user1_env2_voronoi_15x15.mat` |
| env_run_3 | 103 | `user1_env3_voronoi_15x15.mat` |

All other parameters identical to U1 in the existing simulation.

### 4b — Python: cross-environment experiment

**Cross-environment split:**
- Train: env_run_1 + env_run_2 (concatenated, chronological order per run)
- Test: env_run_3 entirely

**Reference split:**
- Train: first 80% of env_run_1 chronologically
- Test: last 20% of env_run_1

Run on both splits:
- `BASE` (E1): h=0, absolute
- `BASE_H` (E4): h=3, absolute
- `BASE_H_delta`: h=3, deltas

Models: RF and XGBoost.

Save to: `results/multi_user_voronoi_15x15/env_variability_results.csv`
Columns: experiment, model, split_type (cross_env / single_run), accuracy, mae

---

## Output Files

```
results/multi_user_voronoi_15x15/
  results_summary.csv               — updated names + E2/E3/E8/E9 + delta variants
  per_user_breakdown.csv            — same
  per_cell_breakdown.csv            — same
  data_volume_sweep.csv             — Step 3c
  env_variability_results.csv       — Step 4b
  plots/
    master_comparison_bar.png       — all E1–E11 + deltas, XGBoost accuracy
    data_volume_curve.png           — BASE_H vs BASE_H_delta across data fractions
    env_variability_bar.png         — cross-env vs single-run comparison
```

---

## Critical Requirements

1. **No data leakage.** All splits strictly chronological per user. Assert that
   max(train step_index) < min(test step_index) for each user before every
   training call.

2. **Do not re-run E1, E4, E5, E6, E7, E10, E11.** Load from existing CSVs.

3. **Consistent hyperparameters.** RF: n_estimators=50, max_depth=15,
   min_samples_leaf=20. XGBoost: same as existing experiments.

4. **AoA noise applied in Python.** For any experiment with `A` in the name:
   apply σ=4° Gaussian noise then 5° quantization to raw AoA values before
   building features. Use independent seeds for azimuth and elevation.

5. **Print data summary** before each new experiment: sample counts per user,
   per Voronoi cell, and train/test sizes.
