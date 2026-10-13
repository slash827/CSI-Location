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
- [x] Mixed per-cell simulations (finished by 15:47)
- [x] `grid_history_extended.py` (h = 0…15 for XGBoost, RF, 1D-CNN) written and smoke-tested
- [x] Extended history and CNN, RMa LOS, NE BS (finished 15:43). Trees stop improving at h≈3 (XGBoost flat, RF worse beyond h=3); the CNN keeps improving up to h=15 without reaching the trees.

### 4.2 Running now

- [ ] Extended history and CNN, RMa LOS, centre BS (started ~15:44, about 2 h)
- [ ] Mixed per-cell pipelines, centre and NE (started 15:47, about 2–3 h each)
- [ ] NLOS 3.0 GHz simulations, centre and NE (started 15:47); then the headline-experiment pipelines

### 4.3 To do

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
- [ ] Update `CLAUDE.md` baselines and `test_results_sanity.py` paths to the primary set
- [ ] Regenerate `compare_placements` and MAE heat map figures from the primary set
- [ ] Section 8 "predictions fixed before the experiment": still unverifiable, remove or source it
- [ ] `reference.bib` (citations are undefined), cut the report to about 12 pages, thesis conversion
- [ ] Consortium report, due end of October

Housekeeping
- [ ] Stop the sleep-prevention process when the runs are done
- [ ] Commit results of record, push, merge `followup-2026-10` into `main`
- [ ] Untracked on purpose: `docs/Meeting with Alon 7.10.26.md`, `docs/Transition_History.zip`

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

