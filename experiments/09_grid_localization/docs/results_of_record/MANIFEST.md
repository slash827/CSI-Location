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
| `history_gain_by_zone_summary.json` | **§6.4 re-confirmed.** History's benefit: +15.94% LOS vs +8.65% NLOS (+7.29 pp). Range confound checked clean — LOS mean range (90.1 m) is *shorter* than NLOS (96.8 m) |
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
| `mixed_propagation/history_mechanism_diagnostic_summary.json` | Run on `sim_data_300users_mixed_2026-09-18_20-25-01`. Same angle-dominant pattern. LOS/NLOS split (this dataset only): `angle_hist` gain bigger in LOS than NLOS for both XGBoost (16.9% vs 10.0%) and RF (14.8% vs 8.8%) — matches `history_gain_by_zone.py`'s LOS>NLOS finding, now localized to the angle channel. Single-antenna `rss_hist`/`full` gains **do clear CI** here (XGBoost +1.36±0.26 m, RF +1.99±0.66 m) — unlike the uniform-NLOS run, where single-antenna never clears. Not yet explained |
| `mixed_propagation/errors_first_seed.npz` | Same, for the mixed dataset |

Full per-seed and per-user breakdowns are inside each `*_summary.json`
(`per_seed`, `per_user` keys) — not duplicated here.

### Reproducing

```bash
E=experiments/09_grid_localization/src/python/experiments_ablation
.venv/Scripts/python $E/history_mechanism_diagnostic.py --data-dir results/grid_localization/grid_25x25/sim_data_300users_2026-07-25_11-46-11            # ~5-80 min CPU, RF dominates; expect machine-sleep stalls if unattended
.venv/Scripts/python $E/history_mechanism_diagnostic.py --data-dir results/grid_localization/grid_25x25/sim_data_300users_mixed_2026-09-18_20-25-01       # ~5 min CPU
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
