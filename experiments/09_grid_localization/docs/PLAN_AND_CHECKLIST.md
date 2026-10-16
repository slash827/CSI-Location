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

- [x] 25x25 regression regenerated at 3.0 GHz (simulation finished 22:59, all five pipelines finished 23:21 on 2026-10-15). Results: `results/regression_25x25_2026_10/umilos_30/{untuned,tuned,custom_loss,segment_shuffle,features_test}`, small copies in `docs/results_of_record/regression_25x25_2026_10/umilos_30/`.
  - Simulation: `run_ne_bs_25x25` with `ne_bs_voronoi_25x25_umilos_config.jsonc` (25x25, 4 m, NE BS [116,116,10], interferers [-25,53,10] and [53,-25,10], five device profiles, seeds 100-500, 400 steps per point, UMi LOS for the whole walk = the effective scenario of the 2026-06-13 data, carrier 3.0 GHz), `sim_data_ne_bs_2026-10-15_09-40-11`.
  - Pipelines: `--sinr-dependent-aoa --history 3 --subsample 0.3 --n-jobs 8`, Cartesian targets, tuned runs with the parameters of technical documentation 7.4.3 (`configs/tuned_params_25x25_regression.json`). The June command lines were never recorded, so these flags are the best reading of the documentation.
  - Incident: the machine slept from 09:56 to 18:55 (Modern Standby) while the simulation ran; nothing was lost. The sleep-prevention process (`keep_awake.py`) must be started first after any reboot or new session.
  - The comparison with the June numbers is in section 10.
- [x] Revised technical documentation written: `docs/Project_documentation/technical_documentation_revised.md` (2026-10-16): what changed, the three propagation sets, the 25x25 regeneration and the AoA noise finding, extended history and CNN, the metric audit, limitations, reproduction steps, and a status map of the sections of the old edition. Open: review it, then decide whether to retire the old file (a pointer to the new edition was added at its top)
- [x] `compare_controlled_grid_sets.py`: one table across the propagation sets (`results/controlled_grid_2026_10/comparison_sets.md`, copied to results of record when the runs finish). First reading: history helps in every row (+4.9 to +27.4 pp, +0.96 to +4.29 m, no-AoA); NLOS at 3.0 GHz equals NLOS at 3.5 GHz within about 1 pp (NE XGBoost BASE_H3 25.8 % against 24.6 %), so the carrier change does not matter; the AoA gain depends on placement in every set (centre +10 to +39 pp, NE -0.4 to +6 pp)
- [x] A background job (`finalize.sh`) waits for the driver and the centre history run, builds the comparison table, copies the CSVs and configs into `docs/results_of_record/`, then commits and pushes

### 4.2 Running now

- [ ] Overnight queue started 2026-10-16 00:58 (`results/_logs/overnight.log` lists the steps; the job commits and pushes the small result copies at the end, and writes `ALL DONE` when finished)
  - Track 1, 25x25 regression with the fixed 4-degree AoA noise (the June setting, same as the macro study; no `--sinr-dependent-aoa`, 30 % subsample, same five pipeline variants as before): (a) UMi LOS data of 2026-10-15 (about 30 min), (b) a new simulation with uniform UMi NLOS (`ne_bs_voronoi_25x25_nlos_config`, about 2 h) and its pipelines, (c) a new simulation with per-cell mixed propagation (`ne_bs_voronoi_25x25_mixed_config`, 2-3 h) and its pipelines. Output: `results/regression_25x25_2026_10/{umilos_30_fixednoise, nlos_30_fixednoise, mixed_30_fixednoise}`.
  - Track 2, extended history (h = 0 to 15) and 1D-CNN on the mixed 15x15 set, NE then centre (about 2 h each with contention). Output: `results/history_extended/{ne_mixed, centre_mixed}`.
  - Status 2026-10-16 09:15: the machine went into Modern Standby again at 01:06 and woke at 09:12 (8 hours frozen) although the first sleep-prevention process (`keep_awake.py`, system-required request only) was running. On this Modern Standby machine a system-required request does not stop the idle path; a second process (`keep_awake2.py`, system and display required, screen stays on) was started at 09:15. Finished before the sleep: track 1 step (a) (`umilos_30_fixednoise`, 01:32) and the two full-training tests. In progress: the NLOS 25x25 simulation (about 2/3 of channel generation) and track 2 (NE mixed history run at BASE h=7). Expected finish now about 14:00-16:00 if the machine stays awake. If the machine is unplugged the battery lasts about an hour under this load.
  - Status 2026-10-16 11:30 (on AC, 78 %): extended history on the mixed NE set finished at 10:40 (`results/history_extended/ne_mixed`); the centre run is at BASE_A h=0 (about 1 h left); the NLOS 25x25 simulation has users 5 done (10:28) and 4 in its last step, users 3, 2, 1 to go (each 25-40 min), so about 13:30 for the simulation and about 14:15 for its pipelines; the mixed 25x25 simulation then needs another 2-3 h (about 17:00 to 19:00 with its pipelines). No standby event since 09:12.
  - New result (mixed NE, MAE m, h = 0 / 3 / 15): 1D-CNN BASE 8.34 / 3.86 / 2.49, RF 4.93 / 2.78 / 3.35, XGBoost 7.34 / 3.58 / 3.46; with AoA CNN 6.04 / 2.53 / 1.67, RF 4.25 / 2.62 / 3.15, XGBoost 4.63 / 3.06 / 2.82. On the mixed set the CNN keeps improving with window length and overtakes both tree models from h about 7 (BASE) or h about 3 (AoA); the trees plateau at h about 3 and Random Forest gets worse. On RMa LOS the CNN only caught up with the trees at h=15. Add to revised technical documentation 6.2 and the report when the centre run is in.
  - Full-training-set test (30 % subsample against 100 %): Random Forest improves by 0.6 to 1.1 m with AoA (BASE_A 8.24 to 7.63, hybrid h=1 8.14 to 7.14), XGBoost by 0.1 to 0.4 m, no-AoA numbers unchanged. The subsample is therefore not the cause of the earlier gap, only a small effect; the AoA noise model is.
  - Fixed-noise 25x25 results on the UMi LOS data (`umilos_30_fixednoise`) reproduce the June folders: tuned XGBoost BASE_A_H3_dp 7.99 (June 7.96), RF BASE_A 8.24 (7.56), RF hybrid h=1 8.14 (7.51), INT variants 7.19 and 7.53 (7.37, 7.63), segment-shuffle XGBoost 29.27 to 15.00 (29.77 to 14.80). The custom-loss XGBoost diverges on BASE_A in this run (59.97 m against 12.21 in June): the instability already described in the technical documentation, not a data problem.
  - Expected finish: between 06:00 and 08:00. Morning to-do: read `overnight.log`, build the three-set 25x25 table, add the mixed-set history/CNN rows to the revised technical documentation 6.2, update report Section 8.

(none: all runs have finished)

### 4.3 To do

25x25 regression (new, 2026-10-15)
- [ ] Update technical documentation 7.4 and report Section 8 from the regenerated 25x25 tables (comparison in section 10: the no-AoA and untuned numbers reproduce within about 1 m; the AoA numbers with tuned parameters are 2.6 to 4.5 m worse, and the hybrid-feature advantage for Random Forest disappears)
  - Resolved 2026-10-16: the June runs used the fixed 4-degree AoA noise (no `--sinr-dependent-aoa`). Rerun with it, the June data gives the June numbers (RF BASE_A 7.56, hybrid h=1 7.51, XGBoost BASE_A_H3 8.16) and the new 3.0 GHz data gives 8.24, 8.14 and 8.36. The report should quote the fixed-noise numbers for the 25x25 regression (the same noise model as the macro study) and say that the controlled-grid pipelines use the SINR-dependent noise. Full-training-set runs (`aoa_gap/new_full_train`, `new_fixed_noise_full_train`) are still running; they are optional.
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
- [x] Technical documentation 7.2-7.4 rewritten from the final sets: done in the revised edition (sections 6.1 to 6.4)
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

## 10. 25x25 regression: June against regenerated (3D MAE in metres)

June: simulation 2026-06-13 (2.6 GHz), folders `ne_bs_voronoi_25x25_regression*`. New: simulation 2026-10-15 (3.0 GHz, UMi LOS), same configuration otherwise, `--sinr-dependent-aoa`, 30 % training subsample.

| Run | Model / experiment | June | New |
|---|---|---|---|
| untuned | XGBoost BASE | 26.12 | 26.07 |
| untuned | XGBoost BASE_H3 | 24.93 | 24.55 |
| untuned | XGBoost BASE_A_H3_dp | 17.19 | 16.50 |
| untuned | RF BASE | 15.24 | 15.28 |
| untuned | RF BASE_H3 | 18.06 | 18.08 |
| untuned | RF BASE_A_H3_dp | 13.50 | 13.08 |
| tuned (ab_testing) | XGBoost BASE | 29.24 | 29.39 |
| tuned | XGBoost BASE_H3 | 13.43 | 13.70 |
| tuned | XGBoost BASE_A | 12.03 | 16.97 |
| tuned | XGBoost BASE_A_H3_dp | 7.96 | 10.67 |
| tuned | XGBoost BASE_A_H3_dp_INT | 7.37 | 9.63 |
| tuned | RF BASE | 14.02 | 14.52 |
| tuned | RF BASE_H3 | 16.27 | 17.06 |
| tuned | RF BASE_A | 7.56 | 12.04 |
| tuned | RF BASE_A_H3_dp | 8.09 | 12.25 |
| custom loss | XGBoost BASE_H3 | 15.87 | 16.77 |
| custom loss | XGBoost BASE_A_H3_dp | 12.03 | 12.85 |
| segment shuffle | XGBoost BASE / BASE_H3 | 29.77 / 14.80 | 29.27 / 14.97 |
| segment shuffle | RF BASE / BASE_H3 | 13.81 / 17.34 | 14.73 / 18.32 |
| features | RF BASE_A_H3_dp_HYBRID | 7.64 | 12.47 |
| features | RF BASE_A_H1_dp_HYBRID | 7.51 | 12.30 |

Reading: everything without AoA reproduces within about 1 m, including the main history result (XGBoost 29.4 to 13.7 m, Random Forest worse with history) and the block-shuffled check. Everything with AoA and tuned parameters is 2.6 to 4.5 m worse than June, and the June advantage of the hybrid features for Random Forest (7.5 against 8.1 m) is gone (12.3 against 12.25). The untuned AoA numbers agree (13.1 against 13.5), so the difference sits in the tuned runs or in the AoA noise model used then.

## 11. 25x25 AoA gap test (2026-10-16), 3D MAE m, tuned, 30 % subsample

| Experiment | June folders | June data, fixed 4 deg noise | New data, fixed 4 deg noise | June data, SINR-dependent noise | New data, SINR-dependent noise |
|---|---|---|---|---|---|
| XGBoost BASE | 29.24 | 29.24 | 29.39 | 29.24 | 29.39 |
| XGBoost BASE_A | 12.03 | 12.11 | 12.50 | 16.49 | 16.97 |
| XGBoost BASE_A_H3_dp | 7.96 | 8.01 | 7.97 | 10.99 | 10.67 |
| RF BASE_A | 7.56 | 7.56 | 8.24 | 11.98 | 12.04 |
| RF BASE_A_H3_dp | 8.09 | 8.09 | 8.85 | 12.42 | 12.25 |
| RF hybrid h=1 | 7.51 | 7.51 | 8.14 | 12.39 | 12.30 |

The BASE row reproduces the June folder to the second decimal on the June data (same pipeline code). The AoA rows reproduce only with the fixed noise. The data change (2.6 to 3.0 GHz) costs at most 0.7 m. Raw outputs: `results/regression_25x25_2026_10/aoa_gap/`.

