# MATLAB runbook — the two simulation jobs still outstanding

Everything in this project that can be done in Python is done (see
`EXPERIMENTS_BACKLOG.md`). Two jobs remain, both MATLAB + QuaDRiGa:

1. **Campaign B re-run with genuinely mixed LOS/NLOS propagation** — fixes a real
   defect in the published dataset, and is the precondition for §5.6 of the report
   saying anything at all.
2. **B6, the targeted LOS → blocked → LOS scenario** — the experiment that isolates
   the mechanism most sharply.

Written for whoever picks this up on the new machine, including a fresh Claude
session with no memory of how any of it was found.

---

## 0. Prerequisites — check these before anything else

| Requirement | How to verify | Notes |
| :--- | :--- | :--- |
| MATLAB R2021a+ | `ver` at the MATLAB prompt | R2023b+ recommended; R2025b was used |
| **A valid licence** | `license('test','MATLAB')` returns `1` | See the warning below |
| QuaDRiGa **v2.8.1** | `which qd_layout` resolves | Newer versions change the `qd_layout` API |
| Toolboxes | Communications, Phased Array, Statistics & ML | |
| Campaign B input data | not needed — these jobs *generate* data | |

> **The old machine was blocked purely by an expired licence.** MATLAB R2025b and
> QuaDRiGa 2.8.1 were both installed at `/d/programs/QuaDRiGa/quadriga_src`, but the
> licence was a trial (`licenses/trial_*.lic`, `LicenseNo: DEMO`) whose every
> `INCREMENT` line expired **16-Nov-2025**. The symptom is unhelpful: `matlab -batch`
> hangs for several minutes and then exits `0x00000001` with no diagnostic and an
> empty `-logfile`. If you see that, check the licence before debugging anything
> else.

Add QuaDRiGa to the path (it must live *outside* the project directory):

```matlab
addpath(genpath('<path>/quadriga_src'));
```

---

## 1. Campaign B re-run with mixed propagation

### What is wrong with the current dataset

`ne_bs_voronoi_25x25_config.jsonc` declares `channel.mixed_scenario.enabled = true`
with four Voronoi cells — highway and park as `3GPP_38.901_UMi_LOS`, shopping centre
and residential as `3GPP_38.901_UMi_NLOS`.

`run_multi_user_300_25x25.m` **never reads that block**. It calls
`l.set_scenario(config_json.channel.scenario)` and assigns
`trk.scenario = {config_json.channel.scenario}` to every track, so all 300 users were
simulated under one uniform `UMi_NLOS` profile. The run's own saved
`simulation_config.json` records `quadriga_scenario: 3GPP_38.901_UMi_NLOS`, which is
how to confirm it on any existing dataset.

Consequence: the four "zones" exist only as labels applied afterwards by nearest
Voronoi centre (in `utils/environment_viz.py` and
`experiments_ablation/history_gain_by_zone.py`). Two regions of a homogeneous NLOS map
were being called LOS.

A second, independent defect sits in `core/generate_simulation_data.m`: it builds one
scenario string per track *segment* but never sets `segment_index`, so a `qd_track`
keeps its default single segment and the whole walk inherits the scenario of its first
position. Per-position mixing requires explicit segmentation. Campaign A went through
that file, so **Campaign A's mixed scenarios are also suspect** and should be checked
the same way.

### The fix

`runners/run_multi_user_300_25x25_mixed.m` (committed, never executed). It:

* reads `mixed_scenario` and assigns every snapshot to its nearest Voronoi cell;
* builds `segment_index` at each cell change, **set before `trk.scenario`** because
  `no_segments` is derived from it;
* absorbs runs shorter than `MIN_SEG_LEN = 4` into the preceding segment, since
  QuaDRiGa merges neighbouring segments across an overlap region and a two-snapshot
  segment gives that merge nothing to work with;
* saves real per-snapshot `voronoi_cell_id`, `voronoi_scenario`, `voronoi_zone_name`
  and `is_los` — the old runner saved the *grid point id* under the name
  `voronoi_cell_id`, which is why the Python side had to re-derive zones;
* keeps the `rng(42)` manifest draw order **byte-identical** to the uniform run, so
  the two datasets are comparable user by user;
* clamps to the available snapshot count if segment merging returns fewer snapshots
  than the track had, and logs when it does.

### Run it

```matlab
cd experiments/09_grid_localization/src/matlab
addpath(genpath('<path>/quadriga_src'));

% smoke test first — segmentation logic only, no QuaDRiGa needed
results = runtests('tests/TestScenarioSegments'); disp(results)

% then the real thing
run_multi_user_300_25x25_mixed
```

Output lands in
`results/grid_localization/grid_25x25/sim_data_300users_mixed_<timestamp>/`.

**Expect hours.** The original 300-user run took hours on the old machine, and this
one is strictly more expensive: segmented tracks mean QuaDRiGa builds and merges a
channel per segment rather than one per user.

### Sanity checks before trusting the output

1. `simulation_config.json` says `quadriga_scenario: "mixed_voronoi"` and
   `mixed_scenario: true`.
2. The run log's zone-occupancy table shows all four zones non-empty, with LOS zones
   at roughly 60–75% of samples (the LOS cells are larger in this layout).
3. Segment counts per user are sane — tens, not hundreds. Hundreds means
   `MIN_SEG_LEN` is too small for the trajectory patterns.
4. Spot-check that LOS-zone samples have **higher** RSS at comparable BS range than
   NLOS-zone samples. If they do not, the scenarios are still not being applied.

### Then, on the Python side

The ablation scripts glob `sim_data_300users_*` and take the **last** match, so the
mixed run will be picked up automatically once it exists — which is convenient and
also a trap. Decide deliberately which dataset each result refers to, and pass an
explicit path where it matters.

Re-run, in this order:

```bash
E=experiments/09_grid_localization/src/python/experiments_ablation
.venv/Scripts/python $E/master_benchmark_rerun.py       # new baseline scorecard
.venv/Scripts/python $E/history_gain_by_zone.py         # A1 — now a real LOS/NLOS test
.venv/Scripts/python $E/fit_pathloss_per_zone.py        # A3 — now separates propagation from range
.venv/Scripts/python $E/history_sweep_all_models.py     # B3 — universality figure
.venv/Scripts/python $E/seed_repeats_all_models.py      # B2 — CIs on the new numbers
```

`history_gain_by_zone.py` should read `is_los` from the `.mat` files rather than
re-deriving zones from coordinates — that is a small edit worth making once the data
exists.

> **Recommendation: keep both datasets.** The uniform-NLOS run is a legitimate
> single-scenario baseline and every current result is measured on it. Report the
> mixed run as the propagation ablation *alongside* it rather than replacing
> everything, or the whole report needs re-baselining at once.

---

## 2. B6 — the targeted LOS → blocked → LOS scenario

### The question

A UE walking a straight sidewalk that passes behind a blocking building, so the link
goes LOS → NLOS → LOS. This is the case where history should be decisive: during the
blocked interval a snapshot model has almost nothing, while a history model can carry
the pre-blockage heading through. It also connects naturally to non-causal (smoothed)
operation, which §7.7 shows is where the smoothing gain actually lives.

This scenario was proposed directly to Alon Levin and is the sharpest isolation of the
mechanism available.

### Method

Straight-line trajectories at constant speed, crossing a rectangular NLOS strip
between two LOS regions. Build it with explicit `segment_index` on the track, exactly
as `run_multi_user_300_25x25_mixed.m` does — the helper `build_scenario_segments` in
that file is directly reusable and its contract is covered by
`tests/TestScenarioSegments.m`.

Vary: strip width (blockage duration), speed, and history depth $h$.

Report $\Delta\text{MAE}$ **within the blocked interval specifically**, not pooled
over the walk. The pooled number will be diluted by the LOS segments where history
matters less.

### Prediction being tested

History's advantage should grow with blockage duration up to the point where the
pre-blockage heading stops being informative, then decay. A clean peak would be
strong evidence for the mechanism as stated; a flat curve would be evidence against.

---

## 3. The third open question, if there is appetite

**Separating sample count from distance travelled** (Limitation 3 in the report).

B1 established that the useful history window is *spatial*, not temporal: per-class
optimal window durations span 1.6 s to 134.7 s, so the optimum is not a fixed time.
But because every walk step advances exactly one grid cell, $h$ is simultaneously a
sample count and a path length ($h=5$ is 20 m for every user regardless of speed).
Which of the two governs the optimum is still open.

Two ways to break the tie, both simulation changes:

* variable step length at fixed speed, or
* fixed step length with a variable sampling rate.

The upstream simulator (Omri Israeli's, see §4.2 of the report) already exposes
`position_update_dt` and `csi_report_interval` as **independent** config parameters,
which is exactly the decoupling needed — hold speed fixed, vary the reporting
interval, and distance per sample moves while the walk does not.

---

## 4. Things not to re-derive

Read `CORRECTIONS_LEDGER.md` before touching the report. Several plausible-sounding
claims in earlier drafts were measured and withdrawn, and the raw numbers behind them
are still in `results_of_record/` where they can easily be picked up again by mistake.
