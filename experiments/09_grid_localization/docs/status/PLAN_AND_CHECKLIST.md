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

- [x] Attention pilot (GRU, CNN) on the irregular-history conditions and HMM tracking filter on snapshot models, with learned and generic motion models and on top of the GRU (2026-10-24; tech doc 6.2; claim map C9). Attention: no substantial gain. Filter: Random Forest + filter 0.71 m (learned) / 0.93 m (generic 2 m) against GRU 1.59 m on the mixed grid; changes the sequence-model claim (C3); macro-study version (Kalman / particle filter) not run. To discuss with the instructors

- [x] Irregular and incomplete history on the 15x15 mixed grid, NE BS, RSS+SINR (2026-10-24; `grid_history_irregular.py`; tech doc 6.2; claim map C8): GRU keeps 80-90 % of its history gain with 30 % of reports missing or uneven gaps, 64 % with 60 % missing; age of reports does not help; training on clean and testing on irregular history costs about 0.8 m. To show Dudi before deciding whether it goes in the paper. 1D-CNN (three seeds, finished 09:53): same pattern, 83-91 % of its gain kept, mismatch costs most (4.81 m against 2.49 m regular)

- [x] LSTM pilot, 15x15 mixed, NE BS, h = 3, 10, 15, two seeds (2026-10-22), `results_of_record/history_extended/ne_mixed_lstm`. Accuracy / MAE at h = 15: LSTM 69.0 % / 1.40 m without AoA and 69.5 % / 1.26 m with AoA, against GRU (3 seeds) 68.5 % / 1.42 m and 68.8 % / 1.30 m. The LSTM equals the GRU within about 1 pp and 0.05 m; not worth a full run on its own.

- [x] GRU and 1D-CNN on the 25x25 regression against trees at h = 0, 3, 7, 15, three sets, one run each (2026-10-20), `docs/results_of_record/regression_25x25_2026_10/sequence_vs_trees/all_mae.md`. Reading: the GRU at h = 15 has the lowest error in all six set x AoA combinations (no AoA 12.3 / 16.9 / 16.7 m against the best tree 13.7 / 21.7 / 19.1 m; with AoA 6.7 / 8.0 / 8.7 m against 8.2 / 11.3 / 10.8 m, UMi LOS / NLOS / mixed); trees plateau after h = 3 on UMi LOS (RF best without history) and improve slowly to h = 15 under NLOS and mixed. Caveats: one seed, the GRU often hit the 150-epoch cap, trees use parameters tuned at h = 3.

- [x] Validate every claim of `REPORT_SKELETON.md` (`REPORT_SKELETON_VALIDATION.md`)
- [x] Follow-up experiments (mechanism, region control, LOS flag, blocked LOS, no-interference, constant-guess baseline); results in `docs/results_of_record/followup_2026_10/`
- [x] Report text corrected in `docs/paper/Transition_History/` (Sections 3, 4, 6–13), compiles to 33 pages
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
- [x] Revised technical documentation written: `docs/technical/Project_documentation/technical_documentation_revised.md` (2026-10-16): what changed, the three propagation sets, the 25x25 regeneration and the AoA noise finding, extended history and CNN, the metric audit, limitations, reproduction steps, and a status map of the sections of the old edition. Open: review it, then decide whether to retire the old file (a pointer to the new edition was added at its top)
- [x] `compare_controlled_grid_sets.py`: one table across the propagation sets (`results/controlled_grid_2026_10/comparison_sets.md`, copied to results of record when the runs finish). First reading: history helps in every row (+4.9 to +27.4 pp, +0.96 to +4.29 m, no-AoA); NLOS at 3.0 GHz equals NLOS at 3.5 GHz within about 1 pp (NE XGBoost BASE_H3 25.8 % against 24.6 %), so the carrier change does not matter; the AoA gain depends on placement in every set (centre +10 to +39 pp, NE -0.4 to +6 pp)
- [x] A background job (`finalize.sh`) waits for the driver and the centre history run, builds the comparison table, copies the CSVs and configs into `docs/results_of_record/`, then commits and pushes
- [x] Why do the trees plateau (and Random Forest degrade) beyond h about 3 while the CNN keeps improving? Tests finished 2026-10-16 19:44 (`results/history_extended/*_wmgru`); the averaging hypothesis is rejected and an information (order) account remains, see section 12.4
  - Test 1, window-mean trees (`xgboost_wm`, `rf_wm`): only the current report and the window mean of each channel are given, for h = 0 to 15. If the plateau comes from the trees being unable to form an average of the lags, these must keep improving with h.
  - Test 2, a GRU (3 seeds, same protocol as the CNN) added to the grid study as requested, so the neural family is CNN and GRU.
  - Both are queued for the four sets (RMa LOS and mixed, NE and centre); about 3-5 h under the present load.
- [x] Extended history and CNN on the mixed 15x15 set finished (NE 10:40, centre 12:18). Same pattern as RMa LOS, stronger: the CNN overtakes the trees (section 12 and the 11:30 note below)
- [x] Overnight queue (started 2026-10-16 00:58, interrupted by two standby periods, finished 20:11 and committed `f4bbbaf`): 25x25 regression with fixed AoA noise on UMi LOS, uniform NLOS and mixed per-cell data; extended history and CNN on the mixed 15x15 set. Results in `results/regression_25x25_2026_10/*_fixednoise` and `results/history_extended/{ne,centre}_mixed`; small copies in `docs/results_of_record/`. Three-set 25x25 table in section 13.
- [x] Order test finished 2026-10-17 10:58 (about 20 min per set): ordering carries the information, see section 14
- [x] Add section 12.4 (the table and the reading) to the revised technical documentation 6.2 and to the report's mechanism section as a hypothesis with its evidence, after the order test (done 2026-10-17: revised technical documentation 6.2 and report Section 5)
- [x] Update technical documentation 7.4 and report Section 8 from the regenerated 25x25 tables (comparison in section 10: the no-AoA and untuned numbers reproduce within about 1 m; the AoA numbers with tuned parameters are 2.6 to 4.5 m worse, and the hybrid-feature advantage for Random Forest disappears) (done 2026-10-17: revised technical documentation 6.4 and report Section 8)
  - Resolved 2026-10-16: the June runs used the fixed 4-degree AoA noise (no `--sinr-dependent-aoa`). Rerun with it, the June data gives the June numbers (RF BASE_A 7.56, hybrid h=1 7.51, XGBoost BASE_A_H3 8.16) and the new 3.0 GHz data gives 8.24, 8.14 and 8.36. The report should quote the fixed-noise numbers for the 25x25 regression (the same noise model as the macro study) and say that the controlled-grid pipelines use the SINR-dependent noise. Full-training-set runs (`aoa_gap/new_full_train`, `new_fixed_noise_full_train`) are still running; they are optional.
- [x] Decide whether to add the other two 25x25 propagation variants (`ne_bs_voronoi_25x25_nlos_config`, `ne_bs_voronoi_25x25_mixed_config` exist, not run), for symmetry with the 15x15 sweep (decided and run 2026-10-16)
- [x] Section 8 of the report calls the 25x25 regression "single-user"; the data are the five device profiles pooled (one simulated user per profile). Check the wording against the pipeline and fix (fixed 2026-10-17)
- [x] `docs/status/OLD_VS_REGENERATED_RUNS.md` written (first version, 2026-10-14): which earlier results are reproduced, changed or unaffected, the reproduction result, and the 20-30 m explanation. Update the NLOS 3.0 centre row and the extended-history numbers when the last runs finish
- [x] M1/M2: audit that MAE and accuracy are computed correctly (done, see 4.1; repeat the decomposition on the final headline set)
  - Synthetic check: known predictions must give known accuracy and MAE (all right = 0 m, all one cell off = 2 m, mixed case = (1 - accuracy) x mean wrong-cell distance). Put it in a test file so it stays checked.
  - Decomposition on a real run: re-train XGBoost on a 15x15 set, save the predictions, and show MAE = (1 - accuracy) x mean error of the wrong predictions, plus the histogram of the error distance. This answers Dudi's "80 % exact cannot give 30 m".
  - Same identity for the macro study (regression: no exact-cell accuracy; show fraction of samples within 5, 10, 20 m instead).
- [x] Extended history and CNN on the mixed set (centre and NE) (done 2026-10-16)
- [x] Compare the four sets in one table: history gain, AoA gain, placement gap, per set and model (script + CSV in `docs/results_of_record/controlled_grid_2026_10/`) (done: `comparison_sets.md`)
- [x] Decide on regenerating the 25×25 regression simulation and the early single-user sweeps at 3.0 GHz (optional) (decided and done 2026-10-15/16)
- [x] Find or drop the §7.4.3 figure 11.486 m (no source) (dropped: the figure is not in the revised documentation or the report)
- [x] Technical documentation 7.2-7.4 rewritten from the final sets: done in the revised edition (sections 6.1 to 6.4)
- [x] Rewrite report Section 5 (and Section 4 setup text) from the final sets; add the extended-history and CNN results to Section 5 or the mechanism section (done 2026-10-17, marked DRAFT until the headline set is chosen)
- [x] Abstract, discussion and conclusion extended with the grid sequence finding (2026-10-17)

### 4.2 Running now

- Nothing is running (LSTM pilot finished 2026-10-22 12:24).

### 4.3 To do

From the 2026-10-22 meeting (section 6b):
- [ ] N2/N2a: tell Dudi the real antenna setup (single omni BS, UE with 1/2/4 omni elements, AoA from QuaDRiGa cluster angles plus synthetic noise, no array processing) and ask whether his plausibility check still holds; verify the UE element spacing in QuaDRiGa (replicated omni elements)
- [ ] N2: get the papers Kimi listed (single-BS accuracy around 1 m in labs or with several BSs; channel charting) for related work
- [ ] N3: abstract, introduction and conclusion lead with "history helps consistently across settings and models; a paradigm of using transitions rather than the current step only"; absolute accuracy only as context (N1)
- [ ] N4: shorten the tree-model material in the paper; keep it as the consistency evidence
- [ ] N9: answer Alon on the corner-BS history gain (with AoA +8.8 against +3.1 pp)
- [ ] N10: send Alon the Voronoi-defect explanation and the list of propagation settings
- [ ] N11: antenna counts to Dudi; footnote in report Section 4
- [ ] Define the propagation settings (RMa LOS, UMi LOS/NLOS, mixed per-cell) where they first appear in report Section 4 (both instructors asked what "LOS"/"NLOS" scenarios are)
- [ ] N6: paper version of the order decomposition: one paragraph, no table
- [ ] N12: Alon looks into venues; follow up

- [x] (done 2026-10-22; result: GRU error at h = 15 +19 to 48 % when the older reports are shuffled, all eight rows) After the fair order test: correct the order claim in report Sections 0 (abstract), 5, 11, 12, 13, revised technical documentation 6.2 and claims list, `docs/Personal/MY_STUDY_GUIDE.md` (Parts 1, 2 step 4, 3, 4), and tell Alon the corrected result


Explaining the old results to the instructors (requested 2026-10-13)
- [ ] Decide which old result sets stay in the report (centre June is reproduced by the RMa 3.0 set for the no-AoA experiments; NE June is not reproduced by anything)

Instructor requests from the 2026-10-12 meeting (section 6; do these before the next meeting)
- [ ] M1: write the explanation of the 20-30 m errors (numbers are in; the paragraph and the slide are not)
  - Finding: with multi-antenna devices the macro error is 19.0 m without and 15.4 m with history, against 37.1 m for always guessing the mean training position; only 8 % of samples are within 5 m and 60 % within 20 m. For single-antenna devices the error is 34.7 m against a constant guess of 33.6 m, so they are not localized at all (the map shows error above 50 m at the far corners).
  - So the 20-30 m values are real and consistent with the weak information in one RSS reading at 20-160 m range; they are not a computation error. They cannot be compared with the 15x15 exact-cell accuracies, which are a different task at a different scale.
  - Still to do: put this in the report (Section 6 already has the constant guess) and in the meeting slide, labelled by study.
  - Compare them with the constant guess (35.3 m multi, 38.5 m single antenna): the best models are about 2x better, not near-perfect.
  - Show where the error is: error against range from the BS, against cell, and the position map.
  - State in one paragraph that the left (15x15 classification, 2 m cells) and right (25x25 regression, 4 m cells, 300 users, unseen users) plots are different experiments with different error scales.
- [x] M3 (25x25 part, done 2026-10-20): error maps and distributions for the 25x25 regression runs (five pooled device profiles), `docs/results_of_record/error_audit/regression25_{umilos,nlos,mixed}{,_rf}` (script `error_maps_regression25.py`, predictions re-run with the new `--save-predictions` flag). Reading: with history and AoA the mean error is 8.4 / 12.5 / 11.3 m (UMi LOS / NLOS / mixed, XGBoost) against 37.3 m for always guessing the mean position; without history the maps show errors above 35 m far from the BS and a clear difference between device profiles (user 3 worst).
  - The macro per-sample errors are in `diagnostics_2026_10/baseline_uniform_nlos/errors_first_seed.npz`; check whether positions are stored, else re-run one seed with positions saved.
  - Output: a figure for the report plus PNGs for the meeting.
- [ ] M5: comparative figure across all settings tested (the report now has `fig_controlled_grid_sets` for the grid; one figure across grid, 25x25 and macro is still to do) (accuracy and MAE per setting, one consistent layout), for the meeting and for the report
- [ ] M4: mention the equal-weight check (difference below 0.1 m) in the report or the meeting notes
- [ ] M6: give the 25x25 regression and macro runs the same set of plots and a short README of settings, like the 15x15 sets
- [ ] M10: prepare the slides/notes for the next meeting: old vs new 15x15 numbers and why they differ (section 2), M1-M5

Experiments
- [ ] Investigate the remaining gap to the June data (within-cell RSS noise, NE walks). Decide whether it matters for the claims or only needs a sentence
- [ ] Grid-size sweep reported in metres (meeting item)

Documentation
- [ ] Choose the primary controlled-grid set for the report and say which propagation each number comes from (your task 1; Section 5 is a DRAFT until then)
- [ ] Update report Section 12 (limitations) for the grid sequence finding, the propagation dependence of the absolute numbers and the fixed against SINR-dependent AoA noise
- [ ] Update `RESULTS_DIRECTORY_MAP.md`, `results_of_record/MANIFEST.md`, `CONTINUE_HERE.md`
- [x] Update `CLAUDE.md` baselines and `test_results_sanity.py` paths to the primary set (the test now reads `centre_bs_nlos35` / `ne_bs_nlos35`, so it is not skipped; repoint it to the headline set) (done 2026-10-22: mixed per-cell chosen; Section 5 DRAFT mark removed, CLAUDE.md baselines and test_results_sanity.py moved to the mixed set, 84 tests pass)
- [ ] Regenerate `compare_placements` and MAE heat map figures from the primary set
- [ ] Section 8 "predictions fixed before the experiment": still unverifiable, remove or source it
- [ ] `reference.bib` (citations are undefined), cut the report to about 12 pages, thesis conversion
- [ ] Consortium report, due end of October

Housekeeping
- [ ] Stop the sleep-prevention process when the runs are done
- [ ] Commit results of record, push, merge `followup-2026-10` into `main`
- [ ] Untracked on purpose: `docs/Personal/` (meeting notes and transcripts, study guide, slides, zip; ignored via `.git/info/exclude`)


## 4.4 Your tasks (author)

These need your decision, your judgement or your presence. Claude's tasks are in 4.3 and wait on the first three.

- [x] 1. Choose the headline set for the controlled grid in the report (suggestion: mixed per-cell as the headline, RMa LOS and NLOS as the propagation sweep; alternative: RMa LOS, closest to the old centre numbers) (done 2026-10-22: mixed per-cell chosen; Section 5 DRAFT mark removed, CLAUDE.md baselines and test_results_sanity.py moved to the mixed set, 84 tests pass)
- [ ] 2. Look at the results (section 8 says where everything is) and tell Claude which figures and tables you want in the report and on the meeting slides
- [ ] 3. Approve the archive proposal for the 25x25 folders (section 9). The regeneration of the 25x25 data at 3.0 GHz was decided on 2026-10-15 and is running (4.2)
- [ ] 4. Decide what to do with the claim in Section 8 of the report that the predictions were fixed before the experiment (unverifiable from the repository: keep with a source, or remove)
- [ ] 5. Meeting with the instructors (Dudi, Sarit, Alon): agree on the date; review the slide on the 20-30 m errors (M1), the comparative figure (M5) and `OLD_VS_REGENERATED_RUNS.md` before the meeting (M10)
- [ ] 6. Report length and form: cut to about 12 pages (what goes to the appendix), thesis conversion, and the consortium report due at the end of October
- [ ] 7. Bibliography: supply the references or the Zotero/BibTeX export for `reference.bib` (the citations are undefined)
- [ ] 8. Overleaf: upload the updated `docs/paper/Transition_History/` once Sections 4, 5, abstract and discussion are rewritten (the local copy is ahead of Overleaf)
- [ ] 9. Merge `followup-2026-10` into `main` when you are satisfied (not merged since `d3d48ba`)
- [ ] 10. Stop the sleep-prevention process (a Python process holding the machine awake) if you no longer need long runs

## 5. Decisions needed from the author

1. (Decided 2026-10-22: mixed per-cell.) Which set is the headline for the controlled grid: RMa LOS (closest to the June data), mixed per-cell (the design the config describes), or NLOS (hardest)? Suggested: mixed per-cell as the headline, the others as a propagation sweep.
2. Is the 25×25 regression simulation (2.6 GHz) worth regenerating?

## 6. Instructor meeting 2026-10-12 (Dudi, Sarit, Alon): what was asked

Source: `docs/Personal/meetings/meeting_with_instructors_12.10.26.srt` (machine transcript; Speaker 2 is the author, Speaker 3 is Dudi, Speaker 1 is probably Sarit, but the diarization mixes voices, so attributions are approximate).

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

## 6b. Instructor meeting 2026-10-22 (Dudi, Alon; Sarit briefly): what was said and decided

Source: `docs/Personal/meetings/meeting_with_instructors_22.10.26.srt` (first transcript, Hebrew model, poor) and the English re-transcription `meeting in english 22.10.26.srt` (author's Documents folder) (ggml-large-v3-turbo, language en, temperature 0; much better; both local only). Speaker 1 is Alon (addressed by name at 22:36), Speaker 2 the author, Speaker 3 Dudi (leaves for his bus at 50:05). The presentation was the deck "Transition History: Progress Since 12.10" (artifact; `docs/Personal/Transition History Progress Since 12.10.pptx`), shown without its last slide.

| # | Point (time) | Who | Decision / action |
|---|---|---|---|
| N1 | "Give up on trying to improve the absolute accuracy or MAE and just stick with the improvement" (14:30); the consultant Isaac wants about 1 m (15:03) | Dudi | Paper framed on the gain from history, not on absolute accuracy |
| N2 | Checked with Kimi during the meeting: with one BS and a 2×2 antenna array, the MAEs we get "make sense" at 3 GHz on a 15×15 field; papers with about 1 m use a lab setup or several BSs; channel charting is more accurate than our approach, so our numbers are plausible. "Please check that this is the case": the 2×2 configuration was his assumption (36:43–39:00) | Dudi | Validate the antenna configuration (N2a below) and report back; collect the papers Kimi listed for the related-work section |
| N2a | Our actual configuration: serving and interfering BSs are a single omni antenna (`qd_arrayant('omni')`), the UE has 1, 2 or 4 omni elements by device profile (`rx_array.no_elements`), and the AoA is QuaDRiGa's power-weighted cluster arrival angle with synthetic noise and 5° quantization, not an estimate from an antenna array (`generate_simulation_data.m`, lines 385–420 and 626–650). This is not a 2×2 array | author (to verify) | Tell Dudi; his plausibility argument assumed an array, so it has to be redone with the real setup |
| N3 | The message: history helps consistently across settings, scenarios and models; "a paradigm change": use history and transitions rather than channel charting or positioning from the current step only; not about the best method or a specific accuracy (39:06–41:04) | Dudi | Lead abstract, introduction and conclusion with this framing |
| N4 | "Why did we talk half an hour on the trees if the GRU is better?" (35:13); answered by himself: to show the gain is consistent across models | Dudi | In the paper, use the tree results as evidence of consistency, not as the main line; keep the trees section short |
| N5 | History beyond 15: asked by the author; "I don't think this is where you should focus"; Alon agrees: "it's now a question of shaping and framing [the points] properly and showing which data supports which claims" (48:45–49:20) | Dudi, Alon | Dropped |
| N6 | Order test: "in real life you get the history of the transitions; why invent something that makes things worse?" Alon: a hypothesis test (order against mere existence of the reports), but "I don't know how much it adds". Dudi: the table breaks the gain into what comes from the order and what from having the history (41:05–45:22) | Dudi, Alon | Decomposition in technical documentation 6.2 (done); one paragraph in the paper |
| N7 | LSTM: "the interesting thing is to explain why despite being different methods they produce the same"; then "you need focus... you want to send a paper; think where your time is most valuable" (46:51–48:37) | Dudi | One sentence in the paper (done in report Section 5); no more work |
| N8 | Someone may argue AoA gives a big help without history; answer: AoA is not available to single-antenna devices (22:38) | Alon | Use as a framing argument: history matters most where no angle is available |
| N9 | "When the BS is in the corner the general results are worse but the improvement [from history] is better" (26:15); not answered in the meeting | Alon | Check and answer: with AoA, history adds +8.8 pp at the corner against +3.1 pp at the centre (XGBoost, mixed); without AoA the gain is similar (+25.7 against +27.4 pp) |
| N10 | Explain the Voronoi defect: "we just had one big cell instead of several?"; which scenarios are used (04:20–05:40) | Alon | Send a short explanation: every walk used the scenario of its first cell for the whole walk (one track segment); now one segment per run inside a cell. List the three sets |
| N11 | How many antennas does a UE have? (author unsure, said 3 or 4) | Dudi | Profiles U1 4, U2 2, U3 1, U4 4, U5 2 (U3 single-antenna, which explains its larger 25×25 error with AoA); footnote in the report |
| N12 | Venues: Dudi does not know venues in this area; Alon to look into venues; "we need to finish / wrap it up" (50:29–51:58) | Alon, Dudi | Alon looks into venues; author starts shaping the paper |
| N13 | "Very nice that you are very insisting on checking everything, I really appreciate it" (51:44) | Dudi | — |

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

## 12. Why trees plateau with longer history while the CNN does not (theory and tests)

Observation (RMa LOS and mixed, both placements): XGBoost takes nearly all of its history gain by h = 1 to 3 and is flat afterwards; Random Forest is best at h = 3 to 5 and gets worse by h = 15 (mixed NE: 2.78 m at h=3, 3.35 m at h=15); the 1D-CNN keeps improving up to h = 15 and on the mixed set ends below both trees (2.49 m against 3.35 and 3.46 m). Earlier macro runs (CNN, GRU against trees) showed the same ordering.

What is known about the data: the walker stays on each cell for 400 consecutive reports, so a window of up to 16 reports almost always comes from one position; the simulated AoA error is independent between reports. Averaging N reports of one position should therefore keep reducing the error like 1/sqrt(N).

Hypotheses:
1. No averaging operator in a tree. A split looks at one feature, so a tree cannot form the mean (or any weighted sum) of several noisy lags; it can only approximate it by a staircase of axis-aligned splits, and that approximation does not get better with more lags. A CNN with global average pooling and a GRU that integrates over time contain the averaging operator by construction. Prediction: trees fed the window mean directly should keep improving with h.
2. Dilution and collinearity (mostly Random Forest). With raw lags there are 4(h+1) strongly correlated features; `max_features = sqrt` makes each split choose among a few of them, so many splits use redundant lags, while the number of training rows and the forest size (50 trees, depth 15, minimum leaf 20) stay fixed, so variance grows with the dimension. XGBoost uses 80 % of the columns per tree and picks the useful ones, so it stays flat rather than degrading. Prediction: Random Forest degrades with raw lags, not with window-mean features.
3. Window bias (not expected here). If the window spanned several positions, old reports would describe other places and long windows would hurt. On this grid the window stays in one cell, so this should not matter; it would matter at higher speed or on the macro grid. The CNN can also learn to weight recent reports more.

Tests: window-mean trees (hypotheses 1 and 2) and a GRU (the second integrating architecture) at h = 0 to 15 on four sets. Reading the result: if `rf_wm` and `xgboost_wm` keep improving and approach the CNN, the plateau is an input-representation problem of trees, not a limit of the information in the window; if they plateau too, the limit is in the data (hypothesis 3 or a noise floor) and the CNN's advantage comes from something else (weighting, nonlinearity). Whichever way it comes out, it belongs in the revised technical documentation 6.2 and in the report's mechanism section as the second half of the averaging account: the gain is averaging, models differ in whether they can average.

### 12.1 First result of the tests (RMa LOS, NE BS, RSS+SINR only; MAE m; written 2026-10-16 14:00, other sets and the AoA experiment still running)

| h | 0 | 1 | 3 | 5 | 7 | 10 | 15 |
|---|---|---|---|---|---|---|---|
| XGBoost, raw lags | 6.06 | 3.69 | 3.48 | 3.44 | 3.43 | 3.40 | 3.40 |
| XGBoost, window mean only | 4.53 | 3.83 | 3.93 | 3.97 | 4.00 | 4.06 | 4.06 |
| RF, raw lags | 3.88 | 3.14 | 2.92 | 2.94 | 2.92 | 3.04 | 3.15 |
| RF, window mean only | 3.88 | 3.21 | 3.35 | 3.38 | 3.38 | 3.41 | 3.44 |
| 1D-CNN | 6.66 | 5.56 | 5.29 | 4.84 | 4.47 | 4.28 | 3.91 |
| GRU | 4.49 | 3.78 | 3.34 | 3.05 | 2.88 | 2.64 | 2.48 |

Reading: hypothesis 1 is not supported for the no-AoA case. Giving the trees the window mean does not make them keep improving: they gain at h=1 (RF 3.88 to 3.21) and then drift upward, and they are slightly worse than with the raw lags. So the plateau is not just the trees' inability to form an average. The GRU improves at every depth and reaches 2.48 m at h=15, better than every tree and the CNN. A window mean throws away the order of the reports; the recurrent model uses it. The remaining candidate is that, without AoA, the useful information in a long window is the ordered sequence of RSS values (movement from cell to cell, the transition itself), which a mean cannot carry and which the trees' axis-aligned splits on raw lags cannot exploit either. That would make the no-AoA grid gain two things: a first-report effect that the trees capture (h = 1 to 3) and a trajectory effect that only sequence models capture. This is a hypothesis; the AoA experiment (where the earlier macro finding was that an unordered mean reproduces the gain) and the other sets will show whether the two regimes differ. Do not put it in the report as established.

### 12.2 AoA experiment, RMa LOS NE (MAE m, written 2026-10-16 15:20)

| h | 0 | 1 | 3 | 5 | 7 | 10 | 15 |
|---|---|---|---|---|---|---|---|
| XGBoost, raw lags | 3.38 | 2.72 | 2.51 | 2.41 | 2.37 | 2.35 | 2.32 |
| XGBoost, window mean only | 3.33 | 2.73 | 2.58 | 2.47 | 2.45 | 2.44 | 2.45 |
| RF, raw lags | 2.94 | 2.43 | 2.20 | 2.25 | 2.25 | 2.32 | 2.38 |
| RF, window mean only | 2.97 | 2.47 | 2.34 | 2.25 | 2.22 | 2.24 | 2.30 |
| 1D-CNN | 4.59 | 3.50 | 2.83 | 2.75 | 2.56 | 2.60 | 2.61 |
| GRU | 3.35 | 2.64 | 2.25 | 2.05 | 1.97 | 1.89 | 1.87 |

With AoA the window mean alone does as well as the raw lags for both trees (RF 2.25 against 2.25 at h=5, XGBoost 2.44 against 2.35 at h=10), which agrees with the macro finding that an unordered mean reproduces the AoA-driven gain; the trees' plateau at about 2.3 m therefore looks like a floor of what an averaged angle can give them. The GRU keeps improving to 1.87 m at h=15, 0.4 m below every tree, so it extracts something beyond the mean even here (candidates: weighting recent reports more, ordering, interaction between RSS and AoA over time). Not yet established; the mixed set and the centre BS are still to come.

### 12.3 25x25 NLOS regression with fixed AoA noise (3D MAE m, finished 14:57)

Tuned: XGBoost BASE 33.25, BASE_H3 24.51, BASE_A 18.02, BASE_A_H3_dp 11.63, INT 11.17; RF BASE 29.32, BASE_H3 26.61, BASE_A 15.99, BASE_A_H3_dp 12.41. Untuned: RF BASE 29.43, BASE_H3 27.04, BASE_A_H3_dp 13.01. Segment shuffle: XGBoost 33.20 to 25.18, RF 29.36 to 27.01. Against the UMi LOS set (tuned XGBoost BASE 29.39, BASE_H3 13.72, BASE_A_H3_dp 7.99) uniform NLOS is much harder: no-AoA error stays near the constant-guess level and history helps less (XGBoost 8.7 m against 15.7 m), but still helps for XGBoost; Random Forest gains only 2.7 m. The mixed 25x25 set is running (started 14:57).

### 12.4 All four sets (finished 2026-10-16 19:44; MAE m)

| Set | AoA | model | h=0 | h=3 | h=15 |
|---|---|---|---|---|---|
| RMa LOS NE | no | XGBoost raw lags | 6.06 | 3.48 | 3.40 |
| RMa LOS NE | no | XGBoost window mean | 4.53 | 3.93 | 4.06 |
| RMa LOS NE | no | RF raw lags | 3.88 | 2.92 | 3.15 |
| RMa LOS NE | no | RF window mean | 3.88 | 3.35 | 3.44 |
| RMa LOS NE | no | 1D-CNN | 6.66 | 5.29 | 3.91 |
| RMa LOS NE | no | GRU | 4.49 | 3.34 | 2.48 |
| RMa LOS NE | yes | XGBoost raw lags | 3.38 | 2.51 | 2.32 |
| RMa LOS NE | yes | XGBoost window mean | 3.33 | 2.58 | 2.45 |
| RMa LOS NE | yes | RF raw lags | 2.94 | 2.20 | 2.38 |
| RMa LOS NE | yes | RF window mean | 2.97 | 2.34 | 2.30 |
| RMa LOS NE | yes | 1D-CNN | 4.59 | 2.83 | 2.61 |
| RMa LOS NE | yes | GRU | 3.35 | 2.25 | 1.87 |
| Mixed NE | no | XGBoost raw lags | 7.34 | 3.58 | 3.46 |
| Mixed NE | no | XGBoost window mean | 5.47 | 4.49 | 4.52 |
| Mixed NE | no | RF raw lags | 4.93 | 2.78 | 3.35 |
| Mixed NE | no | RF window mean | 4.83 | 3.78 | 3.80 |
| Mixed NE | no | 1D-CNN | 8.34 | 3.86 | 2.49 |
| Mixed NE | no | GRU | 5.37 | 2.58 | 1.42 |
| Mixed NE | yes | XGBoost raw lags | 4.63 | 3.06 | 2.82 |
| Mixed NE | yes | XGBoost window mean | 4.58 | 3.48 | 3.15 |
| Mixed NE | yes | RF raw lags | 4.25 | 2.62 | 3.15 |
| Mixed NE | yes | RF window mean | 4.34 | 3.33 | 3.15 |
| Mixed NE | yes | 1D-CNN | 6.04 | 2.53 | 1.67 |
| Mixed NE | yes | GRU | 4.37 | 2.02 | 1.30 |
| RMa LOS centre | no | XGBoost raw lags | 6.83 | 3.81 | 3.65 |
| RMa LOS centre | no | XGBoost window mean | 5.12 | 4.37 | 4.38 |
| RMa LOS centre | no | RF raw lags | 5.34 | 3.32 | 3.56 |
| RMa LOS centre | no | RF window mean | 5.54 | 4.25 | 3.84 |
| RMa LOS centre | no | 1D-CNN | 7.72 | 5.20 | 3.53 |
| RMa LOS centre | no | GRU | 5.25 | 3.28 | 2.19 |
| RMa LOS centre | yes | XGBoost raw lags | 1.74 | 1.35 | 1.34 |
| RMa LOS centre | yes | XGBoost window mean | 1.71 | 1.48 | 1.57 |
| RMa LOS centre | yes | RF raw lags | 1.78 | 1.38 | 1.57 |
| RMa LOS centre | yes | RF window mean | 1.73 | 1.54 | 1.63 |
| RMa LOS centre | yes | 1D-CNN | 2.68 | 1.64 | 1.38 |
| RMa LOS centre | yes | GRU | 2.00 | 1.22 | 1.01 |
| Mixed centre | no | XGBoost raw lags | 8.05 | 3.77 | 3.53 |
| Mixed centre | no | XGBoost window mean | 5.90 | 4.82 | 4.74 |
| Mixed centre | no | RF raw lags | 5.21 | 2.76 | 3.21 |
| Mixed centre | no | RF window mean | 5.21 | 4.04 | 3.90 |
| Mixed centre | no | 1D-CNN | 8.96 | 3.83 | 2.01 |
| Mixed centre | no | GRU | 5.74 | 2.52 | 1.24 |
| Mixed centre | yes | XGBoost raw lags | 1.44 | 1.00 | 0.99 |
| Mixed centre | yes | XGBoost window mean | 1.42 | 1.18 | 1.26 |
| Mixed centre | yes | RF raw lags | 1.25 | 1.04 | 1.31 |
| Mixed centre | yes | RF window mean | 1.24 | 1.11 | 1.18 |
| Mixed centre | yes | 1D-CNN | 1.90 | 0.88 | 0.75 |
| Mixed centre | yes | GRU | 1.38 | 0.80 | 0.60 |

Reading (all four sets, with and without AoA, the same direction every time):
1. The GRU is the best model at long history in every set and keeps improving to h = 15 (mixed centre with AoA 0.60 m against 0.99 m for XGBoost; mixed NE without AoA 1.42 m against 3.46 m). The CNN follows the GRU and overtakes the trees at long history on the mixed sets.
2. Window-mean trees do not keep improving. Without AoA they are worse than the raw-lag trees for h >= 3 (mixed NE XGBoost 4.52 m against 3.51 m, RF 3.78 against 2.78 m). With AoA they equal the raw-lag trees (RF 3.19 against 2.83 at h=5, XGBoost 3.15 against 2.82 at h=15 on mixed NE). So the trees' plateau is not a missing averaging operator; supplying the mean does not help and, without AoA, removes information.
3. Hypothesis 1 of section 12 is therefore rejected, and hypothesis 3 was never plausible on this grid. What remains is an information account: without AoA a single RSS+SINR report is ambiguous between cells (equal RSS on the same contour around the BS) and a mean of the window cannot remove that ambiguity, whereas the ordered sequence of reports traces the movement across contours, which is exactly the transition information the thesis is about. The sequence models (GRU, then CNN) use it; trees on raw lags use only the first one or two lags effectively (the gain at h = 1 to 3) and the extra lags are redundant, correlated inputs (the Random Forest degradation, hypothesis 2, remains plausible and is consistent with RF being worse than XGBoost at large h). With AoA, the ordering still matters for the GRU but less for the mean.
4. This changes what the report can say: on the controlled grid the history gain has an averaging part (shared by all models, and the only part the macro study isolated) and a sequence part that only recurrent and convolutional models exploit. It is an interpretation supported by the four sets, not a direct test: the direct test is to shuffle the order of the reports inside each window for the GRU (a model that stays as good after shuffling uses only the mean). That test is queued as a to-do below.

## 13. 25x25 regression across the propagation sets (fixed 4 deg AoA noise, tuned parameters, 30 % subsample; 3D MAE m)

| Experiment | UMi LOS XGB / RF | NLOS XGB / RF | Mixed per-cell XGB / RF |
|---|---|---|---|
| BASE | 29.39 / 14.52 | 33.25 / 29.32 | 29.89 / 24.33 |
| BASE_H3 | 13.72 / 17.06 | 24.51 / 26.61 | 20.46 / 23.19 |
| BASE_A | 12.52 / 8.24 | 18.02 / 15.99 | 16.24 / 13.30 |
| BASE_A_H3 | 8.35 / 9.42 | 12.49 / 13.26 | 11.30 / 12.43 |
| BASE_A_H3_dp | 7.99 / 8.85 | 11.63 / 12.41 | 10.85 / 11.75 |
| BASE_A_H3_dp_INT | 7.19 / 7.53 | 11.17 / 11.78 | 10.23 / 11.37 |

Block-shuffled split, mixed: XGBoost 29.89 to 21.13, RF 24.22 to 23.60 (history helps XGBoost by 8.8 m, RF by 0.6 m). Features, mixed: absolute h=3 is best for XGBoost (10.85 m against 12.45 to 12.66 for hybrid) and the Random Forest hybrid advantage seen on the UMi LOS data (8.14 against 8.85 m) is gone (11.96 against 11.75 m).

Reading: history helps XGBoost in every set (no AoA: 15.7 m on UMi LOS, 8.7 m on NLOS, 9.4 m on mixed; with AoA 4.2, 5.1 and 4.7 m for BASE_A to BASE_A_H3_dp); Random Forest degrades with history on UMi LOS, and gains 2.7 m (NLOS) and 1.1 m (mixed) elsewhere. The interference fingerprint (`_INT`) helps in all three sets by 0.4 to 1.3 m. The absolute level depends strongly on propagation: the no-AoA error is near the constant guess under NLOS.

## 14. Order test: shuffled windows (finished 2026-10-17 10:58; MAE m, 2 seeds)

The reports inside each window are permuted (all channels of a report together) in training and in test, so a model can use the set of reports but not their order.

| Set | AoA | GRU ordered h=3 / 10 / 15 | GRU shuffled h=3 / 10 / 15 | CNN ordered h=3 / 10 / 15 | CNN shuffled h=3 / 10 / 15 | window-mean RF h=15 | RF raw h=15 |
|---|---|---|---|---|---|---|---|
| RMa LOS NE | no | 3.34 / 2.64 / 2.48 | 4.90 / 5.57 / 6.28 | 5.29 / 4.28 / 3.91 | 5.48 / 5.29 / 5.73 | 3.44 | 3.15 |
| RMa LOS NE | yes | 2.25 / 1.89 / 1.87 | 3.54 / 4.50 / 5.14 | 2.83 / 2.60 / 2.61 | 3.66 / 4.46 / 5.04 | 2.30 | 2.38 |
| Mixed NE | no | 2.58 / 1.58 / 1.42 | 4.46 / 4.93 / 5.53 | 3.86 / 2.57 / 2.49 | 5.01 / 4.93 / 5.49 | 3.80 | 3.35 |
| Mixed NE | yes | 2.02 / 1.37 / 1.30 | 3.82 / 4.59 / 5.29 | 2.53 / 1.82 / 1.67 | 3.91 / 4.57 / 5.17 | 3.15 | 3.15 |
| RMa LOS centre | no | 3.28 / 2.36 / 2.19 | 4.90 / 5.29 / 6.18 | 5.20 / 3.82 / 3.53 | 5.15 / 5.29 / 5.64 | 3.84 | 3.56 |
| RMa LOS centre | yes | 1.22 / 1.03 / 1.01 | 2.84 / 4.44 / 5.17 | 1.64 / 1.43 / 1.38 | 2.91 / 4.31 / 5.09 | 1.63 | 1.57 |
| Mixed centre | no | 2.52 / 1.38 / 1.24 | 4.54 / 4.80 / 5.41 | 3.83 / 2.20 / 2.01 | 5.05 / 4.86 / 5.38 | 3.90 | 3.21 |
| Mixed centre | yes | 0.80 / 0.64 / 0.60 | 2.58 / 4.25 / 5.10 | 0.88 / 0.72 / 0.75 | 2.58 / 4.20 / 4.97 | 1.18 | 1.31 |

Reading:
1. Shuffling destroys the long-history advantage in every set, with and without AoA. Example, mixed NE without AoA: ordered GRU 2.58 / 1.58 / 1.42 m at h = 3 / 10 / 15, shuffled GRU 4.46 / 4.93 / 5.53 m; the shuffled models also get worse as the window grows. Mixed centre with AoA: ordered GRU about 0.60 m at h=15 (section 12.4), shuffled several times higher (see the table).
2. The shuffled networks are worse than trees fed the window mean (mixed NE h=15 without AoA: shuffled GRU 5.53 m, window-mean RF 3.80 m), so a neural network does not find the mean of a shuffled window as efficiently as a hand-made mean feature; the shuffled-network figure is therefore not a clean "mean-only" bound. The clean comparison is the ordered GRU (1.42 m) against the best order-blind model, the window-mean trees (3.80 m): the order is worth well over 2 m there.
3. Taken with section 12.4 this supports the information account: the extra gain of the recurrent and convolutional models over the trees at long history comes from the order of the reports (the path the user traced), not from averaging. On the controlled grid the history gain is therefore not only noise averaging; the transition itself (which values came before which) carries information about the position. The macro-cell finding that an unordered mean reproduces the AoA-driven gain still stands for that study; the two studies differ in task (regression of positions over 100 m against classification of 2 m cells) and in the information a report carries.
4. Caveat for the report: two seeds, three depths, one network each, and the shuffle is applied in training as well; it shows that these models use the order, not that no model could reach the same accuracy without it.

