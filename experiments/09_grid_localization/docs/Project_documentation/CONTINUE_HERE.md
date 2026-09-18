# CONTINUE HERE

Single entry point for continuing this project on a new machine. Self-contained:
current state, what remains, how to run it, and every claim that was measured and
withdrawn so it does not get reintroduced.

**Project:** 5G NR CSI-based UE localization. Central claim: a short window of
**transition history** supplies whichever degree of freedom the hardware lacks, and
it improves *every* model family rather than producing one best model.

---

## Prompt to open the new session with

> Read `experiments/09_grid_localization/docs/Project_documentation/CONTINUE_HERE.md`
> and confirm your understanding: what is done, what remains, and which claims were
> withdrawn. Then check whether MATLAB has a valid licence
> (`license('test','MATLAB')`) and, if it does, start Job 1 — the Campaign B re-run
> with mixed LOS/NLOS propagation. Do not cite any number from
> `master_benchmark_summary.json` or from a Google Doc snapshot without checking it
> against §6 of this file first.

---

## 1. Where things stand

Every Python experiment is complete. Two MATLAB + QuaDRiGa jobs remain.

| Block | Status | Backing |
| :--- | :--- | :--- |
| Tier A (A1–A5) | done 2026-09-13 | `results_of_record/ablations_2026_09/` |
| Tier B (B1–B5) | done 2026-09-14 | same |
| Master benchmark re-run | done 2026-09-14 | `master_benchmark_rerun_summary.json` |
| **Job 1 — Campaign B mixed propagation** | **not started** | runner committed, never executed |
| **Job 2 — B6, LOS→blocked→LOS** | **not started** | §4 below |
| C1 Related Work | not started | §10 of the report is a stub |
| C2 AoA-noise provenance, C3 stray results tree | not started | cleanup |

What Tier B established, in one line each:

* **B1** — the useful history window is **spatial, not temporal**. Per-speed-class
  optimal durations span 1.6 s to 134.7 s, but every walk step advances exactly one
  4 m grid cell, so a fixed $h$ is a fixed *distance*. Report §5.8.
* **B2** — the central claim now has confidence intervals. All seven families gain
  **11.0–14.7%**, every one significant, 35 seed-paired trials with no failures.
  Report §5.7.
* **B3** — Figure 2 rebuilt from a single protocol, all seven families, 12.5–19.3%.
  Report §5.4.
* **B4** — Figures 5 and 6 regenerated on the fixed time base; established the
  smoothing gain is **entirely non-causal**. Report §7.7.
* **B5** — per-depth re-tuning of Random Forest is a **null result** (−0.046 to
  +0.066 m). Report §5.5.

---

## 2. Before running anything: the MATLAB licence

Both remaining jobs are gated on this one thing.

```matlab
license('test','MATLAB')   % must return 1
ver                        % R2021a+; R2023b+ recommended
which qd_layout            % QuaDRiGa must be v2.8.1 exactly
```

> **The old machine was blocked purely by an expired trial licence** — not by
> hardware, and not by a missing QuaDRiGa. `licenses/trial_*.lic`, `LicenseNo: DEMO`,
> every `INCREMENT` line expired **16-Nov-2025**. The symptom is actively
> misleading: `matlab -batch` hangs for several minutes, then exits `0x00000001`
> with no diagnostic and an **empty** `-logfile`. If you see that, check the licence
> before debugging anything else.

QuaDRiGa must live *outside* the project directory:

```matlab
addpath(genpath('<path>/quadriga_src'));
```

Newer QuaDRiGa versions change the `qd_layout` API. Use 2.8.1.

---

## 3. Job 1 — Campaign B re-run with mixed LOS/NLOS propagation

**This is the highest-value remaining item.** It converts a withdrawn claim (§6.4
below) back into a testable one.

### What is wrong with the current dataset

`configs/ne_bs_voronoi_25x25_config.jsonc` declares
`channel.mixed_scenario.enabled = true` with four Voronoi cells — highway and park as
`3GPP_38.901_UMi_LOS`, shopping centre and residential as `3GPP_38.901_UMi_NLOS`.

`runners/run_multi_user_300_25x25.m` **never reads that block**. It calls
`l.set_scenario(config_json.channel.scenario)` and assigns
`trk.scenario = {config_json.channel.scenario}` to every track, so all 300 users ran
under one uniform `UMi_NLOS` profile. Confirm on any existing dataset by checking its
saved `simulation_config.json` for `quadriga_scenario: 3GPP_38.901_UMi_NLOS`.

So the four "zones" exist only as labels applied afterwards by nearest Voronoi centre
(`utils/environment_viz.py`, `experiments_ablation/history_gain_by_zone.py`). Two
regions of a homogeneous NLOS map were being called LOS.

**A second, independent defect:** `core/generate_simulation_data.m` builds one
scenario string per track *segment* but never sets `segment_index`, so a `qd_track`
keeps its default single segment and the whole walk inherits the scenario of its
first position. Campaign A goes through that file, so **Campaign A's mixed scenarios
are also suspect** and should be checked the same way.

### The fix

`runners/run_multi_user_300_25x25_mixed.m` — committed, never executed. It:

* assigns every snapshot to its nearest Voronoi cell;
* builds `segment_index` at each cell change, **set before `trk.scenario`**, because
  `no_segments` is derived from it;
* absorbs runs shorter than `MIN_SEG_LEN = 4` into the preceding segment — QuaDRiGa
  merges neighbouring segments across an overlap region, and a two-snapshot segment
  gives that merge nothing to work with;
* saves real per-snapshot `voronoi_cell_id`, `voronoi_scenario`, `voronoi_zone_name`
  and `is_los`. The old runner saved the *grid point id* under the name
  `voronoi_cell_id`, which is why the Python side had to re-derive zones;
* keeps the `rng(42)` manifest draw order byte-identical to the uniform run, so the
  two datasets stay comparable user by user;
* clamps to the available snapshot count if segment merging returns fewer snapshots
  than the track had, and logs when it does.

### Run it

```matlab
cd experiments/09_grid_localization/src/matlab
addpath(genpath('<path>/quadriga_src'));

% segmentation logic only, no QuaDRiGa needed — run this first
results = runtests('tests/TestScenarioSegments'); disp(results)

run_multi_user_300_25x25_mixed
```

Output: `results/grid_localization/grid_25x25/sim_data_300users_mixed_<timestamp>/`.

**Expect hours.** The original 300-user run took hours, and this one is strictly more
expensive — segmented tracks mean QuaDRiGa builds and merges a channel per segment.

### Sanity checks before trusting the output

1. `simulation_config.json` says `quadriga_scenario: "mixed_voronoi"` and
   `mixed_scenario: true`.
2. The zone-occupancy table in the log shows all four zones non-empty, LOS zones at
   roughly 60–75% of samples (the LOS cells are larger in this layout).
3. Segments per user are tens, not hundreds. Hundreds means `MIN_SEG_LEN` is too
   small for these trajectory patterns.
4. LOS-zone samples have **higher RSS at comparable BS range** than NLOS-zone
   samples. If not, the scenarios still are not being applied — stop and debug.

### Then re-run the Python side

The ablation scripts glob `sim_data_300users_*` and take the **last** match, so the
mixed run is picked up automatically once it exists. Convenient, and a trap — be
deliberate about which dataset each result refers to.

```bash
E=experiments/09_grid_localization/src/python/experiments_ablation
.venv/Scripts/python $E/master_benchmark_rerun.py       # new baseline scorecard
.venv/Scripts/python $E/history_gain_by_zone.py         # A1 — now a real LOS/NLOS test
.venv/Scripts/python $E/fit_pathloss_per_zone.py        # A3 — separates propagation from range
.venv/Scripts/python $E/history_sweep_all_models.py     # B3 — universality figure
.venv/Scripts/python $E/seed_repeats_all_models.py      # B2 — CIs on the new numbers
```

`history_gain_by_zone.py` should be edited to read `is_los` from the `.mat` files
rather than re-deriving zones from coordinates — a small change, worth making once
the data exists.

> **Keep both datasets.** The uniform-NLOS run is a legitimate single-scenario
> baseline and every current result is measured on it. Report the mixed run as the
> propagation ablation *alongside* it, or the entire report needs re-baselining at
> once.

---

## 4. Job 2 — B6, the targeted LOS → blocked → LOS scenario

A UE walking a straight sidewalk that passes behind a blocking building, so the link
goes LOS → NLOS → LOS. The case where history should be decisive: during the blocked
interval a snapshot model has almost nothing, while a history model carries the
pre-blockage heading through. Proposed directly to Alon Levin; the sharpest isolation
of the mechanism available.

**Method.** Straight-line trajectories at constant speed crossing a rectangular NLOS
strip between two LOS regions. Build it with explicit `segment_index` exactly as Job
1 does — `build_scenario_segments` in `run_multi_user_300_25x25_mixed.m` is directly
reusable and its contract is covered by `tests/TestScenarioSegments.m`.

Vary strip width (blockage duration), speed, and history depth $h$.

**Report $\Delta\text{MAE}$ within the blocked interval specifically**, not pooled
over the walk — the pooled number is diluted by the LOS segments.

**Prediction.** History's advantage should grow with blockage duration up to the
point where the pre-blockage heading stops being informative, then decay. A clean
peak is strong evidence; a flat curve is evidence against.

---

## 5. The remaining open question about the mechanism

**Separating sample count from distance travelled** (Limitation 3 in the report).

B1 showed the useful window is spatial, not temporal. But because every walk step
advances exactly one grid cell, $h$ is simultaneously a sample count and a path
length ($h=5$ is 20 m for every user regardless of speed). Which of the two governs
the optimum is still open, and it is the objection a reviewer is most likely to raise
after B1.

Two ways to break the tie, both simulation changes:

* variable step length at fixed speed, or
* fixed step length with a variable sampling rate.

The upstream simulator this project builds on (Omri Israeli's, credited in report
§4.2, <https://github.com/Omri154/5G-Massive-MIMO-Simulator>) already exposes
`position_update_dt` and `csi_report_interval` as **independent** parameters — hold
speed fixed, vary the reporting interval, and distance per sample moves while the
walk does not.

---

## 6. Claims that were measured and withdrawn — do not reintroduce

Every superseded number below is still sitting in `results_of_record/` and in older
Google Doc snapshots. Each is plausible and quotable. Check this list before citing.

**Rule of thumb:** a difference below **~0.5 m** overall, or below **~5 m** in any
single-antenna figure, is not a result. Measured noise floor is in report §5.7.

### 6.1 "The GRU is the best model"
**Was:** GRU best at 18.518 m, explained by recurrent gates extracting motion
derivatives trees cannot express.
**Now:** re-run puts GRU at 19.355 m, **fifth of six**; the five-seed repeat puts it
fourth inside a six-way tie. The six $h=5$ models span 0.74 m against a 1.85 m
marginal seed spread.
**Replacement:** no architecture wins. Given history, a convolution, a boosted tree
ensemble and a recurrent network are indistinguishable on this task.

### 6.2 "Random Forest's single-antenna error is worse than the baseline"
**Was:** RF 38.904 m vs $k$-NN $h{=}0$ baseline 37.142 m; inferred axis-aligned
splits fragment the temporal signal.
**Now:** both were single-seed estimates of the noisiest quantity in the study.
Across five seeds RF is 36.27 ± 2.35 m, the baseline 46.17 ± 3.13 m — **RF leads by
about 10 m**. Confirmed directly: RF single-antenna is 33.069 m at seed 42,
reproduced identically by B2, B3 and B5.

### 6.3 "Fixed-window estimators turn; tree ensembles do not"
**Was:** the 1D-CNN rises 19.260 → 20.215 m from $h{=}5$ to $h{=}10$.
**Now:** the single-protocol sweep gives 19.268 → 19.146 m — it does not turn. The
runs agree at $h{=}5$ and differ by 1.07 m at $h{=}10$, about twice the paired CI.
**Replacement:** only $k$-NN turns, and it is the one deterministic estimator in the
set. Six of seven families are still improving at $h{=}10$. The architectural
explanation survives only as a hypothesis.

### 6.4 "The LOS/NLOS prediction is confirmed"
**Was:** history worth +15.98% in LOS vs +4.84% in NLOS, a 3.3× difference.
**Now:** **Campaign B contains no LOS** (§3 above). The measured per-region gains
(+4.38% to +18.75%) are real but isolate a purely *geometric* contribution.
**Also do not reintroduce** the supporting argument that "the range confound points
the wrong way because the LOS stratum has shorter mean range" — with propagation
uniform, that attributed a geometric difference to physics never simulated.

### 6.5 "$h=5$ is the universal optimum" and "$h=5 \approx 2.5$ s"
**Now:** two separate corrections. The optimum is $h{=}10$ or beyond for six of seven
families (§5.4). And the window is spatial: $h{=}5$ is **20 m of path**, $h{=}10$ is
**40 m**, for every user regardless of speed. Convert depth to distance, never to
time.

### 6.6 "Smoothing degrades every model by 28–48%"
**Now:** that was a bug. `DerivedCSI1DDataset` standardises `SIGNAL_COLS` in place and
`delta_t` is one of them, so the smoother received z-scores rather than seconds —
85.8% negative, clamped to 0.01 s by `max(0.01, dt)`, destroying the state
transition. Fixed in `dee50dd`.
**Replacement:** properly configured, smoothing is worth +2.5% to +4.7%. **But the
gain is entirely non-causal** — the forward Kalman pass alone, at the same tuned
$Q,R$, *degrades* the 1D-CNN by 3.4%. Smoothing suits latency-tolerant applications
only; transition history is fully causal.
**Still invalid:** every `rts_*` field in `campaign_b/master_benchmark_summary.json`,
and the `rts_retune` block in `ablations_2026_09/knn_sweep_rts_retune_summary.json`.

### 6.7 "Boundary crossings cost +1.45 m"
**Now:** sign was inverted. Within-cell 19.34 m vs crossing 18.33 m — crossings are
**1.00 m easier**. QuaDRiGa's spatial consistency prevents transient discontinuities.

### 6.8 "Random walk at 1.5 m/s"
**Now:** four heading-persistent patterns (billiards, momentum walk, waypoint tour,
straight transit), speeds 0.12–14.89 m/s. Matters because a true random walk would be
*adversarial* to history, so the old description undersold the result.

### 6.9 Figure 2 mixed three experiments
**Was:** four hardcoded curves. Only the 1D-CNN was Campaign B; XGBoost and RF came
from the July 200-user sweeps; the GRU curve came from a **single-user** exploration
with a *chronological* split, 3D MAE and raw AoA angles — which is why it read 8.5 m
and −50% where the disjoint-user protocol gives 18.5 m.
**Now:** generated from `history_sweep_all_models_summary.json`, all seven families,
one protocol. `plot_unified_delta_mae.py` reads that JSON, so hardcoded curves cannot
return.

### 6.10 `master_benchmark_summary.json` has drifted generally
Five of seven models reproduce within 0.6 m, but RF is 1.47 m off overall and 5.84 m
off on single-antenna, and the $k$-NN baseline's single-antenna figure is 5.07 m off.
It came from a notebook with no script in the repo, which is why it drifted.
**Cite `ablations_2026_09/master_benchmark_rerun_summary.json` for §6 instead.**

---

## 7. Process failures worth not repeating

* **Non-raw Python strings containing `\text`** — `\t` becomes a tab, the assertion
  fires, and because the exception precedes the file write, **every earlier edit in
  the same script is silently discarded**. This bit twice and went unnoticed for
  hours both times. Use the `Edit` tool, or raw strings, and assert before writing.
* **`s.replace()` without asserting the pattern matched** — silently no-ops. One
  figure edit was lost this way and only caught by looking at the rendered PNG.
* **PowerShell here-strings (`@'...'@`) in a Bash tool** — produced a commit whose
  subject was literally `@`. Use heredocs with quoted delimiters.
* **Windows `MAX_PATH`** — `Compress-Archive` fails on long paths. Build archives
  somewhere short.
* **Git over an intercepting TLS proxy** — `unable to get local issuer certificate`
  while `curl` returns 200. Fix with `git config --local http.sslBackend schannel`.
  Do **not** disable verification.
* **Deep-model per-user MAE is not stable across runs** — the same configuration gave
  user 119 a raw MAE of 9.97, 12.08 and 10.29 m on three runs. Population MAE is
  stable to ~0.2 m. Quote population figures; treat per-user numbers as illustrative.

---

## 8. File map

| Path | What it is |
| :--- | :--- |
| `docs/Project_documentation/FINAL_REPORT.md` | The deliverable. Everything above is reflected in it. |
| `docs/Project_documentation/HANDOVER_KNOWLEDGE_BASE.md` | Full project synthesis and research positioning |
| `docs/Project_documentation/EXPERIMENTS_BACKLOG.md` | Per-experiment specs and measured cost estimates |
| `docs/Project_documentation/PRESENTATION_SLIDES.md` | Marp deck, 4 acts |
| `docs/results_of_record/MANIFEST.md` | **Source of truth** for every number, with warnings on the stale files |
| `src/python/experiments_ablation/` | All ablation scripts; `model_zoo.py` holds the seven families |
| `src/matlab/runners/run_multi_user_300_25x25_mixed.m` | Job 1, committed and unexecuted |
| `src/matlab/tests/TestScenarioSegments.m` | Segmentation contract for Jobs 1 and 2 |

`results/` is gitignored. The ablation scripts need
`results/grid_localization/grid_25x25/sim_data_300users_*` present locally; see
`SHARING.md`.

**Reproducing any September ablation:** commands and runtimes are listed in
`docs/results_of_record/MANIFEST.md`.
