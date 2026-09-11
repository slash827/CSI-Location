---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { font-size: 22px; }
  table { font-size: 18px; }
  h1 { font-size: 36px; color: #1a3a5c; }
  h2 { font-size: 28px; color: #1a3a5c; }
  strong { color: #c0392b; }
---

<!-- _paginate: false -->

# CSI-Based UE Localization with Transition History

**Experiment 09 — Grid Localization Results**

*QuaDRiGa 3GPP simulation · XGBoost / Random Forest / MLP / Gaussian · 2026*

---

## Problem Statement

**Goal:** Predict a UE's position within a known grid using only measurements at a base station.

Two formulations:
- **Classification** → which grid point? (discrete, N² classes)
- **Regression** → continuous (x, y, z) position

**Central hypothesis:**
Including recent movement _transitions_ as input features should improve accuracy — regardless of algorithm.

**Input features available:**
- RSS, SINR, CQI (standard measurements, single-BS)
- AoA azimuth + elevation (antenna arrays required)
- Multi-BS RSS (requires multiple BSs at known positions)

---

## Simulation Setup

**Environment: Voronoi heterogeneous 10×10 grid (primary scenario)**

| Parameter | Value |
|---|---|
| Grid | 10×10, 2 m spacing, 18 m × 18 m |
| Samples | 400 steps/point × 100 points = **40,000** |
| BS position | Grid center [14, 14, 10 m] |
| Channel | QuaDRiGa 3GPP TR 38.901, 3.0 GHz, 100 MHz, 256 SC |
| Voronoi areas | highway (RMa_LOS), shopping_center (UMi_NLOS), residential (UMi_NLOS), park (UMi_LOS) |

**Walk:** Random walk, 8-neighbor connectivity, 1.5 m/s, visits all 100 grid points.
**Split:** Temporal (last 20% of trajectory = test set) — no future information leakage.

---

## How Transition History Works

For each prediction, stack the **current observation + h previous observations**:

```
h=0 (static):    [rss_t]
h=1:             [rss_t, rss_{t-1}]
h=2:             [rss_t, rss_{t-1}, rss_{t-2}]
```

- Static model sees one snapshot — no movement context
- Transition model sees a short trajectory — direction and Doppler encoded implicitly
- History length h is a hyperparameter; h=1 delivers the largest single jump, but depth keeps paying to h=5 (deep models) or beyond h=10 (tree ensembles)

---

## Result 1: Transition History Always Helps

**7×7 grid, RSS+SINR, static (h=0) vs h=3 transition:**

| Algorithm | h=0 Acc | h=3 Acc | MAE h=0 | MAE h=3 |
|---|---|---|---|---|
| Gaussian | 10.9% | 15.5% | 5.03 m | 4.37 m |
| Random Forest | 28.0% | 43.6% | 3.90 m | 2.51 m |
| **XGBoost** | **26.9%** | **45.1%** | **3.93 m** | **2.39 m** |
| MLP | 24.8% | 41.6% | 4.16 m | 2.62 m |

**All 4 algorithms improve with transition history.**
Effect verified across all 6 grid sizes (9 to 400 classes), both feature sets.
h=1 delivers the largest single jump; depth continues to pay, with h=3 beating h=1 at every grid size below.

---

## Result 2: Feature Importance (Single-BS AoA Scenario)

**10×10 Voronoi, XGBoost, h=1:**

| Feature Set | Accuracy | MAE |
|---|---|---|
| RSS only | — | ~6.5 m |
| RSS + SINR | ~60% | ~2.0 m |
| RSS + SINR + AoA_az | — | — |
| **RSS + SINR + AoA_az + AoA_el** | **91.9%** | **0.18 m** |

**AoA is the dominant feature** — adds ~32 pp accuracy over RSS+SINR.

Without AoA: concentric rings (distance only) → ambiguous predictions.
With AoA azimuth: range × bearing → near-unique position.
With AoA elevation: 3D ranging → further disambiguates.

**RSS ≈ SINR on single-BS:** With no interference, both are driven by the same path loss, so SINR adds no independent spatial information.
Adding interference (multi-BS scenario) breaks this degeneracy.

---

## Result 3: Scalability

**XGBoost, RSS+SINR, h=1 accuracy vs grid size (NLOS uniform):**

| Grid | Classes | h=0 | h=1 | h=2 | h=3 |
|---|---|---|---|---|---|
| 3×3 | 9 | — | 57.9% | 60.0% | 62.8% |
| 5×5 | 25 | — | 49.0% | 51.7% | 53.1% |
| 7×7 | 49 | — | 36.8% | 39.1% | 41.1% |
| 10×10 | 100 | — | 49.7% | 54.5% | 55.6% |
| 15×15 | 225 | — | 23.6% | 27.0% | 29.1% |
| 20×20 | 400 | — | 20.9% | 22.6% | 22.4% |

- History helps at every scale — no crashes or OOM up to 400 classes
- 10×10 NLOS is an outlier (AoA would fix this)
- Approach scales to at least 20×20 (400-class problem)

---

## Result 4: Classification vs Regression

**XGBoost / RF, RSS+SINR+AoA_az+AoA_el, Voronoi 4-cell (2 m spacing):**

| Grid | Classif MAE (h=1) | Regression MAE (h=1) | Ratio |
|---|---|---|---|
| 10×10 | **0.25 m** | 0.40 m | 1.60× |
| 15×15 | **0.46 m** | 0.61 m | 1.33× |
| 20×20 | **0.85 m** | 0.98 m | **1.15×** |

**Classification consistently beats regression** at 2 m spacing:
- Grid-snapping advantage: ±0.1 m position jitter → model learns to snap to grid points
- Gap narrows: 1.60× → 1.33× → 1.15× (~0.22× per 5 grid steps)
- Crossover estimated at **~28–30×30 (~800–900 classes)**

At 2 m spacing, regression's interpolation advantage never materializes.

---

## Result 5: Multi-BS Interference — Does SINR Gain Spatial Variation?

**Question:** In a single-BS localization system, RSS ≈ SINR (no interference). Adding co-channel interferers creates a 2D SINR fingerprint. Does it help?

**Scope:** Features = {`rss`, `sinr`} only — standard UE feedback. Per-interferer RSS is NOT used (triangulation = different problem).

**v2 Setup (realistic — IBSs outside grid, 30m ISD):**

```
                 IBS-1 [-16, 14]        grid [5..23]x[5..23]
                     *
                               *  Serving BS [14, 14]
                                   (grid center)

           IBS-2 [14, -16]  *
```

SINR: −4 to +11 dB (realistic — serving BS dominant for 90%+ of grid)

**Results (XGBoost, h=1):**

| Feature Set | Classif Acc | Classif MAE | Regression 3D |
|---|---|---|---|
| RSS | 19.5% | 6.53 m | 7.55 m |
| **RSS + SINR (multi-BS v2)** | **52.8%** | **3.16 m** | 6.44 m |
| RSS + SINR + AoA_az + AoA_el | **92.8%** | **0.158 m** | **0.515 m** |

SINR gradient adds **+33pp** over RSS alone — measurable but falls **~40pp below AoA**.
Localization hierarchy: **AoA ≫ interference SINR > single-BS RSS alone.**

---

## Result 6: Multi-User Heterogeneous Device Experiment

**Question:** Are transition features robust across heterogeneous devices (different antenna count, gain, UE height)?

**Setup:** 15×15 Voronoi, 1 serving BS (single-BS scope), 5 device profiles, 90k samples each

| User | Device | Antennas | Gain | Height |
|---|---|---|---|---|
| U1 | Flagship A | 4 | 0 dB | 1.5 m |
| U2 | Mid-range | 2 | −2 dB | 1.5 m |
| U3 | Budget/Old | 1 | −4 dB | 1.5 m |
| U4 | Flagship B | 4 | 0 dB | 1.5 m |
| U5 | Tablet/IoT | 2 | −1 dB | 0.9 m |

**Results (RF, 225 classes) — without AoA:**

| Experiment | Features | Accuracy | MAE | vs BASE |
|---|---|---|---|---|
| BASE — Static | rss, sinr (h=0) | 43.5% | 5.81 m | baseline |
| BASE_H — Transitions | lags h=3 | 52.5% | 4.01 m | **+9.0 pp** |
| BASE_H_dp — + Device params | BASE_H + [n_ant, gain, h_UE] | **61.2%** | **2.69 m** | **+17.7 pp** |
| Cross-user BASE_H | BASE_H, U5 held out | 46.3% | 4.92 m | +2.8 pp |

**Verdict (without AoA):** Transitions reduce device sensitivity (+9 pp), but explicit device calibration is the decisive factor (+17.7 pp BASE_H_dp vs BASE_H).

---

## Result 7: AoA Eliminates Device Heterogeneity

**Adding AoA (angle of arrival) to the multi-user experiment:**

AoA is purely geometric — it depends on UE position, not antenna count, gain, or hardware.
Realistic impairments applied: **4° Gaussian noise + 5° quantization**.

**Single-user sanity check (per-device, 320 train samples/class — the honest baseline):**

| User | BASE (rss+sinr) | BASE_A (h=0+AoA) | BASE_A_H (h=3+AoA) |
|---|---|---|---|
| U1 | 58.3% | 86.8% | 86.7% |
| U2–U4 | 55–58% | 85–86% | 85–86% |
| U5 | 56.5% | 84.9% | 85.5% |
| **Mean** | **57.2%** | **85.9%** | **86.2%** |

**AoA adds +28.7 pp per device.** Transitions add only +0.3 pp on top of AoA (AoA lags are correlated with current AoA → no new information).

**Pooled vs single-user with realistic noise**: With 4°/5° AoA noise, the pooled model (RF: 77.3%, XGB: 82.2% for BASE_A) is slightly *below* per-device (~86%) — device-heterogeneous RSS/SINR creates feature ambiguity in the pooled model. Unlike oracle (no-noise) AoA, pooling does not inflate the result.

**Cross-device generalisation — the most meaningful AoA result:**

| Experiment | Train | Test on U5 | RF Acc | XGB Acc |
|---|---|---|---|---|
| Cross-user BASE_H | U1–U4 (no AoA) | U5 | 46.3% | 46.4% |
| **Cross-user BASE_A_H** | **U1–U4 + AoA** | **U5** | **72.8%** | **76.7%** |

Cross-user BASE_A_H tests a multi-user AoA database against a completely unseen device — the practically relevant scenario. Residual ~9–13 pp gap vs per-device = device-specific RSS/SINR distributional shift + U5's height difference (0.9 m vs 1.5 m → ~3° elevation shift).

---

## Act 1: Research Positioning & The Scientific Question

**Core Question (Aligned with Alon Levin):**
*Can temporal transition history ($h$) and physical inductive biases resolve the fundamental **distance-ring ambiguity** inherent to single-Base Station cellular localization without private UE telemetry (GPS / IMU)?*

**Strategic Research Positioning:**
* **NOT positioned as:** *"We trained one marginally better model"* (vulnerable to trivial model competition).
* **Positioned as:** **A universal physical-kinematic mechanism**:
  1. **Universal $\Delta\text{MAE}$ Gain:** Introducing temporal transition history ($h$) provides a systematic accuracy gain across *all* model families (Tree Ensembles, RNNs, 1D-CNNs, Attention).
  2. **Resolving Distance-Ring Ambiguity:** In single-BS setups, static RSS only defines an iso-power circle. Sequential transitions allow computing velocity $\mathbf{v} \approx \frac{\Delta\mathbf{r}}{\Delta t}$, breaking symmetry.
  3. **Decoupled Hardware Physics:** Explaining the $2.3\times$ single-antenna gap as a fundamental physical limit of single-BS AoA observability, rather than model failure.

---

## Act 1: Universal $\Delta\text{MAE}$ Gain Across All Model Families

**Empirical Sweep across History Depth ($h \in [0, 1, 3, 5, 10]$):**

* **$h = 0 \to h = 1$ ($\Delta = -1.56\text{m}$, $+6.8\%$ gain):** Velocity vector $\mathbf{v} \approx \frac{\Delta\mathbf{r}}{\Delta t}$ and radial derivative $\frac{d\text{RSS}}{dt}$ become computable $\to$ largest marginal jump.
* **$h = 1 \to h = 5$ ($\Delta = -2.02\text{m}$ additional gain):** Temporal convolutions filter out Rayleigh fast-fading nulls and small-scale angular noise.
* **$h = 5$ is the Empirical Sweet Spot ($\sim 2.5\text{s}$):** $-15.7\%$ cumulative error reduction!
* **$h = 10$ regresses for the 1D-CNN** ($+0.955\text{m}$) — but **not universally**: XGBoost and Random Forest keep improving through $h=10$ on identical data. Fixed-window models must consume every lag; tree ensembles can decline to split on a stale one.

![bg right:48% 95%](../figures/universal_delta_mae_history_curves.png)

---

## Act 2: Realistic 300-User 5G NR Macro Benchmark

**Full Continuous Trajectory Deployment Setup:**
* **Environment:** $100\text{m} \times 100\text{m}$ area ($25 \times 25$ macro grid, $4\text{m}$ spacing).
* **Serving BS:** Single Base Station at $[116, 116, 10]\text{m}$ (Top-Right / NE).
* **Interferers:** Pushed SW towers at $[-60, 53, 10]\text{m}$ and $[53, -60, 10]\text{m}$.
* **Voronoi Areas:** 4 propagation zones (Park LOS, Highway LOS, Shopping NLOS, Residential).
* **Population:** 300 unseen mobile users with random-walk tracks (80/20 train/test split on User IDs).
* **Demographics:** Standard 3GPP benchmark mix (85% multi-antenna smartphones + 15% single-antenna IoT).

![bg right:48% 90%](../figures/environment_spatial_layout.png)

---

## Act 2: Master Cross-Model Benchmark Scorecard ($h=5$)

**Apples-to-Apples Evaluation Across All 7 Architectures:**

| Model Architecture | History | Params | Train Time | Overall 2D MAE | Median P50 | Multi-Ant (85%) | Single-Ant (15%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **k-NN Regressor (Baseline)** | $h=0$ | — | `0.0 s` | **`27.86 m`** | `23.89 m` | `25.36 m` | `37.14 m` |
| **Random Forest Regressor** | $h=5$ | $6.5\text{M}$ | `121.1 s` | **`20.88 m`** | `16.80 m` | `16.03 m` | `38.90 m` |
| **XGBoost Regressor** | $h=5$ | $12.8\text{K}$ | `26.0 s` | **`19.31 m`** | `15.47 m` | `15.20 m` | `34.60 m` |
| **GRU (2-Layer Recurrent)** | $h=5$ | $187.8\text{K}$ | `255.0 s` | **`18.52 m`** | `14.56 m` | **`14.50 m`** | `33.44 m` |
| **1D-CNN (NB06 Baseline)** | $h=5$ | $66.5\text{K}$ | `333.1 s` | **`19.33 m`** | `15.43 m` | `15.39 m` | `33.95 m` |
| **1D-CNN + Attention (NB07)** | $h=5$ | $199.7\text{K}$ | `231.2 s` | **`19.17 m`** | `15.38 m` | `15.23 m` | `33.80 m` |
| **Mask-Aware 1D-CNN** | $h=5$ | $66.7\text{K}$ | `173.2 s` | **`19.25 m`** | `15.96 m` | `15.71 m` | **`32.38 m`** 🏆 |

* Deep Sequence models (GRU / CNN / Attention) lead overall accuracy ($18.5\text{–}19.3\text{m}$).
* **XGBoost** is an ultra-fast production alternative ($19.31\text{m}$ in $26\text{s}$, $12.8\text{K}$ params).

---

## Act 2: Hardware Discontinuity & Outlier Trajectory Audit

**The $2.3\times$ Smartphone vs. IoT Performance Gap:**
* **Multi-Antenna UEs (4-Ant & 2-Ant):** **`14.58 m` MAE / `12.31 m` Median** (Mean angular error $3.5^\circ\text{–}3.7^\circ$).
* **Single-Antenna UEs (1-Ant):** **`34.54 m` MAE / `30.23 m` Median** (Mean angular error $15.8^\circ$, P90: $33.9^\circ$).

**Diagnostic Outlier Trajectory Audit:**
* **100% of top 5 worst outliers are 1-antenna devices** ($33.5\text{m}\text{–}52.9\text{m}$).
* **100% of top 5 best users are multi-antenna devices** ($10.4\text{m}\text{–}11.8\text{m}$).
* Boundary transitions cost nothing at all — $18.33\text{m}$ MAE crossing vs $19.34\text{m}$ within-cell, marginally *better* — confirming the channel data is physically valid.

![bg right:48% 95%](../figures/antenna_cohort_error_cdf.png)

---

## Act 3: Architectural Mitigation — AoA Validity Masking

**Problem: Dummy Boresight Anchoring**
* Single-antenna UEs lack beamforming angle observability. Standard feedback sets dummy $(0^\circ, 0^\circ)$ AoA.
* In trigonometry, $\cos(0^\circ) = 1.0$ and $\text{ray}_y = r_{\text{est}}$, artificially pulling network predictions along the North-East axis!

**Solution: Explicit Masking (Option A)**
* Zero out trigonometric embeddings $(\sin\theta=0, \cos\theta=0)$ and geometric rays $(\text{ray}_x=0, \text{ray}_y=0)$.
* Feed explicit `has_valid_aoa` binary channel.

**Empirical Result:**
* Single-antenna error drops from $33.61\text{m}$ to **`32.19m` ($-1.42\text{m}$ / $-4.2\%$)**.
* Multi-antenna precision preserved at **`15.28m`**.

![bg right:48% 90%](../figures/diagnostic_angular_tracking_multi_vs_single.png)

---

## Summary & Core Contributions

1. **Physical-Kinematic Mechanism:** Sequence history ($h$) universally resolves the single-BS distance-ring ambiguity across *all* model families ($\Delta\text{MAE} = -15.7\%$).
2. **Empirical Horizon:** Optimal transition horizon is $h=5$ ($\sim 2.5\text{s}$), balancing velocity vector integration against random-walk heading decorrelation.
3. **Decoupled Hardware Physics:** Explaining the $2.3\times$ single-antenna gap as a fundamental limit of angle observability, rather than model error. Smartphones achieve **$14.58\text{m}$ MAE / $12.31\text{m}$ median** with $>34\%$ of steps $<10\text{m}$.
4. **Architectural Mitigation:** Explicit AoA validity masking eliminates false boresight vectors, unlocking $-4.2\%$ error reduction on budget IoT devices.
5. **Production Deployability:** XGBoost matches 1D-CNN accuracy ($19.31\text{m}$) with $12.8\text{K}$ parameters in $26\text{s}$, ideal for edge cellular base stations.

---

<!-- _paginate: false -->

## Appendix: Configuration Reference

| Grid | Config | Key parameters |
|---|---|---|
| 10×10 Voronoi | `voronoi_10x10_config.jsonc` | BS@[14,14,10], 4 areas, 400 spp |
| 15×15 Voronoi | `voronoi_15x15_config.jsonc` | BS@[19,19,10], 4 areas, 400 spp |
| 20×20 Voronoi | `voronoi_20x20_config.jsonc` | BS@[24,24,10], 4 areas, 400 spp |
| 10×10 Multi-BS | `multi_bs_10x10_config.jsonc` | +IBS@[5,5,10]+[23,23,10], 400 spp |

**Run classification:**
```bash
python localization_pipeline.py --data-dir <path> --model xgboost \
  --max-history 1 --metrics "rss,sinr,aoa_azimuth,aoa_elevation"
```

**Run regression:**
```bash
python localization_pipeline_regression.py --data-dir <path> --model xgboost \
  --max-history 1 --metrics "rss,sinr,aoa_azimuth,aoa_elevation"
```
