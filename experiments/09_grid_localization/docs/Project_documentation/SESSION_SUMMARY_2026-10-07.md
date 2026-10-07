# Session Summary — 2026-10-07

Alon (project instructor) sent a diagnostic script and run instructions to
test a specific hypothesis about *why* history helps multi-antenna devices
but not single-antenna devices at macro range. This session ran that
diagnostic end to end, copied the 2026-09-19 Job 1/Job 2 results into
`docs/results_of_record/` (they weren't there yet), and pushed everything on
branch `diagnostics-2026-10`.

---

## 1. Alon's hypothesis

Without AoA, history can only "see" motion through changes in RSS, and that
change per step shrinks with range — roughly 2.8 dB/step at 10 m vs 0.6
dB/step at 95 m, against ~10 dB of shadowing. Angle changes don't fade the
same way. That would explain why RSS-only history helps in a small grid but
not in the macro cell, and why history helps multi-antenna devices (which
have AoA) but not single-antenna ones (RSS only).

## 2. What the diagnostic does

`history_mechanism_diagnostic.py` retrains k-NN, Random Forest, and XGBoost
(master-benchmark hyperparameters, same unseen-user split as
`seed_repeats_all_models.py`) on six column subsets of the same h=5 window,
so every condition shares identical rows and train/test users — paired by
sample and by seed:

| Condition | History on |
| :--- | :--- |
| `pure_snap` | nothing — current step only, differences dropped |
| `snap` | nothing — current step of all 13 channels (= recorded h=0) |
| `rss_hist` | rss, sinr, d_rss |
| `angle_hist` | sin/cos az/el, d_az |
| `ray_hist` | ray_x, ray_y, d_ray_x, d_ray_y |
| `full` | everything (= recorded h=5) |

Classical models only — no GPU, no early stopping, nothing selected on test
users. Output breaks down by device group (all/multi/single), range band,
and LOS/NLOS (mixed dataset only), plus radial/tangential split and
within-5/10/20 m fractions.

## 3. What ran

1. Copied the script and its test into `src/python/experiments_ablation/`.
   `test_history_mechanism_diagnostic.py`: 10/10 passed.
2. Copied the 2026-09-19 Job 1 and Job 2 summary JSONs (no plots, no
   checkpoints) into `docs/results_of_record/mixed_propagation_2026_09/` and
   `blocked_los_2026_09/`, with a MANIFEST.md section for each. These results
   existed on disk but had never been checked into `results_of_record`.
3. Smoke test (one seed, XGBoost only, 60 users) on the uniform-NLOS
   dataset: clean.
4. Two full runs, one per macro-cell dataset:
   - **Uniform NLOS** (`sim_data_300users_2026-07-25_11-46-11`): 29,276 s
     wall time. Two Random Forest fits individually stalled 7,434 s and
     20,722 s — the same machine-sleep pattern already documented for Job 1
     (`CONTINUE_HERE.md` §7), not a computational problem. Exit 0, data
     valid.
   - **Mixed LOS/NLOS** (`sim_data_300users_mixed_2026-09-18_20-25-01`):
     307 s, no stall.
5. Copied both runs' `.json` and `.npz` outputs into
   `docs/results_of_record/diagnostics_2026_10/{baseline_uniform_nlos,
   mixed_propagation}/`, with a MANIFEST.md section.
6. Committed the two scripts plus everything copied into
   `results_of_record/` on branch `diagnostics-2026-10`, pushed. Nothing
   under `results/` itself was committed.

## 4. Result — the hypothesis direction holds

**Angle channel carries the multi-antenna gain.** In every model, on both
datasets, `angle_hist` alone matches or beats `full`:

| model | dataset | angle_hist (multi) | rss_hist (multi) | ray_hist (multi) |
| :--- | :--- | :--- | :--- | :--- |
| xgboost | uniform NLOS | +3.284 ± 0.267 m | +0.246 ± 0.139 m | +0.312 ± 0.190 m |
| random_forest | uniform NLOS | +3.135 ± 0.303 m | −0.149 ± 0.233 m | −0.036 ± 0.184 m |
| knn | uniform NLOS | +5.189 ± 0.124 m | −2.269 ± 0.194 m | −0.849 ± 0.270 m |
| xgboost | mixed | +2.756 ± 0.455 m | +0.338 ± 0.200 m | +0.341 ± 0.213 m |
| random_forest | mixed | +2.359 ± 0.249 m | +0.119 ± 0.137 m | +0.143 ± 0.176 m |

`rss_hist` and `ray_hist` sit near zero and mostly fail to clear their own
95% CI. `angle_hist` clears easily, every model, every dataset.

**Single-antenna gain is zero on the uniform-NLOS dataset** — every
condition, every model, CI includes zero (e.g. XGBoost `full`:
−0.143 ± 0.700 m). This is the clean half of Alon's prediction: no AoA, no
gain, exactly as expected.

**Single-antenna gain is NOT zero on the mixed dataset, for RSS-based
conditions** — this is new and not predicted:

| model | condition | single gain |
| :--- | :--- | :--- |
| xgboost | rss_hist | +1.362 ± 0.257 m (clears CI) |
| xgboost | full | +1.380 ± 0.271 m (clears CI) |
| random_forest | rss_hist | +1.989 ± 0.656 m (clears CI) |
| random_forest | full | +1.731 ± 0.769 m (clears CI) |

This sits outside what the hypothesis as stated predicts, and is **not
explained in this session** — flagged in MANIFEST.md, not interpreted
further. Candidate reasons worth checking before reading too much into it:
the mixed dataset's real LOS zones give RSS a cleaner (less multipath-masked)
range signature, which could make the RSS-vs-range derivative Alon's
hypothesis turns on behave differently in LOS than it does under uniform
NLOS. Untested.

**LOS/NLOS split (mixed dataset only) localizes the existing zone-gain
finding to the angle channel.** `history_gain_by_zone.py` already showed
history's benefit is bigger in LOS than NLOS (+15.94% vs +8.65%, Job 1,
`CONTINUE_HERE.md` §1a). This diagnostic shows that difference lives
specifically in the angle channel, not RSS or ray:

| model | angle_hist LOS gain | angle_hist NLOS gain |
| :--- | :--- | :--- |
| xgboost | +16.86% | +10.00% |
| random_forest | +14.81% | +8.76% |

`rss_hist`'s LOS/NLOS gap is much smaller (xgboost: 1.76% vs 2.50% — if
anything NLOS slightly ahead, not a clean LOS advantage).

## 5. What this means for the report

- The hypothesis's core claim — AoA carries the macro-cell history gain,
  RSS alone barely moves it — holds across both datasets and all three
  classical model families. This is citable.
- The single-antenna RSS exception on the mixed dataset is a genuine open
  thread, not yet resolved. Don't fold it into the hypothesis's reported
  support without flagging it as a discrepancy.
- Report the LOS/NLOS-by-channel breakdown as a refinement of the existing
  §6.4 finding (which channel, not just which zone), not a new claim.

## 6. Files

**New** (branch `diagnostics-2026-10`, pushed):
- `src/python/experiments_ablation/history_mechanism_diagnostic.py`
- `src/python/experiments_ablation/test_history_mechanism_diagnostic.py`
- `docs/results_of_record/mixed_propagation_2026_09/` (5 JSONs, from 2026-09-19)
- `docs/results_of_record/blocked_los_2026_09/` (5 per-seed JSONs, from 2026-09-19)
- `docs/results_of_record/diagnostics_2026_10/{baseline_uniform_nlos,mixed_propagation}/`
  (summary JSON + `errors_first_seed.npz` each)
- `docs/results_of_record/MANIFEST.md` — three new sections

**Generated, not committed** (gitignored, local only):
- `results/notebook_experiments/multi_user_poc/history_mechanism_diagnostic_*`
  (full copies of what was trimmed into `results_of_record/`)

## 7. What's next

- Send Alon the two full-run summaries and the single-antenna/mixed-dataset
  discrepancy — he'll likely want to decide whether it needs its own
  follow-up before the report cites this diagnostic.
- `FINAL_REPORT.md` still doesn't reflect this diagnostic, or the Job 1/Job 2
  results from 2026-09-19 (`CONTINUE_HERE.md`'s "prompt to open a new
  session" already flags this as the top remaining item).
- `errors_first_seed.npz` (both datasets) is sitting ready for the
  trajectory/error-distribution figures Alon's instructions mentioned —
  not yet built.
