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
> withdrawn. Both MATLAB jobs are done as of 2026-09-19 (§1a, §1b) — neither is
> reflected in `FINAL_REPORT.md` yet. Propagate those results into the report
> (§5, §6.4, §7), then pick up C1 Related Work or the C2/C3 cleanup items. Do
> not cite any number from `master_benchmark_summary.json` or from a Google
> Doc snapshot without checking it against §6 of this file first.

---

## 1. Where things stand

Every Python experiment, Job 1, and Job 2 are complete.

| Block | Status | Backing |
| :--- | :--- | :--- |
| Tier A (A1–A5) | done 2026-09-13 | `results_of_record/ablations_2026_09/` |
| Tier B (B1–B5) | done 2026-09-14 | same |
| Master benchmark re-run | done 2026-09-14 | `master_benchmark_rerun_summary.json` |
| **Job 1 — Campaign B mixed propagation** | **done 2026-09-19** | see §1a below |
| **Job 2 — B6, LOS→blocked→LOS** | **done 2026-09-19** | see §1b below |
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

### 1a. Job 1 results (2026-09-19)

Campaign B mixed LOS/NLOS re-run completed. The runner
(`run_multi_user_300_25x25_mixed.m`) had to be rewritten first — see §3 for what
changed and why. Dataset:
`results/grid_localization/grid_25x25/sim_data_300users_mixed_2026-09-18_20-25-01/`
(gitignored, local only). Zone occupancy: 76.9% LOS (highway 30.0%, park 46.9%),
23.1% NLOS (shopping_center 14.1%, residential 9.0%).

* **§6.4 is reversed.** The LOS/NLOS mechanism prediction is now **SUPPORTED** on
  real mixed-propagation data for the first time: history's benefit is
  **+15.94% in LOS vs +8.65% in NLOS** (+7.29 pp), `history_gain_by_zone.py`.
  Range confound checked and clean: LOS mean range (90.1 m) is *shorter* than
  NLOS (96.8 m), so the range confound can't be inflating the LOS gain — if
  anything it works against the effect.
* Path-loss exponents fit independently per zone are physically sensible: LOS
  γ=2.58, NLOS γ=3.60 (`fit_pathloss_per_zone.py`) — confirms the mixed data is
  physically correct, not just an RSS offset artifact.
* Universality holds on the new data: **7/7 model families improve with
  history**, 11.3–23.3% gains, six of seven peak at h=10 (only k-NN peaks at
  h=5, consistent with §6.3) — `history_sweep_all_models.py`.
* Seed-paired confidence intervals: **all 7 families significant at 95% CI**,
  gains 11.37–15.43% — `seed_repeats_all_models.py`, closely matching the
  original uniform-NLOS B2 result (11.0–14.7%).
* `master_benchmark_rerun.py` re-run on the mixed dataset; MAE dropped
  1.5–3.9 m across every model vs. the uniform-NLOS baseline. Expected on
  structural grounds (76.9% LOS samples is an easier propagation mix than
  100% NLOS) — not itself evidence of anything, that's what the per-zone
  scripts above are for.

All four summary JSONs are under
`results/notebook_experiments/multi_user_poc/{master_benchmark_rerun,
history_gain_by_zone, pathloss_fit, history_sweep_all_models,
seed_repeats_all_models}_2026-09-19*/`. None of this is reflected in
`FINAL_REPORT.md` yet — the report's §5, §7, and the §6.4 discussion still
describe the withdrawn claim and need updating to cite these new numbers.

### 1b. Job 2 results (2026-09-19) — flat, not peaked; evidence against the specific prediction

New runner `run_b6_los_blocked_los.m` and config
`configs/b6_los_blocked_los_config.jsonc` (neither existed before today).
Straight corridor, far-standoff BS (see §4 for why — two closer geometries
were tried and rejected for range/blockage confounds). Two generations: an
initial 150-user run at strip widths [5,10,20,40,80] m, then an extended
360-user run adding [100,120,150] m after the first showed gain still rising
at the widest width tested with no sign of turning over. Datasets:
`results/b6_los_blocked_los/sim_data_b6_2026-09-19_{12-45-03 (150u),
12-54-09 (360u, use this one)}/` (gitignored, local only).

**Verdict, from `b6_los_blocked_los_analysis.py` run across 5 seeds on the
360-user dataset (widths 5–150 m):**

| width (m) | mean gain | std | mean n |
| :--- | :--- | :--- | :--- |
| 5 | 24.1% | ±10.6 | 59 |
| 10 | 25.4% | ±16.2 | 90 |
| 20 | 23.8% | ±13.6 | 175 |
| 40 | 26.8% | ±4.8 | 386 |
| 80 | 31.6% | ±4.3 | 899 |
| 100 | 27.4% | ±7.5 | 1039 |
| 120 | 26.3% | ±9.2 | 1544 |
| 150 | 32.2% | ±10.3 | 1536 |

**Flat, not peaked.** Gain within the blocked interval hovers 24–32% across
the whole tested range with no coherent rise-then-fall; the per-seed "peak"
location bounced between width=10, 80 and 120 depending on seed — a scatter
that itself shows there's no stable peak, just noise riding a flat trend. Per
the method's own stated criterion (§4): *"a flat curve is evidence against."*
That is the result. **History still helps substantially inside the blocked
interval** (24–32% MAE reduction even at 5 m) — consistent with the universal
gain established elsewhere — but the specific "advantage grows with blockage
duration then decays once the pre-blockage heading goes stale" dynamic is
**not supported** in this range. Do not report a peak from this data; report
the flat curve as a (mild) negative result on the mechanism's specific
functional form, not on whether history helps.

Caveats before citing this: (1) narrow straps (5–20 m) have high seed-to-seed
variance (std 10.6–16.2 pp) even at n=59–175, so their individual numbers are
unreliable — only the 40–150 m range (std 4.3–10.3 pp) is trustworthy enough
to call genuinely flat; (2) this used a single XGBoost model per depth, not
the seven-family sweep — unconfirmed whether other model families show the
same flat pattern; (3) corridor length is fixed at 200 m, so widths beyond
150 m were not reachable without redesigning the geometry (would leave
under 25 m of LOS runway on each side).

`fit_pathloss_per_zone.py`-equivalent per-zone check was not re-run for B6;
`history_gain_by_zone.py` is grid/Voronoi-specific and does not apply here.

---

## 2. Before running anything: the MATLAB licence

Both Job 1 and Job 2 were gated on this — kept here for any future MATLAB work.

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

## 3. Job 1 — Campaign B re-run with mixed LOS/NLOS propagation (DONE 2026-09-19)

Converted the withdrawn §6.4 claim back into a testable one, and confirmed it.
Results in §1a above. What follows is kept for the record — the runner
described here as "the fix" is **not** what actually ran; see the crash and
the real fix below before reusing any of this for Job 2.

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

### The originally-planned fix (does NOT work — QuaDRiGa crash)

The plan below builds `segment_index` correctly and was believed sufficient:

* assigns every snapshot to its nearest Voronoi cell;
* builds `segment_index` at each cell change, **set before `trk.scenario`**, because
  `no_segments` is derived from it;
* absorbs runs shorter than `MIN_SEG_LEN = 4` into the preceding segment.

It ran cleanly for two batches (50 users), then crashed deterministically the
moment a user's walk crossed an LOS↔NLOS boundary:

```
Unable to perform assignment because the size of the left side is 2-by-1-by-34-by-2
and the size of the right side is 2-by-1-by-58-by-2.
Error in qd_channel/merge (line 203)
```

**Root cause:** `3GPP_38.901_UMi_LOS` has `NumClusters=12`, `_NLOS` has
`NumClusters=20` (QuaDRiGa's own scenario `.conf` files) — a different
`no_path`. `qd_channel/merge.m`'s `init_path_indices.m` computes the
path-index mapping **once**, from a track's *first* segment, and reuses it
unchanged for every later segment. It has no mechanism for a later segment
whose own path count differs from the first. This is architectural, not a
tuning problem — no `MIN_SEG_LEN` or seed choice avoids it. Two batches
succeeded only because none of those particular users' walks happened to
cross a LOS/NLOS *type* boundary yet.

### The actual fix: per-segment independent channels, no merge

`runners/run_multi_user_300_25x25_mixed.m` was rewritten to generate **each
Voronoi segment as its own single-scenario, single-segment `qd_track`**, with
its own `get_channels()` call — sidestepping `merge()` entirely. Checked
against the scenario configs first: `SC_lambda` (spatial-consistency
correlation distance, 7–15 m for both scenarios) is far shorter than a
typical segment (28–128 m at `MIN_SEG_LEN=4`, 2 m spacing), so this only
discards about one correlation-length of large-scale-parameter continuity at
each boundary — small, and it doesn't apply to LOS↔NLOS crossings anyway
(those never had coefficient continuity even in the original merged design,
since the cluster models are structurally different). The ML pipeline only
consumes scalar `rss`/`sinr`/`aoa_az`/`aoa_el` per snapshot, never raw channel
coefficients, so this is invisible downstream.

One naming trap hit during this rewrite: **do not put an underscore in a
`qd_track.name`.** QuaDRiGa's own channel-naming convention
(`get_channels.m`, `merge.m`) splits track names on the *first* underscore
expecting exactly `TxName_RxName`; a name like `UE1_seg1` breaks that parsing
with an unrelated-looking error (`rx_order` assignment size mismatch). Use
`UE1S1` instead.

`sim_config.channel_generation = 'per_segment_independent'` is saved in every
mixed dataset's `simulation_config.json` as a provenance marker.

### Run it

```matlab
cd experiments/09_grid_localization/src/matlab
addpath(genpath('<path>/quadriga_src'));

% segmentation logic only, no QuaDRiGa needed — run this first
results = runtests('tests/TestScenarioSegments'); disp(results)

run_multi_user_300_25x25_mixed
```

Output: `results/grid_localization/grid_25x25/sim_data_300users_mixed_<timestamp>/`.

**Budget ~1–4.5 hours.** The per-segment rewrite is much faster per batch than
the merge-based design once it fails to crash (a 6-user smoke test ran batches
at ~18s/user; the full 300-user run took 265.9 min, but two of its twelve
batches individually stalled 3900–8700 s consistent with the machine
sleeping mid-run — watch for that if running unattended).

### Sanity checks before trusting the output (all passed 2026-09-19)

1. `simulation_config.json` says `quadriga_scenario: "mixed_voronoi"` and
   `mixed_scenario: true`. ✓
2. The zone-occupancy table in the log shows all four zones non-empty, LOS
   zones at roughly 60–75% of samples. Actual: 76.9% LOS — a touch above the
   expected band but not concerning (see §1a). ✓
3. Segments per user are tens, not hundreds; zero truncation events across
   all 300 users. ✓
4. LOS-zone samples have **higher RSS at comparable BS range** than NLOS-zone
   samples. Actual: 16.87 dB population-level gap, holds in 96.7% of users
   who visited both zone types. ✓

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

`history_gain_by_zone.py` (and `multi_user_200_pipeline.py`'s `load_200_users`,
which it depends on) were edited 2026-09-19 to read real `is_los` /
`voronoi_zone_name` from the `.mat` files rather than re-deriving zones from
coordinates, with a fallback to the old geometric method for datasets that
lack these fields (the uniform-NLOS baseline). `fit_pathloss_per_zone.py`
still uses the geometric method only — not yet updated, left as an option for
whoever touches it next.

> **Keep both datasets.** The uniform-NLOS run is a legitimate single-scenario
> baseline and every current result is measured on it. Report the mixed run as the
> propagation ablation *alongside* it, or the entire report needs re-baselining at
> once.

### Environment note: the migrated `.venv` was broken, and torch silently ran on CPU

Neither of these is specific to Job 1, but both were only caught *because* of
Job 1's heavy compute, so recording them here:

* The migrated `.venv/pyvenv.cfg` pointed at a Python 3.11 install path that
  doesn't exist on a new machine. Fixed by installing Python 3.11.2 via
  `winget install --id Python.Python.3.11 --version 3.11.2`, which happened to
  land at the exact path the old config expected, bringing the existing
  `site-packages` back to life with zero reinstalls.
* The inherited `torch==2.7.1+cu118` pin has no kernels for a Blackwell GPU
  (`sm_120`, e.g. RTX 50-series). It doesn't error — it silently falls back to
  CPU. Symptom: a GRU that should train in ~3 minutes took **7.7 hours**
  (`master_benchmark_rerun.py`'s first run). Fixed by reinstalling
  `torch/torchvision/torchaudio` against the `cu128` index (see
  `requirements.txt`'s header for the exact steps) — confirmed with a direct
  GPU matmul + GRU forward-pass timing test, not just `torch.cuda.is_available()`
  (which returns `True` even when the installed build can't run kernels for
  the device's compute capability — check `torch.cuda.get_device_capability()`
  against what the installed build supports if in doubt).
* **Lesson: if any deep-model training step on a freshly-migrated machine
  takes wildly longer than its documented runtime, suspect a silent CPU
  fallback before assuming the hardware is slow.** `torch.cuda.is_available()`
  alone is not sufficient evidence the GPU is actually usable.

---

## 4. Job 2 — B6, the targeted LOS → blocked → LOS scenario (DONE 2026-09-19)

Result in §1b above: **flat, not peaked — evidence against the specific
grows-then-decays prediction**, though history still helps substantially
throughout. What follows is the original spec plus what changed executing it.

A UE walking a straight sidewalk that passes behind a blocking building, so the link
goes LOS → NLOS → LOS. The case where history should be decisive: during the blocked
interval a snapshot model has almost nothing, while a history model carries the
pre-blockage heading through. Proposed directly to Alon Levin; the sharpest isolation
of the mechanism available.

**Method, as executed.** Straight-line trajectories at constant speed
crossing a rectangular NLOS strip between two LOS regions
(`run_b6_los_blocked_los.m`, `configs/b6_los_blocked_los_config.jsonc` — both
new, not reused from Job 1). `build_scenario_segments` from
`run_multi_user_300_25x25_mixed.m` was **not** reused as originally planned —
B6's segmentation is simpler (always exactly 3 segments per user: LOS-in,
NLOS-strip, LOS-out, derived directly from the strip boundary, no absorption
logic needed). What *was* mandatory to carry over was the channel-generation
pattern: each segment generated as its own independent single-scenario
`qd_track` and `get_channels()` call, never a single multi-segment track fed
to a merged `get_channels()` — a LOS→NLOS→LOS crossing is exactly the
`merge()` path-count crash Job 1 hit (§3), and unavoidable here since this
scenario *is* the LOS/NLOS boundary. Also carried over: no underscore in any
`qd_track.name` (§3's naming trap; used `B6U{uid}S{k}`).

**Geometry required two fix cycles before the RSS came out physically
correct** — full detail and rejected alternatives are in
`b6_los_blocked_los_config.jsonc`'s `base_station` comment. Summary: BS
placement couples range to the LOS/NLOS transition unless deliberately
avoided, and that coupling can silently reverse the measured effect (blocked
segment reading a *stronger* raw signal than LOS, purely from geometry, not
propagation). The fix that worked: a large standoff distance (500 m) so range
is ~constant (<2% variation) across the whole corridor. Validate any new
geometry the same way before trusting it — per-user smoke test RSS direction
isn't enough (a single user can look right by luck, as happened here at
first); check the *pooled* direction across several repeats before scaling up.

Varied strip width (5–150 m across two generations) and speed (1.5, 4.0,
10.0 m/s); history depth $h$ swept in the Python analysis, not generation.

**Reported $\Delta\text{MAE}$ within the blocked interval specifically**, not
pooled over the walk (`b6_los_blocked_los_analysis.py`).

**Prediction, and outcome.** History's advantage should grow with blockage duration up to the
point where the pre-blockage heading stops being informative, then decay. A clean
peak is strong evidence; a flat curve is evidence against. **Result: flat** (§1b) —
gain hovers 24–32% from 5 m to 150 m with no coherent peak, and the apparent
"peak" location was unstable across seeds (10, 80, or 120 m depending on
seed) — noise on a flat trend, not a real shape. Checked with a single
XGBoost model across 5 seeds at h∈{0,5}, not the full seven-family sweep or
depth range other B-block results use — a natural next step if this result
needs to go in the report with the same rigor as B2/B3.

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

### 6.4 "The LOS/NLOS prediction is confirmed" — RE-CONFIRMED 2026-09-19, no longer withdrawn
**Was withdrawn because:** the original Campaign B contained no real LOS at all (the
mixed-scenario runner silently ran everyone under uniform NLOS; see the old §3
description, now superseded — §3 above has the real fix). The old +15.98%/+4.84%
number and the "range confound points the wrong way" supporting argument were both
measured on a homogeneous NLOS map and attributed to physics never simulated — do
not cite those specific numbers or that argument.
**Now, on the real mixed LOS/NLOS dataset (Job 1, §1a):** history's benefit is
**+15.94% in LOS vs +8.65% in NLOS** (+7.29 pp, `history_gain_by_zone.py`). Range
confound re-checked on real data and comes out clean: LOS mean range (90.1 m) is
*shorter* than NLOS (96.8 m), so it can't be inflating the LOS gain. Independently
corroborated by `fit_pathloss_per_zone.py`: LOS γ=2.58 vs NLOS γ=3.60, the expected
direction. **The mechanism prediction is SUPPORTED.**

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
* **QuaDRiGa `qd_channel/merge.m` cannot merge segments with different path
  counts** (e.g. LOS vs NLOS scenarios) — deterministic crash the first time a
  merged multi-segment track actually crosses that boundary, not a rare edge
  case. Full diagnosis in §3. Generate mismatched-scenario segments as
  independent single-segment channels instead of relying on `merge()`.
* **No underscore in a `qd_track.name`** — QuaDRiGa's own channel-naming
  convention splits on the first underscore expecting `TxName_RxName`; a name
  like `UE1_seg1` breaks that parsing with an error that looks unrelated
  (`rx_order` assignment size mismatch in `get_channels.m`).
* **A migrated `.venv` can look intact and be silently unusable or silently
  wrong** — `pyvenv.cfg` pointing at a nonexistent interpreter path fails
  loudly (easy); `torch` built for a CUDA architecture the new GPU doesn't
  support fails silently by falling back to CPU (hard — `torch.cuda.
  is_available()` still returns `True`). Both hit during Job 1; full details
  in §3's environment note. After any machine migration, time one small
  known-cost deep-learning training step before trusting a "no errors"
  result.
* **BS placement can silently couple range to whatever you're trying to
  isolate** — designing B6 (§4), two BS geometries in turn produced a
  confound where the blocked interval read a *stronger* raw signal than the
  LOS segments, purely from geometry (closest-approach point coinciding with
  or being systematically nearer than the comparison region), not
  propagation. A single-user smoke test looked fine by luck before this was
  caught at n=12. **Check the *pooled* direction across several repeats, not
  one user, before trusting a new geometry.** Fixed by a large standoff
  distance making range ~constant across the region of interest — the
  general fix whenever a manipulated variable (here, LOS/NLOS) must be
  measured independently of position.

---

## 8. Machine-specific paths

Audited 2026-09-18. **All active scripts are portable.** Four ablation scripts
hardcoded `Path('d:/gilad/projects/Academy/CSI-Location')` and were converted to
`Path(__file__).resolve().parents[5]`, matching the nine that were already portable:
`knn_sweep_and_rts_retune.py`, `per_user_process_noise.py`,
`rts_retune_all_models.py`, `xgb_per_h_retune.py`.

`setup.m` now searches for QuaDRiGa rather than assuming one location. Set
`QUADRIGA_HOME` to skip the search:

```matlab
setenv('QUADRIGA_HOME', '<path>/QuaDRiGa');
```

The MATLAB runners and every `configs/*.jsonc` were already clean — no absolute
paths at all.

### Known remaining, none of them blocking

| Location | What | Impact |
| :--- | :--- | :--- |
| `src/python/utils/environment_viz.py:276` | writes to a `.gemini/antigravity-ide/brain/…` path from a long-dead IDE session | fails only if that one function is called; the figure it makes is already committed |
| `src/python/utils/parse_terminal_output.py:103,110` | references user `gilad.battat` and a `GitHub_Personal` checkout — a *different* machine again | standalone dev utility, unused by any pipeline |
| `answers/extract_bs_parameters.m:8` | `exp11_2025-11-15…` results dir | one-off script from the exp11 era |
| `ml_training/experiments/neural_networks/debugging/*.py` | four scripts pointing at `exp11`/`exp10` dataset dirs | superseded debugging scripts |
| Various `docs/**/*.md` | `file:///d:/gilad/…` links and `cd D:\gilad\…` snippets | cosmetic; links stop resolving, prose still correct |

None of these are on the path to Job 1 or Job 2. Left as-is deliberately rather than
touched without a reason to run them.

---

## 9. File map

| Path | What it is |
| :--- | :--- |
| `docs/Project_documentation/FINAL_REPORT.md` | The deliverable. Everything above is reflected in it. |
| `docs/Project_documentation/HANDOVER_KNOWLEDGE_BASE.md` | Full project synthesis and research positioning |
| `docs/Project_documentation/EXPERIMENTS_BACKLOG.md` | Per-experiment specs and measured cost estimates |
| `docs/Project_documentation/PRESENTATION_SLIDES.md` | Marp deck, 4 acts |
| `docs/results_of_record/MANIFEST.md` | **Source of truth** for every number, with warnings on the stale files |
| `src/python/experiments_ablation/` | All ablation scripts; `model_zoo.py` holds the seven families |
| `src/matlab/runners/run_multi_user_300_25x25_mixed.m` | Job 1 — done 2026-09-19; per-segment independent channel generation, no QuaDRiGa merge (§3) |
| `src/matlab/tests/TestScenarioSegments.m` | Segmentation contract for Job 1's `build_scenario_segments` — Job 2 did NOT reuse it (§4), its own segmentation is simpler (fixed 3 segments) |
| `src/python/pipelines/multi_user_200_pipeline.py` | `load_200_users` extended 2026-09-19 to load real `is_los`/`voronoi_zone_name` when present |
| `src/matlab/runners/run_b6_los_blocked_los.m` | Job 2 — done 2026-09-19; new, not derived from Job 1's runner beyond the per-segment pattern (§4) |
| `configs/b6_los_blocked_los_config.jsonc` | Job 2 config — BS geometry comment documents two rejected confounded placements, read before changing it |
| `src/python/experiments_ablation/b6_los_blocked_los_analysis.py` | Job 2 analysis — blocked-interval MAE vs h and vs strip width; result is §1b |

`results/` is gitignored. The ablation scripts need
`results/grid_localization/grid_25x25/sim_data_300users_*` present locally; see
`SHARING.md`. Job 2's data is under `results/b6_los_blocked_los/` instead —
separate tree, not picked up by the `sim_data_300users_*` glob.

**Reproducing any September ablation:** commands and runtimes are listed in
`docs/results_of_record/MANIFEST.md`.
