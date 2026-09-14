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
