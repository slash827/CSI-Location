# Plan and checklist — controlled-grid regeneration and report update

Started 2026-10-13. Branch `followup-2026-10`. This file is the working plan: what the goal is, what runs where, and what is done. Update the checkboxes and the run table as things finish.

## 1. Goal

Make every number in the controlled-grid part of the report (technical documentation §7.2–7.3, report Sections 4–5) come from one coherent set of simulations with a recorded configuration, then finish the extra experiments the meeting asked for (longer history, neural model on the grid) and bring the report text in line.

## 2. What we learned this session (why the plan changed)

- The generator `core/generate_simulation_data.m` never passed the configured carrier to QuaDRiGa, so all 15×15 data ran at 2.6 GHz instead of the configured 3.5 GHz. Fixed (commit `59b6f9f`); configs now say 3.0 GHz like the macro-cell study (`f329ffd`).
- The Voronoi cells never set the propagation: the track has one segment, so each walk ran under the scenario of its first cell. The 2026-06-12 data therefore ran RMa LOS (the generator's default for the highway cell) for every user. Fixed: `uniform_scenario` (whole walk, commit `32f5158`) and `per_cell_segments` (real per-cell scenarios, commit `5affbfe`).
- Uniform NLOS at 3.5 GHz gives much lower accuracy than the June data (centre XGBoost BASE_H3 28.2 % against 51.0 %). RMa LOS at 3.0 GHz gives 48.6 % at the NE BS (June: 86.0 %). The remaining gap to June is unexplained: the June NE data has a within-cell RSS spread of 0.06 dB against 0.19 dB now, and the June NE walks differ from the regenerated ones. The June centre walks are identical to the new ones.
- User 3 (one antenna) gains from AoA features only because NaN is replaced by 0, which marks the device (technical documentation §7.2.3).

## 3. Data sets (all 15×15, 3.0 GHz unless noted)

| Set | Propagation | Config | Simulations | Pipeline output |
|---|---|---|---|---|
| NLOS 3.5 GHz (earlier) | UMi NLOS everywhere | `*_voronoi_15x15_config` at 3.5 GHz | `sim_data_*_2026-10-13_01-02-4x` | `controlled_grid_2026_10/{centre,ne}_bs_nlos35` |
| RMa LOS | RMa LOS everywhere | `*_rmalos_config` | `sim_data_*_2026-10-13_10-43-xx` | `controlled_grid_2026_10/{centre,ne}_bs_rmalos_30` |
| Mixed per-cell | UMi LOS / NLOS by cell | `*_mixed_config` | `sim_data_*_2026-10-13_11-23-xx` | `controlled_grid_2026_10/{centre,ne}_bs_mixed_30` |
| NLOS 3.0 GHz | UMi NLOS everywhere | `*_voronoi_15x15_config` | `sim_data_*_2026-10-13_15-47-xx` | `controlled_grid_2026_10/{centre,ne}_bs_nlos_30` (headline experiments only) |

The driver log is `results/_logs/drive30.log`. Extended history and CNN results go to `results/history_extended/<placement>_<set>`.

## 4. Checklist

### 4.1 Done

- [x] Validate every claim of `REPORT_SKELETON.md` (`REPORT_SKELETON_VALIDATION.md`)
- [x] Follow-up experiments (mechanism, region control, LOS flag, blocked LOS, no-interference, constant-guess baseline); results in `docs/results_of_record/followup_2026_10/`
- [x] Report text corrected in `docs/Transition_History/` (Sections 3, 4, 6–13), compiles to 33 pages
- [x] Provenance map and archive of `results/` (`RESULTS_DIRECTORY_MAP.md`)
- [x] Generator fixes: carrier frequency, uniform scenario, per-cell segments (verified on short walks: NLOS cells 3–7 dB weaker)
- [x] Runners store the config copy, git commit and settings with each simulation
- [x] NLOS 3.5 GHz simulations and full pipelines; technical documentation §7.2–7.3 and report Section 5 rewritten from them (commit `a585ca7`; to be redone from the final set, see 4.3)
- [x] Configs switched to 3.0 GHz; RMa LOS simulations and full pipelines (finished 14:04 / 14:12)
- [x] Mixed per-cell simulations and full pipelines, centre and NE (pipelines finished 21:30 / 21:32)
- [x] `grid_history_extended.py` (h = 0…15 for XGBoost, RF, 1D-CNN) written and smoke-tested
- [x] Extended history and CNN, RMa LOS, NE BS (finished 15:43). Trees stop improving at h≈3 (XGBoost flat, RF worse beyond h=3); the CNN keeps improving up to h=15 without reaching the trees.

- [x] M1/M2 audit, part 1: `tests/test_error_metrics.py` (7 tests: known predictions give known accuracy and MAE; MAE = (1 - accuracy) x mean wrong-cell distance)
- [x] M1/M2 audit, part 2: `error_audit_grid.py` on the RMa LOS NE set, XGBoost. The identity holds exactly (BASE_H3: 48.9 % exact, wrong predictions 6.81 m off, MAE 3.48 m = 0.511 x 6.81). Results in `docs/results_of_record/error_audit/grid_ne_rmalos/`
- [x] M4: equal-weight (per grid point) MAE equals the sample-weighted MAE to within 0.06 m (BASE_H3 3.46 m against 3.48 m; BASE 6.21 against 6.06; BASE_A_H3 2.47 against 2.51)
- [x] M3 (macro): `error_maps_macro.py` writes error distribution, error maps by position, error by range and histogram from the saved per-sample errors (uniform NLOS and mixed). Results in `docs/results_of_record/error_audit/macro_*`
- [x] M7: macro per-user `.mat` files store `grid_point_id`, `x_pos`, `y_pos`, `step_index`, `timestamp_sec`, `speed_ms`, plus a 300-row `user_manifest`; the 15x15 files store the same fields. Answer to Sarit: yes

- [x] Reproduction attempt of the 2026-06-12 data with the committed code (`6c1c02a`) and configs, user 1, seed 100, 2.6 GHz default (finished 00:00). **Not reproducible.**
  - Centre: walk, x/y and the clean AoA values are bit-identical to the June file, but RSS differs (per-cell map correlation 0.51, mean 1.9 dB, sd 4.7 dB) and SINR is uncorrelated (corr -0.14, mean 10 dB lower). So the June RSS/SINR came from settings that are not in the repository at that commit (probably an uncommitted working tree).
  - NE: the walk itself differs (different grid points, positions, angles), so the June NE file was made with a different seed or walk configuration.
  - Determinism holds (the old code and the current code give identical results on the same short walk), so the difference is real, not run-to-run noise.
  - Consequence: the June results cannot be regenerated; say so to the instructors and rely on the documented regenerated sets. The centre no-AoA numbers happen to agree with the RMa LOS regeneration, the NE ones do not.

- [x] `compare_controlled_grid_sets.py`: one table across the propagation sets (`results/controlled_grid_2026_10/comparison_sets.md`, copied to results of record when the runs finish). First reading: history helps in every row (+4.9 to +27.4 pp, +0.96 to +4.29 m, no-AoA); NLOS at 3.0 GHz equals NLOS at 3.5 GHz within about 1 pp (NE XGBoost BASE_H3 25.8 % against 24.6 %), so the carrier change does not matter; the AoA gain depends on placement in every set (centre +10 to +39 pp, NE -0.4 to +6 pp)
- [x] A background job (`finalize.sh`) waits for the driver and the centre history run, builds the comparison table, copies the CSVs and configs into `docs/results_of_record/`, then commits and pushes

### 4.2 Running now

- [ ] 25x25 single-placement regression regenerated at 3.0 GHz (started 2026-10-15 09:40)
  - Status 2026-10-15 22:55: simulation users 5, 4, 3, 2 finished (10:03, 19:23, 19:50, 21:31); user 1 started 21:31 and is in the interference step (expected about 23:15-23:30). The users run one after another in this runner, about 25-100 min each depending on contention. The pipelines (about 3-5 h) start automatically after that; results expected between 03:00 and 04:30.
  - Incident: the machine went into Modern Standby (idle timeout) at 09:56 and stayed asleep until 18:55; the simulation was frozen for about 9 hours (no data lost, it resumed). The earlier sleep-prevention process had been lost at the reboot of 08:58. A new one was started at 18:57 (`keep_awake.py`, holds ES_SYSTEM_REQUIRED). If a long run is started again after a reboot or a new session, start it first.
  - Simulation: `run_ne_bs_25x25` with `ne_bs_voronoi_25x25_umilos_config.jsonc` (same grid 25x25, 4 m, NE BS [116,116,10], interferers [-25,53,10] and [53,-25,10], five device profiles with walk seeds 100 to 500, 400 steps per point; propagation: UMi LOS for the whole walk, which is what the 2026-06-13 data effectively ran because the first cell is UMi LOS; carrier 3.0 GHz instead of 2.6). Output: `results/grid_localization/grid_25x25/sim_data_ne_bs_2026-10-15_09-40-11`, about 1-2 h.
  - Pipelines (driver `drive25.sh`, starts when the simulation ends), all with `--sinr-dependent-aoa --history 3 --subsample 0.3 --n-jobs 8`, Cartesian targets, into `results/regression_25x25_2026_10/umilos_30/`: `untuned` (6 experiments), `tuned` (Optuna parameters of technical documentation 7.4.3 from `configs/tuned_params_25x25_regression.json`, 6 experiments plus `_INT`), `custom_loss` (xgboost_custom), `segment_shuffle` (segment length 5), `features_test` (absolute against hybrid h = 1, 2, 3). About 3-5 h in total.
  - The June folders' exact command lines were never recorded; the settings above are taken from technical documentation 7.4 and the report text. The spherical-target variant of 7.4.1 is no longer in the code (the pipeline predicts Cartesian x, y, z), so the untuned table is the Cartesian one.

### 4.3 To do

25x25 regression (new, 2026-10-15)
- [ ] Compare the regenerated 25x25 tables with technical documentation 7.4 and the report Section 8 numbers (RF `BASE_A_H3_dp` 13.5 m untuned, XGBoost 29.2 to 13.4 m with history, block-shuffled split, hybrid features) and update 7.4 and Section 8 accordingly
- [ ] Decide whether to add the other two 25x25 propagation variants (`ne_bs_voronoi_25x25_nlos_config`, `ne_bs_voronoi_25x25_mixed_config` exist, not run), for symmetry with the 15x15 sweep
- [ ] Section 8 of the report calls the 25x25 regression "single-user"; the data are the five device profiles pooled (one simulated user per profile). Check the wording against the pipeline and fix

Explaining the old results to the instructors (requested 2026-10-13)
- [x] `docs/OLD_VS_REGENERATED_RUNS.md` written (first version, 2026-10-14): which earlier results are reproduced, changed or unaffected, the reproduction result, and the 20-30 m explanation. Update the NLOS 3.0 centre row and the extended-history numbers when the last runs finish
- [ ] Decide which old result sets stay in the report (centre June is reproduced by the RMa 3.0 set for the no-AoA experiments; NE June is not reproduced by anything)

Instructor requests from the 2026-10-12 meeting (section 6; do these before the next meeting)
- [x] M1/M2: audit that MAE and accuracy are computed correctly (done, see 4.1; repeat the decomposition on the final headline set)
  - Synthetic check: known predictions must give known accuracy and MAE (all right = 0 m, all one cell off = 2 m, mixed case = (1 - accuracy) x mean wrong-cell distance). Put it in a test file so it stays checked.
  - Decomposition on a real run: re-train XGBoost on a 15x15 set, save the predictions, and show MAE = (1 - accuracy) x mean error of the wrong predictions, plus the histogram of the error distance. This answers Dudi's "80 % exact cannot give 30 m".
  - Same identity for the macro study (regression: no exact-cell accuracy; show fraction of samples within 5, 10, 20 m instead).
- [ ] M1: write the explanation of the 20-30 m errors (numbers are in; the paragraph and the slide are not)
  - Finding: with multi-antenna devices the macro error is 19.0 m without and 15.4 m with history, against 37.1 m for always guessing the mean training position; only 8 % of samples are within 5 m and 60 % within 20 m. For single-antenna devices the error is 34.7 m against a constant guess of 33.6 m, so they are not localized at all (the map shows error above 50 m at the far corners).
  - So the 20-30 m values are real and consistent with the weak information in one RSS reading at 20-160 m range; they are not a computation error. They cannot be compared with the 15x15 exact-cell accuracies, which are a different task at a different scale.
  - Still to do: put this in the report (Section 6 already has the constant guess) and in the meeting slide, labelled by study.
  - Compare them with the constant guess (35.3 m multi, 38.5 m single antenna): the best models are about 2x better, not near-perfect.
  - Show where the error is: error against range from the BS, against cell, and the position map.
  - State in one paragraph that the left (15x15 classification, 2 m cells) and right (25x25 regression, 4 m cells, 300 users, unseen users) plots are different experiments with different error scales.
- [ ] M3: error maps for the single-user 25x25 regression runs (the macro study is done, see 4.1); 15x15 maps exist
  - The macro per-sample errors are in `diagnostics_2026_10/baseline_uniform_nlos/errors_first_seed.npz`; check whether positions are stored, else re-run one seed with positions saved.
  - Output: a figure for the report plus PNGs for the meeting.
- [ ] M5: comparative figure across all settings tested (accuracy and MAE per setting, one consistent layout), for the meeting and for the report
- [ ] M4: mention the equal-weight check (difference below 0.1 m) in the report or the meeting notes
- [ ] M6: give the 25x25 regression and macro runs the same set of plots and a short README of settings, like the 15x15 sets
- [ ] M10: prepare the slides/notes for the next meeting: old vs new 15x15 numbers and why they differ (section 2), M1-M5


Experiments
- [ ] Extended history and CNN on the mixed set (centre and NE)
- [ ] Compare the four sets in one table: history gain, AoA gain, placement gap, per set and model (script + CSV in `docs/results_of_record/controlled_grid_2026_10/`)
- [ ] Investigate the remaining gap to the June data (within-cell RSS noise, NE walks). Decide whether it matters for the claims or only needs a sentence
- [ ] Decide on regenerating the 25×25 regression simulation and the early single-user sweeps at 3.0 GHz (optional)
- [ ] Find or drop the §7.4.3 figure 11.486 m (no source)
- [ ] Grid-size sweep reported in metres (meeting item)

Documentation
- [ ] Choose the primary controlled-grid set for the report and say which propagation each number comes from
- [ ] Rewrite technical documentation §7.2–7.3 from the final sets (currently NLOS 3.5 GHz)
- [ ] Rewrite report Section 5 (and Section 4 setup text) from the final sets; add the extended-history and CNN results to Section 5 or the mechanism section
- [ ] Update the abstract, discussion and limitations for the new numbers and for the propagation caveat
- [ ] Update `RESULTS_DIRECTORY_MAP.md`, `results_of_record/MANIFEST.md`, `CONTINUE_HERE.md`
- [ ] Update `CLAUDE.md` baselines and `test_results_sanity.py` paths to the primary set (the test now reads `centre_bs_nlos35` / `ne_bs_nlos35`, so it is not skipped; repoint it to the headline set)
- [ ] Regenerate `compare_placements` and MAE heat map figures from the primary set
- [ ] Section 8 "predictions fixed before the experiment": still unverifiable, remove or source it
- [ ] `reference.bib` (citations are undefined), cut the report to about 12 pages, thesis conversion
- [ ] Consortium report, due end of October

Housekeeping
- [ ] Stop the sleep-prevention process when the runs are done
- [ ] Commit results of record, push, merge `followup-2026-10` into `main`
- [ ] Untracked on purpose: `docs/Meeting with Alon 7.10.26.md`, `docs/Transition_History.zip`

## 4.4 Your tasks (author)

These need your decision, your judgement or your presence. Claude's tasks are in 4.3 and wait on the first three.

- [ ] 1. Choose the headline set for the controlled grid in the report (suggestion: mixed per-cell as the headline, RMa LOS and NLOS as the propagation sweep; alternative: RMa LOS, closest to the old centre numbers)
- [ ] 2. Look at the results (section 8 says where everything is) and tell Claude which figures and tables you want in the report and on the meeting slides
- [ ] 3. Approve the archive proposal for the 25x25 folders (section 9). The regeneration of the 25x25 data at 3.0 GHz was decided on 2026-10-15 and is running (4.2)
- [ ] 4. Decide what to do with the claim in Section 8 of the report that the predictions were fixed before the experiment (unverifiable from the repository: keep with a source, or remove)
- [ ] 5. Meeting with the instructors (Dudi, Sarit, Alon): agree on the date; review the slide on the 20-30 m errors (M1), the comparative figure (M5) and `OLD_VS_REGENERATED_RUNS.md` before the meeting (M10)
- [ ] 6. Report length and form: cut to about 12 pages (what goes to the appendix), thesis conversion, and the consortium report due at the end of October
- [ ] 7. Bibliography: supply the references or the Zotero/BibTeX export for `reference.bib` (the citations are undefined)
- [ ] 8. Overleaf: upload the updated `docs/Transition_History/` once Sections 4, 5, abstract and discussion are rewritten (the local copy is ahead of Overleaf)
- [ ] 9. Merge `followup-2026-10` into `main` when you are satisfied (not merged since `d3d48ba`)
- [ ] 10. Stop the sleep-prevention process (a Python process holding the machine awake) if you no longer need long runs

## 5. Decisions needed from the author

1. Which set is the headline for the controlled grid: RMa LOS (closest to the June data), mixed per-cell (the design the config describes), or NLOS (hardest)? Suggested: mixed per-cell as the headline, the others as a propagation sweep.
2. Is the 25×25 regression simulation (2.6 GHz) worth regenerating?

## 6. Instructor meeting 2026-10-12 (Dudi, Sarit, Alon): what was asked

Source: `docs/File-פגישה עם דודי ושרית 12.10.26.srt` (machine transcript; Speaker 2 is the author, Speaker 3 is Dudi, Speaker 1 is probably Sarit, but the diarization mixes voices, so attributions are approximate).

| # | Request | Who | Status |
|---|---|---|---|
| M1 | Explain the 10–30 m errors against 60–80 % exact-cell accuracy. "If it is real, we need to explain why"; "it is the second time we discuss it; Alon could not figure it out; please check, then we meet again" | Sarit, Dudi | Open |
| M2 | Decide: either accept the absolute level and report only the history gain, or check for a fundamental error in the MAE computation | Dudi | Check not done explicitly |
| M3 | Show the distribution of errors and per-cell error maps for the experiments with 20–30 m errors ("this kind of graph, exactly") | Dudi, Sarit | 15×15 maps exist; macro / 25×25 maps missing |
| M4 | Average the error over all grid points, not over random-walk visits | Dudi (then softened: "maybe we need to rely on the random walk, keep it for now") | Low priority; 15×15 test rows per cell range 156–537 |
| M5 | A comparative graph for each kind of setting tested, like the 15×15 bar chart | Author offered, Dudi asked for the error tool instead | Open |
| M6 | Every experiment needs enough plots and detail to present | Author promised | Done for the 15×15 sets, open for 25×25 and macro |
| M7 | Are per-user logs stored (which point, when)? | Sarit | `.mat` files store `grid_point_id`, positions, step, timestamp for the 15×15 data; macro data to confirm |
| M8 | Show both base-station placements (centre and outside) | Alon | Done (centre and NE) |
| M9 | Remark: AoA at the centre BS hides the history gain; H=0 with AoA already gets 20 % | Dudi | Covered by the placement study |
| M10 | Next meeting with the answers | all | Pending M1–M3 |

Cause of the confusion in M1: the slide put the 15×15 classification study (2 m cells, exact-cell accuracy) beside the 25×25 regression study (4 m, no classification), and their numbers were read as one experiment. The 15×15 numbers they saw (80 % accuracy, below 0.5 m) come from the June data, which is superseded (section 2).

## 7. Old against regenerated controlled-grid runs (XGBoost accuracy % / MAE m)

All with `--sinr-dependent-aoa`, history 3, default hyperparameters unless noted. "May run" is the May 2026 run (tuned RF, older simulations `sim_data_*_2026-03-02` and `2026-04-11`); "June" is `*_optimal` (simulations of 2026-06-12).

| Centre BS | BASE | BASE_H3 | BASE_A | BASE_A_H3 |
|---|---|---|---|---|
| May run | 25.7 / 8.56 | 48.9 / 4.64 | 81.7 / 0.45 | 83.2 / 0.40 |
| June | 28.6 / 8.66 | 51.0 / 4.86 | 80.2 / 1.16 | 82.4 / 0.85 |
| RMa LOS, 3.0 GHz | 33.5 / 6.84 | 50.6 / 3.79 | 68.3 / 1.72 | 71.6 / 1.35 |
| Mixed per-cell, 3.0 GHz | 31.7 / 8.06 | 59.1 / 3.77 | 75.5 / 1.43 | 78.6 / 1.00 |
| NLOS, 3.5 GHz | 13.8 / 10.40 | 28.2 / 7.24 | 63.9 / 1.97 | 67.5 / 1.37 |

| NE BS | BASE | BASE_H3 | BASE_A | BASE_A_H3 |
|---|---|---|---|---|
| May run | 37.5 / 6.28 | 60.9 / 2.93 | 61.4 / 2.05 | 68.4 / 1.32 |
| June | 57.2 / 5.34 | 86.0 / 1.37 | 81.7 / 1.80 | 88.3 / 0.94 |
| RMa LOS, 3.0 GHz | 31.4 / 6.03 | 48.6 / 3.48 | 46.0 / 3.39 | 52.6 / 2.51 |
| Mixed per-cell, 3.0 GHz | 31.6 / 7.37 | 57.3 / 3.55 | 49.6 / 4.61 | 58.4 / 3.06 |
| NLOS, 3.5 GHz | 11.3 / 10.49 | 24.6 / 7.42 | 23.2 / 6.74 | 30.9 / 4.86 |

Reading: at the centre BS the no-AoA results of the old runs are reproduced by the RMa LOS regeneration (BASE_H3 51.0 against 50.6), the AoA results are lower (BASE_A_H3 82.4 against 71.6). At the NE BS the June run is an outlier even against the May run (BASE_H3 86.0 against 60.9); no regeneration comes near it. The settings that differ between June and the regeneration are: carrier 2.6 against 3.0 GHz; cell layout (June: `auto_generate` with seed 42 and area types; now explicit cells); scenario (June: the first auto cell, RMa LOS; now uniform or per cell); NE interferers ([19,-10] and [-10,19] in June, [-11,19] and [19,-11] now); the NE walks (differ between the June data and every regeneration).

## 8. Where the results are

Everything local is under `C:\Git\CSI-Locationesults` (gitignored); the small committed copies are in `docs/results_of_record/`.

| What | Local folder |
|---|---|
| Controlled-grid pipelines (plots, MAE maps, CSVs, sweeps) | `results/controlled_grid_2026_10/{centre,ne}_bs_{rmalos_30,mixed_30,nlos_30,nlos35}` (plots in `images/`, tables in `csvs/`, `PIPELINE_REPORT.md`) |
| Table across the propagation sets | `results/controlled_grid_2026_10/comparison_sets.md` and `.csv` |
| Extended history and 1D-CNN | `results/history_extended/{ne,centre}_rmalos/history_extended_summary.csv` |
| Metric audit and error maps | `results/error_audit/` (`grid_ne_rmalos`, `macro_uniform_nlos`, `macro_mixed_propagation`) |
| 15x15 simulations (data) | `results/grid_localization/grid_15x15/sim_data_*_2026-10-13_*` (each with `data_generation_config.jsonc`) |
| Macro-cell and follow-up analyses (Python ablations) | `results/notebook_experiments/multi_user_poc/` (summaries in `docs/results_of_record/`) |
| Older controlled-grid runs | `results/multi_user_voronoi_15x15*`, `results/ne_bs_voronoi_15x15*` (June and May), see `RESULTS_DIRECTORY_MAP.md` |
| Logs of the regeneration | `results/_logs/` (`drive30.log`) |

## 9. The 25x25 folders

| Folder | What it is | Used by | Proposal |
|---|---|---|---|
| `ne_bs_voronoi_25x25_regression` | Single user, spherical regression, untuned, data `sim_data_ne_bs_2026-06-13_14-54-18` (2.6 GHz) | Report Section 8 via technical documentation §7.4.1 | Keep |
| `..._regression_tuned` | RF tuned spherical | §7.4.2/7.4.3 | Keep |
| `..._regression_ab_testing`, `..._regression_cartesian_custom` | Cartesian targets, XGBoost with MSE and custom loss | Report Section 8 (§7.4.3: XGBoost 29.239 to 13.430 m) | Keep |
| `..._regression_segment_shuffle` | Block-shuffled split, the leakage check | Report Section 8 (§7.4.4) | Keep |
| `..._regression_features_test` | Delta and hybrid feature modes | Report Section 8 (§7.4.5) | Keep |
| `..._regression_cartesian`, `test_regression_tuning` | Intermediate and smoke tests | Nothing | Already in `_archive/superseded` |

So none of the six remaining 25x25 folders is obsolete: the report cites all of them. To reduce clutter without breaking the references they could be moved under one parent folder (for example `results/single_user_25x25_regression/`) with a README, and the folder names in the documents updated; propose this only if you want it.

No new 25x25 simulation has been made since 2026-09-18 (the 300-user mixed simulation). The 2026-10-07 to 2026-10-12 follow-up experiments (uniform NLOS, mixed propagation, angle error models, neural models, history depth, no-interference, naive baseline) ran on the existing 300-user macro data (`sim_data_300users_2026-07-25_11-46-11` and `..._mixed_2026-09-18_20-25-01`) and their outputs are in `results/notebook_experiments/multi_user_poc/`. The 25x25 regression data of the existing folders is still the 2.6 GHz simulation from 2026-06-13; a 3.0 GHz regeneration was started on 2026-10-15 (section 4.2).

