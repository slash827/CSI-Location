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
5. On the controlled grid, sequence models (GRU, 1D-CNN) keep improving with the window length up to h = 15 and end below the tree models in mean error, while the trees plateau at h = 3 to 5. With the current report kept in place, shuffling the older reports raises the GRU error at h = 15 by 19 to 48 % in all eight set × AoA rows, so the order of the older reports carries information beyond their set; part of the GRU advantage does not depend on order (section 6.2). The same plateau and GRU advantage appear in the 25×25 regression (section 6.4).

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

25×25 cells at 4 m, NE BS (116,116,10), interferers (−25,53,10) and (53,−25,10), same five profiles and seeds, 400 steps per cell, carrier 3.0 GHz, UMi LOS for the whole walk (config `ne_bs_voronoi_25x25_umilos_config.jsonc`; the first cell is UMi LOS, which is what the 2026-06-13 data effectively ran). Simulation `sim_data_ne_bs_2026-10-15_09-40-11`. Two further variants were run (`ne_bs_voronoi_25x25_nlos_config.jsonc`, simulation `2026-10-16_01-32-21`; `ne_bs_voronoi_25x25_mixed_config.jsonc`, per-cell segments, simulation `2026-10-16_14-57-54`).

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

### 6.2 Extended history, CNN, GRU and the plateau of the trees (MAE m)

Depths h = 0 to 15, RSS+SINR ("no AoA") and RSS+SINR+AoA, on four sets (RMa LOS and mixed, both BS positions). XGBoost and Random Forest on raw lags (single run); 1D-CNN and GRU (3 seeds); window-mean trees receive only the current report and the window mean of each channel (azimuth averaged as a unit vector). Full tables: `docs/results_of_record/history_extended/`.

| Set | AoA | Model | h=0 | h=1 | h=3 | h=5 | h=10 | h=15 |
|---|---|---|---|---|---|---|---|---|
| RMa LOS, NE BS | no | XGBoost | 6.06 | 3.69 | 3.48 | 3.44 | 3.40 | 3.40 |
| RMa LOS, NE BS | no | RF | 3.88 | 3.14 | 2.92 | 2.94 | 3.04 | 3.15 |
| RMa LOS, NE BS | no | XGBoost window mean | 4.53 | 3.83 | 3.93 | 3.97 | 4.06 | 4.06 |
| RMa LOS, NE BS | no | RF window mean | 3.88 | 3.21 | 3.35 | 3.38 | 3.41 | 3.44 |
| RMa LOS, NE BS | no | 1D-CNN | 6.66 | 5.56 | 5.29 | 4.84 | 4.28 | 3.91 |
| RMa LOS, NE BS | no | GRU | 4.49 | 3.78 | 3.34 | 3.05 | 2.64 | 2.48 |
| RMa LOS, NE BS | yes | XGBoost | 3.38 | 2.72 | 2.51 | 2.41 | 2.35 | 2.32 |
| RMa LOS, NE BS | yes | RF | 2.94 | 2.43 | 2.20 | 2.25 | 2.32 | 2.38 |
| RMa LOS, NE BS | yes | XGBoost window mean | 3.33 | 2.73 | 2.58 | 2.47 | 2.44 | 2.45 |
| RMa LOS, NE BS | yes | RF window mean | 2.97 | 2.47 | 2.34 | 2.25 | 2.24 | 2.30 |
| RMa LOS, NE BS | yes | 1D-CNN | 4.59 | 3.50 | 2.83 | 2.75 | 2.60 | 2.61 |
| RMa LOS, NE BS | yes | GRU | 3.35 | 2.64 | 2.25 | 2.05 | 1.89 | 1.87 |
| Mixed, NE BS | no | XGBoost | 7.34 | 3.83 | 3.58 | 3.51 | 3.47 | 3.46 |
| Mixed, NE BS | no | RF | 4.93 | 3.21 | 2.78 | 2.82 | 3.08 | 3.35 |
| Mixed, NE BS | no | XGBoost window mean | 5.47 | 4.05 | 4.49 | 4.52 | 4.52 | 4.52 |
| Mixed, NE BS | no | RF window mean | 4.83 | 3.40 | 3.78 | 3.78 | 3.80 | 3.80 |
| Mixed, NE BS | no | 1D-CNN | 8.34 | 5.51 | 3.86 | 3.26 | 2.57 | 2.49 |
| Mixed, NE BS | no | GRU | 5.37 | 3.48 | 2.58 | 2.11 | 1.58 | 1.42 |
| Mixed, NE BS | yes | XGBoost | 4.63 | 3.39 | 3.06 | 2.93 | 2.83 | 2.82 |
| Mixed, NE BS | yes | RF | 4.25 | 3.12 | 2.62 | 2.83 | 2.97 | 3.15 |
| Mixed, NE BS | yes | XGBoost window mean | 4.58 | 3.45 | 3.48 | 3.34 | 3.17 | 3.15 |
| Mixed, NE BS | yes | RF window mean | 4.34 | 3.34 | 3.33 | 3.19 | 3.05 | 3.15 |
| Mixed, NE BS | yes | 1D-CNN | 6.04 | 3.84 | 2.53 | 2.19 | 1.82 | 1.67 |
| Mixed, NE BS | yes | GRU | 4.37 | 2.79 | 2.02 | 1.65 | 1.37 | 1.30 |
| RMa LOS, centre BS | no | XGBoost | 6.83 | 4.05 | 3.81 | 3.72 | 3.64 | 3.65 |
| RMa LOS, centre BS | no | RF | 5.34 | 3.77 | 3.32 | 3.30 | 3.40 | 3.56 |
| RMa LOS, centre BS | no | XGBoost window mean | 5.12 | 4.22 | 4.37 | 4.39 | 4.39 | 4.38 |
| RMa LOS, centre BS | no | RF window mean | 5.54 | 4.47 | 4.25 | 3.92 | 3.83 | 3.84 |
| RMa LOS, centre BS | no | 1D-CNN | 7.72 | 6.06 | 5.20 | 4.64 | 3.82 | 3.53 |
| RMa LOS, centre BS | no | GRU | 5.25 | 4.01 | 3.28 | 2.85 | 2.36 | 2.19 |
| RMa LOS, centre BS | yes | XGBoost | 1.74 | 1.41 | 1.35 | 1.34 | 1.36 | 1.34 |
| RMa LOS, centre BS | yes | RF | 1.78 | 1.43 | 1.38 | 1.43 | 1.52 | 1.57 |
| RMa LOS, centre BS | yes | XGBoost window mean | 1.71 | 1.44 | 1.48 | 1.51 | 1.53 | 1.57 |
| RMa LOS, centre BS | yes | RF window mean | 1.73 | 1.52 | 1.54 | 1.51 | 1.58 | 1.63 |
| RMa LOS, centre BS | yes | 1D-CNN | 2.68 | 1.77 | 1.64 | 1.48 | 1.43 | 1.38 |
| RMa LOS, centre BS | yes | GRU | 2.00 | 1.42 | 1.22 | 1.13 | 1.03 | 1.01 |
| Mixed, centre BS | no | XGBoost | 8.05 | 4.01 | 3.77 | 3.65 | 3.58 | 3.53 |
| Mixed, centre BS | no | RF | 5.21 | 3.31 | 2.76 | 2.78 | 2.93 | 3.21 |
| Mixed, centre BS | no | XGBoost window mean | 5.90 | 4.29 | 4.82 | 4.84 | 4.76 | 4.74 |
| Mixed, centre BS | no | RF window mean | 5.21 | 3.55 | 4.04 | 4.03 | 3.95 | 3.90 |
| Mixed, centre BS | no | 1D-CNN | 8.96 | 5.58 | 3.83 | 2.91 | 2.20 | 2.01 |
| Mixed, centre BS | no | GRU | 5.74 | 3.62 | 2.52 | 1.95 | 1.38 | 1.24 |
| Mixed, centre BS | yes | XGBoost | 1.44 | 1.04 | 1.00 | 0.99 | 0.98 | 0.99 |
| Mixed, centre BS | yes | RF | 1.25 | 0.98 | 1.04 | 1.16 | 1.26 | 1.31 |
| Mixed, centre BS | yes | XGBoost window mean | 1.42 | 1.09 | 1.18 | 1.19 | 1.23 | 1.26 |
| Mixed, centre BS | yes | RF window mean | 1.24 | 1.02 | 1.11 | 1.11 | 1.16 | 1.18 |
| Mixed, centre BS | yes | 1D-CNN | 1.90 | 1.16 | 0.88 | 0.86 | 0.72 | 0.75 |
| Mixed, centre BS | yes | GRU | 1.38 | 0.92 | 0.80 | 0.72 | 0.64 | 0.60 |

Findings (the same direction in all four sets, with and without AoA):

1. The trees take their gain at h = 1 to 3 and stay flat (XGBoost) or get worse (Random Forest, best at h = 3 to 5). The 1D-CNN improves with every added depth and, on the mixed sets, ends below both trees (mixed NE without AoA at h=15: CNN 2.49 m, RF 3.35 m, XGBoost 3.46 m). The GRU is the best model at long history in every set (mixed NE 1.42 m, mixed centre with AoA 0.60 m against 0.99 m for XGBoost).
2. The plateau of the trees is not a missing average. Window-mean trees do not keep improving: without AoA they are worse than raw-lag trees for h >= 3 (mixed NE XGBoost 4.52 m against 3.51 m at h=5); with AoA they equal them.

#### Order test (corrected 2026-10-22)

The first order test (2026-10-17, models `gru_shuf`, `cnn_shuf`) permuted all reports inside every window. That also hid which report is the current one, and the target is the current position, so the shuffled networks could only locate the region of the window: at h = 15 they reached about 5.6 % exact-cell accuracy, below the CNN with no history at all (18.8 %, mixed NE). That test showed that knowing the newest report matters, not that order matters. It is superseded.

The fair test (`gru_shufold`, `cnn_shufold`) keeps the current report in its place and permutes only the older ones, in training and test (h = 3, 10, 15, two seeds; ordered networks three seeds). Mean position error in metres, h = 3 / 10 / 15; files `docs/results_of_record/history_extended/*_shufold/` and `order_test_comparison.csv`.

| Set | AoA | GRU ordered | GRU, older shuffled | CNN ordered | CNN, older shuffled | best tree at h = 15 |
|---|---|---|---|---|---|---|
| RMa LOS, NE BS | no | 3.34 / 2.64 / 2.48 | 3.45 / 3.22 / 2.96 | 5.29 / 4.28 / 3.91 | 5.37 / 4.51 / 4.39 | 3.15 (RF) |
| RMa LOS, NE BS | yes | 2.25 / 1.89 / 1.87 | 2.33 / 2.21 / 2.28 | 2.83 / 2.60 / 2.61 | 2.97 / 2.91 / 2.86 | 2.30 (RF window mean) |
| Mixed, NE BS | no | 2.58 / 1.58 / 1.42 | 2.87 / 2.13 / 2.03 | 3.86 / 2.57 / 2.49 | 4.49 / 3.49 / 3.46 | 3.35 (RF) |
| Mixed, NE BS | yes | 2.02 / 1.37 / 1.30 | 2.27 / 1.85 / 1.91 | 2.53 / 1.82 / 1.67 | 2.94 / 2.65 / 2.46 | 2.82 (XGBoost) |
| RMa LOS, centre BS | no | 3.28 / 2.36 / 2.19 | 3.50 / 2.89 / 2.83 | 5.20 / 3.82 / 3.53 | 5.51 / 4.41 / 4.34 | 3.56 (RF) |
| RMa LOS, centre BS | yes | 1.22 / 1.03 / 1.01 | 1.33 / 1.29 / 1.29 | 1.64 / 1.43 / 1.38 | 1.75 / 1.68 / 1.73 | 1.34 (XGBoost) |
| Mixed, centre BS | no | 2.52 / 1.38 / 1.24 | 2.87 / 1.90 / 1.84 | 3.83 / 2.20 / 2.01 | 4.37 / 3.12 / 3.08 | 3.21 (RF) |
| Mixed, centre BS | yes | 0.80 / 0.64 / 0.60 | 0.89 / 0.81 / 0.82 | 0.88 / 0.72 / 0.75 | 1.06 / 1.01 / 1.05 | 0.99 (XGBoost) |

Exact-cell accuracy of the GRU at h = 15, ordered against older shuffled: 47.9 / 41.9 %, 51.5 / 45.8 %, 68.5 / 62.7 %, 68.8 / 62.4 %, 51.0 / 45.0 %, 68.5 / 64.1 %, 70.8 / 65.1 %, 79.4 / 75.7 % (rows in the order of the table).

Reading:

- With the current report known, shuffling the older reports raises the GRU error at h = 15 by 19 to 48 % in all eight set × AoA rows (accuracy 3.7 to 6.4 pp lower). The shuffled GRU gains little or nothing from h = 10 to h = 15, the ordered one keeps gaining. The order of the older reports therefore carries information on the grid, and most of the gain from long windows depends on it.
- The shuffled GRU is better than the best tree at h = 15 in all eight rows (MAE; by only 0.02 m on RMa LOS NE with AoA), so part of the advantage of the GRU does not need order: the set of older reports together with the current one is more useful to it than the raw lags or the window mean are to the trees.
- The CNN loses more from shuffling than the GRU; its convolutions also rely on which positions are neighbours, so its result is a weaker test of order.
- In exact-cell accuracy, the trees match or beat the ordered GRU on the RMa LOS sets (centre with AoA: XGBoost 71.2 % against 68.5 %); the GRU leads in MAE, that is, its wrong predictions are closer. Results for the GRU should be quoted with the metric.
- Caveats: two seeds for the shuffled networks, one architecture of each kind, shuffling applied in training as well.

Decomposition of the GRU gain (framing from the 2026-10-22 meeting: how much of the gain is the extra information in the window and how much is knowing the order). GRU mean error in metres at h = 0, at h = 15 with the older reports shuffled, and at h = 15 ordered; the information part is h = 0 minus shuffled, the order part is shuffled minus ordered.

| Set | AoA | GRU h=0 | shuffled h=15 | ordered h=15 | information part | order part | order share |
|---|---|---|---|---|---|---|---|
| RMa LOS, NE BS | no | 4.49 | 2.96 | 2.48 | 1.53 | 0.48 | 24 % |
| RMa LOS, NE BS | yes | 3.35 | 2.28 | 1.87 | 1.07 | 0.41 | 28 % |
| Mixed, NE BS | no | 5.37 | 2.03 | 1.42 | 3.34 | 0.61 | 15 % |
| Mixed, NE BS | yes | 4.37 | 1.91 | 1.30 | 2.46 | 0.61 | 20 % |
| RMa LOS, centre BS | no | 5.25 | 2.83 | 2.19 | 2.42 | 0.64 | 21 % |
| RMa LOS, centre BS | yes | 2.00 | 1.29 | 1.01 | 0.71 | 0.28 | 28 % |
| Mixed, centre BS | no | 5.74 | 1.84 | 1.24 | 3.90 | 0.60 | 13 % |
| Mixed, centre BS | yes | 1.38 | 0.82 | 0.60 | 0.56 | 0.22 | 28 % |

About 72 to 87 % of the GRU's gain from h = 0 to h = 15 comes from the information in the window without its order, and 13 to 28 % from the order. In practice the order of the reports is always known, so this is an analysis of where the gain comes from, not a deployment scenario. For the paper: one paragraph, no table (decided 2026-10-22).

#### LSTM pilot (2026-10-22)

Mixed set, NE BS, h = 3, 10, 15, two seeds; same width, head and training as the GRU (`grid_history_extended.py --models lstm`; `docs/results_of_record/history_extended/ne_mixed_lstm/`). Exact-cell accuracy / MAE at h = 15: LSTM 69.0 % / 1.40 m without AoA and 69.5 % / 1.26 m with AoA, against GRU (three seeds) 68.5 % / 1.42 m and 68.8 % / 1.30 m. The LSTM equals the GRU within about 1 pp and 0.07 m at every depth; no full runs. In the paper: one sentence.

#### Irregular and incomplete history (2026-10-24)

Question: in practice a history is not a clean, evenly spaced sequence. Does the gain survive missing reports and uneven timing? `src/python/experiments_ablation/grid_history_irregular.py`; mixed set, NE BS, RSS+SINR, current report plus K = 10 older reports; each report carries a "present" flag and its age in steps. Conditions: `mask30` / `mask60` drop each older report with probability 0.3 / 0.6; `gap2` / `gap4` place the 10 older reports at random gaps (geometric, mean 2 / 4 steps); `gap2_noage` hides the age; `mismatch_gap2` trains on regular windows and tests on gap2 windows. Training and test draw their gaps and masks independently. GRU two seeds; 1D-CNN three seeds (architecture and training as in the extended-history runs); XGBoost on the flattened inputs (missing reports as NaN, age as a feature), one run. Files: `docs/results_of_record/history_irregular/ne_mixed/` (GRU, XGBoost) and `ne_mixed_cnn/` (CNN).

| Condition | GRU accuracy / MAE | GRU gain kept | 1D-CNN accuracy / MAE | CNN gain kept | XGBoost accuracy / MAE |
|---|---|---|---|---|---|
| snapshot (no history) | 47.5 % / 5.43 m | — | 19.0 % / 8.44 m | — | 43.7 % / 5.75 m |
| regular | 67.1 % / 1.59 m | 100 % | 53.1 % / 2.49 m | 100 % | 57.3 % / 3.45 m |
| mask30 | 63.9 % / 2.06 m | 88 % | 47.2 % / 3.38 m | 85 % | 52.9 % / 4.07 m |
| mask60 | 58.6 % / 2.99 m | 64 % | 43.9 % / 4.23 m | 71 % | — |
| gap2 | 63.8 % / 1.99 m | 90 % | 49.9 % / 3.01 m | 91 % | 53.4 % / 3.93 m |
| gap4 | 61.4 % / 2.37 m | 80 % | 46.8 % / 3.51 m | 83 % | — |
| gap2 without age | 63.6 % / 2.00 m | 90 % | 48.7 % / 3.11 m | 90 % | — |
| trained regular, tested gap2 | 54.1 % / 2.80 m | 69 % | 36.2 % / 4.81 m | 61 % | — |

Reading:

- History stays useful when it is incomplete or uneven: with 30 % of the older reports missing or with uneven gaps the GRU keeps 80 to 90 % of its gain over the snapshot, and two thirds with 60 % missing.
- The GRU degrades more gracefully than XGBoost (73 to 79 % of its gain kept), and the GRU with imperfect history (about 2.0 m) is still better than XGBoost with perfect history (3.45 m).
- Giving the age of each report does not help here (1.99 against 2.00 m). The gaps follow the same distribution in training and test, so the network does not need them; it may matter when the gap pattern differs between users or over time (not tested).
- A model trained on clean history and tested on irregular history falls to 2.80 m: still far better than no history, but well below training on irregular history. Train with the irregularity expected in use.
- The 1D-CNN behaves the same way: 83 to 91 % of its gain kept with 30 % missing or uneven gaps, the age channel does not help (3.01 against 3.11 m), and the train/test mismatch costs most (4.81 m). Its share figures are inflated by a weak snapshot (8.44 m: a convolution over a single report), so compare it in metres: with uneven gaps it ends about 0.5 m above its regular window, the GRU about 0.4 m. The CNN is not hurt by uneven spacing more than the GRU; it is weaker throughout (regular 2.49 against 1.59 m). The CNN seeds spread more (up to 0.4 m on the regular window).
- Caveats: one set, one placement, no AoA; synthetic geometric gaps.

#### Attention pooling (pilot, 2026-10-24)

GRU and 1D-CNN with attention pooling over time (`gru_attn`, `cnn_attn` in `grid_history_extended.py`) on the irregular-history conditions above (same data, seeds 2 / 3). GRU: no change beyond seed noise in any condition (regular 1.56 against 1.59 m, mask30 2.08 against 2.06 m, gap2 2.01 against 1.99 m). CNN: slightly better on the regular window (2.41 against 2.49 m) and much more robust to the train/test mismatch (3.71 against 4.81 m), but worse with missing or uneven reports (gap2 3.27 against 3.01 m, mask60 4.55 against 4.23 m). Mixed, no substantial gain; one sentence at most in the paper. Files: `docs/results_of_record/history_irregular/ne_mixed_{gru,cnn}_attn/`.

#### Tracking filter on a snapshot model (2026-10-24)

History used through a motion model instead of a learned window. `src/python/experiments_ablation/grid_tracking_filter.py`: a snapshot model (Random Forest or XGBoost on the current report, RSS+SINR) gives a probability per cell; an HMM forward filter combines the previous belief, moved by a transition matrix, with the current probabilities (causal: past reports only). The forward-backward smoother also uses future reports and is an upper bound, not comparable. Transition matrices: `learned` from the training walks (on this grid every step moves to a neighbour: 7.2 successors on average, never stays); `generic2` / `generic4` not learned, a Gaussian kernel over distance with width 2 m / 4 m (stays 18 % / 5 %, about 30 / 70 reachable cells), to test a mismatched motion model. Same missing and irregular conditions as above (the filter skips missing reports and applies the transition once per elapsed step). Mixed set, NE BS, no AoA; mean error in metres (accuracy in brackets for the main rows).

| Condition | RF snapshot | RF + filter, learned | RF + filter, generic2 | RF + filter, generic4 | GRU h = 10 (for comparison) |
|---|---|---|---|---|---|
| regular | 4.93 (52.3 %) | 0.71 (80.9 %) | 0.93 (76.1 %) | 1.58 (70.6 %) | 1.59 (67.1 %) |
| mask30 | 4.90 | 0.98 | 1.16 | 1.88 | 2.06 |
| mask60 | 4.91 | 1.54 | 1.65 | 2.43 | 2.99 |
| gap2 | 4.93 | 1.27 | 1.41 | 2.20 | 1.99 |
| gap4 | 4.88 | 2.11 | 2.21 | 2.88 | 2.37 |

Other rows: XGBoost snapshot 7.34 m, + learned filter 2.27 m, + generic2 2.93 m (XGBoost's snapshot model is weaker here). GRU h = 10 output + filter (regular, one seed): 1.62 → 1.01 m (learned), 1.22 m (generic2), 1.31 m (generic4); Random Forest + filter is better than GRU + filter (0.71 against 1.01 m).

Reading:

- Using history through a motion model on top of a snapshot model is very effective on this grid: with the learned motion model the error falls from 4.93 to 0.71 m, well below the GRU (1.59 m), and it stays below the GRU with missing and irregular reports.
- It does not depend on knowing the exact motion: with a generic kernel that allows stops and jumps the simulated walk never makes, the filter still reaches 0.93 m (2 m kernel); only a very loose 4 m kernel brings it to the level of the GRU (1.58 m).
- Filtering the GRU's output helps the GRU (1.62 → 1.01 m) but does not beat filtering Random Forest; the GRU's probabilities already contain the history, so the filter partly counts it twice.
- Caveats: the walk on this grid is a neighbour-to-neighbour random walk at constant speed, which a motion model suits well; one set, one placement, no AoA; GRU + filter one seed. The test that matters is the macro study, with realistic trajectories (pedestrians, vehicles, waypoint tours) and regression targets (Kalman or particle filter), not yet run.
- For the paper: the claim "history helps" is strengthened (a second, classical way to use it), but the claim that sequence models are the best way to use it does not hold on this grid. Discuss with the instructors before writing section 5.3.

### 6.3 Placement and the AoA gain
At the centre BS the azimuth covers 360° and AoA alone separates neighbouring cells (BASE_A 64 to 77 % in every set). At the NE corner the grid falls within about 52° of azimuth, neighbouring cells are no longer separated by azimuth, and the AoA gain falls to −0.4 to +6 pp; what remains is consistent with elevation, which encodes distance, but it was not isolated on the grid.

### 6.4 25×25 regression across propagation sets (3D MAE m, five pooled device profiles, NE BS, 3.0 GHz)

Regenerated 2026-10-15 to 2026-10-16: Cartesian targets, fixed 4° AoA noise with 5° quantization (the setting of the earlier 25×25 runs and of the macro study), 30 % training subsample, history 3, tuned parameters of section 7.4.3 of the earlier edition (`configs/tuned_params_25x25_regression.json`). Simulations: UMi LOS `sim_data_ne_bs_2026-10-15_09-40-11`, NLOS `2026-10-16_01-32-21`, mixed per-cell `2026-10-16_14-57-54`.

| Experiment | UMi LOS XGBoost / RF | NLOS XGBoost / RF | Mixed per-cell XGBoost / RF |
|---|---|---|---|
| BASE | 29.39 / 14.52 | 33.25 / 29.32 | 29.89 / 24.33 |
| BASE_H3 | 13.72 / 17.06 | 24.51 / 26.61 | 20.46 / 23.19 |
| BASE_H3_dp | 11.95 / 14.93 | 20.46 / 22.13 | 18.61 / 20.51 |
| BASE_A | 12.52 / 8.24 | 18.02 / 15.99 | 16.24 / 13.30 |
| BASE_A_H3 | 8.35 / 9.42 | 12.49 / 13.26 | 11.30 / 12.43 |
| BASE_A_H3_dp | 7.99 / 8.85 | 11.63 / 12.41 | 10.85 / 11.75 |
| BASE_A_H3_dp_INT | 7.19 / 7.53 | 11.17 / 11.78 | 10.23 / 11.37 |

Reading:

- History helps XGBoost in every set (no AoA 15.7 m on UMi LOS, 8.7 m on NLOS, 9.4 m on mixed; with AoA 4.2, 5.1 and 4.7 m for BASE_A to BASE_A_H3_dp). Random Forest degrades with history on UMi LOS (14.52 to 17.06 m) and gains 2.7 m (NLOS) and 1.1 m (mixed) elsewhere. The block-shuffled control gives the same picture (mixed: XGBoost 29.89 to 21.13 m, Random Forest 24.22 to 23.60 m).
- The interference fingerprint (`_INT`) helps in all three sets by 0.4 to 1.3 m. The earlier Random Forest advantage of the hybrid features (UMi LOS 8.14 against 8.85 m) is not present on the mixed set (11.96 against 11.75 m); for XGBoost the absolute features are best in every set.
- The absolute level depends strongly on propagation: under NLOS the no-AoA snapshot error is near the constant guess (BASE 33.25 m XGBoost against 37.3 m); with history it is 24.51 m.
- Spherical targets (the earlier untuned table) are no longer produced by the code; the pipeline predicts Cartesian x, y, z.

#### Longer history, GRU and 1D-CNN (2026-10-20/21)

Same data, split, subsample and AoA noise as above. Trees: `multi_user_pipeline_regression.py` with the new experiments `BASE_H7`, `BASE_H15`, `BASE_A_H7`, `BASE_A_H15` (parameters tuned at h = 3). GRU and 1D-CNN: `regression25_sequence.py` (architectures of the controlled-grid study with a three-output regression head, MSE on standardized targets, epoch chosen on the last 10 % of each user's training rows, 150 epochs at most). Mean 3D error in metres, h = 0 / 3 / 7 / 15, one run each; full table in `docs/results_of_record/regression_25x25_2026_10/sequence_vs_trees/all_mae.md`.

| Set, AoA | XGBoost | RF | GRU | CNN |
|---|---|---|---|---|
| UMi LOS, no | 29.4 / 13.7 / 14.0 / 14.4 | 14.5 / 17.1 / 17.9 / 18.7 | 26.2 / 19.6 / 15.6 / 12.3 | 28.2 / 21.3 / 16.7 / 14.2 |
| UMi LOS, yes | 12.5 / 8.4 / 8.6 / 8.9 | 8.2 / 9.4 / 9.5 / 9.6 | 14.1 / 8.8 / 7.3 / 6.7 | 15.1 / 9.5 / 7.9 / 8.0 |
| NLOS, no | 33.3 / 24.5 / 22.8 / 21.7 | 29.3 / 26.6 / 26.3 / 26.0 | 31.2 / 25.2 / 21.0 / 16.9 | 31.6 / 26.0 / 21.5 / 17.2 |
| NLOS, yes | 18.0 / 12.5 / 11.7 / 11.3 | 16.0 / 13.3 / 12.8 / 12.5 | 17.8 / 11.7 / 9.2 / 8.0 | 18.3 / 11.7 / 10.2 / 8.9 |
| Mixed, no | 29.9 / 20.5 / 19.6 / 19.1 | 24.3 / 23.2 / 23.3 / 23.5 | 28.7 / 23.0 / 19.2 / 16.7 | 29.0 / 23.7 / 19.7 / 17.4 |
| Mixed, yes | 16.2 / 11.3 / 10.9 / 10.8 | 13.3 / 12.4 / 12.3 / 12.2 | 16.7 / 11.3 / 9.5 / 8.7 | 17.0 / 11.7 / 9.9 / 9.5 |

GRU at h = 15 over three seeds (150 epochs): UMi LOS 12.4 / 6.6 m, NLOS 16.7 / 8.0 m, mixed 16.7 / 8.7 m (no AoA / AoA), seed spread at most 0.4 m. With a 400-epoch limit (seed 0): 11.5 / 6.3, 16.8 / 7.7, 16.3 / 8.3 m.

Reading:

- The GRU at h = 15 is best in all six set × AoA combinations, 1.3 to 5.0 m below the best tree at any depth. The same ordering as on the controlled grid: trees plateau, sequence models keep improving.
- Trees: on UMi LOS no tree gains beyond h = 3, and Random Forest is best without history; under NLOS and mixed XGBoost still improves slowly to h = 15 (24.5 to 21.7 m without AoA under NLOS).
- Caveats: tree parameters were tuned at h = 3; the GRU often reached the epoch limit; the CNN and the tree depths beyond 3 are single runs.

#### Error distribution and maps

`error_maps_regression25.py` on per-sample predictions (`multi_user_pipeline_regression.py --save-predictions`); outputs in `docs/results_of_record/error_audit/regression25_{umilos,nlos,mixed}{,_rf}`. Always guessing the mean test position gives 37.3 m. XGBoost with AoA and h = 3: 8.4 / 12.5 / 11.3 m (UMi LOS / NLOS / mixed). Without history and AoA the error exceeds 35 m far from the BS. The device profiles differ: on UMi LOS with AoA and h = 3 one profile has 13.7 m against 6.4 to 7.4 m for the others.

#### Agreement with the earlier folders and the AoA noise model

The earlier folders (2026-06-13, 2.6 GHz) are reproduced when the fixed noise is used: no-AoA numbers to the second decimal on the earlier data (same pipeline code), AoA numbers within 0.1 m on the earlier data and within 0.7 m on the 3.0 GHz UMi LOS data. The first regeneration used the SINR-dependent noise of the controlled-grid pipelines and was 3 to 4 m worse with AoA. A full-training-set run improves Random Forest with AoA by 0.6 to 1.1 m and XGBoost by 0.1 to 0.4 m.

| 3D MAE (m), tuned, 30 % subsample | Earlier folders | Earlier data, fixed 4° noise | New data, fixed 4° noise | New data, SINR-dependent noise |
|---|---|---|---|---|
| XGBoost BASE_A | 12.03 | 12.11 | 12.50 | 16.97 |
| XGBoost BASE_A_H3_dp | 7.96 | 8.01 | 7.97 | 10.67 |
| RF BASE_A | 7.56 | 7.56 | 8.24 | 12.04 |
| RF BASE_A_H3_dp | 8.09 | 8.09 | 8.85 | 12.25 |
| RF hybrid h=1 | 7.51 | 7.51 | 8.14 | 12.30 |

Which noise model a study uses is part of its definition: the 25×25 regression and the macro study use the fixed 4° noise, the 15×15 controlled-grid pipelines the SINR-dependent noise.

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
- The order test uses two seeds and one architecture of each kind, and shuffling is applied in training as well. The first version of the test (2026-10-17) also hid the current report and is superseded.
- The 25×25 regression pools five simulated device profiles (one user each); it is not a single-user experiment.

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
