# Results directory map (controlled-grid studies)

Written 2026-10-13. It records, for the `results/` folders of the 15×15 controlled-grid study and the 25×25 single-user regression runs, which one backs which number in `technical_documentation.md` and the report, how each was produced, and what is missing. `results/` is gitignored, so this file is the only tracked record.

`src/python/utils/results_inventory.py` regenerates the raw inventory (size, dates, the command recorded in each `PIPELINE_REPORT.md`).

## 1. Which folder backs what

How this was established: every number in `technical_documentation.md` §7.2–7.4 was matched against the `results_summary.csv`, `per_user_breakdown.csv` and `per_cell_breakdown.csv` of each folder, and each folder's data was matched against the simulation datasets by sample counts and Voronoi cell counts.

### 15×15, BS at the grid centre

| Folder | What it is | Backs |
|---|---|---|
| `multi_user_voronoi_15x15_optimal` | Full data (450,005 samples), `--sinr-dependent-aoa`, default hyperparameters, simulation `sim_data_multi_user_2026-06-12_12-19-55`. Run 2026-06-12 20:09 with only six experiments (`BASE`, `BASE_H3`, `BASE_H3_dp`, `BASE_A`, `BASE_A_H3`, `BASE_A_H3_dp`). | §7.2.1 headline table, §7.2.2, §7.2.3 per-user, §7.2.4 per-cell, §7.3.1–7.3.3 centre column |
| `multi_user_voronoi_15x15` | The **May 2026 run** (checkpoints 2026-05-11 21:10 to 23:59): 24 experiments per model, full data, Random Forest with tuned parameters loaded from `tuning/tuned_params.json` (150 trees, depth 16, min leaf 5). Its CSVs and report were rewritten on 2026-06-12 14:35 from those checkpoints. | §7.2.5 cross-user, §7.2.6 device-knowledge isolation, §7.3.5 centre column |
| `multi_user_voronoi_15x15_backup_20260509_1741` | Older run (2026-03-25), older experiment names. | Nothing. Archived. |
| `multi_user_voronoi_15x15_opt_noise` | Trial of the SINR-dependent noise on a 30% training subsample. | Nothing. Archived. |

### 15×15, BS beyond the NE corner

| Folder | What it is | Backs |
|---|---|---|
| `ne_bs_voronoi_15x15_optimal` | Same recipe as the centre `_optimal` run, simulation `sim_data_ne_bs_2026-06-12_13-51-50`. | §7.3.1–7.3.3 corner column, §7.3.4 per-cell |
| `ne_bs_voronoi_15x15` | The May run (2026-05-12 08:06 to 10:43), 24 experiments, tuned RF parameters. The log `pipeline_run.log` is the original May log. | §7.3.5 corner column |
| `ne_bs_voronoi_15x15_backup_20260509_1741`, `ne_bs_voronoi_15x15_opt_noise` | As above. | Nothing. Archived. |

`compare_placements.py`, `plot_mae_heatmap.py` and `gen_voronoi_map.py` default to `results/multi_user_voronoi_15x15` and `results/ne_bs_voronoi_15x15`, so those two names stay.

### 25×25 single-user regression (§7.4)

| Folder | Backs |
|---|---|
| `ne_bs_voronoi_25x25_regression` | §7.4.1 untuned table (RF `BASE_A_H3_dp` 13.497 m, XGBoost 17.185 m) |
| `ne_bs_voronoi_25x25_regression_tuned` | RF tuned spherical (10.045 m). The 11.486 m spherical-tuned XGBoost figure quoted in §7.4.3 was **not found in any folder** |
| `ne_bs_voronoi_25x25_regression_ab_testing` | §7.4.3 XGBoost (MSE) and Random Forest Cartesian rows (29.239 → 13.430 m) |
| `ne_bs_voronoi_25x25_regression_cartesian_custom` | §7.4.3 XGBoost (custom loss) rows |
| `ne_bs_voronoi_25x25_regression_segment_shuffle` | §7.4.4 |
| `ne_bs_voronoi_25x25_regression_features_test` | §7.4.5 delta / hybrid feature modes |
| `ne_bs_voronoi_25x25_regression_cartesian`, `test_regression_tuning` | Intermediate and smoke-test runs. Archived. |

Data for these: `grid_25x25/sim_data_ne_bs_2026-06-13_14-54-18`.

### Other folders, not reorganized

`b6_los_blocked_los`, `notebook_experiments` (the Python ablations; summaries are in `docs/results_of_record/`), `grid_localization` (simulation data, read by the code), `experiment_matrix` (Feb–Mar 2026 scalability sweep, §7.1), `placement_comparison` (plots made from the May runs), `early_experiments` (14.9 GB, Nov–Dec 2025), `logs`.

## 2. The simulation datasets are not the same

The three runs that matter use **different simulated data**. Sample counts and Voronoi cell counts identify them; RSS and SINR show the channel differs.

| Dataset | Used by | Cell counts (cells 1–4) | RSS mean / sd (dBm) | SINR mean (dB) |
|---|---|---|---|---|
| `sim_data_multi_user_2026-03-02_19-41-39` | probably the May centre run (inferred) | 156,873 / 51,054 / 41,608 / 200,470 | −34.95 / 4.40 | −2.9 |
| `sim_data_multi_user_2026-06-12_12-19-55` | `multi_user_voronoi_15x15_optimal` | same cell counts | −36.78 / 6.46 | **+7.8** |
| `sim_data_ne_bs_2026-04-11_20-11-48` | the May NE run (confirmed: cell counts match its log) | 62,891 / 296,306 / 14,070 / 76,738 | −44.18 / 4.98 | −3.8 |
| `sim_data_ne_bs_2026-06-12_13-51-50` | `ne_bs_voronoi_15x15_optimal` | **158,646 / 48,716 / 42,159 / 200,484** | −49.39 / 4.32 | −8.3 |

- The centre BS keeps the same walks and cells but the channel changed (mean SINR 10.7 dB higher). The NE walks and cell partition are different, and RSS is 5 dB lower.
- So `BASE` accuracy differs between the May and `_optimal` runs for a reason that has nothing to do with the AoA noise: centre XGBoost `BASE` is 25.7% (May) against 28.6% (`_optimal`), and NE 37.5% against 57.2%.
- **The technical documentation mixes the two.** §7.3.1 (AoA gain at the corner, +2.3 pp) comes from the `_optimal` NE run; §7.3.5 (corner `cross_user_BASE_A_H3` 58.4%) comes from the May NE run, whose AoA is much weaker (`BASE_A` 61.4% against 81.7%). The two are not comparable, and §7.2.1 `BASE_H3` (51.0%) sits beside §7.2.6 `BASE_H3` (48.9%) for the same reason. The documentation says "separate run" for the second but does not say that the data and noise model differ.

## 3. What is not recorded

- **Settings of the 06-12 simulations.** `experiment_info.mat` stores only the config file name, the BS position and the profile table. The config as it stood on 2026-06-12 is not in git: the 15×15 configs were next committed on 2026-07-24, with explicit Voronoi cells and a scenario mapping, and the NE interferer positions changed from `[19,-10], [-10,19]` to `[-11,19], [19,-11]`. The 10.7 dB difference in mean SINR between the two centre simulations is not explained by any committed config change. The report states 3.5 GHz and interferers at `[-11,19,10]`, `[19,-11,10]`; this is what the committed configs say, and no file proves it for the 06-12 data.
- **Settings of the May runs.** The May `PIPELINE_REPORT.md` and `experiment_config.json` were overwritten on 2026-06-12 with the parameters of a different command (`--subsample 0.30`, 198,000 samples). Those values describe the June re-save, not the results. What is known about the May run comes from `ne_bs_voronoi_15x15/pipeline_run.log` (full data, tuned RF parameters loaded, 60 fits planned) and the file dates.
- **AoA noise in the May runs.** The log does not say whether `--sinr-dependent-aoa` was set; `experiment_config.json` names a fixed "4°/5° noise". It was probably off, which would explain the weak NE AoA.

## 4. Two defects to resolve before the controlled grid is cited further

1. **The Voronoi cells probably carry no propagation difference.** `core/generate_simulation_data.m` sets the scenario per segment (lines 415–440) but never splits the track into segments, so by the same reading of the code that `CONTINUE_HERE.md` §3 recorded for the macro-cell campaign, each walk runs under the scenario of its first position. This was read from the code and has not been checked on the 15×15 data. If it holds, the per-cell tables (§7.2.4, §7.3.4) are partitions of a channel that is homogeneous per user, and the explanation in §7.2.4 ("under Rural Macro LOS…") does not apply. The report's controlled-grid text does not make a per-cell propagation claim, so it is not affected.
2. **A single-antenna user gains from AoA that does not exist.** User 3 (one antenna, AoA missing) goes from 50.6% to 60.9% with `BASE_A_H3` in the centre `_optimal` run (+10.3 pp, described in §7.2.3 as a graceful fall-back), from 86.1% to 92.6% at the NE corner, and from 52.5% to 83.7% in the May centre run. A device without AoA should gain nothing from AoA features. The cause was not traced (candidates: NaN filling that changes the feature layout, or AoA computed for all users in the older simulations).

## 5. Gaps and what is being done

| Gap | Action |
|---|---|
| The two `_optimal` runs have **no plots**, no MAE heat maps, no history-depth curve, no cross-user or device-isolation experiments. The pipeline writes plots only for a full run; these runs used `--run-only`. | Both resumed on 2026-10-13 as full runs into the same folders: the 12 existing results are kept from checkpoints, the other experiments and all plots are added. Same data, flags and defaults. Pre-run copies are in `results/_archive/pre_fill_backups/`. |
| Per-grid-point MAE maps (`mae_heatmap_*.csv`) and `data_volume_sweep.csv` exist only for the old runs | Regenerate with `plotting/plot_mae_heatmap.py` and `--data-volume-sweep` after the main runs finish |
| §7.4.3 XGBoost spherical-tuned 11.486 m has no source folder | Re-run or remove the sentence |
| Settings of the 06-12 simulations are not recorded | See §6 |

## 6. Decision for the author

The 06-12 datasets can be kept, with the limits in §3 stated, or the two simulations can be regenerated from the committed configs and the full pipeline re-run, so that every controlled-grid number comes from one dataset and one noise model with a saved config snapshot. The second option costs about two hours of MATLAB plus about five hours of pipeline time per placement, changes the numbers in §7.2–7.3 slightly, and removes the mixing described in §2. It also lets defect 1 above be fixed first, using the per-segment approach from `run_multi_user_300_25x25_mixed.m`.

## 7. Found while regenerating (2026-10-13)

1. **Every run of `core/generate_simulation_data.m` used 2.6 GHz, not the configured carrier.** The generator read `channel.center_frequency` but never passed it to QuaDRiGa, whose default is 2.6 GHz; the MATLAB log of the 2026-06-12 NE run says "1 frequency (2.6 GHz)". This covers the controlled-grid simulations (config 3.5 GHz), the early single-user grid-size sweeps and the 25×25 regression simulation behind §7.4 (config 3.0 GHz). The macro-cell runners (`run_multi_user_300_25x25*.m`, `run_b6_los_blocked_los.m`) set `l.simpar.center_frequency` themselves and were not affected. The report's statement that the controlled grid ran at 3.5 GHz and the sweeps at 3.0 GHz is therefore wrong for every existing simulation of that generator. Fixed in commit `59b6f9f`; the regenerated 15×15 data is at 3.5 GHz.
2. **Per-cell scenarios** never took effect (§4, defect 1). The generator now takes `channel.mixed_scenario.uniform_scenario` (UMi NLOS in both 15×15 configs) and applies it to the whole walk; Voronoi cells stay as labels. Commit `32f5158`.
3. **Provenance is now saved.** Both runners copy the config into the output folder as `data_generation_config.jsonc` and store git commit, carrier frequency, bandwidth, scenario, transmit power and interferer positions in `experiment_info.mat`.

### Regenerated set

Simulations (MATLAB, 2026-10-13): `sim_data_multi_user_2026-10-13_*` and `sim_data_ne_bs_2026-10-13_*` under `results/grid_localization/grid_15x15/`, 3.5 GHz, uniform UMi NLOS, same walk seeds and device profiles as before, config from the repository at commit `a86ae4a`.
Pipeline output, full run with every experiment, plots, per-grid-point MAE maps and the data-volume sweep, `--sinr-dependent-aoa`, default hyperparameters: `results/controlled_grid_2026_10/centre_bs` and `results/controlled_grid_2026_10/ne_bs`.
XGBoost stays on the CPU: on a 200,000-sample 225-class test the GPU fit took 107 s against 148 s on the CPU (with MATLAB running), too small a gain to justify changing the numerics.

### Outcome of the regeneration (finished 2026-10-13, ~05:30–05:45)

Both placements ran the full pipeline (50 result rows each, 17 plots, MAE maps, data-volume sweep). Condensed CSVs and configs are committed in `docs/results_of_record/controlled_grid_2026_10/`. **All controlled-grid numbers changed a lot**, because the old data had line of sight for some users (walk-start scenario) and a different carrier:

| XGBoost accuracy, centre BS | old `_optimal` (06-12 data) | regenerated |
|---|---|---|
| BASE | 28.6 % | 13.8 % |
| BASE_H3 | 51.0 % | 28.2 % |
| BASE_A | 80.2 % | 63.9 % |
| BASE_A_H3 | 82.4 % | 67.5 % |

NE BS, XGBoost: BASE 57.2 % -> 11.3 %, BASE_H3 86.0 % -> 24.7 %, BASE_A 81.7 % -> 23.2 %, BASE_A_H3 88.3 % -> 30.9 %. What survives: history gains in all four model/placement cells (+9.7 to +14.4 pp, -2.5 to -3.2 m), AoA gain much larger at the centre than at the corner (+39 vs +6 pp). What does not: the corner BS no longer helps the no-AoA models, the XGBoost history gain is no longer larger at the corner, the Highway-cell AoA gain, the "all NE cells >= 80 %" statement. User 3 (one antenna, AoA = NaN -> 0) still gains from `BASE_A`; the gain equals the gain from the user id alone, so it is an implicit device indicator (technical_documentation.md §7.2.3). Technical documentation §7.2–7.3, report Section 5 and the sanity tests were updated to the new numbers; the older docs under `docs/archive/plans`, `docs/archive/session_summary` and the Drive snapshots are historical and still quote the old values.

Not regenerated: the 25×25 regression simulation (2.6 GHz), the early single-user grid-size sweeps and the 7×7 depth sweep (report Section 5 depth and scale paragraphs). The §7.4.3 figure 11.486 m has no source.
