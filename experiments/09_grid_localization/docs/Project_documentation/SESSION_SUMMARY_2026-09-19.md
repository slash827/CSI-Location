# Session Summary — 2026-09-19

Machine migration to a new laptop (RTX 5060, Blackwell) was completed, and both
remaining MATLAB + QuaDRiGa jobs from `CONTINUE_HERE.md` were run to
completion: **Job 1** (Campaign B mixed LOS/NLOS re-run) and **Job 2** (B6,
the targeted LOS→blocked→LOS scenario). Both required real engineering fixes
before they would run at all, not just "press go." This doc is a narrative
record of what happened, why, and what it means for the report and for
whoever picks this up next. `CONTINUE_HERE.md` has the terse, load-bearing
version of the same information (§1a, §1b, §3, §4, §7) — this doc is the
readable companion, not a replacement.

---

## 1. Starting point

The previous session had left two MATLAB jobs blocked purely by an expired
trial licence on the old machine — QuaDRiGa itself had never actually run.
This session began with a fresh MATLAB R2026a install (licensed) and
QuaDRiGa 2.8.1 on the new machine, confirmed working, then attempted Job 1.

## 2. Job 1 — Campaign B mixed LOS/NLOS re-run

### 2.1 What it's for

The project's central claim is that transition history helps every model
family. A secondary, more specific prediction is that history should help
**more in LOS than in NLOS** propagation, because LOS gives a clean,
ambiguous range-to-RSS map that history can disambiguate, while NLOS
multipath already gives each position a distinctive signature. This
prediction had been tested once before and the result was **withdrawn**: the
dataset used for that test turned out to contain no real LOS samples at all
(a runner bug silently ran every user under uniform NLOS, see below), so the
"LOS vs NLOS" split was really just two arbitrary geometric regions of an
identical NLOS map.

### 2.2 The crash, and its root cause

`run_multi_user_300_25x25_mixed.m` (committed previously, never executed) was
believed to be the fix: assign every walk snapshot to its nearest of four
Voronoi cells (two LOS zones, two NLOS zones), build QuaDRiGa
`segment_index` at each cell boundary, and let `get_channels()`'s automatic
`merge()` step stitch the per-segment channels into one continuous track.

It ran cleanly for 2 of 12 batches (50 users), then crashed:

```
Unable to perform assignment because the size of the left side is 2-by-1-by-34-by-2
and the size of the right side is 2-by-1-by-58-by-2.
Error in qd_channel/merge (line 203)
```

Tracing this into QuaDRiGa's own source revealed the cause: `merge.m`
computes its path-index remapping **once**, from a track's first segment,
via `init_path_indices.m`, and reuses that mapping unchanged for every later
segment. `3GPP_38.901_UMi_LOS` has `NumClusters=12`; `_NLOS` has
`NumClusters=20` — a structurally different number of propagation paths.
Any user whose walk crosses an LOS↔NLOS boundary — which, given the whole
point of the mixed run, is most users — hits this deterministically. It
isn't a tuning problem; no segment-length threshold or random seed avoids
it. The two batches that succeeded simply hadn't yet processed a user whose
walk crossed a boundary.

### 2.3 The actual fix

Rewrote the channel-generation loop so each Voronoi segment is its own
**independent single-scenario, single-segment** `qd_track` with its own
`get_channels()` call — QuaDRiGa's `merge()` is never invoked. Verified this
was an acceptable trade-off before committing to it: `SC_lambda` (the
spatial-consistency correlation distance for both scenarios) is 7–15 m,
while segments run 28–128 m long, so this only discards about one
correlation-length of large-scale-parameter continuity at each boundary —
and it doesn't matter at all for LOS↔NLOS crossings specifically, since
those never had coefficient continuity in the merged design either (the
cluster models are structurally different). The ML pipeline only ever
consumes scalar `rss`/`sinr`/`aoa_az`/`aoa_el` per snapshot, never raw
channel coefficients, so this is invisible downstream.

One extra bug surfaced during smoke-testing: QuaDRiGa's own channel-naming
convention splits a track name on the *first* underscore, expecting exactly
`TxName_RxName`. Naming segments `UE1_seg1` broke that parsing with an
unrelated-looking error. Renamed to `UE1S1` (no underscore) and it worked.

A 6-user smoke test then passed cleanly with the correct physics (LOS RSS
higher than NLOS RSS by 8–23 dB across users). The full 300-user run
followed, taking 265.9 minutes — two of its twelve batches individually
stalled for 65–145 minutes each, consistent with the machine sleeping
mid-run rather than any computational problem (confirmed: not a GPU/CUDA
issue like the one described below, since QuaDRiGa's channel generation is
pure CPU MATLAB code).

### 2.4 Results

All four §3 sanity checks passed: correct config flags, all four zones
populated (76.9% LOS / 23.1% NLOS), segments per user in the tens with zero
truncation events across all 300 users, and a 16.87 dB population-level
LOS-vs-NLOS RSS gap holding in 96.7% of users who visited both zone types.

Five Python analyses were then run against the new dataset:

| Script | Result |
| :--- | :--- |
| `master_benchmark_rerun.py` | Scorecard regenerated; MAE dropped 1.5–3.9 m vs. the uniform-NLOS baseline — expected, since 76.9% LOS is a structurally easier propagation mix, not itself evidence of anything |
| `history_gain_by_zone.py` | **The withdrawn claim is reversed.** History's benefit is **+15.94% in LOS vs +8.65% in NLOS** (+7.29 pp). Range confound checked and clean: LOS mean range (90.1 m) is *shorter* than NLOS (96.8 m), so it can't be inflating the LOS gain |
| `fit_pathloss_per_zone.py` | Independently fitted path-loss exponents are physically correct: LOS γ=2.58, NLOS γ=3.60 — confirms the fix produced genuinely different propagation physics, not just an RSS offset |
| `history_sweep_all_models.py` | **7/7 model families still improve with history**, 11.3–23.3% gains, six of seven peak at h=10 |
| `seed_repeats_all_models.py` | **All 7 families significant at 95% CI**, gains 11.37–15.43% — closely matching the original uniform-NLOS result (11.0–14.7%) |

`history_gain_by_zone.py` (and the `multi_user_200_pipeline.py` loader it
depends on) were also edited to read the real per-snapshot `is_los` /
`voronoi_zone_name` fields the fixed runner now saves, instead of
re-deriving zones from coordinates — with a fallback to the old geometric
method for datasets that don't have these fields (the uniform-NLOS
baseline). `fit_pathloss_per_zone.py` was **not** updated the same way —
left as an optional follow-up.

### 2.5 An unplanned but necessary detour: the migrated Python environment

Running `master_benchmark_rerun.py` the first time surfaced a second, wholly
unrelated bug: the GRU model, which should train in a few minutes, took
**27,853 seconds (7.7 hours)**. The log explained why:

```
NVIDIA GeForce RTX 5060 Laptop GPU with CUDA capability sm_120 is not compatible
with the current PyTorch installation.
```

Two things were actually broken, both artifacts of the machine migration
rather than of this project's code:

1. The migrated `.venv/pyvenv.cfg` pointed at a Python 3.11 install path
   that didn't exist on the new machine — installing Python 3.11.2 via
   `winget` happened to land at the exact path the old config expected,
   bringing the existing `site-packages` back to life with zero reinstalls.
2. The inherited `torch==2.7.1+cu118` pin has no kernels for the RTX 5060's
   Blackwell architecture. It doesn't error, it silently falls back to CPU —
   `torch.cuda.is_available()` still returned `True` throughout, which is
   why this wasn't obvious until a training step took absurdly long.
   Reinstalling `torch/torchvision/torchaudio` against the `cu128` CUDA
   index fixed it, confirmed with a direct GPU matmul + GRU forward-pass
   timing test (not just the `is_available()` check). The exact same GRU
   training step then took 189.9 seconds — a **147× speedup**, same
   hardware, same code, only the CUDA build changed.

`requirements.txt`'s pin and its own migration-instructions header comment
were updated to match. **Lesson for any future machine migration:** if a
deep-learning training step takes wildly longer than its documented
runtime, suspect a silent CPU fallback before assuming the hardware is slow
— `torch.cuda.is_available()` alone is not sufficient evidence the GPU is
usable; check `torch.cuda.get_device_capability()` against what the
installed build actually supports.

---

## 3. Job 2 — B6, the targeted LOS→blocked→LOS scenario

### 3.1 What it's for

The sharpest possible isolation of the mechanism (proposed directly to Alon
Levin): a UE walks a straight sidewalk that passes behind a blocking
building, so the link goes LOS→NLOS→LOS. During the blocked interval a
snapshot-only model has almost nothing to go on, while a history model
carries the pre-blockage heading through. The prediction: history's
advantage should **grow with blockage duration up to a point, then decay**
once the pre-blockage heading goes stale — a clean peak in gain-vs-width
would be strong evidence for the mechanism; a flat curve would be evidence
against it.

Neither a runner nor a config existed for this before today — both were
built from scratch, reusing Job 1's per-segment channel-generation pattern
(mandatory here, since this scenario *is* an LOS/NLOS boundary by
construction — exactly what crashes QuaDRiGa's `merge()`). Job 1's
`build_scenario_segments` segmentation helper itself was **not** reused —
B6's segmentation is simpler, always exactly three segments per user
(LOS-in, NLOS-strip, LOS-out), derived directly from the strip boundary.

### 3.2 A geometry bug caught before it corrupted the result

The first BS placement (perpendicular to the corridor, centred on the
blocking strip) put the point of minimum range-to-BS **inside the blocked
interval itself** — a 13 dB range-driven signal advantage that partly
cancelled or reversed the expected NLOS penalty. Caught in a 2-user smoke
test: one user's blocked-segment RSS came out *higher* than its LOS RSS,
backwards from physical expectation.

A second attempt (BS offset along the corridor instead of perpendicular)
traded that confound for a different one — a monotonic range ramp across
the whole corridor, so the aggregate LOS average (mixing a near segment with
a far segment) came out weaker than the blocked segment for wide straps.
Also wrong, for a different reason.

The fix that actually worked: a large BS standoff distance (500 m) so range
varies less than 2% across the entire 200 m corridor, decoupling range
essentially completely from the LOS/NLOS transition being measured. This was
validated properly — not on a single lucky user, but pooled across 12 users
(6 repeats × 2 widths), where it gave 100% consistent correct-direction
results with tight, matched gaps between strip widths (19.5 dB and 20.6 dB).
**Lesson recorded for future work: validate any new measurement geometry
against a pooled sample, not a single-user smoke test — a single user can
look right by pure luck, as happened here on the very first attempt.**

### 3.3 Two generation rounds

A first 150-user run (strip widths 5–80 m) showed gain still rising
monotonically through 80 m with no sign of decay, and the narrowest widths
(5 m, 10 m) too noisy across a 5-seed check to trust individually (std
12.5–18.7 pp on tiny per-stratum sample counts). Extended to a 360-user run
adding widths 100, 120, and 150 m, and increased repeats per combination
from 10 to 15 for better statistics on the narrow straps.

### 3.4 Result — flat, not peaked

Averaged across 5 seeds on the 360-user dataset:

| strip width (m) | mean gain | std | mean n |
| :--- | :--- | :--- | :--- |
| 5 | 24.1% | ±10.6 | 59 |
| 10 | 25.4% | ±16.2 | 90 |
| 20 | 23.8% | ±13.6 | 175 |
| 40 | 26.8% | ±4.8 | 386 |
| 80 | 31.6% | ±4.3 | 899 |
| 100 | 27.4% | ±7.5 | 1039 |
| 120 | 26.3% | ±9.2 | 1544 |
| 150 | 32.2% | ±10.3 | 1536 |

No coherent rise-then-fall. The per-seed "peak" location bounced between
width=10, 80, and 120 m depending on seed — a scatter that itself confirms
there is no stable peak, just noise riding a flat trend. Per the method's
own stated criterion, **a flat curve is evidence against the specific
predicted dynamic.** This does not mean history doesn't help inside the
blocked interval — it clearly does, 24–32% MAE reduction even at the
narrowest 5 m blockage, consistent with the universal-gain finding
established everywhere else in this project. It means the specific
"advantage grows then decays" shape was not observed in the 5–150 m range
tested.

An early version of the analysis script's peak-detection logic was too
permissive — it called any local maximum that wasn't at the array's edge a
"clean interior peak," which is trivially satisfied by a single noisy spike.
Fixed to require the peak to exceed every later point by at least 5
percentage points (a genuine sustained decline, not a one-point dip that
recovers) before calling it clean. Also fixed an unrelated bug at the same
time: `bool()`-casting two verdict fields that were numpy booleans and
silently broke the JSON serialization step.

**Caveats on this result before it goes in a report:** narrow straps
(5–20 m) have high seed-to-seed variance even at n=59–175, so only the
40–150 m range (std 4.3–10.3 pp) is trustworthy enough to call genuinely
flat; this used a single XGBoost model at only two depths (h∈{0,5}) across 5
seeds, not the full seven-family sweep or the fuller depth range other
B-block results use; and the corridor length is fixed at 200 m, so widths
beyond 150 m are not reachable without a geometry redesign (would leave
under 25 m of LOS runway on either side for the model to build a heading).

---

## 4. Documentation updated

`CONTINUE_HERE.md` — the project's single entry point for continuing on a
new machine — was updated throughout:

- Status table: both jobs marked done, with new §1a (Job 1) and §1b (Job 2)
  results sections.
- §3 (Job 1 spec): the originally-planned fix is now clearly marked as not
  working, with the crash and root cause documented, followed by what
  actually shipped.
- §4 (Job 2 spec): updated to "as executed," including the geometry-fix
  history and the flat, non-peaked result.
- §6.4: the withdrawn LOS/NLOS claim is now marked **RE-CONFIRMED**, with
  the old numbers explicitly flagged as still not citable (they were
  measured on a broken dataset) even though the general prediction now
  holds on real data.
- §7 (process failures worth not repeating): four new entries — the
  QuaDRiGa merge path-count limitation, the track-naming underscore trap,
  the migrated-venv/silent-CPU-fallback pattern, and the BS-geometry
  range/blockage confound.
- §9 (file map): every new and modified file listed, including a note that
  Job 2's data lives in a separate `results/b6_los_blocked_los/` tree, not
  picked up by the `sim_data_300users_*` glob the other ablation scripts use.
- The "prompt to open a new session" at the top was rewritten to point at
  what's actually next (propagate into `FINAL_REPORT.md`, then C1/C2/C3),
  since both jobs it used to point at are now done.

---

## 5. Files created or changed this session

**New:**
- `src/matlab/runners/run_b6_los_blocked_los.m`
- `configs/b6_los_blocked_los_config.jsonc`
- `src/python/experiments_ablation/b6_los_blocked_los_analysis.py`
- This document, and `SESSION_SUMMARY_2026-09-19.md`'s artifact counterpart

**Rewritten:**
- `src/matlab/runners/run_multi_user_300_25x25_mixed.m` — per-segment
  independent channel generation, no QuaDRiGa merge

**Edited:**
- `src/python/experiments_ablation/history_gain_by_zone.py` — real
  `is_los`/`voronoi_zone_name` with geometric fallback
- `src/python/pipelines/multi_user_200_pipeline.py` — `load_200_users`
  extended to load the new fields
- `requirements.txt` — torch pin updated to `2.11.0+cu128`, header comment
  updated to match
- `experiments/09_grid_localization/docs/Project_documentation/CONTINUE_HERE.md`
  — see §4 above

**Generated (gitignored, local only):**
- `results/grid_localization/grid_25x25/sim_data_300users_mixed_2026-09-18_20-25-01/`
  — Job 1's dataset
- `results/b6_los_blocked_los/sim_data_b6_2026-09-19_{12-45-03,12-54-09}/`
  — Job 2's two generations (use the second, 360-user one)
- Five `results/notebook_experiments/multi_user_poc/*_2026-09-19*/` summary
  JSON directories (Job 1's five analyses)
- Multiple `b6_los_blocked_los_*` summary JSON directories (one per seed run)

---

## 6. What's next

**Needed for the research** (in the order CONTINUE_HERE.md's updated prompt
now recommends):

1. **Propagate Job 1 and Job 2's results into `FINAL_REPORT.md`.** Its §5,
   §6.4, and §7 still describe the withdrawn claim and the never-executed
   runner. This is the highest-priority remaining item — everything above is
   measured and correct but not yet in the deliverable.
2. **C1 — Related Work.** §10 of the report is still a stub.
3. **C2/C3 — cleanup.** AoA-noise provenance documentation and a stray
   results tree.

**Optional, lower priority:**

- If Job 2's flat result is going into the report with the same rigor as
  B2/B3, it would need the same treatment those got: the full seven-model
  sweep (not just XGBoost) and a fuller depth range, not just h∈{0,5}.
- `fit_pathloss_per_zone.py` could be updated to use real `is_los` data the
  same way `history_gain_by_zone.py` was, for consistency (currently still
  geometric-only).
- The open mechanism question from `CONTINUE_HERE.md` §5 (separating sample
  count from distance travelled) remains unaddressed — unrelated to this
  session's work, but still the most likely objection a reviewer raises
  after B1.

---

## 7. Reference index

| Need to know... | Look at... |
| :--- | :--- |
| Full technical detail on either job, exact numbers, sanity-check results | `CONTINUE_HERE.md` §1a, §1b, §3, §4 |
| Whether a specific old number is still citable | `CONTINUE_HERE.md` §6 |
| Process pitfalls (QuaDRiGa, naming, environment, geometry) | `CONTINUE_HERE.md` §7 |
| Where every file lives | `CONTINUE_HERE.md` §9 |
| Report's current state (not yet updated with this session's results) | `docs/Project_documentation/FINAL_REPORT.md` |
