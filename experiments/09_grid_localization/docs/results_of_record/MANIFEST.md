# Results of Record

Machine-written outputs backing every number in `FINAL_REPORT.md` and
`technical_documentation.md`. These are the **source of truth**: the Markdown
documents are hand-transcribed from these files, and where the two ever disagree,
these win.

Copied verbatim from `results/notebook_experiments/multi_user_poc/` (which is
gitignored, being ~35 MB of plots and model checkpoints). Nothing here was edited
by hand — full float precision is preserved.

---

## `campaign_b/` — the 300-user macro-cell campaign

| File | Backs |
| :--- | :--- |
| `master_benchmark_summary.json` | The seven-model scorecard: MAE, P50, P90, per-cohort MAE, parameter counts, training times |
| `master_benchmark_scorecard.md` | Human-readable rendering of the same run |
| `ablation_results_summary.json` | History depth sweep, feature-set ablation, hardware ablation, antenna-cohort breakdown, LOS/NLOS split, distance-zone split |
| `bad_data_and_outlier_diagnostic_report.md` | Top-5 best/worst user audit, Voronoi boundary-crossing audit, turn-angle audit |
| `aoa_masking_experiment_report.md` | AoA validity masking (Option A) head-to-head |

> **Warning — Campaign B has uniform NLOS propagation, not the mixed LOS/NLOS map
> its config declares.** `run_multi_user_300_25x25.m` ignores the config's
> `mixed_scenario` block and assigns `3GPP_38.901_UMi_NLOS` to every track. Any
> LOS/NLOS split in these files — `propagation_breakdown` in
> `ablation_results_summary.json`, the zone rows in `history_gain_by_zone_summary.json`,
> the per-zone fits in `pathloss_fit_summary.json` — partitions a homogeneous map
> into geometric regions. Those partitions are real and the MAEs within them are
> correct; only the LOS/NLOS *labels* are wrong. See `FINAL_REPORT.md` §5.6.

> **Warning — `master_benchmark_summary.json` has drifted from the current
> pipeline.** Re-running it today (`ablations_2026_09/master_benchmark_rerun_summary.json`)
> reproduces five of seven models within 0.6 m, but Random Forest is 1.47 m better
> and 5.84 m better on the single-antenna cohort, and the k-NN baseline's
> single-antenna error is 5.07 m worse. Cite the re-run for §6.

> **Warning — the `rts_*` fields in `master_benchmark_summary.json` are invalid.**
> They were produced before the `delta_t` defect was found and fixed (see below).
> Every **raw** field in that file is correct and is what the report cites; only
> the smoothing columns are affected. Use `ablations_2026_09/` for smoothing.

## `ablations_2026_09/` — September ablations

| File | Backs |
| :--- | :--- |
| `knn_sweep_rts_retune_summary.json` | k-NN history sweep, h ∈ {0,1,3,5,10}. **The `rts_retune` block is pre-fix and invalid**; the `knn_history_sweep` block is correct and is what §5.4 cites |
| `xgb_per_h_retune_summary.json` | Per-depth Optuna re-tuning of XGBoost (§5.5). Tuned on training users only; test users evaluated once |
| `master_benchmark_rerun_summary.json` | The §6 scorecard regenerated under the current pipeline, with a row-by-row comparison against `campaign_b/master_benchmark_summary.json`. **This supersedes that file's error columns.** |
| `rf_per_h_retune_summary.json` | **B5** — the same per-depth Optuna protocol on Random Forest (§5.5). Null result: 20 trials per depth move it by −0.046 to +0.066 m |
| `rts_retune_all_models_summary.json` | Cross-model Kalman/RTS sweep, **post-fix**. Backs the §7.7 table |
| `rts_retune_report.md` | Human-readable rendering of the same run |
| `per_user_process_noise_summary.json` | Global vs per-user process noise, `q_u = k·v_u`, wide grids (§7.7) |
| `history_gain_by_zone_summary.json` | **A1** — history gain per propagation zone. Backs §5.6, the LOS vs NLOS prediction test |
| `aoa_masking_across_models_summary.json` | **A2** — AoA masking applied to k-NN, RF, XGBoost. Backs §7.6.1, the negative generalisation result |
| `pathloss_fit_summary.json` | **A3** — fitted γ and σ per Voronoi zone, and the recomputed range-resolution table. Backs §7.5 |
| `deep_history_sweep_trees_summary.json` | **A4** — XGBoost depth sweep to h=30. Backs the saturation finding in §5.4 |
| `history_by_speed_class_summary.json` | **B1** — history sweep within each speed class. Backs §5.8, the finding that the useful window is spatial rather than temporal |
| `trajectory_diagnostics_summary.json` | **B4** — per-user trajectory diagnostics regenerated against the fixed time base, plus population raw / RTS-default / RTS-tuned / causal-Kalman MAE. Backs Figures 5 and 6 |
| `seed_repeats_all_models_summary.json` | **B2** — five-seed repeats across all seven families at h=0 and h=5. Backs §5.7: marginal spread, seed-paired history CIs, and the finding that scorecard ranks 1-6 are a statistical tie |
| `history_sweep_all_models_summary.json` | **B3** — h ∈ {0,1,3,5,10} for all seven families under one protocol. Backs §5.4 and Figure 2, replacing a figure that mixed three experiments |
| `seed_repeats_summary.json` | **A5** — five-seed repeats, marginal spread and seed-paired CIs. Backs §5.7, the noise floor |

### Reproducing the September ablations

```bash
E=experiments/09_grid_localization/src/python/experiments_ablation
.venv/Scripts/python $E/master_benchmark_rerun.py        # scorecard, ~14 min (GPU)
.venv/Scripts/python $E/rf_per_h_retune.py               # B5, ~2 h (CPU)
.venv/Scripts/python $E/regenerate_trajectory_diagnostics.py  # B4, ~6 min (GPU)
.venv/Scripts/python $E/seed_repeats_all_models.py       # B2, ~95 min (GPU)
.venv/Scripts/python $E/history_sweep_all_models.py      # B3, ~50 min (GPU)
.venv/Scripts/python $E/history_by_speed_class.py        # B1, ~22 min (GPU)
.venv/Scripts/python $E/history_gain_by_zone.py          # A1, ~5 min
.venv/Scripts/python $E/aoa_masking_across_models.py     # A2, ~10 min
.venv/Scripts/python $E/fit_pathloss_per_zone.py         # A3, ~1 min
.venv/Scripts/python $E/deep_history_sweep_trees.py      # A4, ~2 min
.venv/Scripts/python $E/seed_repeats.py                  # A5, ~4 min
```

## `history_sweeps_july/` — independent corroboration

| File | Backs |
| :--- | :--- |
| `xgb_history_sweep_results.csv` | XGBoost h ∈ {0..10} on 7 raw channels — independent confirmation that tree ensembles do not turn at h=10 (§5.4) |
| `rf_history_sweep_results.csv` | Random Forest, same |

These predate the derived-feature pipeline and used `build_history_features`, so
their `mae_rts` column has a **correct** time base and is unaffected by the defect.

## `mixed_propagation_2026_09/` — Job 1, real LOS/NLOS data (2026-10-07)

Same filenames as `ablations_2026_09/` but a different dataset: these ran on
`sim_data_300users_mixed_2026-09-18_20-25-01` (per-segment independent channel
generation, real `is_los`), not the uniform-NLOS baseline. See
`docs/Project_documentation/CONTINUE_HERE.md` §1a for the fix and the full
results narrative.

| File | Backs |
| :--- | :--- |
| `master_benchmark_rerun_summary.json` | Scorecard on the mixed dataset. MAE drops 1.5–3.9 m vs. the uniform-NLOS baseline — a structural effect of 76.9% LOS samples, not evidence on its own |
| `history_gain_by_zone_summary.json` | History gain per region: +15.94% in the LOS regions vs +8.65% in the NLOS regions (+7.29 pp), seed 42, XGBoost. **Not evidence of a propagation effect** — the same regions show +15.98% vs +4.84% on the uniform-NLOS dataset (`ablations_2026_09/history_gain_by_zone_summary.json`), and the 20-seed control in `followup_2026_10/` finds no difference between the datasets. The earlier "§6.4 re-confirmed" reading was wrong; see `REPORT_SKELETON_VALIDATION.md` A4 |
| `pathloss_fit_summary.json` | LOS γ=2.58, NLOS γ=3.60 — physically correct, confirms real propagation difference, not an RSS offset artifact |
| `history_sweep_all_models_summary.json` | 7/7 model families improve with history on the mixed data, 11.3–23.3% gains, six of seven peak at h=10 |
| `seed_repeats_all_models_summary.json` | All 7 families significant at 95% CI, gains 11.37–15.43% — matches the original uniform-NLOS B2 result (11.0–14.7%) |

## `blocked_los_2026_09/` — Job 2, B6 LOS→blocked→LOS (2026-10-07)

Five seeds (42, 1, 7, 13, 99) on the 360-user B6 dataset
(`sim_data_b6_2026-09-19_12-54-09`, strip widths 5–150 m). See
`CONTINUE_HERE.md` §1b and §4.

| File | Backs |
| :--- | :--- |
| `b6_seed42_summary.json`, `b6_seed1_summary.json`, `b6_seed7_summary.json`, `b6_seed13_summary.json`, `b6_seed99_summary.json` | Per-seed `b6_los_blocked_los_analysis.py` runs. **Result: flat, not peaked** — gain within the blocked interval hovers 24–32% across the whole 5–150 m range, no coherent rise-then-fall. Evidence against the specific grows-then-decays prediction; history still helps throughout |

## `diagnostics_2026_10/` — history-mechanism diagnostic (2026-10-07)

Requested by Alon: which input channels carry the history gain, per device
group and range. `history_mechanism_diagnostic.py` retrains k-NN, Random
Forest, XGBoost (master-benchmark hyperparameters, unseen-user split) on six
column subsets of the same h=5 windows — `pure_snap`, `snap` (=h=0),
`rss_hist`, `angle_hist`, `ray_hist`, `full` (=h=5) — 5 seeds each, paired by
sample and by seed. Script and its test (`test_history_mechanism_diagnostic.py`,
10/10 passing) live in `src/python/experiments_ablation/`.

| File | Backs |
| :--- | :--- |
| `baseline_uniform_nlos/history_mechanism_diagnostic_summary.json` | Run on `sim_data_300users_2026-07-25_11-46-11` (uniform NLOS). **Angle channel carries the multi-antenna gain**: `angle_hist` alone (+2.79 to +5.19 m) matches or beats `full`; `rss_hist`/`ray_hist` near zero, mostly inside CI. Single-antenna: every condition, every model, CI includes zero — no gain anywhere |
| `baseline_uniform_nlos/errors_first_seed.npz` | Per-sample errors + predicted/true xy, seed 42, `snap` and `full` conditions — for trajectory/error-distribution figures |
| `mixed_propagation/history_mechanism_diagnostic_summary.json` | Run on `sim_data_300users_mixed_2026-09-18_20-25-01`. Same angle-dominant pattern. LOS/NLOS split (this dataset only): `angle_hist` gain bigger in the LOS regions than the NLOS regions for both XGBoost (16.9% vs 10.0%) and RF (14.8% vs 8.8%) — a regional difference that `followup_2026_10/` shows is also present with no LOS, so not a propagation effect. Single-antenna `rss_hist`/`full` gains **do clear CI** here (XGBoost +1.36±0.26 m, RF +1.99±0.66 m) — unlike the uniform-NLOS run, where single-antenna never clears. Not yet explained |
| `mixed_propagation/errors_first_seed.npz` | Same, for the mixed dataset |

Full per-seed and per-user breakdowns are inside each `*_summary.json`
(`per_seed`, `per_user` keys) — not duplicated here.

### Reproducing

```bash
E=experiments/09_grid_localization/src/python/experiments_ablation
.venv/Scripts/python $E/history_mechanism_diagnostic.py --data-dir results/grid_localization/grid_25x25/sim_data_300users_2026-07-25_11-46-11            # ~5-80 min CPU, RF dominates; expect machine-sleep stalls if unattended
.venv/Scripts/python $E/history_mechanism_diagnostic.py --data-dir results/grid_localization/grid_25x25/sim_data_300users_mixed_2026-09-18_20-25-01       # ~5 min CPU
```

## `followup_2026_10/` — follow-up to the mechanism diagnostic (2026-10-12)

Runs that settle the open points of `docs/REPORT_SKELETON_VALIDATION.md`; that
document is the narrative for everything here. Scripts:
`history_mechanism_followup.py` (classical models, 11 unit tests) and
`history_mechanism_deep.py` (the four neural models), both in
`src/python/experiments_ablation/`. Same protocol as the diagnostic. All
intervals are Student-t 95% over seed-paired differences. Files are the
scripts' JSON output with whitespace removed; nothing else was changed.

| File | Backs |
| :--- | :--- |
| `uniform_nlos/history_mechanism_followup_summary.json` | 20 seeds, XGBoost + RF, `sim_data_300users_2026-07-25_11-46-11`. Extra conditions `az_hist`, `el_hist`, `angle_mean`, `angle_stats`, `angle_shuffled`; error by region, range band and region x range; radial/tangential RMS, radial share, range correlation. **Elevation history carries >80% of the gain; an order-free window mean recovers all of it** |
| `mixed_propagation/history_mechanism_followup_summary.json` | Same on `sim_data_300users_mixed_2026-09-18_20-25-01`, plus `snap_los` and strata by real LOS and by whether the window crosses an LOS/NLOS boundary |
| `mixed_propagation/region_gain_did_vs_uniform.json` | Seed-paired contrast of the LOS-region minus NLOS-region gain between the two datasets. **No difference (−0.16 ± 0.28 m, XGBoost angle history): LOS propagation does not change the history gain** |
| `mixed_propagation_los_flag/history_mechanism_followup_summary.json` | 20 seeds, conditions `rss_hist`, `full`, `snap_los`, `rss_hist_los`. Single-antenna gain on mixed data: oracle LOS flag +3.3 m; RSS history adds +1.0 m on top, mostly in boundary-crossing windows |
| `blocked_los/history_mechanism_followup_summary.json` | 20 seeds on `sim_data_b6_2026-09-19_12-54-09`, by device group, blocked/unblocked and strip width. **Multi-antenna +6.3 m (36%) blocked, +6.7 m unblocked; single-antenna no detectable gain; all of it azimuth averaging.** Supersedes the pooled 5-seed reading in `blocked_los_2026_09/` |
| `aoa_impairment/clean/…` | 10 seeds, uniform NLOS, exact AoA. Multi-antenna error ~2 m, **history gain zero** |
| `aoa_impairment/quant5_only/…`, `noise4_only/…`, `noise8_quant5/…` | 10 seeds each: 5° quantization only (14.2 m, gain +1.9 m), 4° noise only (18.5 m, +3.1 m), 8° noise + 5° quantization (21.7 m, +2.4 m) |
| `aoa_impairment/corr_rho{0,0.5,0.9,0.99}/…` | 10 seeds each: AoA error AR(1) along the walk with lag-1 correlation rho. **Gain falls from +3.1 m (17%) at rho=0 to about +1.0 m (5–6%) at rho>=0.9** |
| `neural_uniform_nlos/{cnn-gru,cnn_attn,mask_aware_cnn}/history_mechanism_deep_summary.json` | 5 seeds each, uniform NLOS, all four neural models: angle history alone equals full history (+2.98 to +3.43 m vs +2.85 to +3.19 m); RSS history under +0.2 m |
| `neural_exact_aoa/{cnn,gru,cnn_attn-mask_aware_cnn}/…` | 5 seeds, exact AoA, h=0 vs h=5. Error 1.8–3.2 m; **history gain negative in all four (−0.48 to −0.78 m)** |
| `neural_corr_rho0.9/{cnn-gru,cnn_attn-mask_aware_cnn}/…` | 5 seeds, AoA error lag-1 correlation 0.9. **Gain +0.34 to +0.61 m (2–3%)** |
| `neural_mixed/{cnn-gru,cnn_attn-mask_aware_cnn}/…` | 5 seeds, mixed dataset, `snap` / `rss_hist` / `full`. Multi-antenna +2.9 to +3.1 m; single-antenna RSS-history gain clears its interval for GRU and CNN+attention only |
| `history_depth/h{1,3,10,20}/history_mechanism_followup_summary.json` | 10 seeds, uniform NLOS, `--history` 1, 3, 10, 20. Gain +1.2 / +2.5 / +3.5 / +3.7 m (XGBoost; h=5 is in `uniform_nlos/`). Window-mean-only input collapses at h=20 |
| `single_share_50/{uniform_nlos,mixed_propagation}/…` | 20 seeds with `--single-ant-ratio 0.5` (14–22 single-antenna test users per seed). Uniform: XGBoost +0.30 ± 0.24 m, RF +0.18 ± 0.24 m. Mixed: +1.23 ± 0.15 m, +1.39 ± 0.14 m. **Different training mix from the report** |
| `knn_uniform_nlos/…` | 5 seeds, k-NN through the follow-up conditions: elevation +3.34 m, azimuth +1.89 m |

### Reproducing

```bash
E=experiments/09_grid_localization/src/python/experiments_ablation
U=results/grid_localization/grid_25x25/sim_data_300users_2026-07-25_11-46-11
M=results/grid_localization/grid_25x25/sim_data_300users_mixed_2026-09-18_20-25-01
.venv/Scripts/python $E/history_mechanism_followup.py --data-dir $U            # ~30 min CPU
.venv/Scripts/python $E/history_mechanism_followup.py --data-dir $M            # ~27 min
.venv/Scripts/python $E/history_mechanism_followup.py --did <uniform summary.json> <mixed summary.json>
.venv/Scripts/python $E/history_mechanism_followup.py --data-dir $M --conditions rss_hist full snap_los rss_hist_los
.venv/Scripts/python $E/history_mechanism_followup.py --data-dir results/b6_los_blocked_los/sim_data_b6_2026-09-19_12-54-09 --b6
S="42 1 7 13 99 3 11 17 23 29"
.venv/Scripts/python $E/history_mechanism_followup.py --data-dir $U --seeds $S --aoa-noise-std 0 --aoa-quant-step 0.000001
.venv/Scripts/python $E/history_mechanism_followup.py --data-dir $U --seeds $S --aoa-noise-std 0 --aoa-quant-step 5
.venv/Scripts/python $E/history_mechanism_followup.py --data-dir $U --seeds $S --aoa-noise-std 4 --aoa-quant-step 0.000001
.venv/Scripts/python $E/history_mechanism_followup.py --data-dir $U --seeds $S --aoa-noise-std 8 --aoa-quant-step 5
for r in 0 0.5 0.9 0.99; do .venv/Scripts/python $E/history_mechanism_followup.py --data-dir $U --seeds $S --aoa-noise-corr $r --conditions rss_hist angle_hist full az_hist el_hist angle_mean; done
ALL="cnn gru cnn_attn mask_aware_cnn"
.venv/Scripts/python $E/history_mechanism_deep.py --data-dir $U --models $ALL --conditions snap rss_hist angle_hist angle_mean full
.venv/Scripts/python $E/history_mechanism_deep.py --data-dir $U --models $ALL --conditions snap full --aoa-noise-std 0 --aoa-quant-step 0.000001
.venv/Scripts/python $E/history_mechanism_deep.py --data-dir $U --models $ALL --conditions snap full --aoa-noise-corr 0.9
.venv/Scripts/python $E/history_mechanism_deep.py --data-dir $M --models $ALL --conditions snap rss_hist full
# neural runs: ~5 min per training alone at ~8% GPU use (CPU-bound batching); run several
# processes side by side, one or two models each - the output folder is named after the models
for h in 1 3 10 20; do .venv/Scripts/python $E/history_mechanism_followup.py --data-dir $U --seeds $S --history $h --conditions rss_hist angle_hist full el_hist az_hist angle_mean; done
.venv/Scripts/python $E/history_mechanism_followup.py --data-dir $U --single-ant-ratio 0.5 --conditions rss_hist angle_hist full
.venv/Scripts/python $E/history_mechanism_followup.py --data-dir $M --single-ant-ratio 0.5 --conditions rss_hist angle_hist full snap_los rss_hist_los
.venv/Scripts/python $E/history_mechanism_followup.py --data-dir $U --seeds 42 1 7 13 99 --models knn
```

## `superseded/` — kept for provenance, do not cite

| File | Why superseded |
| :--- | :--- |
| `rts_retune_all_models_PREFIX_BROKEN_DT.json` | Ran before the `delta_t` fix; its RTS figures (−28% to −48%) are artifacts |
| `diagnostic_BEST_user_119_ant2_PREFIX_BROKEN_DT.png` | The old Figure 5. Its smoothed track collapses to a stub and its RTS error sawtooths 0–30 m; regenerated by B4 |
| `diagnostic_WORST_user_250_ant1_PREFIX_BROKEN_DT.png` | The old Figure 6, same defect |
| `per_user_process_noise_narrow_grid.json` | Correct, but the swept grids were too narrow and the optima sat on a boundary. Replaced by the wide-grid run |

---

## The `delta_t` defect, in one paragraph

`DerivedCSI1DDataset` standardises `SIGNAL_COLS` in place, and `delta_t` is one of
those columns because it is a model input. The per-sample `delta_t` handed to the
Kalman/RTS smoother was read *after* that standardisation, so the smoother
received z-scores rather than seconds: 85.8% of values were negative and got
clamped to 0.01 s by `max(0.01, dt)`, destroying the state transition. Fixed in
commit `dee50dd`. **Only smoothing results are affected** — every raw MAE in every
file here is correct.

## Reproducing

```bash
# error decomposition into range vs bearing components
.venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/error_decomposition.py

# k-NN history sweep + RTS re-tune
.venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/knn_sweep_and_rts_retune.py

# per-depth XGBoost re-tune
.venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/xgb_per_h_retune.py

# cross-model RTS sweep
.venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/rts_retune_all_models.py

# global vs per-user process noise
.venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/per_user_process_noise.py
```

All of these require the simulation data under `results/grid_localization/grid_25x25/`,
which is gitignored — see `docs/Project_documentation/SHARING.md` for how to obtain it.
