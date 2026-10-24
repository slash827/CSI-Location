# Paper outline

Written 2026-10-24 from `../status/CLAIM_EVIDENCE_MAP.md` (claims C1–C8). Target: about 12 pages including figures, before references, in a generic single-column conference/journal format; adjust once Alon names a venue (a double-column IEEE format would be about 8 pages and needs the cuts marked "first to cut"). The 36-page report in `Transition_History/` stays as the long version (thesis); the paper is a new, shorter text that reuses its paragraphs and figures.

Working title: **Transition History for Single-Base-Station 5G Localization: a Consistent Gain Across Settings and Models**

## The story in five sentences

1. Single-BS localization from per-report CSI is limited; most work improves the per-report estimator (fingerprinting, channel charting, better angle estimation).
2. We take a different view: use the history of a user's reports, the transitions, rather than the current report alone (Dudi's "paradigm change").
3. Across three simulated studies, three propagation settings, two BS placements and seven model families, history lowers the error consistently (C1, C2).
4. Sequence models exploit long windows where tree ensembles stop at about three steps; most of their gain is the information in the window and part of it is the order (C3, C4), and the gain survives missing and irregular reports (C8).
5. Where history helps depends on what one report already carries: on small cells it helps most without an angle; at macro range it works through averaging noisy angle reports (C5, C6). Absolute errors are plausible for one omni BS and are context, not the claim (C7).

## Sections and page budget

| # | Section | Pages | Claims | Figures / tables | Source in the current report |
|---|---|---|---|---|---|
| 1 | Introduction: problem, the history view, contributions (bulleted C1–C8 in one line each) | 1.0 | all | — | `1_introduction.tex` (rewrite around the framing) |
| 2 | Related work: single-BS CSI localization and its accuracy, channel charting, fingerprinting, sequence models for localization and tracking (RNN, filters) | 0.75 | C7 context | — | `2_related_work.tex` (needs `reference.bib`) |
| 3 | System model: one omni BS, per-report features (RSS, SINR, AoA with noise model), history window of h reports, the estimation task (classification on the grid, regression elsewhere) | 0.75 | — | — | `3_system_model.tex` |
| 4 | Experimental setup: the three studies in one table (G, R, M); propagation settings defined in one line each (RMa LOS, UMi LOS/NLOS, mixed per-cell); device profiles and antennas (footnote: 1/2/4 omni elements, single omni BS, AoA = simulator angle + noise); splits; metrics and constant-guess baselines; models | 1.25 | — | **T1** studies table; **F1** `fig_study_maps` | `4_experimental_setup.tex` |
| 5.1 | History helps in every setting and every model family | 1.5 | C1, C2 | **F2** `fig_controlled_grid_sets` (or its MAE version); **T2** new cross-study summary: per study and setting, best snapshot against best history model, with the constant guess | `5_…`, `7_…` (`fig_history_gain_ci`) |
| 5.2 | Placement and the angle: AoA worth +19.5 pp at the centre, +1.0 pp at the corner; history adds more where the angle is weak | 0.5 | C5 | numbers in text (no figure) | `5_…` |
| 5.3 | Window length and model family: trees plateau, sequence models keep improving (grid and 25×25); order decomposition in one paragraph; LSTM and attention in one sentence; tracking-filter baseline (HMM on a snapshot model, learned and generic motion model) with an honest comparison | 1.75 | C3, C4, C9 | **F3** `fig_history_extended`; **T3** 25×25 best tree against GRU h = 15 (6 rows); **T5** grid: snapshot, trees, GRU, filter baselines (regular and two imperfect conditions) | `5_…`, `8_…`; tech doc 6.2 |
| 5.4 | Macro cell: the gain is the averaging of noisy angle reports | 1.0 | C6 | **F4** `fig_mechanism_conditions` | `9_results_mechanism.tex` |
| 5.5 | Robustness: propagation, interferers and blocked LOS (macro); incomplete and irregular history (grid) | 0.75 | C6, C8 | numbers in text, or a small **T4** for irregular history | `10_results_propagation.tex`; tech doc 6.2 |
| 6 | Discussion: why history helps without an angle on small cells but not at macro range (C5/C6 paragraph); absolute accuracy in context (C7); practical lessons (train with the irregularity expected in use) | 1.0 | C5–C8 | — | `11_discussion.tex` |
| 7 | Limitations and conclusion | 0.75 | — | — | `12_…`, `13_…` |
| | Total | about 10.75 + figures inside | | 4 figures, 3–4 tables | |

## Figures and tables

| ID | Content | Status |
|---|---|---|
| F1 | `fig_study_maps`: the deployments at the same scale | exists |
| F2 | `fig_controlled_grid_sets`: 12 settings, accuracy (MAE version exists as a PNG in the deck only) | exists; choose accuracy or MAE |
| F3 | `fig_history_extended`: MAE against h, trees, CNN, GRU, fair-shuffle GRU | exists |
| F4 | `fig_mechanism_conditions`: macro gain by channel group | exists |
| T1 | The three studies (grid, cell size, users, task, propagation, AoA noise) | exists in `4_experimental_setup.tex`; shorten |
| T2 | Cross-study summary: best snapshot, best history model, constant guess, per study and setting | **new** |
| T3 | 25×25: best tree at any depth against GRU h = 15 (three seeds) | **new** (numbers in `all_mae.md`) |
| T4 | Irregular history (snapshot, regular, mask30, gap2, mismatch; GRU and CNN) | **new**, only if Dudi wants C8 in |
| T5 | Grid baselines: snapshot, XGBoost h = 3, GRU h = 10, RF + filter (learned, generic 2 m); regular, mask30, gap2 | **new** (numbers in tech doc 6.2); can merge with T4 |

First to cut if the venue is shorter: F1 (describe the geometry in text), T4 (one sentence), section 5.5 macro robustness (one sentence each).

## What leaves the paper (stays in the report and the technical documentation)

Report Section 6 (error scale) except one sentence and the constant guess in T2; `fig_error_cdf`, `fig_error_by_range`; `fig_history_by_group`, `fig_speed_classes`; `fig_trajectories`; `fig_radial_tangential`, `fig_mechanism_by_range`, `fig_angle_decomposition`, `fig_aoa_error_model` (one sentence each in 5.4); `fig_mixed_history_gain_ci`, `fig_region_control`, `fig_blocked_by_width` (one sentence each in 5.5); `fig_controlled_grid_depth`, `fig_controlled_grid_scale` (2.6 GHz, not regenerated); `fig_regression25_no_aoa` (replaced by T3); window-mean details; LSTM details; first order test; June data.

## Decisions needed

1. Venue and format (Alon), which fixes the page budget.
2. F2 in accuracy or MAE. Suggestion: MAE, so that all studies are in metres; accuracy in T2 for the grid.
3. The C5/C6 paragraph: agree the explanation with the instructors before writing section 6.
4. Whether C8 (irregular history) goes in (Dudi), and in how much space.
6. Decided 2026-10-24: the paper stays on learned history; the tracking filter is a baseline (C9), reported honestly as stronger than the GRU on the grid, with the reason; no macro-study filter.
5. Whether the grid study (classification) and the 25×25/macro studies (regression) are reported with one metric (mean error in metres) throughout; suggestion: yes, with exact-cell accuracy only as a secondary grid number.

## Writing order

1. T2 and T3 (numbers exist; small scripts or by hand from the results of record).
2. Sections 4 and 5 (results first, they fix what the text can claim).
3. Section 6, then 1 and the abstract, then 2 (with `reference.bib`), then 7.
4. Cut to the page budget at the end.
