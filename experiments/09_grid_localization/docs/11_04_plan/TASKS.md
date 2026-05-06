# Tasks — April 2026 Session

## Context

New experiment: place the serving BS at the **NE corner** of the 15×15 grid
(`ne_bs_voronoi_15x15`) to test whether AoA informativeness depends on
angular coverage diversity.  See `research_plan.md` for full rationale.

Parallel track: engineering improvements (parallelism, progress bars, logging).

---

## Task 1 — New MATLAB config: `ne_bs_voronoi_15x15_config.jsonc`

Copy `multi_user_voronoi_15x15_config.jsonc`, change only:

```jsonc
"base_station": {
  "position": [48, 48, 10],          // 15m north + 15m east of NE corner (33,33)
  "interferers": {
    "enabled": true,
    "positions": [
      [19, -10, 10],                  // south of grid
      [-10,  19, 10]                  // west of grid
    ],
    "tx_power_dbm": 30
  }
}
```

Update experiment name to `"ne_bs_voronoi_15x15"`.

---

## Task 2 — New MATLAB runner: `run_ne_bs_15x15.m`

Copy `run_multi_user_15x15.m`, change:
- `OVERRIDE_CONFIG_NAME` → `'ne_bs_voronoi_15x15_config.jsonc'`
- Output subfolder → `'sim_data_ne_bs_<timestamp>'`
- Output filename pattern → `'user%d_ne_bs_15x15.mat'`
- `experiment_info.mat` description field updated

Same 5 device profiles and walk seeds.

---

## Task 3 — Engineering: MATLAB progress bar + ETA

In `generate_simulation_data.m`:
- Wrap walk-generation loop with a counter that prints `step/total (%)  ETA: Xs`
  every 1000 steps using `\r` (overwrite same line)
- Wrap `l.get_channels()` with `tic` / `toc` and print elapsed + ms/snapshot

---

## Task 4 — Engineering: MATLAB timestamped logging

In each `run_*.m` wrapper (starting with `run_ne_bs_15x15.m`):

```matlab
log_file = fullfile(output_dir, 'logs', ...
           sprintf('run_%s.log', datestr(now, 'yyyy-mm-dd_HH-MM-SS')));
mkdir(fileparts(log_file));
diary(log_file); diary on;
% ... simulation ...
diary off;
```

---

## Task 5 — Engineering: MATLAB `parfor` multi-user parallelism

Refactor `generate_simulation_data.m`-based loop to be callable as a function:

1. Create `run_single_user_sim.m` — a function that accepts user parameters
   instead of reading globals, calls the simulation steps, returns output path.
2. In `run_ne_bs_15x15.m` (and `run_multi_user_15x15.m`):

```matlab
if license('test', 'Distrib_Computing_Toolbox')
    parfor u = 1:n_users
        run_single_user_sim(u, profiles(u,:), output_dir, config_name);
    end
else
    for u = 1:n_users
        run_single_user_sim(u, profiles(u,:), output_dir, config_name);
    end
end
```

Expected speedup: ~4–5× on a quad-core machine with PCT.

---

## Task 6 — Engineering: Python timestamped logging

In `multi_user_pipeline.py`:
- Add `setup_logging(out_dir)` function (see `research_plan.md` §7.4)
- Replace `print(...)` with `logging.info(...)` for pipeline-level messages
  (keep `print` for tqdm progress bars since those go to stderr)
- Log file written to `<out_dir>/logs/run_<timestamp>.log`

---

## Task 7 — Engineering: Python `ProcessPoolExecutor` parallelism

In `multi_user_pipeline.py`:
- Extract training logic for a single experiment into `_run_single_experiment()`
- In `run_all_experiments()`, use `ProcessPoolExecutor(max_workers=cpu_count//2)`
  to run training jobs in parallel after features are built
- Feature building must still happen sequentially (shared DataFrame)
- Add `--workers N` CLI arg (default: 1 for safety, set to `auto` for N/2 cores)

---

## Task 8 — Engineering: `tqdm` progress bars in Python

In `multi_user_pipeline.py`:
- Wrap the main experiment loop with `tqdm(EXPERIMENTS, desc='Experiments')`
- Wrap per-user training loops with `tqdm(..., leave=False)` for nested bars
- Add install note: `pip install tqdm` (already in most ML envs)

---

## Task 9 — Run MATLAB simulation for `ne_bs_voronoi_15x15`

After Tasks 1–4 are done, run `run_ne_bs_15x15.m` in MATLAB.  
Estimated time: ~2–3 h sequential, ~40 min with `parfor` (if PCT available).  
Output: `results/grid_localization/grid_15x15/sim_data_ne_bs_<timestamp>/`

---

## Task 10 — Run Python pipeline on new simulation data

```bash
cd experiments/09_grid_localization/src/python
python multi_user_pipeline.py \
  --data-dir results/grid_localization/grid_15x15/sim_data_ne_bs_<timestamp> \
  --out-dir results/ne_bs_voronoi_15x15 \
  --models xgboost rf \
  --history 3 \
  --plots
```

Then run the MAE heatmap script:

```bash
python plot_mae_heatmap.py \
  --data-dir results/grid_localization/grid_15x15/sim_data_ne_bs_<timestamp> \
  --out-dir results/ne_bs_voronoi_15x15 \
  --experiments BASE BASE_H BASE_A BASE_A_H
```

---

## Task 11 — Comparison analysis: NE vs center BS

Create `src/python/compare_placements.py` (or add to `multi_user_pipeline.py`):
- Load `results/multi_user_voronoi_15x15/csvs/results_summary.csv` (center)
- Load `results/ne_bs_voronoi_15x15/csvs/results_summary.csv` (NE)
- Generate side-by-side bar chart of accuracy for core experiments
- Generate AoA-gain comparison: Δacc = `BASE_A_H` − `BASE_H` for each placement
- Generate MAE heatmap side-by-side (same colour scale) for `BASE_H`

Outputs:
- `results/placement_comparison/accuracy_comparison.png`
- `results/placement_comparison/aoa_gain_comparison.png`
- `results/placement_comparison/mae_heatmap_comparison.png`
- `results/placement_comparison/comparison_summary.csv`

---

## Task 12 — Update `research_documentation.md`

Add new section after the current multi-user results:

- NE BS geometry diagram (ASCII)
- Angular diversity analysis (center 360° vs NE 60°)
- Results table: all experiments, both placements, Δacc column
- AoA gain comparison table
- MAE spatial gradient analysis (SW dead zone or not)
- Answer to each of the 5 research questions (Q1–Q5 from `research_plan.md`)

---

## Progress Tracker

| # | Task | Status |
|---|------|--------|
| 1 | `ne_bs_voronoi_15x15_config.jsonc` | ✅ done |
| 2 | `run_ne_bs_15x15.m` | ✅ done |
| 3 | MATLAB progress bar + ETA | ✅ done |
| 4 | MATLAB timestamped logs | ✅ done |
| 5 | MATLAB `parfor` parallelism | ✅ done |
| 6 | Python timestamped logging | ⬜ todo |
| 7 | Python `ProcessPoolExecutor` | ⬜ todo |
| 8 | Python `tqdm` progress bars | ⬜ todo |
| 9 | Run MATLAB simulation | ✅ done — `sim_data_ne_bs_2026-04-11_20-11-48` |
| 10 | Run Python pipeline | ✅ done — `results/ne_bs_voronoi_15x15/` |
| 11 | Comparison analysis script | ✅ done — `src/python/compare_placements.py` |
| 12 | Update research_documentation.md | ✅ done — §9 added |

---

## Deferred Engineering: MATLAB Directory Reorganisation

Planned subdirectory layout for `src/matlab/` — **do after simulation finishes**
(moving files while `generate_simulation_data.m` is running would break it):

```
src/matlab/
  core/        generate_simulation_data.m  run_single_user_sim.m
  lib/         AreaGenerator.m  GeometryUtils.m  TrafficUtils.m  read_jsonc.m
  runners/     run_ne_bs_15x15.m  run_multi_user_15x15.m  run_env_variability_15x15.m
               run_voronoi.m  run_voronoi_10x10.m  run_voronoi_15x15.m
               run_voronoi_20x20.m  run_multi_bs_10x10.m  run_multi_bs_10x10_v2.m
               run_from_config.m
  tests/       TestReadJsonc.m  TestGridGeneration.m   ← already created
```

After moving files, update path derivation in each script:
- Files in `core/`    → `fileparts(fileparts(fileparts(mfilename('fullpath'))))` to reach `src/matlab`
- Files in `runners/` → same 3-level up
- Files in `lib/`     → add `addpath(fullfile(src_matlab, 'lib'))` in callers

---

## Deferred from March 2026 Plan

### Task D1 — Environmental Variability Experiment (March Task 4)

Run U1 three times on the same 15×15 Voronoi grid with different QuaDRiGa channel
seeds to simulate day-to-day channel drift. Train on runs 1+2, test on run 3.

**What already exists:**
- `src/matlab/run_env_variability_15x15.m` — runner script, ready to execute
- `generate_simulation_data.m` — supports `OVERRIDE_CHANNEL_SEED` global
- `multi_user_pipeline.py` — `run_env_variability()` function implemented, `--env-dir` CLI flag

**What remains:**
1. Run `run_env_variability_15x15.m` in MATLAB (~1.5 h, 3 sequential seeds)
   - Output: `results/grid_localization/grid_15x15/sim_data_env_variability_<timestamp>/`
   - Files: `run1_voronoi_15x15.mat`, `run2_voronoi_15x15.mat`, `run3_voronoi_15x15.mat`
2. Run Python pipeline with `--env-dir <path>`
3. Add results section to `research_documentation.md`

**Why deferred:** Lower priority than NE-BS geometry question. Run after April tasks complete.
