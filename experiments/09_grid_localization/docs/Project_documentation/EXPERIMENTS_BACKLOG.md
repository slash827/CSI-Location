# Experiment backlog

Open experiments and analyses, with measured-basis cost estimates.

**Tier A** runs in under 30 minutes on the current machine. **Tier B** needs the new
box; each Tier B entry carries enough detail for a fresh Claude session to execute
it without re-deriving context.

---

## Timing basis

All estimates extrapolate from runs measured during the 2026-09-10/11 session on
the **old** machine (Python 3.11.2, torch 2.7.1+cu118, 114,633 train / 29,804 test
windows at h=5, 81 flat features):

| Operation | Measured |
| :--- | ---: |
| `load_and_prepare_data` | ~5 s |
| `DerivedCSI1DDataset` build, train + test | ~15 s |
| Flatten to dense arrays | ~10 s |
| k-NN fit + predict | ~19 s |
| XGBoost, 50 estimators | 10–26 s |
| Random Forest, 150 trees | 40–120 s |
| 1D-CNN train, early stopping (~20 epochs) | ~200 s |
| GRU (2-layer) train | ~180 s |
| 1D-CNN + attention train | ~206 s |
| Kalman/RTS sweep, 60 (Q,R) pairs × 47 users | ~165 s per model |
| Optuna XGBoost, 20 trials | 246 s at h=0 → 1262 s at h=10 |
| `error_decomposition.py` end to end | ~60 s |

The new machine should be roughly **2–3× faster on deep training** (GPU) and
**1.5–2× on tree/sklearn work** (CPU + RAM). Tier B estimates below are given for
the *old* machine, so treat them as upper bounds.

---

# Tier A — run now, under 30 minutes each

## A1. Does history help more where the ambiguity is worse?

**Question.** The mechanism says history resolves distance-ring ambiguity. The
ambiguity is *worst in LOS*, where the range-to-RSS map is clean and multipath
gives no tie-breaker. So history's benefit should be **larger in LOS zones than in
NLOS zones**.

**Why it matters.** This is a falsifiable prediction the mechanism makes, tested
on data already in hand. Confirmation is strong evidence; refutation would mean
the mechanism story needs revising. Currently we report only *aggregate* MAE per
zone (LOS 19.401 m, NLOS 18.868 m) and have never measured *history gain* per
zone.

**Method.**
1. Assign each test sample a zone by nearest Voronoi centre — the four centres are
   hardcoded in `utils/environment_viz.py` (Highway LOS `[35,15]`, Shopping NLOS
   `[95,15]`, Residential NLOS `[75,5]`, Park LOS `[60,90]`).
2. Train XGBoost at h ∈ {0, 1, 3, 5} on the full training set.
3. Report ΔMAE vs h=0 **within each zone** and within the LOS/NLOS aggregate.
4. Control for confounds: report mean BS range per zone alongside, since zone and
   range are correlated and range drives error independently (§7.5).

**Estimate.** 4 depths × ~35 s + data prep ≈ **5 minutes**.

**Expected output.** A 4×4 table (zone × depth) of MAE and ΔMAE. Success criterion
stated in advance: LOS gain exceeding NLOS gain by more than the range confound
explains.

---

## A2. Does AoA validity masking generalise beyond the 1D-CNN?

**Question.** Masking is currently a **1D-CNN-only** result (§7.6). It is a
*feature-pipeline* fix, not an architectural one, so it should help any model that
consumes the derived features.

**Why it matters.** If it generalises, contribution C4 stops being an
architecture trick and becomes a second mechanism-level claim, structurally
parallel to the history claim — *"here is an encoding fix that improves every
model."* That is a substantially stronger paper.

**Method.**
1. Build the derived features twice: unmasked (dummy `(0°,0°)` for
   single-antenna) and masked (`sin=cos=0`, `ray_x=ray_y=0`, plus a
   `has_valid_aoa` channel).
2. Train k-NN, Random Forest and XGBoost at h=5 on each.
3. Report overall / multi-antenna / single-antenna MAE for both arms.

**Estimate.** 3 models × 2 arms × ~60 s + prep ≈ **10 minutes**.

**Reference point.** The 1D-CNN result to beat or match: single-antenna
33.607 → 32.188 m (−4.22%), multi-antenna 15.408 → 15.279 m (+0.84%).

---

## A3. Fit the path-loss exponent and shadow fading per Voronoi zone

**Question.** The range-resolution argument (§7.5, and the deck's range-physics
slide) uses textbook γ = 4 and σ = 6 dB. What are they actually, in this data?

**Why it matters.** It converts an illustrative slide into a measured one. The
σ_range bound (32.9 m at 95 m range) is load-bearing for the claim that the
multi-antenna radial error of 13.69 m is *better* than naive path-loss ranging —
and that claim is currently resting on assumed constants.

**Method.** Per zone, regress `rss` on `10·log10(r)` where `r` is range to the
serving BS. Slope gives −γ, residual std gives σ. Report per zone and pooled, then
recompute the σ_range table with fitted values.

**Estimate.** Pure pandas/numpy on 144 k rows ≈ **3 minutes**.

---

## A4. Extend the tree-ensemble depth sweep past h=10

**Question.** XGBoost had not turned at h=10 (19.027 m, still improving). Where
*is* its optimum?

**Why it matters.** §5.4 claims tree ensembles improve monotonically "over the
range tested" — an honest but unsatisfying hedge. Finding the actual turn, or
showing there isn't one up to a feature-count limit, closes it.

**Method.** XGBoost at h ∈ {10, 15, 20, 30}. Note feature count grows as
`13(h+1) + 3`, so h=30 is 406 features; watch for the point where dimensionality
rather than staleness becomes binding.

**Estimate.** 4 depths, cost grows with h; ~**15 minutes**.

---

## A5. Seed repeats for the cheap models

**Question.** Every number in the report is a single-seed point estimate.

**Why it matters.** A reviewer will ask for confidence intervals, and the smaller
claimed deltas (+2.2% feature ablation, +0.84% multi-antenna masking gain) are not
obviously larger than seed noise. Establishing the noise floor on the cheap models
tells us whether those claims survive.

**Method.** XGBoost and k-NN at h ∈ {0, 5}, seeds {42, 1, 7, 13, 99}. The seed
drives both the user split and model initialisation, so this captures split
variance too — which is the dominant term with only 47 test users.

**Estimate.** 2 models × 2 depths × 5 seeds × ~35 s ≈ **12 minutes**.

**Watch for.** If split variance turns out large, the user split itself should be
reported as k-fold over users rather than a single 80/20, which would be a
protocol change worth making before submission.

---

# Tier B — new machine

Each entry is written so a fresh Claude session can execute it cold.

## B1. Disentangle history depth from elapsed time ★ highest value

**Question.** Is the h=5 optimum about *six samples* or about *two and a half
seconds*?

**Why it matters.** This is the largest unexamined confound in the study (§9.3).
Step duration is `spacing / speed`, and speed spans 0.12–14.89 m/s, so per-user Δt
ranges 0.27–32.5 s and the h=5 window covers **1.3 s to 162 s** depending on the
user. Every history result is averaged over that spread. Until it is separated,
"h=5 is optimal" can only mean "six samples", and any physical interpretation in
terms of coherence or decorrelation time is unsupported.

**Method.**
1. Partition test users into the four generating speed classes: static
   (0.1–0.5 m/s), pedestrian (1.0–1.5), jogger (2.5–4.5), vehicle (8.0–15.0).
   Derive per-user speed as `4.0 / median(delta_t)` — the grid pitch is 4 m — or
   read `speed_m_s` directly from the dataframe.
2. Sweep h ∈ {0, 1, 3, 5, 10} and report MAE **per speed class**, not pooled.
3. Plot gain against *window duration in seconds* (h · Δt) as well as against h.
   If the optimum aligns across classes in seconds, the effect is temporal; if it
   aligns in samples, it is a model-capacity effect.
4. Run on at least the 1D-CNN (fixed-window, turns) and XGBoost (does not turn),
   since §5.4 says these behave differently.

**Setup.** Start from `experiments_ablation/knn_sweep_and_rts_retune.py`, which
already has the data-loading and flattening scaffolding; add the speed-class
grouping and swap in the two models.

**Estimate.** 2 models × 5 depths × (train + per-class eval). CNN dominates:
5 × 200 s = ~17 min, XGBoost ~5 min, plus prep. **≈ 45 minutes on the old
machine**, likely ~20 on the new one. Class sizes are unequal (vehicles ~25% of
users, static ~10%), so report per-class n alongside.

**Success criterion.** Stated in advance: if per-class optima coincide in *samples*
(all at h=5) the effect is architectural; if they coincide in *seconds* the effect
is physical. Either outcome is publishable; the current pooled result is not
interpretable.

---

## B2. Seed repeats with confidence intervals, all models

**Question.** Confidence intervals on every headline number.

**Method.** Seeds {42, 1, 7, 13, 99} × all seven model families at h=5. Report
mean ± 95% CI for overall, multi-antenna and single-antenna MAE. Reuse
`experiments_ablation/rts_retune_all_models.py`, which already trains all seven
under one protocol — strip the RTS sweep and loop over seeds instead.

**Estimate.** 5 seeds × ~7 min of training per full sweep ≈ **35 minutes** for the
deep models plus ~10 for the classical ones. **≈ 45 minutes.**

**Note.** With 47 test users, split variance likely dominates initialisation
variance. Report both if the runs allow separating them (fix the split, vary only
model seed, for one configuration).

---

## B3. Extend the universality figure to all seven families

**Question.** Figure 2 shows four paradigms; the claim says *every* family.

**Why it matters.** The central claim is breadth. The figure should cover the same
set as the scorecard — k-NN, RF, XGBoost, GRU, 1D-CNN, CNN+attention, mask-aware
CNN — not a subset.

**Method.** Depth sweep h ∈ {0, 1, 3, 5, 10} for all seven, then regenerate
`universal_delta_mae_history_curves.png` with all seven curves. Keep the two-panel
layout (absolute MAE left, normalised gain right).

**Estimate.** 7 models × 5 depths. Deep models dominate: 4 deep × 5 × ~200 s =
~67 min, classical ~15 min. **≈ 1.5 hours on the old machine.**

**Validation gate.** k-NN h=0 must reproduce 27.44 m and the 1D-CNN h=5 must
reproduce ≈19.26 m before the figure is regenerated.

---

## B4. Re-run notebooks 06 and 07 to regenerate smoothed trajectory plots

**Question.** The RTS trajectory plots in NB06/NB07 — including the green smoothed
path in the report's Figure 5 — were produced with the broken `delta_t` time base.

**Why it matters.** Those figures are currently in the report and the deck with a
caveat attached. The fix is committed (`dee50dd`); the figures just need
regenerating.

**Method.** Run both notebooks end to end on the fixed code. Verify the smoothed
track now *improves* on the raw one at the notebook's default Q, or adjust Q per
§7.7 (optimum is Q ≈ 1–4 with a correct time base, not 128). Replace
`diagnostic_BEST_user_119_ant2.png` and `diagnostic_WORST_user_250_ant1.png`.

**Estimate.** Two notebooks, ~10 min of compute each plus inspection.
**≈ 30 minutes**, but interactive rather than batch.

---

## B5. Full per-depth re-tune including Random Forest

**Question.** §5.5 re-tuned XGBoost only. Random Forest is the one model whose
single-antenna error (38.904 m) is worse than the h=0 k-NN baseline, and the one
where history degraded results in the tuned 25×25 regression study.

**Method.** Optuna, 20 trials per depth, h ∈ {0, 1, 3, 5, 10}, tuned on training
users split into sub-train/validation by user id — never on test users. Mirror
`experiments_ablation/xgb_per_h_retune.py` exactly, swapping the estimator.

**Estimate.** RF costs 40–120 s per fit against XGBoost's 10–26 s, so roughly
4× the XGBoost run's 49 minutes. **≈ 3.5 hours on the old machine.** Consider
cutting to 10 trials per depth if time is tight; the XGBoost result suggests the
tuning surface is flat.

---

## B6. Targeted LOS → blocked → LOS scenario (requires MATLAB + QuaDRiGa)

**Question.** The case where history should be decisive: a UE walking a straight
sidewalk that passes behind a blocking building, so the link goes LOS → NLOS →
LOS.

**Why it matters.** This is the scenario you proposed to Alon directly. It isolates
the mechanism: during the blocked interval a snapshot model has almost nothing,
while a history model can carry the pre-blockage heading through. It also connects
naturally to non-causal (smoothed) operation, which is legitimate whenever the
application can tolerate latency.

**Method.**
1. New MATLAB runner modelled on `runners/run_multi_user_300_25x25.m`.
2. Straight-transit trajectories only, fixed heading, crossing a blocking region
   that forces an NLOS scenario assignment for a contiguous stretch.
3. Sweep h ∈ {0, 1, 3, 5, 10} and report error **as a function of position along
   the path**, so the blocked interval can be read directly.
4. Compare causal (history only) against non-causal (RTS-smoothed) operation.

**Estimate.** QuaDRiGa generation dominates — the 300-user run took hours.
A narrower scenario (say 50 users, 500 steps) should be well under that.
**Half a day, mostly simulation.** Requires MATLAB and QuaDRiGa v2.8.1 installed
on the new machine.

---

# Analysis-only, no compute

## C1. Related Work (§10 / technical documentation §10)

Still a TODO stub. Needs to cover classical RSS fingerprinting, geometric
ToA/TDoA/AoA multilateration, sequence models for CSI, and hybrid kinematic/radio
fusion — including the contrast with Raz Weintock's concurrent work, which
balances two separate estimators where this work raises the input dimensionality
of one. Requires real citations, which have not been gathered.

## C2. Resolve the §7.2 AoA-noise provenance conflict

`technical_documentation.md` §7.2 states the headline 15×15 numbers used the
SINR-dependent noise model. The run whose numbers match exactly
(`results/multi_user_voronoi_15x15_optimal/`, BASE 28.56 / BASE_H3 50.98 /
BASE_A 80.21 / BASE_A_H3 82.42) carries a config saying `4°/5°`. One is wrong and
the artifacts cannot say which, because `experiment_config.json` never records the
`--sinr-dependent-aoa` flag.

**Fix, two parts:** add the flag to the saved config in
`pipelines/multi_user_pipeline.py` so this cannot recur, then re-run one
configuration under each noise model and match against the recorded numbers to
determine which produced them.

## C3. Consolidate the stray results tree

`experiments/results/` holds three files that exist nowhere else, created by
scripts resolving a relative `results/` path against the wrong working directory.
Move them into the main tree and fix the offending script, or the new machine will
grow a second results tree too.

---

# Suggested order

1. **A1 and A2 first.** Cheap, need no new data, and both directly strengthen the
   central claim — A1 tests a prediction the mechanism makes, A2 potentially
   promotes C4 to a mechanism-level contribution.
2. **A3, A5** — convert assumed constants to measured ones, and establish the
   noise floor before defending any small delta.
3. **B1** once the new machine is live. It is the most likely reviewer objection
   and the answer is currently unknown.
4. **B3, B2** to make the universality figure and the error bars match the claims.
5. **B4, C2, C3** as cleanup.
6. **B5, B6** last — expensive, and neither blocks the current claims.
