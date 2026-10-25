# Claim–evidence map for the paper

Written 2026-10-24 after the instructor meeting of 2026-10-22 ("it's now a question of shaping and framing the points properly and showing which data supports which claims"). One row per claim: where the evidence is, the key number, and how strong it is. Paths are relative to `experiments/09_grid_localization/docs/` unless they start with `src/`. Numbers were checked against the results of record; the technical documentation section is given for each.

Studies: **G** = 15×15 controlled grid (classification, 2 m cells, five device profiles, three propagation sets, mixed per-cell is the headline set); **R** = 25×25 regression (five device profiles, NE BS, three propagation sets, fixed 4° AoA noise); **M** = macro cell (300 users simulated, 232 retained, unseen test users, regression).

Strength: **strong** = several settings and seeds or splits, same direction everywhere; **medium** = several settings, few seeds; **weak** = one setting or one run.

---

## Core message (Dudi, 22.10)

> Using the history of transitions, rather than positioning from the current step only, improves single-BS localization consistently across propagation settings, BS placements and model families. The contribution is this consistent gain, not a best method or a specific accuracy.

---

## C1. History improves localization in every setting tested

| Study | Evidence | Key number | Strength |
|---|---|---|---|
| G | `results_of_record/controlled_grid_2026_10/comparison_sets.md`; figures `fig_controlled_grid_sets` (accuracy) and the MAE version (deck only so far); tech doc 6.1 | Without AoA, h = 3 raises exact-cell accuracy in 12 of 12 combinations (3 sets × 2 placements × 2 models): +4.9 to +27.4 pp, 1.0 to 4.3 m lower mean error. With AoA: mean error lower in 12 of 12, accuracy higher in 11 of 12 (Random Forest, mixed, centre: −0.7 pp) | strong for direction (single run per bar, but 12 of 12) |
| R | `results_of_record/regression_25x25_2026_10/sequence_vs_trees/all_mae.md`; tech doc 6.4 | The best model with history beats the best snapshot model in 6 of 6 set × AoA combinations (e.g. NLOS without AoA 16.7 against 29.3 m; UMi LOS with AoA 6.6 against 8.2 m) | strong (GRU three seeds) |
| M | report Sections 6–7; tech doc 6.5; `results_of_record/followup_2026_10/` | Multi-antenna devices: 19.0 → 15.4 m (XGBoost); 15 to 21 % lower error in all seven model families | strong (20 user splits for XGBoost and RF, 5 for the others) |

Scope limits to state with it: single-antenna devices in M gain nothing (34.7 m, constant guess 33.6 m); Random Forest gets worse with history on R UMi LOS (14.5 → 17.1 m). Safe wording: "history improves the best model in every setting".

## C2. The gain is consistent across model families

| Study | Evidence | Key number | Strength |
|---|---|---|---|
| G | tech doc 6.2 table | XGBoost, Random Forest, 1D-CNN, GRU and LSTM all improve from h = 0 to their best depth in all four sets tested | strong |
| M | report Section 7 | seven families (XGBoost, RF, k-NN, four neural models), 15 to 21 % | strong |

Use the tree-model results here, as consistency evidence, and keep them short (Dudi: "why did we talk half an hour on the trees?").

## C3. Sequence models use long windows; tree ensembles stop at about three steps

| Study | Evidence | Key number | Strength |
|---|---|---|---|
| G | tech doc 6.2; `fig_history_extended`; `results_of_record/history_extended/` | Trees flat (XGBoost) or worse (RF) after h = 3 to 5; CNN and GRU improve to h = 15 in all four sets. Mixed NE without AoA at h = 15: GRU 1.42 m, CNN 2.49 m, RF 3.35 m, XGBoost 3.46 m | strong (GRU and CNN three seeds) |
| G | tech doc 6.2 (window mean) | Giving trees the window mean does not remove the plateau (mixed NE XGBoost h = 5: 4.52 against 3.51 m), so it is not a missing average | medium (single run) |
| R | `sequence_vs_trees/all_mae.md`; tech doc 6.4 | GRU at h = 15 lowest error in 6 of 6, 1.3 to 5.0 m below the best tree at any depth; seed spread ≤ 0.4 m | strong |
| G | tech doc 6.2 (LSTM pilot) | An LSTM of the same size equals the GRU (1.40 against 1.42 m): the sequence matters, not the cell type | weak (one set, two seeds); one sentence in the paper |

Caveats to state: tree parameters tuned at h = 3; on the RMa LOS grid sets the trees match or beat the GRU in exact-cell accuracy while the GRU wins on mean error.

## C4. Most of the sequence-model gain is the information in the window; the order adds the rest

| Study | Evidence | Key number | Strength |
|---|---|---|---|
| G | tech doc 6.2 (fair order test and decomposition); `results_of_record/history_extended/order_test_comparison.csv` | With the current report kept in place, shuffling the older reports raises the GRU error at h = 15 by 19 to 48 % in 8 of 8 rows; of the GRU gain from h = 0 to h = 15, 72 to 87 % comes from the window without its order and 13 to 28 % from the order | medium (shuffled runs two seeds, one architecture of each kind) |

Paper: one paragraph, no table. Frame as an analysis of where the gain comes from, not a deployment case (in practice the order is always known). Do not mention the first version of the test.

## C5. BS placement decides the value of AoA, and history helps most where the angle is weak

| Study | Evidence | Key number | Strength |
|---|---|---|---|
| G | `comparison_sets.md`; report Section 5 | AoA gain (XGBoost, mixed, h = 3): +19.5 pp with the BS at the centre, +1.0 pp beyond the corner | strong for direction (all sets) |
| G | `comparison_sets.md` (history gain with AoA) | With AoA, history adds more beyond the corner: +8.8 against +3.1 pp (XGBoost), +8.7 against −0.7 pp (RF), mixed set | medium |
| G, R | `comparison_sets.md`, `all_mae.md` | Without AoA the history gain is larger than with it (G: +4.9 to +27.4 pp against −0.7 to +8.8 pp) | strong |

Tension to resolve before writing: in M the history gain comes from the angle channels and single-antenna devices gain nothing, while in G and R history helps most without an angle. First explanation ("one report on a small cell already narrows the position to a few cells") was not convincing to the author (2026-10-24). Candidate explanations, to test:

- H1, the studies are split differently. G and R train and test on the same users (the first 80 % of each walk against the last 20 %), so the model learns each user's own channel map and RSS is informative (G snapshot 4.93 m against a 10.9 m guess). M tests on unseen users; if their RSS does not transfer between users (own shadowing realization, own antenna gain), RSS carries almost nothing (M single-antenna snapshot 34.7 m, at the 33.6 m guess) and history has nothing to accumulate. The angle is geometric and transfers, which is why the M gain is in the angle channels.
- H2, range. At 100 m or more the RSS changes little from one step to the next compared with shadowing, so a sequence of RSS reports adds little; on a 30 m grid each step changes RSS clearly.
- Common reading: history amplifies whatever position information the single reports carry; where a report carries none that generalizes, there is nothing to amplify.

Tests that separate H1 from H2: (a) G with a leave-one-user-out split (train on four device profiles, test on the fifth; short, CPU and GPU): if the RSS snapshot and the history gain collapse, H1; (b) M single-antenna devices with a within-user time split: if RSS history then helps, H1. This also answers Alon's single-antenna argument (22.10), which holds for G and R but not for M.

Result of test (a), 2026-10-24 (`src/python/experiments_ablation/grid_leave_one_user_out.py`; `results_of_record/leave_one_user_out/ne_mixed/`; mixed grid, NE BS, RSS+SINR): on an unseen user every model collapses, with or without history: about 1 % exact-cell accuracy (chance 0.4 %) and about 12 m mean error, worse than the 10.9 m constant guess (e.g. GRU h = 10: 1.62 m on the usual split, 12.38 m on an unseen user). Cause: the users do not share a channel map. Per-cell mean RSS correlates between users at only 0.02 to 0.83 (U1 and U4, identical device profiles: 0.02), with per-profile offsets of −5.9 to +4.5 dB; SINR correlates more (0.3 to 0.8). In the simulation each user of the grid (and of the 25×25 runs) is a separate QuaDRiGa run whose random state is seeded by its walk seed (`generate_simulation_data.m`: `rng(OVERRIDE_WALK_SEED)` before the channel generation), so each user gets its own shadowing realization of the environment. The macro runner instead puts 25 users in one layout, so users of a batch share one realization.

Consequences: (1) H1 is confirmed: G and R measure history in a known-map setting (the model learns each user's own map from the first 80 % of the walk); none of it transfers to an unseen user in this simulation. (2) Part of this is a simulation artefact: in a real deployment all users in one place share the large-scale shadowing, so a new device would differ mainly by its gain offset, not by a new map. (3) The grid cannot test cross-user generalization until users share one environment (one layout with all users as receivers, as in the macro runner, or a common channel seed with a common map extent). To discuss with the instructors before writing: state as a limitation, or regenerate the headline grid set with a shared environment and rerun the leave-one-user-out test.

Shared-environment attempt, 2026-10-25: a common channel seed for all users (`RUNNER_SHARED_CHANNEL_SEED`, short test run `sim_data_ne_bs_2026-10-25_07-46-16_shared_env`) shares the map only partly: U2, U3 and U5 agree (RSS map correlation 0.79–0.86), the four-antenna users U1 and U4 do not (−0.51 to 0.66). The reliable fix is one QuaDRiGa layout with all users as receivers (as in the macro runner), which needs a refactor of `generate_simulation_data.m`. Stopped here by the author's decision: reported as a limitation (per-user environment realizations; results are within-user, known-map results), to raise with the instructors.

## C6. In the macro cell the gain is the averaging of noisy angle reports

| Study | Evidence | Key number | Strength |
|---|---|---|---|
| M | report Section 9; tech doc 6.5; `results_of_record/diagnostics_2026_10/`, `followup_2026_10/` | An unordered mean of the AoA window recovers the gain; elevation carries more than 80 % of it; with exact AoA the gain is zero (trees) or negative (neural); when the AoA error persists across reports the gain falls from about 17 % to 2–6 % | strong |
| M | report Section 10 | Line of sight, interfering BSs and a blocked line of sight do not change the multi-antenna gain | strong |

Relation to C4: not a contradiction. At macro range the averaging part dominates; on the grid the order adds a further part.

## C7. Absolute errors are plausible for a single omni BS; they are context, not the contribution

| Study | Evidence | Key number | Strength |
|---|---|---|---|
| G | tech doc 5.3; report Section 5 | Best 0.60 m (GRU h = 15, mixed, centre, AoA) against 10.9 m for a constant guess | strong |
| R | `error_audit/regression25_*` | Best 6.6 m (GRU, UMi LOS, AoA) against 37.3 m | strong |
| M | report Section 6; `error_audit/macro_*` | Multi-antenna 15.4 m against 37.1 m | strong |
| all | tests `src/python/tests/test_error_metrics.py`; `error_audit_grid.py` | MAE = (1 − accuracy) × mean error of the wrong predictions; equal-weight and sample-weighted MAE differ by < 0.1 m | strong |
| — | Dudi's check with Kimi (22.10) | Assumed a 2×2 array; our BS is one omni antenna and the AoA is the simulator's angle plus noise (`generate_simulation_data.m`) | open: plan item N2/N2a |

Paper: absolute numbers only as context; the claim is the gain (Dudi, 22.10).

## C8. The gain survives incomplete and irregular history

| Study | Evidence | Key number | Strength |
|---|---|---|---|
| G | tech doc 6.2 (irregular and incomplete history); `results_of_record/history_irregular/ne_mixed/` | With 30 % of the older reports missing or with uneven gaps (mean 2 steps), the GRU keeps 80 to 90 % of its gain over the snapshot (2.06 / 1.99 m against 1.59 m regular and 5.43 m snapshot), two thirds with 60 % missing; it still beats XGBoost with perfect history (3.45 m). Report timestamps do not help (1.99 against 2.00 m). A model trained on clean history and tested on irregular history falls to 2.80 m. The 1D-CNN shows the same pattern (83–91 % of its gain kept; regular 2.49, gap2 3.01, mismatch 4.81 m) | medium (one set, one placement, no AoA; GRU two seeds, CNN three) |

Paper: one robustness paragraph under C1/C3 ("history helps even with missing and irregular reports, if the model is trained with them"), marked "pending Dudi's approval" in the drafts (author's decision, 2026-10-24); extensions (centre BS, AoA) only if he wants it in.

## C9. History through a motion model (tracking filter) is a strong alternative on the grid

| Study | Evidence | Key number | Strength |
|---|---|---|---|
| G | tech doc 6.2 (tracking filter); `results_of_record/tracking_filter/` | HMM forward filter on a Random Forest snapshot model: 4.93 → 0.71 m with the learned motion model, 0.93 m with a generic 2 m kernel, against 1.59 m for the GRU (mixed, NE, no AoA); stays below the GRU with missing and irregular reports | medium (one set, one placement; the grid walk suits a motion model) |

Decision (author, 2026-10-24): the paper stays on learned history; the filter is reported as a classical history-based baseline, not run in the macro study. Consequences: C1 is strengthened (history helps whether learned or filtered); C3 is stated as "sequence models use long windows where tree ensembles on the same windows cannot", not as "sequence models are the best way to use history"; the paper reports honestly that on the grid the filter with a learned or generic motion model is better than the GRU, and explains why (a neighbour-to-neighbour walk at constant speed suits a motion model; real trajectories are less regular, which the macro study would test).

---

## Not in the paper (or only one line)

| Result | Where it stays | Reason |
|---|---|---|
| History beyond h = 15 | not run | Dropped at the 22.10 meeting |
| LSTM details | tech doc 6.2 | One sentence in the paper (C3) |
| Attention pooling (GRU, CNN) | tech doc 6.2 | Mixed, no substantial gain; at most one sentence |
| First order test (whole window shuffled) | tech doc 6.2, superseded note | It hid the current report |
| Full tree tables, window-mean details | tech doc 6.2 | Consistency evidence only (C2) |
| June 2026 15×15 data, old 25×25 folders | `OLD_VS_REGENERATED_RUNS.md` | Superseded |
| Grid-size sweep, 7×7 depth sweep (2.6 GHz) | report Section 5, older figures | Not regenerated; keep at most as a supplementary note |
| Device-parameter features (`_dp`), interference fingerprint (`_INT`) | tech doc 6.1, 6.4 | Secondary; one line at most |
| B6 blocked LOS, region control, LOS oracle | report Section 10 | Robustness of C6; one paragraph |
| 3.5 GHz NLOS reference set | `comparison_sets.md` | One line: the carrier hardly matters |

## Open before writing

1. N2/N2a: Dudi's view after he hears the real antenna setup; the papers Kimi listed (related work, positioning of C7).
2. The C5/C6 tension: write and agree on the paragraph that explains why history helps without an angle on small cells but not at macro range.
3. Venue (Alon) and therefore the length and format.
4. `reference.bib`: channel charting, single-BS CSI localization, sequence models for localization, 3GPP device mix.
