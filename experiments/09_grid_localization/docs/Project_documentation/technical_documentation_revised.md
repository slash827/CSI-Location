# Technical Documentation, Revised Edition
# CSI-Based UE Localization Using Transition History

Revision of 2026-10-16. This edition supersedes `technical_documentation.md` (written before October 2026) for everything that concerns the simulation settings, the controlled-grid results and the interpretation of the history gain. Parts of the older document that were not affected (feature engineering details, model hyperparameters, the early scalability sweeps) are kept there and are referenced by section number. Section 9 maps every old section to its status.

## 0. What changed and why

| Change | Effect |
|---|---|
| The simulation generator never passed the configured carrier frequency to QuaDRiGa, which ran at its 2.6 GHz default (all controlled-grid, grid-size-sweep and 25×25 simulations; the macro-cell runners were not affected) | Fixed in `generate_simulation_data.m`; the generator logs the applied carrier; all controlled-grid and 25×25 simulations in this edition were regenerated at 3.0 GHz |
| The Voronoi cells never changed the propagation scenario: the walk was one track segment, so QuaDRiGa applied the scenario of the first cell to the whole walk | Fixed: `uniform_scenario` (one scenario for the whole walk) and `per_cell_segments` (one segment per run inside a cell) |
| The runs of 2026-06-12 cannot be regenerated from the repository (section 3.5) | The controlled grid was rerun under three documented propagation settings; every simulation folder now holds the configuration copy and the git commit |
| The mechanism behind the history gain was re-examined | The gain is the averaging of per-report AoA error, not the turning rate of the bearing (section 6.5) |
| The metric audit and the constant-guess baseline were added | The 20 to 30 m macro errors are real and only about 2x better than guessing (section 5.3) |

## 1. Problem statement and claims

A single base station localizes a moving UE from per-report channel measurements (RSS, SINR, and for multi-antenna devices the angle of arrival, AoA). The thesis is that stacking the previous reports ("transition history") lowers the position error of every estimator.

What is established (sections 6 and 7):

1. History lowers the error in every model family tested, on both studies. Controlled grid: all 16 set × placement × model rows without AoA (12 at 3.0 GHz and the four NLOS 3.5 GHz rows), +4.9 to +27.4 pp exact-cell accuracy, 0.96 to 4.29 m. Macro cell: 2.8 to 4.1 m (15 to 21 %) for multi-antenna devices in seven families.
2. The gain comes from the AoA channels. It is reproduced by an unordered mean of the window and it is zero or negative when the AoA is exact. The account that "the rate at which the bearing turns reveals range" is not supported.
3. The size of the gain depends on how the AoA error is modelled. With an error independent between reports (what the pipeline simulates) it is about 17 %; with an error persistent across the window it is about 6 % (trees) or 2 to 3 % (neural models).
4. The AoA gain depends strongly on the base-station placement (centre BS +10 to +39 pp, corner BS −0.4 to +6 pp on the grid).

What is not established: the absolute accuracy of any single setting (it moves with the propagation scenario by tens of points), anything about measured traces, and the 2026-06-12 absolute numbers.

## 2. Pipeline

MATLAB with QuaDRiGa generates one `.mat` file per simulated user (RSS, SINR, clean AoA, positions, grid point, cell, step, timestamp) plus `data_generation_config.jsonc` and `experiment_info.mat`. Python loads the files, applies the AoA impairment (Gaussian noise and 5° quantization, optionally with a SINR-dependent standard deviation), builds the history features, splits each user chronologically 80/20 and trains the models. Details of feature construction and models are unchanged and are in `technical_documentation.md` sections 2 and 4.

Entry points:

| Task | Command |
|---|---|
| 15×15 simulation, centre BS | `runners/run_multi_user_15x15.m` (config chosen by `RUNNER_CONFIG_NAME`) |
| 15×15 simulation, NE BS | `runners/run_ne_bs_15x15.m` |
| 25×25 simulation (five device profiles) | `runners/run_ne_bs_25x25.m` |
| Classification pipeline | `pipelines/multi_user_pipeline.py --data-dir ... --out-dir ... --sinr-dependent-aoa --models xgboost rf --history 3` |
| Regression pipeline (25×25) | `pipelines/multi_user_pipeline_regression.py ... --subsample 0.3 --load-tuned-params configs/tuned_params_25x25_regression.json` |
| Extended history and 1D-CNN | `experiments_ablation/grid_history_extended.py` |
| Metric audit | `experiments_ablation/error_audit_grid.py`, `error_maps_macro.py`, `tests/test_error_metrics.py` |
| Table across the propagation sets | `experiments_ablation/compare_controlled_grid_sets.py` |

## 3. Simulation environment

### 3.1 Common settings of the 15×15 controlled grid

15×15 cells at 2 m, 400 steps per cell (90,001 reports per user), 5 device profiles (U1 4 antennas 0 dB 1.5 m seed 100; U2 2 antennas −2 dB seed 200; U3 1 antenna −4 dB seed 300; U4 as U1 with seed 400; U5 2 antennas −1 dB 0.9 m seed 500), serving BS at the centre (19,19,10) or beyond the NE corner (48,48,10), interferers at (−11,19,10) and (19,−11,10), transmit power 30 dBm, bandwidth 100 MHz, carrier **3.0 GHz**, four Voronoi cells (labels for per-cell breakdowns).

### 3.2 Propagation sets

| Set | Config suffix | Propagation | Simulation folders (2026-10-13) |
|---|---|---|---|
| RMa LOS | `_rmalos` | RMa LOS for the whole walk | `10-43-34` (centre), `10-43-29` (NE) |
| Mixed per-cell | `_mixed` | UMi LOS in cells 1 and 4, UMi NLOS in cells 2 and 3, one segment per run in a cell (minimum run 100 reports) | `11-23-48`, `11-23-43` |
| NLOS | none | UMi NLOS for the whole walk | `15-47-39`, `15-47-28` |
| NLOS 3.5 GHz (comparison only) | none | as NLOS, carrier 3.5 GHz | `01-02-45`, `01-02-42` |

The per-cell implementation was checked on a short walk: NLOS cells came out 3 to 7 dB weaker than LOS cells. The carrier has no material effect: NLOS at 3.0 and 3.5 GHz agree within about 1 pp (NE XGBoost BASE_H3 25.8 % against 24.6 %).

### 3.3 25×25 regression data

25×25 cells at 4 m, NE BS (116,116,10), interferers (−25,53,10) and (53,−25,10), same five profiles and seeds, 400 steps per cell, carrier 3.0 GHz, UMi LOS for the whole walk (config `ne_bs_voronoi_25x25_umilos_config.jsonc`; the first cell is UMi LOS, which is what the 2026-06-13 data effectively ran). Simulation `sim_data_ne_bs_2026-10-15_09-40-11`. Two further variants (`_nlos`, `_mixed`) exist as configurations and have not been run.

### 3.4 Macro-cell study (unchanged)

25×25 cells at 4 m, 300 users with a manifest of device types, BS at (116,116,10), interferers at (−60,53,10) and (53,−60,10), 3.0 GHz, uniform UMi NLOS (primary) and a per-segment mixed variant. Generated by `run_multi_user_300_25x25*.m`, which set the carrier from the config; not affected by the generator defects.

### 3.5 What cannot be reproduced

The simulations of 2026-06-12 (`multi_user_voronoi_15x15_optimal`, `ne_bs_voronoi_15x15_optimal`) were reproduced from the repository state of 2026-06-06 (commit `6c1c02a`) with the original configs, user 1, seed 100: for the centre BS the walk, positions and clean AoA are bit-identical, RSS differs (per-cell map correlation 0.51) and SINR is uncorrelated; for the NE BS the walk itself differs. The generator is deterministic (old and current code agree on the same short walk), so the June files were made with settings that are not in the repository. Their numbers are not used in this edition. `OLD_VS_REGENERATED_RUNS.md` has the full comparison.

### 3.6 Provenance

Every simulation of this edition stores `data_generation_config.jsonc`, and `experiment_info.mat` holds the git commit, a dirty flag for MATLAB sources and configs, carrier, bandwidth, scenario, uniform scenario, transmit power and interferer positions. Committed copies of the result tables and configs are in `docs/results_of_record/`.

## 4. Features, experiments, models

Unchanged from `technical_documentation.md` sections 4 and 5.4, with these clarifications:

- Experiment names: `BASE` (RSS+SINR, h=0), `BASE_H3` (history 3), `BASE_A` (+AoA), `BASE_A_H3`, `_dp` (device parameters), `_uid` (user id).
- The neural models of the macro study use 13 channels per report: RSS, SINR, sin and cos of both angles, two ray coordinates (a path-loss range estimate times the AoA unit vector), RSS and angle first differences, and the time increment `delta_t`; plus three static device features. There is no other measured quantity. Delay spread and K-factor were used in the earliest pipeline and removed on 2026-03-01 as not UE-measurable. Using the 13 derived channels instead of the 5 raw ones changed the error by only 2.2 % (19.69 to 19.26 m).
- Single-antenna devices have NaN AoA, replaced by 0 before training. The zeros are a constant that identifies the device, so a model that sees the AoA columns also sees a device flag. Single-antenna device 3 on the controlled grid gains from `BASE_A` exactly as much as from adding the user id alone, so that gain is not angle information.

## 5. Evaluation

### 5.1 Split and metrics
Chronological 80/20 per user; accuracy is exact grid cell, MAE is the mean Euclidean distance between the predicted and true cell positions. Seed repeats and Student-t intervals are used in the macro and follow-up studies (20 seeds trees, 5 neural); the controlled grid is a single run per configuration and differences below 2 to 3 pp are not interpreted.

### 5.2 Metric audit
`tests/test_error_metrics.py` checks that known predictions give known accuracy and MAE and that MAE = (1 − accuracy) × (mean distance of the wrong predictions). On the RMa LOS NE set (XGBoost): BASE 31.4 % exact, wrong predictions 8.83 m off, MAE 6.06 m; BASE_H3 48.9 %, 6.81 m, 3.48 m; BASE_A_H3 52.5 %, 5.28 m, 2.51 m. The MAE averaged per grid point (equal weights) differs from the sample-weighted MAE by less than 0.1 m (test rows per cell 156 to 537). An 80 % exact-cell result therefore cannot coincide with a 30 m MAE in the same experiment.

### 5.3 Reference levels and the macro error scale
Always guessing the mean training position: 37.1 m (multi-antenna) and 33.6 m (single-antenna) on the uniform NLOS macro data; on the 15×15 grid about 10.9 m. Macro XGBoost, uniform NLOS: multi-antenna 19.0 m without history and 15.4 m with it (8 % of samples within 5 m, 60 % within 20 m); single-antenna 34.7 m, which is not better than the constant guess. Error maps by position (`results/error_audit/macro_*`) show the single-antenna error above 50 m at the far corners. The 20 to 30 m values are therefore real and are the consequence of the weak information in one RSS report at 20 to 160 m range.

## 6. Results

### 6.1 Controlled grid across propagation settings (accuracy % / MAE m)

| Set | BS | Model | BASE | BASE_H3 | BASE_A | BASE_A_H3 |
|---|---|---|---|---|---|---|
| RMa LOS | centre | XGBoost | 33.5 / 6.84 | 50.6 / 3.79 | 68.3 / 1.72 | 71.6 / 1.35 |
| RMa LOS | centre | RF | 43.9 / 5.34 | 55.3 / 3.32 | 66.7 / 1.78 | 69.0 / 1.38 |
| RMa LOS | NE | XGBoost | 31.4 / 6.03 | 48.6 / 3.48 | 46.0 / 3.39 | 52.6 / 2.51 |
| RMa LOS | NE | RF | 50.5 / 3.88 | 55.4 / 2.92 | 54.1 / 2.94 | 58.2 / 2.20 |
| Mixed | centre | XGBoost | 31.7 / 8.06 | 59.1 / 3.77 | 75.5 / 1.43 | 78.6 / 1.00 |
| Mixed | centre | RF | 53.5 / 5.21 | 66.5 / 2.76 | 77.1 / 1.25 | 76.4 / 1.04 |
| Mixed | NE | XGBoost | 31.6 / 7.37 | 57.3 / 3.55 | 49.6 / 4.61 | 58.4 / 3.06 |
| Mixed | NE | RF | 52.3 / 4.93 | 63.8 / 2.78 | 54.6 / 4.25 | 63.4 / 2.62 |
| NLOS | centre | XGBoost | 14.4 / 10.21 | 29.6 / 7.03 | 63.9 / 1.99 | 68.2 / 1.39 |
| NLOS | centre | RF | 23.9 / 9.02 | 35.4 / 5.95 | 64.8 / 1.97 | 67.2 / 1.38 |
| NLOS | NE | XGBoost | 12.6 / 10.36 | 25.8 / 7.36 | 24.2 / 6.72 | 32.0 / 4.85 |
| NLOS | NE | RF | 20.1 / 9.02 | 29.4 / 6.68 | 27.1 / 6.50 | 35.2 / 4.47 |

(`results/controlled_grid_2026_10/comparison_sets.md` holds the same table with the gains.) Reading:

- History helps in every row. Without AoA: +4.9 to +27.4 pp and 0.96 to 4.29 m. With AoA the gain is smaller at the centre BS (+2.3 to +4.2 pp, 0.2 to 0.6 m, one row −0.7 pp) and larger at the NE BS (+4.1 to +8.8 pp, 0.7 to 2.0 m).
- The AoA gain (BASE_H3 → BASE_A_H3) is +10 to +39 pp at the centre BS and −0.4 to +6 pp at the NE BS.
- Absolute levels depend on the propagation set: centre XGBoost BASE_H3 is 29.6 % (NLOS), 50.6 % (RMa LOS) and 59.1 % (mixed). The RF snapshot model is much better than the XGBoost snapshot model in every set (for example 43.9 % against 33.5 % RMa LOS centre), so the XGBoost history gain is partly recovery from a weak snapshot model.
- Per-user results: the 4-antenna devices reach the highest AoA accuracy; user 3 (one antenna) gains from AoA features only through the NaN-to-0 device flag (section 4).

### 6.2 Extended history and a 1D-CNN (MAE m, RMa LOS, RSS+SINR; 3 CNN seeds)

| Centre BS | h=0 | h=1 | h=3 | h=5 | h=7 | h=10 | h=15 |
|---|---|---|---|---|---|---|---|
| XGBoost | 6.83 | 4.05 | 3.81 | 3.72 | 3.70 | 3.64 | 3.65 |
| RF | 5.34 | 3.77 | 3.32 | 3.30 | 3.26 | 3.40 | 3.56 |
| 1D-CNN | 7.72 | 6.06 | 5.20 | 4.64 | 4.06 | 3.82 | 3.53 |

| NE BS | h=0 | h=1 | h=3 | h=5 | h=7 | h=10 | h=15 |
|---|---|---|---|---|---|---|---|
| XGBoost | 6.06 | 3.69 | 3.48 | 3.44 | 3.43 | 3.40 | 3.40 |
| RF | 3.88 | 3.14 | 2.92 | 2.94 | 2.92 | 3.04 | 3.15 |
| 1D-CNN | 6.66 | 5.56 | 5.29 | 4.84 | 4.47 | 4.28 | 3.91 |

The trees take almost all of the gain at h=1 to 3 and stay flat or get worse (Random Forest) beyond h≈5. The 1D-CNN improves with every added depth up to h=15 (centre 7.72 to 3.53 m) and ends level with the trees. With AoA the CNN gains up to h≈10 to 15 (centre 2.68 to 1.38 m) and reaches the trees' level (XGBoost 1.34 m). On the grid the neural family therefore also gains from history, from a longer window than the trees need.

### 6.3 Placement and the AoA gain
At the centre BS the azimuth covers 360° and AoA alone separates neighbouring cells (BASE_A 64 to 77 % in every set). At the NE corner the grid falls within about 52° of azimuth, neighbouring cells are no longer separated by azimuth, and the AoA gain falls to −0.4 to +6 pp; what remains is consistent with elevation, which encodes distance, but it was not isolated on the grid.

### 6.4 25×25 regression (3D MAE m, five pooled device profiles, NE BS, UMi LOS, 3.0 GHz)

Regenerated 2026-10-15 with Cartesian targets, 30 % training subsample, history 3. The table below uses the SINR-dependent AoA noise; the fixed-noise comparison follows it.

| Run | Experiment | XGBoost | RF |
|---|---|---|---|
| untuned | BASE | 26.07 | 15.28 |
| untuned | BASE_H3 | 24.55 | 18.08 |
| untuned | BASE_A_H3_dp | 16.50 | 13.08 |
| tuned | BASE | 29.39 | 14.52 |
| tuned | BASE_H3 | 13.70 | 17.06 |
| tuned | BASE_A | 16.97 | 12.04 |
| tuned | BASE_A_H3_dp | 10.67 | 12.25 |
| tuned | BASE_A_H3_dp_INT | 9.63 | 11.32 |
| segment shuffle | BASE / BASE_H3 | 29.27 / 14.97 | 14.73 / 18.32 |
| custom loss (XGBoost) | BASE / BASE_H3 / BASE_A_H3_dp | 29.32 / 16.77 / 12.85 | n/a |

All numbers without AoA reproduce the earlier (2026-06-13, 2.6 GHz) folders within about 1 m, including the history result (XGBoost 29.4 to 13.7 m, Random Forest worse with history) and the block-shuffled control. The AoA numbers with tuned parameters are 2.6 to 4.5 m worse than the earlier folders, and the earlier hybrid-feature advantage for Random Forest does not reappear.

The difference was traced to the AoA noise model. The earlier 25×25 runs used a fixed noise of 4° (standard deviation) with 5° quantization; the regenerated runs above used the SINR-dependent noise (`--sinr-dependent-aoa`) that the controlled-grid pipelines use. Rerunning with the fixed noise reproduces the earlier folders, on the earlier (2.6 GHz) data and on the regenerated (3.0 GHz) data:

| 3D MAE (m), tuned, 30 % subsample | Earlier folders | Earlier data, fixed 4° noise | New data, fixed 4° noise | New data, SINR-dependent noise |
|---|---|---|---|---|
| XGBoost BASE_A | 12.03 | 12.11 | 12.50 | 16.97 |
| XGBoost BASE_A_H3 | 8.17 | 8.16 | 8.36 | 11.04 |
| XGBoost BASE_A_H3_dp | 7.96 | 8.01 | 7.97 | 10.67 |
| XGBoost hybrid h=3 | 9.56 | 9.61 | 9.55 | n/a |
| RF BASE_A | 7.56 | 7.56 | 8.24 | 12.04 |
| RF BASE_A_H3_dp | 8.09 | 8.09 | 8.85 | 12.25 |
| RF hybrid h=1 | 7.51 | 7.51 | 8.14 | 12.30 |

So the earlier 25×25 numbers are reproduced (no-AoA numbers to the second decimal on the earlier data, AoA numbers to within 0.1 m on the earlier data and within 0.7 m on the 3.0 GHz data), and the hybrid-feature result survives under the fixed noise. With the SINR-dependent noise the angles are noisier at the low SINR of the far cells, and every AoA number is 3 to 4 m worse. Which noise model a study used is therefore part of its definition: the 25×25 regression and the macro study use the fixed 4° noise; the 15×15 controlled-grid pipelines use the SINR-dependent noise.

### 6.5 Mechanism of the history gain (macro cell, unchanged findings)
- An unordered mean of the AoA window recovers the gain; elevation carries more than 80 % of it; with exact AoA the gain is zero for trees and negative for all four neural models.
- The gain falls from about 17 % (independent error) to about 6 % (trees) or 2 to 3 % (neural) when the error correlates across the window.
- Region control: uniform NLOS, with no LOS anywhere, shows the same regional gap as mixed propagation, so the regional difference is not a LOS effect. An oracle LOS flag, a blocked-LOS corridor and removing the interferers do not change the conclusion.
- Single-antenna devices are not localized (constant guess 38.5 m, models 36.3 m, with or without history). On mixed data the tree ensembles gain 1.2 to 1.4 m (20/20 seeds), tied to the propagation state.

## 7. Limitations
- The AoA error is simulated; the size of the gain depends on its correlation across reports.
- The controlled grid tests later time steps of users seen in training; the macro study tests unseen users.
- The June absolute results are not reproducible (section 3.5); the 25×25 data come from one simulation.
- The two grid studies differ in scale, propagation and task (classification of 2 m cells against regression over a 100 m area); they are not directly comparable.
- Model hyperparameters of the grid were not tuned per history depth.

## 8. Reproducing this edition
1. `RUNNER_CONFIG_NAME='<config>'; run_multi_user_15x15` (or `run_ne_bs_15x15`, `run_ne_bs_25x25`) from `src/matlab/runners`; QuaDRiGa 2.8.1 on the path (`ensure_quadriga` finds it through `QUADRIGA_HOME`).
2. `multi_user_pipeline.py --data-dir <sim folder> --out-dir <out> --sinr-dependent-aoa --models xgboost rf --history 3 --n-jobs 8` (all experiments, plots, sweep; `--run-only` for subsets).
3. `grid_history_extended.py --data-dir <sim folder> --out-dir <out>` for section 6.2; `compare_controlled_grid_sets.py` for section 6.1.
4. The machine must not sleep during long runs (a Windows idle timeout froze one run for 9 hours without loss).

## 9. Status of the sections of the earlier edition

| Earlier section | Status |
|---|---|
| 1 to 5 (problem, architecture, simulation, features, evaluation) | Valid except the carrier (2.6 GHz was applied, not the configured value) and the scenario statements for the Voronoi cells |
| 6 Summary of findings | Replaced by section 1 here |
| 7.0 Regression against classification, 7.1 grid-size scalability | Not rerun; generated at 2.6 GHz; the carrier effect is small (section 3.2); use as qualitative |
| 7.2, 7.3 Controlled grid centre and NE | Replaced by sections 6.1 to 6.3. The tables of the earlier edition (centre 51.0 %, NE 86.0 %) came from the June data |
| 7.4 25×25 regression | Replaced by section 6.4; the spherical-target table is no longer produced by the code |
| 7.5 Kalman filtering | Not affected |
| 8 Macro 300-user ablations, 9 Master benchmark | Not affected by the generator defects; mechanism interpretation updated (section 6.5) |
