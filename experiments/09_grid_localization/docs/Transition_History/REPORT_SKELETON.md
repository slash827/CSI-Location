# Report skeleton: Transition History for Single-BS CSI Localization

This is the working reference for `Project Report 2/`. It records:
- the claims and take-aways;
- the story arc;
- every exhibit and its source;
- the mechanism predictions, fixed on 2026-10-04 before the diagnostic ran, and their outcome.

**Source of record.** JSONs under `CSI-Location/experiments/09_grid_localization/docs/results_of_record/` override `FINAL_REPORT.md`, which overrides the tech doc and the analysis notes.

**Never in the prose:** `Campaign A/B` naming, code names, and mean point error (MPE).

## Working title

The current title in `main.tex` is "Transition History for Single-BS 5G NR CSI Localization: Model-Agnostic Gains and Their Hardware Dependence". C2 makes a sharper option available:
- "Transition History for Single-BS 5G NR CSI Localization: How Angle Sequences Recover Range"

The old title's "universal mechanism" is contradicted by C3. The final wording is the author's call.

## Naming

| Prose name | Means |
|---|---|
| the controlled-grid study | 15×15 classification (multi-user, centre and corner BS), plus the single-user grid-size sweeps; 3.5 GHz for 15×15, 3.0 GHz for the sweeps |
| the macro-cell study | 300 users, 25×25 grid at 4 m spacing, unseen-user regression, 3.0 GHz; uniform NLOS is primary, and the mixed LOS/NLOS run is a propagation ablation |
| the single-user 25×25 regression runs | tech doc §7.4–7.4.5 (chronological and block-shuffled splits) |
| the blocked line-of-sight scenario | the B6 corridor runs |
| multi-antenna / single-antenna devices | AoA available / AoA unavailable |

## Claims

### C1. History lowers error in every model family, for devices that report an angle *(established)*
- **The gain.** Five steps of history (20 m of travel) cut multi-antenna error by 2.75–4.06 m (14.7–20.8%) in all seven families. Paired CIs are ±0.13–0.85 m. Source: `seed_repeats_all_models_summary.json`, per-run `multi_mae`.
- **Overall.** The gain over both device groups is 2.38–3.24 m (11.0–14.7%). Source: same file, `verdict`.
- **Replicated under mixed propagation.** All seven families stay significant overall (11–15%), with multi-antenna gains of 2.3–3.9 m. Source: `mixed_propagation_2026_09/seed_repeats_all_models_summary.json`.
- **Not a tuning artifact.** Per-depth re-tuning changes XGBoost by at most 0.44 m and Random Forest by less than 0.07 m.
- **Model choice barely matters.** At h=5, ranks 1–6 sit within 0.47 m with overlapping CIs. XGBoost trains in 4 s and predicts 1000 positions in 1.7 ms. Deep models select their checkpoint on test users, which favours them, so the tie holds a fortiori.

### C2. The gain comes from the angle channels, and it mainly fixes range error *(established for XGBoost, Random Forest and k-NN; inferred for the neural models)*
- **Angle history carries it.** Angle history alone matches or beats full history on both datasets and for all three models. Uniform NLOS, XGBoost: +3.28 ± 0.27 m, against +3.24 m with all channels.
- **Signal strength adds little.** RSS history gives at most +0.3 m and makes k-NN worse (−2.27 m). Source: `diagnostics_2026_10/`.
- **It is range that improves.** For multi-antenna devices (XGBoost, 5 seeds), radial error falls 17.3 → 14.1 m while tangential error moves only 5.0 → 4.6 m. A sequence of bearings constrains distance because the bearing turns more slowly with range (dθ/dt = v⊥/r).
- **The LOS advantage is in the angle channel.** Under mixed propagation, history helps more in LOS regions (+15.9% vs +8.7%, single run). The difference sits in the angle channels: XGBoost angle history gives +3.12 m in LOS against +1.51 m in NLOS, while RSS history is equal in both.
- **The range explanation for RSS history was tested and not supported** (see P3 below).

### C3. Without an angle, history doesn't help at macro range, so the error is two different failures blended *(established on uniform NLOS; one open exception)*
- **Multi-antenna devices (~15 m) are range-limited:** 90% of the error variance is radial. That is still about 5× better than the RSS-only bound of σ_r ≈ 68 m at median range.
- **Single-antenna devices (~35 m) are ring-smeared:** placed at about the right distance but the wrong bearing (tangential 25.3 m > radial 20.1 m). History changes neither component.
- **The single-antenna null on uniform NLOS** (paired, h=0 → h=5) runs from −1.39 to +0.32 m, and no CI excludes zero. XGBoost is 0.06 ± 0.18 m. There are 5–10 single-antenna test users per split.
- **Supporting evidence:** in the single-user 25×25 runs without AoA, Random Forest gets worse with history.
- **Open exception.** Under mixed propagation, RSS history helps single-antenna devices with tree models by about 1.5 m (XGBoost +1.36 ± 0.26, Random Forest +1.99 ± 0.66). It appears in both LOS and NLOS samples and is unexplained. A one-split lead points to windows that cross an LOS/NLOS boundary.

### Supporting: the controlled grid *(single runs; direction, not size)*
- **History helps without AoA** at short range, in every configuration. Random Forest is the magnitude reference: +8.5 pp at the centre BS, +5.9 pp at the corner.
- **BS placement.** With history included, moving the BS to the corner removes almost all of AoA's added value (XGBoost +31.4 → +2.3 pp). History's value stays positive. This is scoped to the short-range grid.

## Take-aways

1. History is a cheap, model-agnostic input. It helps every model family, but only for devices that report an angle.
2. What history reads is how the bearing moves, and what that buys is better range estimates.
3. The ~19 m average error hides two populations, which must be reported separately.
4. The reported history gains are about 15% understated, because the "no history" input already holds one step of change: removing it costs 0.4–0.5 m.
5. History keeps its value through a blocked line of sight of any length tested (24–32%). The predicted rise and fall with blockage length does not appear.

## Arc and sections

| § | File | Beat | Status |
|---|---|---|---|
| 0 | `0_abstract.tex` | — | placeholder; draft next |
| 1 | `1_introduction.tex` | Problem | linked; contributions and scope still to draft |
| 2 | `2_related_work.tex` | Problem | linked (carried over) |
| 3 | `3_system_model.tex` | Problem | linked |
| 4 | `4_experimental_setup.tex` | Setup | complete |
| 5 | `5_results_controlled_grid.tex` | First test | complete |
| 6 | `6_results_error_scale.tex` | Reality check | complete |
| 7 | `7_results_multi_antenna.tex` | Main result (C1) | complete |
| 8 | `8_results_single_antenna.tex` | Turn (C3); closes with the hypothesis and P1–P3 | complete |
| 9 | `9_results_mechanism.tex` | Explanation tested (C2) | complete |
| 10 | `10_results_propagation.tex` | Stress tests | complete |
| 11 | `11_discussion.tex` | Resolution | placeholder; draft next |
| 12 | `12_limitations.tex` | — | complete |
| 13 | `13_conclusion.tex` | Resolution | placeholder; draft next |

## Key figures (the six that carry the argument)

| Figure | Section | Shows |
|---|---|---|
| `fig_study_maps` | §4 | Both deployments at the same scale: a 28 m grid against a 96 m macro cell 21–157 m from the BS |
| `fig_history_gain_ci` | §7 | The headline: every multi-antenna CI is well above zero, and every single-antenna CI crosses zero |
| `fig_error_cdf` | §6 | The two error populations barely overlap; history shifts only the multi-antenna curve |
| `fig_mechanism_conditions` | §9 | Angle history alone matches full history; RSS and ray history are near zero |
| `fig_radial_tangential` | §9 | History cuts range error, not bearing error |
| `fig_trajectories` | §8 | Single-antenna ring smearing in one picture |

## All exhibits

**Generators.**
- `figure_scripts/make_figures.py` and `figure_scripts/make_figures_diagnostic.py` build every figure.
- `figure_scripts/check_overlaps.py` must report 0 overlaps after any change.

| Exhibit | Section | Content | Source |
|---|---|---|---|
| Table studies | §4 | Study setup | configs (`multi_user_voronoi_15x15`, `ne_bs_voronoi_15x15`, `ne_bs_voronoi_25x25`); FINAL_REPORT §4.1, §4.3, §7.5 |
| Table estimators | §4 | Estimators | `model_zoo.build_classical`; FINAL_REPORT §4.6 |
| `fig_study_maps` | §4 | Both deployments at the same scale | 15×15 and 25×25 configs; macro-cell transmitters from `run_multi_user_300_25x25.m` (interferers [−60,53], [53,−60]; the config's [−25,53], [53,−25] are not read); 15×15 interferers [−11,19], [19,−11], read by the generator |
| `fig_controlled_grid_placement` | §5 | Accuracy at h=0 and h=3, plus AoA, by model and BS placement | tech doc §7.2.1, §7.3.1–7.3.3 (only these two depths were recorded) |
| `fig_controlled_grid_depth` | §5 | Accuracy for h=0..3: 7×7 grid with three models; 15×15 single scenario with AoA | FINDINGS.md §3.3; analysis/regression_vs_classification.md §4 |
| `fig_controlled_grid_scale` | §5 | Accuracy vs grid size, 3×3 to 20×20 | tech doc §7.1 |
| Table reference levels | §6 | RSS-only bound and measured errors per group | `pathloss_fit_summary.json`; seed repeats |
| `fig_error_cdf` | §6 | Error distribution per group, h=0 and h=5 | `diagnostics_2026_10/baseline_uniform_nlos/errors_first_seed.npz` |
| `fig_error_by_range` | §6 | Error by range band per group, h=0 and h=5 | diagnostic `per_seed.xgboost.*.range_bins` |
| `fig_history_gain_ci` | §7, §8 | Seed-paired gain ± CI per model and group | seed repeats (per-run records) |
| `fig_history_by_group` | §7 | Gain vs depth per family, per group | `history_sweep_all_models_summary.json` |
| `fig_speed_classes` | §7 | Gain vs window in metres and in seconds, per speed class | `history_by_speed_class_summary.json` |
| `fig_trajectories` | §8 | Median single- and multi-antenna user (users 250 and 27, chosen by rule) | diagnostic `.npz` |
| `fig_single_user_no_aoa` | §8 | Single-user 25×25, RSS+SINR, h=0 vs h=3, two splits | tech doc §7.4.3, §7.4.4 |
| `fig_mechanism_conditions` | §9 | Gain by channel group, model, device group and dataset | diagnostic `summary.*.*.*.gain_vs_snap` |
| `fig_radial_tangential` | §9 | Radial and tangential error, h=0 vs h=5 | diagnostic `per_seed.xgboost` |
| `fig_mechanism_by_range` | §9 | RSS-only and angle-only gain by range band | diagnostic `gain_vs_snap_by_range` |
| `fig_mixed_history_gain_ci` | §10 | Per-model gains on the mixed dataset | `mixed_propagation_2026_09/seed_repeats_all_models_summary.json` |
| `fig_los_nlos_channels` | §10 | LOS vs NLOS gain by channel group | diagnostic `gain_vs_snap_by_los` |
| `fig_blocked_by_width` | §10 | Blocked-stretch gain vs strip width | `blocked_los_2026_09/b6_seed*_summary.json` |
| Table history-gain | Appendix | Per-model gains and cost | seed repeats; `master_benchmark_rerun_summary.json` |
| Supplementary tables | Appendix | Full depth sweep, seed spread, retuning | B3 sweep, seed repeats, retune JSONs |

## Mechanism diagnostic: predictions fixed before the run (2026-10-04)

**Conditions.** Each condition is a column subset of the same h=5 windows; see `Gilad Diagnostic 2026-10/history_mechanism_diagnostic.py`.

| Condition | Channels with all six steps |
|---|---|
| `snap` | none: the current step of all 13 channels, which is the recorded h=0 input |
| `pure_snap` | none, and the difference channels are dropped as well |
| `rss_hist` | RSS side: rss, sinr, d_rss |
| `angle_hist` | angle side: sin/cos az/el, d_az |
| `ray_hist` | ray channels: ray x/y, d_ray x/y |
| `full` | all channels, which is the recorded h=5 input |

**Predictions:**
- **P1.** For multi-antenna devices, `angle_hist` (and/or `ray_hist`) recovers most of `full`'s gain over `snap`, and `rss_hist` recovers little.
- **P2.** For single-antenna devices, no condition beats `snap` beyond its paired CI.
- **P3.** The `rss_hist` gain is largest in the `<40 m` bin and shrinks with range.

**Falsifiers:**
- If `rss_hist` ≈ `full` for multi-antenna devices, the claim that the gain depends on AoA fails.
- If `rss_hist` shows no range trend, the range mechanism fails.
- The `<40 m` bin is small, so an inconclusive P3 is reported as inconclusive.

## Mechanism diagnostic: outcome (2026-10-07)

Source: `results_of_record/diagnostics_2026_10/` (uniform NLOS and mixed; XGBoost, Random Forest, k-NN; 5 seeds).

- **P1 confirmed.** For multi-antenna devices, angle history alone matches or beats full history on both datasets and for all three models. RSS history gives at most +0.3 m and makes k-NN worse.
- **P2 confirmed on uniform NLOS, fails on mixed.** Under mixed propagation, RSS history lowers single-antenna error for both tree ensembles, positive in every seed. The mixed seed repeats agree for the trees; the neural models do not share the gain.
- **P3 not supported.** On uniform NLOS, the multi-antenna RSS-only gain shows no consistent fall with range. On mixed data, the single-antenna RSS-only gain *rises* with range (+0.4 m → +2.4 m). The range explanation is dropped; the AoA dependence stands.
- **Beyond the predictions:**
  - History mainly reduces radial error (C2).
  - The h=0 baseline already contains one step of change, worth 0.4–0.5 m.
  - The angle-only gain falls from ~10 m below 40 m to under 2 m at 80–120 m, then rises to 5.5 m beyond 120 m; that last rise is unexplained.

## Fidelity notes

- **Macro-cell AoA impairment.** It is a fixed 4° Gaussian error plus 5° quantization (`load_and_prepare_data`). The SINR-dependent noise model belongs to the controlled grid.
- **"h=0" in the macro-cell study.** It is the current measurement plus its first differences, not a pure snapshot.
- **Test-set checkpoint selection.** Deep models early-stop on test MAE. Comparisons within a family are unaffected; comparisons across families favour the deep models.
- **Controlled grid.** It is single-seed, and identical configurations appear 2–3 pp apart in different runs. Random Forest is the magnitude reference, because XGBoost's snapshot baseline is weak.
- **Error vs range.** `FINAL_REPORT.md`'s "error grows with range" came from one 1D-CNN run with the device groups pooled. The five-seed, per-group XGBoost data do not show it; the report follows the new data.
- **Mixed-dataset path-loss fits.** Per-region fits are unstable (one region gives γ = 6.9), so only the pooled LOS and NLOS fits are reported.
