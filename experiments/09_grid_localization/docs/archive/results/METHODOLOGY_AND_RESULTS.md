# CSI-Based UE Localization: Methodology and Results

**Experiment 09 — Grid Localization with Transition History**
*Last updated: 2026-03-02*

---

## 1. Problem Statement

We address the problem of **UE (User Equipment) localization** in a cellular network using channel-state information (CSI) derived measurements. The goal is to predict the 2D position of a mobile UE within a known grid area, using only the signals observed at a single base station (BS).

We investigate two formulations:
- **Classification**: predict which discrete grid point (N² classes) the UE inhabits
- **Regression**: predict the continuous (x, y, z) position relative to the BS

The central hypothesis is that **transition history** — observations from the UE's recent movement — can significantly improve localization accuracy at every grid scale.

---

## 2. Channel Simulation

### 2.1 QuaDRiGa Channel Model

All channel data is generated using **QuaDRiGa v2.8.1** implementing 3GPP TR 38.901 propagation scenarios. QuaDRiGa produces spatially-consistent, time-varying channel coefficients as a UE walks along a trajectory.

**Simulation parameters:**

| Parameter | Value |
|---|---|
| Center frequency | 3.0 GHz (3.5 GHz for multi-user experiment §10) |
| Bandwidth | 100 MHz |
| Subcarriers | 256 |
| UE height | 1.5 m |
| UE speed | 1.5 m/s (pedestrian) |
| Position jitter | ±0.1 m (prevents exact grid alignment) |

### 2.2 UE Walk Pattern

The UE follows a random walk on the grid with 8-connected neighbor transitions:

```
steps_per_point: 400   (400 channel snapshots per grid point visit)
starting_point:  center
connectivity:    8 (up/down/left/right/diagonals)
```

This produces a continuous trajectory through all grid points. The transition between adjacent grid points is what enables history-based prediction.

---

## 3. Grid Environments

### 3.1 Uniform NLOS Environment (Scalability Baseline)

Used to study how classification accuracy degrades with grid size.

| Parameter | Value |
|---|---|
| Scenario | 3GPP_38.901_UMa_NLOS |
| Grid spacing | 2 m |
| BS position | Outside grid (single sector) |
| Grids tested | 3×3 to 20×20 (9 to 400 classes) |

### 3.2 Voronoi Heterogeneous Environment (Main Study)

A more realistic scenario with multiple distinct propagation environments within the same grid. The grid area is divided into **4 Voronoi cells**, each assigned a different 3GPP channel scenario.

**Configuration (10×10, 2m spacing):**

| Voronoi Cell | 3GPP Scenario | Channel Type | Grid Points |
|---|---|---|---|
| Park | UMi_LOS | Open outdoor | ~101 pts (largest) |
| Residential | 50/50 UMi_LOS/NLOS | Mixed suburban | ~35 pts |
| Highway | RMa_LOS | Open rural macro | ~26 pts |
| Shopping center | UMi_NLOS | Dense indoor/enclosed | ~8 pts (smallest) |

**Design rationale:** Each cell uses a maximally distinct channel type. Using duplicate scenarios (e.g., two UMi_NLOS areas) was found to add little localization value — the high diversity is intentional.

**BS placement:** The BS is positioned **inside the grid** at the center `[14, 14, 10m]`. This enables:
- 360° AoA coverage — the UE surrounds the BS in all directions
- Distance range: 8.6 – 15.4 m (short range, small cell)
- Large AoA variation across grid points (high discriminative power)

---

## 4. Feature Metrics

### 4.1 Available Measurements

At each time step, the following metrics are extracted from the simulated channel:

| Metric | Description | Realistic? |
|---|---|---|
| RSS | Wideband received signal strength (dBm) | Yes |
| SINR | Wideband signal-to-interference+noise ratio (dB) | Yes |
| CQI | Channel Quality Indicator (1–15, quantized) | Yes |
| AoA azimuth | Angle of Arrival in azimuth plane (degrees) | Yes, w/ noise |
| AoA elevation | Angle of Arrival in elevation plane (degrees) | Yes, w/ noise |
| Timing advance | Round-trip propagation delay | **No** (exact, no noise model) |
| K-factor | Rician K-factor | **No** (not a real UE measurement) |

### 4.2 AoA Noise Model

Real-world AoA estimation suffers from angular resolution limits and RF noise. We apply a two-stage impairment model configured in `ml_config.jsonc`:

```
Step 1: Additive Gaussian noise: σ = 4°
Step 2: Quantization:            Δ = 5° steps
```

This is applied independently to azimuth and elevation with different seeds to prevent correlation artifacts. The result is a noisy, discretized AoA estimate consistent with a practical beam-scanning BS.

### 4.3 Feature Selection Findings

**On the BS-inside-grid (10×10 Voronoi), XGBoost h=1:**

| Feature Set | Accuracy | MAE | Notes |
|---|---|---|---|
| RSS | 23.2% | 5.70m | Only encodes distance from BS |
| SINR | 22.9% | 5.74m | = RSS (no interferers, single BS) |
| RSS+SINR | 23.0% | 5.72m | No improvement over RSS alone |
| +AoA azimuth | 77.9% | 0.58m | **+55pp** — breaks angular symmetry |
| +AoA elevation | **88.5%** | **0.25m** | +10pp — elevation encodes distance |
| CQI | 1.3% | 9.11m | Saturates at close range (all max CQI) |

**Key insight:** RSS and SINR both encode only the distance from BS (concentric rings). Without angular information, countless grid points share the same distance ring. AoA breaks this symmetry uniquely — azimuth gives bearing, elevation gives range.

---

## 5. Localization Approaches

### 5.1 Classification Pipeline

The UE position is treated as a classification problem over N² discrete grid points.

**Algorithm:** XGBoost (best overall), Random Forest (comparable)

**Feature mode:** Raw stacking (plain measurement vector) consistently outperforms "smart" features (engineered deltas, magnitudes). Reason: tree-based ensembles prefer raw features and find their own interactions.

**Transition history (h):** The feature vector for time step t is formed by concatenating observations from steps t−h through t:

```
x_input = [m(t-h), m(t-h+1), ..., m(t-1), m(t)]  ← (h+1)×D features
```

This stacking makes the model aware of recent movement direction and rate of change.

**Data split:** Temporal (last 20% of trajectory as test set) to prevent leakage from trajectory correlation.

### 5.2 Regression Pipeline

Instead of N² classes, the pipeline predicts continuous 3D spherical coordinates relative to the BS:
- **Distance** (m): Euclidean 3D distance to BS
- **Azimuth** (°): Horizontal bearing from BS
- **Elevation** (°): Vertical angle from BS

The 3D Euclidean position error (meters) is then directly comparable to classification MAE.

**Multi-output strategy:**
- RandomForest: native multi-output support
- XGBoost: wrapped with `MultiOutputRegressor` (trains 3 independent regressors)

---

## 6. Classification Results

### 6.1 Single-Scenario NLOS — Scalability (XGBoost, RSS+SINR)

| Grid | Classes | h=0 MAE | h=3 MAE | Improvement |
|---|---|---|---|---|
| 3×3 | 9 | 1.28m | 1.05m | −18% |
| 5×5 | 25 | 2.65m | 1.89m | −29% |
| 7×7 | 49 | 3.96m | 2.64m | −33% |
| 10×10 | 100 | 4.50m | 2.64m | −41% |
| 15×15 | 225 | 8.87m | 6.21m | −30% |
| 20×20 | 400 | 10.31m | 7.50m | −27% |

**Transition history consistently reduces MAE at every scale** — confirmed from 9 to 400 classes.

### 6.2 Voronoi Mixed-Scenario (AoA Features)

**10×10 Voronoi (2m spacing, 400 spp, 40k samples), XGBoost, rss+sinr+aoa_az+aoa_el:**

| h | Accuracy | MAE |
|---|---|---|
| 0 | 84.6% | 0.34m |
| 1 | **88.5%** | **0.25m** |
| 2 | 88.1% | 0.26m |
| 3 | 88.3% | 0.25m |

**15×15 Voronoi — Fixed (2m spacing, 400 spp, 90k samples), XGBoost, rss+sinr+aoa_az+aoa_el:**

| h | Accuracy | MAE |
|---|---|---|
| 0 | 75.1% | 0.61m |
| 1 | **80.8%** | **0.46m** |

*After `AreaGenerator` fix (randperm): 4 distinct area labels — highway/RMa_LOS, shopping_center/UMi_NLOS, residential/UMi_NLOS, park/UMi_LOS. `residential` 50/50 coin flip landed on UMi_NLOS (same model as shopping_center) for seed 42, giving 3 distinct channel scenarios. Slightly worse than old broken run (0.38m) because old run accidentally doubled RMa_LOS (most distinctive scenario).*

**15×15 Voronoi — Old/broken reference (2m spacing, 2× RMa_LOS bug):**

| h | Accuracy | MAE |
|---|---|---|
| 0 | 79.1% | 0.52m |
| 1 | 84.1% | 0.38m |

**15×15 Voronoi — 5m spacing reference (100 spp, 22.5k samples), XGBoost:**

| h | Accuracy | MAE |
|---|---|---|
| 0 | 74.4% | 1.77m |
| 1 | **80.2%** | **1.34m** |

→ Changing spacing 5m→2m and spp 100→400 improves MAE by 3.5× (1.34m→0.38m) on old data with stronger cell contrast.

**20×20 Voronoi — Fixed (2m spacing, 400 spp, 160k samples), XGBoost, rss+sinr+aoa_az+aoa_el:**

| h | Accuracy | MAE |
|---|---|---|
| 0 | 60.6% | 1.11m |
| 1 | **67.5%** | **0.85m** |

*Same fix applied: 4 distinct area labels, residential→UMi_NLOS (3 distinct channel scenarios).*

### 6.3 Per-Voronoi-Cell Breakdown (10×10, XGBoost h=1, full AoA)

| Cell | Channel | Size | Accuracy | Cross-cell Confusion |
|---|---|---|---|---|
| Park | UMi_LOS | 101 pts | 95.0% | 3.4% |
| Residential | Mixed | 35 pts | 92.2% | 5.1% |
| Highway | RMa_LOS | 26 pts | 73.4% | 27% |
| Shopping center | UMi_NLOS | 8 pts | 65.8% | 36% |

- Large cells are well-classified; small cells bleed heavily into neighboring cells
- LOS channels (Park) are most distinguishable; NLOS (Shopping center) hardest
- Per-cell accuracy correlates strongly with cell size — small cells need more data density

---

## 7. Regression Results

**RandomForest, rss+sinr+aoa_az+aoa_el:**

| Grid | Environment | Spacing | h=0 error | h=1 error |
|---|---|---|---|---|
| 10×10 | Voronoi 4-cell | 2m | 0.44m | **0.40m** |
| 15×15 | Voronoi 4-cell | 2m (fixed) | 0.75m | **0.61m** |
| 15×15 | Voronoi 4-cell | 2m (old/broken) | 0.62m | 0.52m |
| 15×15 | Voronoi 4-cell | 5m (ref) | 2.01m | **1.82m** |
| 20×20 | Voronoi 4-cell | 2m (fixed) | 1.27m | **0.98m** |
| 20×20 | NLOS uniform | 2m | 1.54m | — |

**Classification vs Regression (matched 2m spacing, Voronoi AoA features, fixed diversity):**

| Grid | Classification MAE | Regression MAE | Ratio |
|---|---|---|---|
| 10×10 (2m, 40k) | 0.25m (XGB h=1) | 0.40m (RF h=1) | 1.60× |
| 15×15 (2m, 90k) | 0.46m (XGB h=1) | 0.61m (RF h=1) | 1.33× |
| 20×20 (2m, 160k) | 0.85m (XGB h=1) | 0.98m (RF h=1) | **1.15×** |

**Classification consistently outperforms regression**, and the gap narrows progressively: 1.60× → 1.33× → 1.15× (Δ ≈ 0.27, 0.18). At this rate, the crossover approaches **~28–30×30 (800–900 classes)**.

**Cell diversity affects absolute performance:** The old (buggy) 15×15/20×20 accidentally doubled RMa_LOS (the most spectrally distinct model), producing better MAE despite being wrong. The fix correctly assigns all 4 area type labels, but `residential`→UMi_NLOS (same model as shopping_center for seed 42) gives only 3 distinct channel models. The scalability ratio trend is still valid.

**Why classification still wins:** At 2m grid spacing, ground-truth positions are nearly exactly on grid points (±0.1m jitter). The model can perfectly "snap to grid" without needing to interpolate, removing regression's main advantage.

**XGBoost vs RF for regression:** RF outperforms XGBoost (0.40m vs 0.59m on 10×10). The `MultiOutputRegressor` wrapper around XGBoost trains independent regressors per target, losing the correlation structure between distance, azimuth and elevation that RF exploits natively.

---

## 8. Multi-BS Interference Experiment (10×10 Voronoi, 2026-03-02)

**Goal:** Test whether co-channel interference from neighbouring BSs creates enough spatial SINR variation to improve fingerprinting accuracy — without any triangulation assumptions.

**Scope of this experiment:** The serving BS performs localization using only measurements it legitimately receives:
- `rss` — UE-reported serving-cell RSRP
- `sinr` — UE-reported SINR (now spatially varied by IBS interference)
- `aoa_*` — angle-of-arrival at the serving BS antenna array

`rss_ibs_1`, `rss_ibs_2` (per-interferer RSS at UE) are **not used** — that would constitute triangulation: a fundamentally different problem requiring UE reporting of per-neighbor RSRP and cooperative multi-BS localization, which is outside our single-BS scope.

**Experiment v1 Setup (unrealistic — interferers too close):**
Serving BS: [14,14,10] (grid center); IBS-1: [5,5,10]; IBS-2: [23,23,10] — both at grid corners.
Problem: interferers are co-located with UEs, producing SINR range −47 to −23 dB (interference-dominated). Serving BS is not always the dominant BS for corner UEs. **Not representative of a realistic deployment.**

**Valid results from v1 (XGBoost, h=1, `rss+sinr` only):**

| Feature Set | Classif Acc (h=0) | Classif MAE (h=0) | Classif Acc (h=1) | Classif MAE (h=1) |
|---|---|---|---|---|
| `rss` | 16.4% | 7.67m | 19.5% | 6.53m |
| `rss+sinr` (multi-BS, v1) | 52.1% | 3.16m | 60.2% | 2.06m |
| `rss+sinr+aoa_az+aoa_el` | 90.5% | 0.210m | 91.9% | 0.178m |

*Note: `rss+sinr` performance matches single-BS `rss+sinr` — the interference pattern did not add useful spatial information. Likely because the SINR is very negative throughout (overwhelmed by interference), reducing it to noise rather than a spatial signal.*

**Triangulation reference (separate problem — not our scope):**

| Feature Set | Classif MAE (h=1) | Note |
|---|---|---|
| `rss+rss_ibs_1+rss_ibs_2` | 0.046m | Trilateration — requires per-neighbor RSRP reporting |
| `rss+sinr+rss_ibs_1+rss_ibs_2` | 0.042m | Same assumption |

These results are included only as a geometric upper bound. They are not achievable with a single serving BS and standard UE reporting.

**Next: Experiment v2 (realistic placement — interferers outside grid)**

**SINR computation bug (discovered during v2):** The v1 simulation had a 30 dB SINR error — interference was scaled by the actual IBS TX power (30 dBm = 1 W) but `CSIMetrics` uses a 0 dBm = 1 mW reference for the serving BS signal. This made SINR artificially 30 dB too negative. Fixed by scaling interference to `|H_IBS|² × (1e-3 × rel_power)` where `rel_power = 10^((IBS_TX − serving_TX)/10)`.

**Experiment v2 Setup (realistic — interferers outside grid):**
Serving BS: [14,14,10] (center); IBS-1: [-16,14,10] (30m west); IBS-2: [14,-16,10] (30m south).
Orthogonal directions create a 2D SINR gradient (west-east + south-north). Inter-site distance ~30m (typical urban small cell).

**v2 results (XGBoost, h=0 and h=1):**

| Feature Set | Classif Acc (h=0) | Classif MAE (h=0) | Classif Acc (h=1) | Classif MAE (h=1) | Regression 3D (h=0) |
|---|---|---|---|---|---|
| `rss` | 16.4% | 7.67m | 19.5% | 6.53m | 7.55m |
| `rss+sinr` (multi-BS v2) | 43.4% | 4.53m | 52.8% | 3.16m | 6.44m |
| `rss+sinr+aoa_az+aoa_el` | 91.6% | 0.184m | 92.8% | 0.158m | 0.515m |

**SINR metrics v2:** range −4.14 to +10.90 dB (realistic, serving BS dominant); CQI: 2–9 (meaningful for first time).

**Interpretation:**

- **SINR from realistic interference does help**: +27pp accuracy over RSS alone (43% vs 16%); 2D spatial SINR gradient is measurable and exploitable
- **But falls far short of AoA**: 53% vs 93% (h=1) — the SINR spatial range (15 dB across 18m×18m) carries far less positional entropy than AoA (360° span)
- **Regression:** `rss+sinr` → 6.44m, `rss+sinr+AoA` → 0.51m — interference barely moves the needle; AoA is decisive
- **Conclusion:** Realistic multi-BS interference provides moderate, measurable benefit to SINR-based fingerprinting. It cannot substitute for AoA in this scenario. The effective localization hierarchy is: AoA ≫ interference SINR > single-BS RSS alone.

---

## 9. Key Findings

1. **AoA is the dominant feature** — provides +55pp accuracy gain over RSS+SINR on BS-inside-grid. Without AoA, localization is essentially range-only (concentric ring ambiguity).

2. **Transition history always helps** — verified across all 6 grid sizes (9 to 400 classes), both feature sets, and both approaches. h=1 provides most of the gain; h>1 yields diminishing returns.

3. **RSS ≈ SINR without interference** — on a single-BS scenario, both metrics encode the same distance information. Combining does not help. Interference would differentiate them but is not present in this setup.

4. **CQI is useless at short range** — at 8–15m from BS, all UEs achieve maximum SINR, collapsing CQI to its top quantization bucket.

5. **Classification beats regression, but the gap narrows consistently** — at 10×10 (2m) classification is 1.60× better; at 15×15 (2m) it's 1.33×; at 20×20 (2m) it's 1.15×. At this rate (~0.22× per 5 grid steps), crossover approaches **~28–30×30 (~800–900 classes)**. Regression may never fully catch classification at 2m spacing due to the grid-snapping advantage.

6. **Simulation resolution matters enormously** — switching the 15×15 grid from 5m/100spp to 2m/400spp improves MAE by 3.5× (1.34m→0.38m) for the same algorithm. Finer grid spacing increases class discriminability; more steps per point reduces label noise.

7. **Voronoi cell size → accuracy** — small cells (~8 pts) suffer 36% cross-cell confusion; large cells (~100 pts) achieve 95% accuracy. Minimum viable cell size for reliable classification is ~25–30 points.

8. **Memory management** — path enumeration for Gaussian transition model at h=3 grows cubically: fixed via 256 MB chunked batch processing in `predict_batch`. OOM verified fixed up to 15×15 (90k samples, 225 classes).

9. **Multi-BS interference provides moderate benefit, not AoA-comparable** — Realistic outside-grid interferers (30m ISD) create a measurable 2D SINR gradient (−4 to +11 dB). Adding SINR to RSS improves accuracy by +27pp (43% vs 16%) but remains ~40pp below AoA (93%). A 30 dB SINR computation bug (wrong TX power reference) was also discovered and fixed; it caused all v1 SINR values to be 30 dB too negative and CQI always = 0.

10. **AoA adds ~29 pp per device in the multi-user heterogeneous setting** — Single-user sanity check: E1 (RSS+SINR) = 57%, E5 (add AoA) = 86%, +28.7 pp. AoA is geometrically device-independent; the realistic per-device ceiling is ~86% with 4°/5° noise. The pooled multi-user E5/E6 (RF: 77.3%/77.1%; XGB: 82.2%/83.6%) is slightly *below* the per-device ceiling, because device-heterogeneous RSS/SINR in the pooled feature vector introduces ambiguity the AoA cannot fully overcome. The most meaningful cross-device result is cross-user E6 = 76.7% (XGB) / 72.8% (RF) (trained on 4 users, evaluated on completely unseen U5 device type), demonstrating that an AoA-based model generalises well across heterogeneous devices even with realistic impairments.

---

## 10. Multi-User Heterogeneous Device Experiment (15×15 Voronoi)

### 10.1 Motivation and Hypothesis

Real cellular networks serve UEs with heterogeneous hardware: different antenna counts, receiver gain, and physical height. If the localization model is trained on a single "reference" device type and then deployed across varied devices, static fingerprint features (RSS, SINR at one instant) may degrade because absolute signal levels differ per device.

**Central hypothesis**: transition-based features (relative changes over h steps) are more robust to device heterogeneity than static features, because relative changes cancel out device-specific offsets.

### 10.2 Experimental Setup

**Grid**: 15×15, 2 m spacing, 225 grid points, [5,33]×[5,33] m, 4 Voronoi environment cells

**Network** (single-BS scope — NOT triangulation):
- 1 serving BS at [19, 19, 10] (grid center) — sole feature source
- 2 interfering BSs outside the grid (30 m ISD), creating orthogonal E-W and N-S SINR gradients:
  - IBS-1: [−11, 19, 10] (30 m west)
  - IBS-2: [19, −11, 10] (30 m south)
- Features: RSS and SINR from serving BS only

**Device profiles** (5 users, each with independent QuaDRiGa simulation run):

| User | Device type | Antennas | Gain | UE height | Walk seed |
|---|---|---|---|---|---|
| U1 | Flagship A | 4 | 0 dB | 1.5 m | 100 |
| U2 | Mid-range | 2 | −2 dB | 1.5 m | 200 |
| U3 | Budget/Old | 1 | −4 dB | 1.5 m | 300 |
| U4 | Flagship B | 4 | 0 dB | 1.5 m | 400 |
| U5 | Tablet/IoT | 2 | −1 dB | 0.9 m | 500 |

U1 and U4 share identical device parameters but use different walk seeds, isolating device effects from trajectory randomness.

**Multi-antenna UE modelling**: MRC (Maximum Ratio Combining) is applied in MATLAB simulation: $H_{\text{eff}}(f) = \sqrt{\sum_i |H_i(f)|^2}$. Antenna gain offset is applied post-simulation to both RSS and SINR.

**Data**: 90,001 samples per user → 450,005 total. Split: 80% chronological train (360,005) / 20% test (90,000), strictly per-user with no data leakage.

**Experiments**:
- **E1** — Static baseline: [rss, sinr] (h=0)
- **E2** — Transitions only: [rss_t, sinr_t, …, rss_{t−h}, sinr_{t-h}] (h=3)
- **E3** — Transitions + device params: E2 + [n_antennas, antenna_gain_db, ue_height]
- **E4** — Transitions + user_id: E2 + [user_id as integer]
- **E5** — Static + AoA: [rss, sinr, aoa_az, aoa_el] (h=0)
- **E6** — Transitions + AoA: E2 features + [aoa_az_t, aoa_el_t, …, aoa_az_{t-h}, aoa_el_{t-h}]
- **E7** — Transitions + AoA + device params: E6 + [n_antennas, antenna_gain_db, ue_height]
- **Cross-user E2/E6**: train on U1–U4, evaluate on U5 (held-out device type)

**AoA impairment model**: AoA is extracted from QuaDRiGa's `ch.par.AoA_cb` (power-weighted cluster angle of arrival). Clean values are saved in `.mat` files; realistic impairments are applied in Python before training, matching the convention of all other AoA experiments in this study:
- **Gaussian noise**: σ = 4° per axis (typical for practical antenna arrays at 3–4 GHz)
- **Quantization**: 5° step (typical codebook resolution)
With an omni BS antenna this is still an oracle measurement in the sense that no physical array is simulated — in a real BS deployment a multi-element array would be required to estimate direction.

**Model**: Random Forest (n_estimators=50, max_depth=15, min_samples_leaf=20)

### 10.3 Overall Results

**Pooled (all 5 users in training), both models, with realistic AoA noise (4°/5°):**

| Experiment | Features | RF Acc | RF MAE | XGB Acc | XGB MAE | vs RF-E1 |
|---|---|---|---|---|---|---|
| E1 | rss+sinr (h=0) | 43.5% | 5.81 m | 27.3% | 8.39 m | baseline |
| E2 | transitions h=3 | 52.5% | 4.01 m | 50.4% | 4.53 m | +9.0 pp |
| E3 | transitions + device params | 61.2% | 2.69 m | 58.3% | 3.20 m | +17.7 pp |
| E4 | transitions + user_id | 61.6% | 2.85 m | 57.8% | 3.26 m | +18.1 pp |
| **E5** | **rss+sinr+AoA (h=0)** | **77.3%** | **0.555 m** | **82.2%** | **0.439 m** | **+33.8 pp** |
| **E6** | **transitions+AoA h=3** | **77.1%** | **0.526 m** | **83.6%** | **0.388 m** | **+33.6 pp** |
| **E7** | **transitions+AoA+device** | **79.3%** | **0.471 m** | **84.9%** | **0.355 m** | **+35.8 pp** |
| Cross-user E2 | transitions (U5 held out) | 46.3% | 4.92 m | 46.4% | 5.05 m | +2.8 pp |
| **Cross-user E6** | **transitions+AoA (U5 held out)** | **72.8%** | **0.643 m** | **76.7%** | **0.612 m** | **+29.3 pp** |

**Note on pooled vs single-user AoA**: With realistic noise, device-dependent RSS/SINR variation slightly *hurts* the pooled AoA model (77–82%) compared to a per-device model seeing only its own device's signals (~86% per-device sanity check below). This contrasts with clean oracle AoA (no noise), where pooling inflates to 99.9% due to data volume. The noise model reveals the true operating point.

**Single-user sanity check (each user trains/tests on its own data; 320 train samples/class, RF, with noise):**

| User | E1 (rss+sinr) | E5 (h=0+AoA) | E6 (h=3+AoA) |
|---|---|---|---|
| U1 | 58.3% | 86.8% | 86.7% |
| U2 | 56.6% | 85.8% | 86.1% |
| U3 | 56.8% | 85.9% | 86.1% |
| U4 | 57.9% | 86.0% | 86.4% |
| U5 | 56.5% | 84.9% | 85.5% |
| **Mean** | **57.2%** | **85.9%** | **86.2%** |

→ Fair per-device comparison: E1 single-user (**57.2%**) → E5 single-user (**85.9%**) = **+28.7 pp** from AoA. Transition history on top of AoA gives negligible additional benefit (+0.3 pp, E6 vs E5 single-user).

### 10.4 Per-User Breakdown

| User | Device | E1 acc | E2 acc | E3 acc | E4 acc | E2 vs E1 |
|---|---|---|---|---|---|---|
| U1 | Flagship A (4 ant, 0 dB) | 56.5% | 63.6% | 65.3% | 66.2% | +7.1 pp |
| U2 | Mid-range (2 ant, −2 dB) | 31.7% | 42.0% | **58.7%** | 56.0% | +10.3 pp |
| U3 | Budget/Old (1 ant, −4 dB) | 43.7% | 55.3% | 59.7% | 61.3% | +11.6 pp |
| U4 | Flagship B (4 ant, 0 dB) | 55.8% | 62.3% | 63.5% | 64.0% | +6.5 pp |
| U5 | Tablet/IoT (2 ant, −1 dB, 0.9 m) | 30.0% | 39.3% | **58.9%** | 60.3% | +9.3 pp |

### 10.5 Learning Curve (h=0 to h=4)

| History h | Accuracy | MAE (m) |
|---|---|---|
| h=0 | 43.5% | 5.81 m |
| h=1 | **54.1%** | 4.30 m |
| h=2 | 54.5% | 4.00 m |
| h=3 | 52.5% | 4.01 m |
| h=4 | 53.6% | 3.98 m |

The biggest gain is from h=0→h=1 (+10.6 pp); subsequent history increments yield diminishing returns.

### 10.6 Key Findings

1. **Transitions improve over static, but don't eliminate device heterogeneity (E2 > E1: +9 pp)**. History-based relative features partially reduce the spread between best (U1: 63.6%) and worst (U5: 39.3%) device types.

2. **Explicit device parameters unlock substantially better performance (E3 >> E2: +17.7 pp overall)**. U2 and U5, the users most penalised by device effects in E1, gain the most from E3: +16.7 pp (U2) and +19.6 pp (U5). This suggests device-specific calibration in the model is valuable.

3. **U1 and U4 (same device parameters, different walk seeds) achieve nearly identical accuracy** (E2: 63.6% vs 62.3%), confirming the experimental design isolates device effects from stochastic trajectory variation.

4. **Cross-user generalisation penalty exists but is manageable**: withholding U5 during training drops accuracy from 52.5% (E2) to 46.3% (−6.2 pp), showing the model does rely on device-specific signal patterns. This is the "unknown device" scenario in production.

5. **History optimum is at h=1** (54.1%, 4.30 m), with further history steps providing negligible benefit. Using larger h increases feature dimensionality and computation without accuracy gain for this 15×15 setting.

6. **AoA is device-independent and adds ~29 pp per device over RSS+SINR**. Single-user sanity check (training and testing on one device only, 320 samples/class): E1→E5 = 57.2%→85.9% = **+28.7 pp**. AoA depends on position geometry only (not antenna count, gain, or height), so all 5 users exhibit the same AoA distribution at each grid point. With realistic 4°/5° AoA noise, the pooled E5 (RF: 77.3%, XGB: 82.2%) is *below* the per-device ceiling (~86%), because device-heterogeneous RSS/SINR in the pooled feature vector creates ambiguity during classification.

7. **Transition history adds negligible benefit on top of AoA**. Single-user E6 (AoA + transitions h=3) = 86.2%, vs E5 (AoA only, h=0) = 85.9% — a difference of +0.3 pp. AoA lags are highly correlated with the current AoA (the UE moves slowly relative to grid spacing), so adding them provides almost no new information. This is in contrast to the non-AoA experiments (E1→E2: +9 pp), where transitions carry genuine relative-change information. The pooled E6 (RF: 77.1%, XGB: 83.6%) is similar to E5 — consistent with the AoA-dominated regime where transitions add little.

8. **AoA generalises across device types: cross-user E6 = 76.7% (XGB) / 72.8% (RF)**. Even when U5 (Tablet/IoT, 0.9 m height) is completely excluded from training, the AoA model trained on 4 users achieves 76.7% (XGB) / 72.8% (RF) on U5 — vs 46.4%/46.3% for cross-user E2 (no AoA). The ~9–13 pp gap below per-device performance (~86%) traces to two factors: (1) device-specific RSS/SINR variation creating distributional shift for the unseen device, and (2) U5's different UE height (0.9 m vs 1.5 m) shifting the elevation AoA by ~3°. Cross-user E6 is the most meaningful AoA result: it uses a multi-user training database and tests against an entirely unseen device profile — the practically relevant deployment scenario.

---

## 11. Configuration Reference

### Run New Experiment (Classification)
```bash
cd experiments/09_grid_localization/src/python
python run_experiment_matrix.py \
  --data-dir results/grid_localization/grid_10x10/sim_data_voronoi_2026-02-25_23-17-56 \
  --algorithms xgboost \
  --metrics rss sinr "rss,sinr" "rss,sinr,aoa_azimuth" "rss,sinr,aoa_azimuth,aoa_elevation" \
  --feature-modes raw \
  --max-history 1
```

### Run New Experiment (Regression)
```bash
python localization_pipeline_regression.py \
  --data-dir results/grid_localization/grid_10x10/sim_data_voronoi_2026-02-25_23-17-56 \
  --model random_forest --max-history 1 \
  --metrics rss sinr "rss,sinr" "rss,sinr,aoa_azimuth" "rss,sinr,aoa_azimuth,aoa_elevation"
```

### Regenerate Scalability Plot
```bash
python plot_scalability_results.py
# After new 15x15 clean simulation:
python plot_scalability_results.py \
  --new-15x15-classif-mae <value> \
  --new-15x15-regress-mae <value>
```

### Per-Cell Analysis
```bash
python analyze_voronoi_cells.py \
  --data-dir results/grid_localization/grid_10x10/sim_data_voronoi_2026-02-25_23-17-56 \
  --algorithm xgboost --metrics "rss,sinr,aoa_azimuth,aoa_elevation" --history 1
```

---

## 12. Data Inventory

| Grid | Environment | Samples | Key Result | Path |
|---|---|---|---|---|
| 10×10 | Voronoi 4-cell (2m) | 40k | 88.5% / 0.25m | `grid_10x10/sim_data_voronoi_2026-02-25_23-17-56/` |
| 10×10 | Multi-BS v1 (1+2 BSs, SINR buggy) | 40k | rss+sinr: 60.2%→invalid | `grid_10x10/sim_data_voronoi_2026-03-02_08-59-41/` |
| 10×10 | Multi-BS v2 (1+2 BSs, SINR fixed) | 40k | rss+sinr: 52.8% / 3.16m | `grid_10x10/sim_data_voronoi_2026-03-02_09-45-15/` |
| 15×15 | Voronoi 4-cell (2m, fixed✓) | 90k | 80.8% / 0.46m | `grid_15x15/sim_data_voronoi_2026-03-02_08-12-13/` |
| 15×15 | Voronoi 4-cell (2m, old) | 90k | 84.1% / 0.38m | `grid_15x15/sim_data_voronoi_2026-03-01_22-00-15/` |
| 15×15 | Voronoi 4-cell (5m, ref) | 22.5k | 80.2% / 1.34m | `grid_15x15/sim_data_voronoi_2026-02-07_17-16-42/` |
| 20×20 | Voronoi 4-cell (2m, fixed✓) | 160k | 67.5% / 0.85m | `grid_20x20/sim_data_voronoi_2026-03-02_08-19-16/` |
| 20×20 | Voronoi 4-cell (2m, old) | 160k | 77.1% / 0.64m | `grid_20x20/sim_data_voronoi_2026-03-01_23-39-16/` |
| 15×15 | Multi-user heterogeneous (5 devices, w/ AoA) | 450k | XGB E6: 83.6% / 0.388m | `grid_15x15/sim_data_multi_user_2026-03-02_19-41-39/` |
| 15×15 | Multi-user heterogeneous (5 devices, E1–E4 only) | 450k | E3: 61.2% / 2.69m | `grid_15x15/sim_data_multi_user_2026-03-02_13-51-15/` |
| 3–20 | NLOS uniform | 3.6k–160k | see §6.1 | `grid_NxN/sim_data_NLOS_*/` |

---

## 13. Consolidated Comparison: Single-User vs Multi-User Voronoi

This section provides a single reference table combining all Voronoi localization results for easy comparison of accuracy and MAE across grid sizes, feature sets, and user configurations.

### 13.1 Single-User Voronoi — Classification (XGBoost, 2m spacing)

| Grid | Features | h=0 Acc | h=0 MAE | h=1 Acc | h=1 MAE |
|---|---|---|---|---|---|
| 10×10 (40k) | rss+sinr | — | — | 23.0% | 5.72 m |
| 10×10 (40k) | rss+sinr+AoA | 84.6% | 0.34 m | **88.5%** | **0.25 m** |
| 15×15 (90k) | rss+sinr+AoA | 75.1% | 0.61 m | **80.8%** | **0.46 m** |
| 20×20 (160k) | rss+sinr+AoA | 60.6% | 1.11 m | **67.5%** | **0.85 m** |

*AoA with 4°/5° noise. 10×10 BS-inside-grid [14,14,10]. 15×15 and 20×20 BS at grid centre.*

### 13.2 Single-User Voronoi — Regression (RandomForest, 2m spacing, 3D position error)

| Grid | Features | h=0 MAE | h=1 MAE |
|---|---|---|---|
| 10×10 (40k) | rss+sinr+AoA | 0.44 m | **0.40 m** |
| 15×15 (90k) | rss+sinr+AoA | 0.75 m | **0.61 m** |
| 20×20 (160k) | rss+sinr+AoA | 1.27 m | **0.98 m** |

### 13.3 Multi-User Voronoi 15×15 — All Experiments (pooled, realistic AoA noise 4°/5°)

225 classes, 5 device types, 450k samples total (90k × 5 users). Algorithm comparison: RF vs XGBoost.

| Experiment | Features | h | RF Acc | RF MAE | XGB Acc | XGB MAE |
|---|---|---|---|---|---|---|
| E1 — Static baseline | rss+sinr | 0 | 43.5% | 5.81 m | 27.3% | 8.39 m |
| E2 — Transitions | rss+sinr lags | 3 | 52.5% | 4.01 m | 50.4% | 4.53 m |
| E3 — +Device params | E2 + [n_ant, gain, ht] | 3 | 61.2% | 2.69 m | 58.3% | 3.20 m |
| E4 — +User ID | E2 + user_id | 3 | 61.6% | 2.85 m | 57.8% | 3.26 m |
| **E5 — Static+AoA** | rss+sinr+AoA | 0 | **77.3%** | **0.555 m** | **82.2%** | **0.439 m** |
| **E6 — Transitions+AoA** | rss+sinr lags+AoA lags | 3 | **77.1%** | **0.526 m** | **83.6%** | **0.388 m** |
| **E7 — +Device+AoA** | E6 + device params | 3 | **79.3%** | **0.471 m** | **84.9%** | **0.355 m** |
| Cross-user E2 | rss+sinr lags (U5 held out) | 3 | 46.3% | 4.92 m | 46.4% | 5.05 m |
| **Cross-user E6** | rss+sinr+AoA (U5 held out) | 3 | **72.8%** | **0.643 m** | **76.7%** | **0.612 m** |

*Per-device sanity check (RF, each user trains/tests on its own 90k samples): E1=57.2%, E5=85.9%, E6=86.2% (mean across 5 users).*

### 13.4 AoA Impact Summary

| Configuration | Without AoA (best) | With AoA (best) | AoA Gain |
|---|---|---|---|
| Single-user 10×10, XGB h=1 | 23.0% / 5.72 m | 88.5% / 0.25 m | **+65.5 pp / 22× MAE** |
| Single-user 15×15, XGB h=1 | — | 80.8% / 0.46 m | — |
| Single-user 20×20, XGB h=1 | — | 67.5% / 0.85 m | — |
| Multi-user 15×15, RF pooled | E3: 61.2% / 2.69 m | E7: 79.3% / 0.471 m | +18.1 pp / 5.7× MAE |
| Multi-user 15×15, per-device | E1: 57.2% / — | E5: 85.9% / — | +28.7 pp |
| Multi-user 15×15, cross-user RF | E2: 46.3% / 4.92 m | E6: 72.8% / 0.643 m | +26.5 pp / 7.7× MAE |

### 13.5 Grid-Scale Comparison (single-user, XGB h=1, AoA features)

| Grid | Samples | Classes | Accuracy | MAE |
|---|---|---|---|---|
| 10×10 (2m) | 40k | 100 | **88.5%** | **0.25 m** |
| 15×15 (2m) | 90k | 225 | 80.8% | 0.46 m |
| 20×20 (2m) | 160k | 400 | 67.5% | 0.85 m |

Accuracy degrades ~10–13 pp per 5-grid-step increase; MAE roughly doubles. The 15×15 multi-user pooled XGB E6 (83.6% / 0.388 m) achieves comparable MAE to 15×15 single-user (0.46 m) despite 5 heterogeneous devices, attributable to 5× more training data compensating for device diversity.
