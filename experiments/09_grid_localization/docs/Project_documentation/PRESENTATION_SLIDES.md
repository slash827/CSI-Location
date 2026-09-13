---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { font-size: 21px; }
  table { font-size: 17px; }
  h1 { font-size: 36px; color: #1a3a5c; }
  h2 { font-size: 27px; color: #1a3a5c; }
  h3 { font-size: 21px; color: #1a3a5c; }
  strong { color: #c0392b; }
  blockquote { font-size: 19px; border-left: 3px solid #1a3a5c; padding-left: 14px; color: #445; }
---

<!-- _paginate: false -->

# Breaking the Distance Ring

### Transition history as a universal mechanism for single-BS 5G NR localization

**Gilad Battat** · Bar-Ilan University
Advisors: Prof. Sarit Kraus, Prof. David Sarne · Industry: CEVA, Cellcom

*QuaDRiGa 3GPP TR 38.901 · 300-user macro-cell · 7 model families · 2026*

---

## The positioning of this work

**Not:** *"we trained a better localization model."*
Vulnerable — anyone can publish a new model next week, and our absolute error is not state of the art.

**Instead:** *"here is a mechanism that improves every model."*

> "If you claim you have the best model, someone can say 'everybody creates a new model every day'. Whereas if you suggest an improvement to the mechanism, you don't need to show you have the best results — just that you're improving the results for every single model."
> — Alon Levin, 20 Aug 2026

**Consequences for how we report:**
- Primary metric is **ΔMAE against each model's own h=0 baseline**, not a leaderboard
- The claim is **falsifiable**: one model family where history fails would refute it
- Absolute MAE is context, not the headline

---

## Act 1 — The problem: distance-ring ambiguity

A single base station measures **range well and bearing poorly**.

Under log-distance path loss, $\text{RSS} \approx P_{tx} - 10\gamma\log_{10} r + \chi$:

- the inverse map identifies $r$ (up to shadow fading $\chi$)
- it leaves bearing $\phi$ **completely unconstrained**

In polar coordinates, **a snapshot observes one of the two degrees of freedom it needs.** Every position on an iso-power ring looks alike.

This is the accuracy ceiling of classical RSS fingerprinting, and it is worst in LOS, where the range-to-RSS map is clean and there is no multipath diversity to break the tie.

**SINR and AoA can supply bearing — but conditionally.** SINR needs calibrated interferers; AoA needs UE beamforming hardware a large fraction of devices do not have.

---

## The ambiguity, observed directly

Single-antenna UEs have **zero** AoA capability. They are the distance-ring ambiguity in isolation:

| Cohort | Mean angular error | P90 | 2D MAE |
|---|---:|---:|---:|
| 4-antenna | **3.53°** | 7.08° | 15.50 m |
| 2-antenna | **3.69°** | 7.61° | 15.23 m |
| 1-antenna | **15.76°** | 33.94° | 33.80 m |

The model predicts **range correctly and bearing not at all** — error smears along the arc of the right circle.

![bg right:44% 96%](../figures/diagnostic_angular_tracking_multi_vs_single.png)

---

## Act 2 — The mechanism

A **moving** UE breaks the symmetry for free.

Stack the current observation with $h$ previous ones:

```
h=0 (snapshot):  [ m(t) ]
h=1:             [ m(t-1), m(t) ]
h=5:             [ m(t-5) ... m(t) ]
```

Consecutive observations of a spatially-consistent channel make two quantities computable that a snapshot cannot expose:

- **radial velocity** — $\dfrac{d\text{RSS}}{dt} \propto -\dfrac{10\gamma}{\ln 10}\cdot\dfrac{\dot r}{r}$ → motion along the BS bearing
- **angular rate** — $\dot\theta = v_\perp / r$ → motion across it

Together they constrain position to a range ring **intersected with a motion-consistent arc**.

---

## Result 1: every algorithm improves

**7×7 grid, RSS+SINR, h=0 vs h=3:**

| Algorithm | h=0 Acc | h=3 Acc | Δ | MAE h=0 | MAE h=3 |
|---|---|---|---|---|---|
| Gaussian | 10.9% | 15.5% | +4.6 pp | 5.03 m | 4.37 m |
| Random Forest | 28.0% | 43.6% | +15.6 pp | 3.90 m | 2.51 m |
| **XGBoost** | **26.9%** | **45.1%** | **+18.2 pp** | **3.93 m** | **2.39 m** |
| MLP | 24.8% | 41.6% | +16.8 pp | 4.16 m | 2.62 m |

Four algorithms spanning probabilistic, ensemble, boosted and neural families. **All four improve.**

---

## The universal ΔMAE curve

Four algorithmic paradigms, same data, same protocol — only the input window varies.

**1D-CNN depth sweep (300-user macro cell):**

| $h$ | 2D MAE | Step Δ | Cumulative gain |
|---|---:|---:|---:|
| 0 | 22.846 m | — | baseline |
| 1 | 21.284 m | **−1.562 m** | **+6.8%** |
| 3 | 20.026 m | −1.258 m | +12.3% |
| 5 | **19.260 m** | −0.766 m | **+15.7%** |
| 10 | 20.215 m | +0.955 m | +11.5% |

**The first extra frame does 44% of the work** — exactly where velocity becomes computable.

![bg right:40% 95%](../figures/universal_delta_mae_history_curves.png)

---

## But the optimum is model-class dependent

A finding that changes how the claim must be stated:

| Estimator | $h=0$ | $h=5$ | $h=10$ | Behaviour |
|---|---:|---:|---:|---|
| 1D-CNN | 22.846 | **19.260** | 20.215 | **turns** (+0.955 m) |
| k-NN | 27.440 | **23.983** | 24.485 | **turns** (+0.502 m) |
| XGBoost | 22.349 | 19.434 | **19.027** | still improving |
| XGBoost (Jul, raw feats) | 28.325 | 25.404 | **25.002** | still improving |
| Random Forest (Jul) | 27.704 | 25.945 | **25.880** | still improving |

**Fixed-window estimators turn; tree ensembles do not.** A tree simply never splits on an uninformative lag. A convolution over a fixed window, and a distance metric over a fixed vector, must consume every position in it.

→ *"History always helps"* is supported. *"h=5 is the universal optimum"* is **not**.

---

## And the gain is not a capacity artifact

**Objection:** enlarging the input space without re-fitting capacity is not a controlled comparison. Earlier runs even showed history *hurting* tree ensembles.

**Test:** per-depth Optuna re-tuning of XGBoost (20 trials each). Tuned on training users only; test users touched once.

| $h$ | Fixed defaults | Per-depth tuned | Gain (default) | Gain (tuned) |
|---|---:|---:|---:|---:|
| 0 | 22.349 m | 21.906 m | — | — |
| 1 | 21.117 m | 21.199 m | +5.51% | +3.23% |
| 3 | 19.801 m | 19.657 m | +11.40% | +10.27% |
| 5 | 19.434 m | 19.072 m | +13.04% | +12.94% |
| 10 | **19.027 m** | **18.968 m** | **+14.87%** | **+13.41%** |

Monotone under **both** regimes; re-tuning buys at most 0.44 m. **The anomaly does not reproduce — no "provided you re-tune" qualifier is needed.**

---

## Result 3: it holds at every scale

**XGBoost, RSS+SINR, single-user grids, 9 → 400 classes:**

| Grid | Classes | h=0 | h=1 | h=2 | h=3 | Gain |
|---|---|---|---|---|---|---|
| 3×3 | 9 | 53.4% | 57.9% | 60.0% | **62.8%** | **+9.4 pp** |
| 5×5 | 25 | 39.1% | 49.0% | 51.7% | **53.1%** | **+14.0 pp** |
| 7×7 | 49 | 26.9% | 36.8% | 39.1% | **41.1%** | **+14.2 pp** |
| 10×10 | 100 | 33.8% | 49.7% | 54.5% | **55.6%** | **+21.8 pp** |
| 15×15 | 225 | 13.8% | 23.6% | 27.0% | **29.1%** | **+15.3 pp** |
| 20×20 | 400 | 13.4% | 20.9% | **22.6%** | 22.4% | **+9.2 pp** |

Six grid sizes, no OOM, gain at every scale.

---

## The decisive test: does it survive bad geometry?

Move the serving BS from **grid centre (360° azimuth spread)** to a **corner (52° wedge)** and re-run everything.

| Effect | Centre BS | NE-corner BS | |
|---|---:|---:|---|
| **AoA** gain (BASE_H3 → BASE_A_H3) | +31.4 pp | **+2.3 pp** | collapses ~14× |
| **History** gain (BASE → BASE_H3) | +22.4 pp | **+28.8 pp** | *grows* |

**AoA's value is a property of the deployment. History's is not.**

This is the strongest single argument that transition history is a mechanism rather than a configuration-specific trick: it survives precisely the change that destroys the competing information source.

---

## Act 3 — Realistic scale: 300-user macro cell

- **Area:** 96 × 96 m, 25×25 grid at 4 m pitch
- **Serving BS:** [116, 116, 10] m — off-grid to the NE, range **21–157 m**
- **Interferers:** two pushed SW towers. SINR counts *only* these two plus noise — **no UE-to-UE interference**
- **Population:** 300 users, **disjoint train/test user IDs** — zero-shot over trajectory *and* device
- **Hardware mix:** 85% multi-antenna (4-ant, 2-ant) + 15% single-antenna IoT
- **Mobility:** four heading-persistent patterns (billiards, momentum walk, waypoint tour, straight transit), speeds 0.12–14.89 m/s

> **Caution for reading every h result:** step duration is spacing/speed, so a fixed $h$ is **not** a fixed time window. Per-user Δt spans 0.27–32.5 s, making the $h{=}5$ window anywhere from **1.3 s to 162 s**.

![bg right:38% 92%](../figures/environment_spatial_layout.png)

---

## Master cross-model scorecard (h = 5)

| Model | Params | Train | 2D MAE | P50 | Multi-ant 85% | Single-ant 15% |
|---|---:|---:|---:|---:|---:|---:|
| k-NN (h=0 baseline) | — | 0.0 s | 27.857 m | 23.892 m | 25.356 m | 37.142 m |
| Random Forest | 6.5 M | 121 s | 20.884 m | 16.801 m | 16.032 m | 38.904 m |
| **XGBoost** | **12.8 K** | **26 s** | 19.314 m | 15.469 m | 15.199 m | 34.598 m |
| **GRU (2-layer)** | 187.8 K | 255 s | **18.518 m** | **14.560 m** | **14.500 m** | 33.440 m |
| 1D-CNN | 66.5 K | 333 s | 19.330 m | 15.430 m | 15.394 m | 33.946 m |
| 1D-CNN + attention | 199.7 K | 231 s | 19.172 m | 15.377 m | 15.233 m | 33.801 m |
| Mask-aware 1D-CNN | 66.7 K | 173 s | 19.250 m | 15.959 m | 15.713 m | **32.383 m** |

- Deep temporal models lead, but only by ~4%
- **XGBoost is the deployment answer**: within 4% of the best on **12.8 K parameters and 26 seconds**
- Every row shows the same cohort split — no architecture closes it

---

## Where does the error actually live?

Decompose each error into **range** (along the BS bearing) and **bearing** (perpendicular):

| Cohort | Total | Radial (range) | Tangential (bearing) | Radial share |
|---|---:|---:|---:|---:|
| All users | 19.43 m | 14.93 m | 9.14 m | 73% |
| **Multi-antenna** | 15.29 m | **13.69 m** | 4.71 m | **89%** |
| **Single-antenna** | 34.81 m | 19.53 m | **25.60 m** | 37% |

**This reverses the naive reading.** For the 85% majority, **bearing is essentially solved** — 4.71 m tangential matches the geometric prediction $R\tan(3.5°) = 5.6$ m at 92 m mean range. Their bottleneck is **range**.

For single-antenna devices the mirror image holds: 25.60 m tangential vs a prediction of 26.0 m. Purely geometric failure.

→ **History supplies whichever degree of freedom the hardware lacks** — bearing for AoA-blind devices, range for AoA-capable ones at macro distance.

---

## Why range is the bottleneck at macro range

RSS sensitivity to range falls off as $1/r$:  $\dfrac{d\,\text{RSS}}{dr} = \dfrac{10\gamma}{r \ln 10}$ dB/m

| Operating range | dB per metre | $\sigma_{\text{range}}$ at 6 dB shadow fading |
|---|---:|---:|
| ~10 m (15×15 centre BS) | 1.737 | 3.5 m |
| ~40 m (15×15 NE BS) | 0.434 | 13.8 m |
| **~95 m (macro median)** | **0.182** | **32.9 m** |
| ~126 m (macro p90) | 0.138 | 43.6 m |

At 95 m, one metre of displacement moves RSS by **0.18 dB** — far below the shadow-fading floor.

The measured multi-antenna radial error of 13.69 m is **well inside** the 32.9 m naive bound — evidence that history, SINR and elevation contribute real range information beyond raw path loss.

*(γ = 4 and 6 dB assumed; not fitted per Voronoi zone.)*

---

## The hardware cohort discontinuity

| Cohort | Share | 2D MAE | P50 | P90 |
|---|---:|---:|---:|---:|
| 4-antenna | ~45% | 14.843 m | 12.607 m | 28.555 m |
| 2-antenna | ~40% | 14.371 m | 12.074 m | 28.020 m |
| **Multi-antenna combined** | **85%** | **14.580 m** | **12.310 m** | 28.250 m |
| **1-antenna (IoT)** | **15%** | **34.538 m** | **30.232 m** | 65.991 m |

The break is **binary, not a gradient**: 2-ant and 4-ant are statistically indistinguishable. What matters is $N \ge 2$ (bearing observable) vs $N = 1$ (not).

**Reporting one population mean of 19.3 m describes no actual device.** Outlier audit: 100% of the five worst users are 1-antenna, 100% of the five best are multi-antenna.

![bg right:40% 96%](../figures/antenna_cohort_error_cdf.png)

---

## Mitigation: stop telling the model the angle is zero

**Problem.** AoA-blind devices are conventionally fed dummy $(0°, 0°)$. Then $\cos(0°) = 1$ and $\text{ray}_y = r_{est}$ — asserting a *confident* bearing along +y. The network is not uninformed, it is **misinformed**, and the false anchor pollutes shared kernels via gradients.

**Fix.** Zero the trig embeddings so $\sin^2\theta + \cos^2\theta = 0$ — strictly off the unit circle, so filters can distinguish *"no angle"* from *"angle = 0°"*. Zero the ray vectors. Add a binary `has_valid_aoa` channel.

| Metric | Unmasked | Masked | Δ |
|---|---:|---:|---:|
| Overall 2D MAE | 19.269 m | **18.866 m** | −0.403 m (+2.09%) |
| Multi-antenna | 15.408 m | **15.279 m** | −0.129 m (+0.84%) |
| **Single-antenna** | 33.607 m | **32.188 m** | **−1.419 m (+4.22%)** |
| Single-ant angular error | 15.84° | **14.83°** | −1.01° |

**Both cohorts improve** — the multi-antenna gain is *cross-cohort gradient protection*. Cost: one channel, 0.2 K parameters.

---

## Act 4 — What this does not establish

- **Simulation only.** Spatial consistency — the precondition for the whole mechanism — is a model property here. No field validation.
- **A fixed $h$ is not a fixed time window.** Speed spans two orders of magnitude, so the $h{=}5$ window covers 1.3 s to 162 s across users. **Every history result averages over widely different temporal horizons.** This is the biggest unexamined confound.
- **Synthetic mobility.** Heading-persistent and speed-diverse, but generated on a grid graph — not measured traces.
- **Cohort mix is assumed**, not measured. Results are sensitive to the 85/15 split.
- **Single-seed point estimates.** No confidence intervals yet — matters most for the smaller deltas (+2.2%, +0.84%).
- **Not state-of-the-art absolute accuracy.** 14.58 m at 100 m range is respectable for single-BS, not competitive with multi-BS or UWB. That was never the claim.

---

## Two live issues, stated openly

**1. A defect we found and fixed.** The Kalman/RTS smoother was being handed *z-scored* `delta_t` instead of seconds — 85.8% of steps clamped to a 0.01 s timestep. Every published smoothing number was measuring that bug.

Corrected: at default settings smoothing is roughly neutral (−1.8% to +10.4%, not −44%), and properly tuned it is worth **+2.5% to +4.7%**. **All raw MAE results are unaffected** — the defect only ever touched post-processing.

**2. A single global process noise is the wrong model.** For a population spanning 0.12–14.89 m/s, scaling per user as $q_u = k\,v_u$ beats the best global setting for every model tested (XGBoost +4.35% → **+5.66%**).

> Same lesson as the antenna cohorts, on a different axis: **population heterogeneity has to be modelled explicitly.**

---

## Summary

1. **A mechanism, not a model.** Transition history reduces error in **every** family tested — trees, k-NN, GRU, CNN, attention — measured as ΔMAE against each model's own baseline.
2. **It survives the geometry that kills AoA.** Moving the BS to a corner collapses AoA's contribution 31.4 → 2.3 pp while history's *grows* to +28.8 pp.
3. **The optimum is architectural, not physical.** Fixed-window models turn at h=10; tree ensembles keep improving. And the gain is not a capacity artifact — it survives per-depth re-tuning.
4. **Error is range-limited, not bearing-limited, for 85% of users.** 89% of multi-antenna error is radial. History supplies whichever degree of freedom the hardware lacks.
5. **Heterogeneity must be explicit.** Antenna cohorts reported separately; per-user process noise beats a global constant.
6. **Deployable cheaply.** XGBoost at h=5: 96% of the best accuracy on 12.8 K parameters and 26 s of training.

---

## Next

1. **Disentangle history depth from elapsed time** — sweep $h$ *within* each speed class, so "six samples" stops being confounded with "thirteen seconds". Highest value, since every current h result averages across a 1.3–162 s spread.
2. **Seed-repeated runs with confidence intervals** on all reported deltas.
3. **Extend the depth sweep past h=10** for tree ensembles — they had not saturated at the deepest window tested.
4. **A targeted LOS → blocked → LOS scenario** — a UE passing a blocking building, where history should be decisive and non-causal smoothing is legitimate.
5. **Field or measured-trace validation.**

---

<!-- _paginate: false -->

# Appendix

---

## A1: Feature progression (10×10 Voronoi, XGBoost)

*Source: `results/experiment_matrix/2026-02-26_07-54-19/experiment_results.csv`*

| Feature set | h=0 Acc | h=1 Acc | h=1 MAE | h=3 Acc |
|---|---:|---:|---:|---:|
| RSS only | 18.80% | 23.15% | 5.699 m | 26.51% |
| SINR only | 18.80% | 22.94% | 5.745 m | 26.30% |
| RSS + SINR | 18.80% | 22.96% | 5.717 m | 26.43% |
| RSS + SINR + CQI | 18.80% | 22.96% | 5.717 m | 26.43% |
| **+ AoA azimuth** | 69.63% | **77.93%** | **0.581 m** | 78.94% |
| **+ AoA elevation** | 84.60% | **88.54%** | **0.246 m** | 88.30% |

**Two things stand out:**
- **RSS ≈ SINR ≈ RSS+SINR ≈ +CQI, identical to three decimals.** Without interference they are all driven by the same path loss — SINR adds no independent spatial information, and CQI is a quantized function of SINR.
- **AoA azimuth alone is worth +55 pp**; elevation adds a further +11 pp by encoding distance through the BS-height geometry.

*A separate run (`2026-02-25_23-51-23`) adds timing advance + k-factor, reaching 93.96% / 0.132 m at h=1.*

---

## A2: Classification vs regression

**XGBoost / RF, full AoA feature set, Voronoi 4-cell, 2 m spacing:**

| Grid | Classification MAE (h=1) | Regression MAE (h=1) | Ratio |
|---|---|---|---|
| 10×10 | **0.25 m** | 0.40 m | 1.60× |
| 15×15 | **0.46 m** | 0.61 m | 1.33× |
| 20×20 | **0.85 m** | 0.98 m | **1.15×** |

Classification wins at 2 m spacing because ±0.1 m jitter ≪ grid pitch, so the label is unambiguous and the model can snap. The gap narrows with scale (1.60× → 1.15×), with crossover estimated near 28–30 per side.

At the 4 m pitch and 96 m scale of the macro campaign, regression is used instead — 625 classes is memory-prohibitive and the evaluation targets unseen users, not seen cells.

---

## A3: Multi-BS interference — does SINR gain spatial variation?

**Scope note:** features are `{rss, sinr}` only. Per-interferer RSS is deliberately excluded — that would be multilateration, a different problem requiring coordinated infrastructure.

Adding co-channel interferers outside the grid (30 m ISD) creates a 2D SINR gradient where previously RSS ≈ SINR. The SINR fingerprint does add real information, but remains far below what AoA provides.

**Hierarchy: AoA ≫ interference SINR > single-BS RSS alone.**

> ⚠ The specific figures previously shown on this slide could not be traced to any surviving results directory and have been removed pending a re-run. The qualitative ordering above is supported by A1 and by §7.3 of the technical documentation.

---

## A4: Campaign A — 15×15, five device profiles

| User | Device | Antennas | Gain | Height |
|---|---|---|---|---|
| U1 | Flagship A | 4 | 0 dB | 1.5 m |
| U2 | Mid-range | 2 | −2 dB | 1.5 m |
| U3 | Budget/Old | 1 | −4 dB | 1.5 m |
| U4 | Flagship B | 4 | 0 dB | 1.5 m |
| U5 | Tablet/IoT | 2 | −1 dB | 0.9 m |

**Without AoA (RF, 225 classes):** BASE 43.5% → BASE_H **52.5%** (+9.0 pp) → BASE_H_dp **61.2%** (+17.7 pp).
Transitions reduce device sensitivity; explicit device calibration is decisive.

**With AoA (4°/5° noise):** +28.7 pp per device. Cross-device generalization to an unseen handset: BASE_H 46.3% → **BASE_A_H 72.8% (RF) / 76.7% (XGB)**.
AoA generalizes across devices because angle is geometrically, not electronically, determined.

*Source: `results/multi_user_voronoi_15x15_backup_20260509_1741/`*

---

## A5: Configuration reference

| Grid | Config | Key parameters |
|---|---|---|
| 10×10 Voronoi | `voronoi_10x10_config.jsonc` | BS@[14,14,10], 4 areas, 400 spp |
| 15×15 Voronoi | `voronoi_15x15_config.jsonc` | BS@[19,19,10], 4 areas, 400 spp |
| 15×15 NE-BS | `ne_bs_voronoi_15x15_config.jsonc` | BS@[48,48,10], 52° wedge |
| 20×20 Voronoi | `voronoi_20x20_config.jsonc` | BS@[24,24,10], 4 areas, 400 spp |
| **25×25 macro** | `ne_bs_voronoi_25x25_config.jsonc` | BS@[116,116,10], 300 users, 4 m pitch |

**Production notebooks:** `06_cnn_h5_derived_features.ipynb`, `07_cnn_attn_h5_derived_features.ipynb`
**Ablation scripts:** `src/python/experiments_ablation/`
**Numbers of record:** `docs/results_of_record/` — every figure in this deck traces to a machine-written JSON or CSV there.
