# CSI-Based UE Localization Using Transition History

**Student:** Gilad  
**Advisors:** Prof. Sarit Kraus, Prof. David Sarna (Dudi)  
**Institution:** Bar-Ilan University  
**Industry Partners:** CEVA, Cellcom  
**Last Updated:** March 2026

---

## 1. Problem Statement

### 1.1 Motivation

Accurate indoor localization is an open challenge in 5G/6G cellular networks. GPS is unavailable indoors, and traditional methods based solely on received signal strength (RSS) suffer from low accuracy due to distance ambiguity: many locations on the same distance ring from the base station produce identical RSS values.

### 1.2 Central Hypothesis

**Transition history — the sequence of measurements observed as a UE moves — contains richer positional information than any single static snapshot.**

When a UE moves through space, the sequence of measurements encodes not only its current location but also the direction it came from. Two locations that appear identical in a static snapshot can be disambiguated by the trajectory that led to them.

### 1.3 Formal Definition

Given a single serving base station (BS) and a known grid of discrete locations, at each time step t the UE reports measurements m(t) (RSS, SINR, and optionally AoA). The model input is a window of h+1 consecutive observations:

```
x_input = [m(t-h), m(t-h+1), ..., m(t-1), m(t)]
```

where h is the history depth hyperparameter. The output is the predicted grid point (classification) or continuous coordinates (regression).

**Scope:** The serving BS performs localization using only measurements it legitimately receives from the UE. Per-interferer RSS is deliberately excluded — using it would constitute triangulation, a fundamentally different problem.

---

## 2. Simulation Environment

### 2.1 Channel Model — QuaDRiGa

All channel data is generated using **QuaDRiGa v2.8.1** implementing 3GPP TR 38.901 propagation scenarios. QuaDRiGa produces spatially-consistent, time-varying channel coefficients: as the UE moves, the channel evolves smoothly rather than independently at each step. This spatial consistency is what makes transition-based features meaningful.

**Simulation parameters:**

| Parameter | Value |
|-----------|-------|
| Center frequency | **3.5 GHz** |
| Bandwidth | 100 MHz |
| Subcarriers | 256 |
| BS antenna | 64-element Massive MIMO |
| UE height | 1.5 m (default) |
| UE speed | 1.5 m/s (pedestrian) |
| Position jitter | ±0.1 m (prevents exact grid alignment) |

### 2.2 UE Walk Model

The UE follows a **random walk** on a square grid with 8-neighbor connectivity (horizontal, vertical, and diagonal). At each grid point, 400 channel snapshots are collected before moving to the next point. This ensures adequate per-class representation in the dataset.

**Train/Test split:** Chronological — first 80% of trajectory steps form the training set, last 20% form the test set. Random splitting is explicitly avoided to prevent temporal leakage from trajectory correlation.

### 2.3 Simulation Environments

Two environments were used:

**Uniform NLOS (scalability baseline):**
- Scenario: `3GPP_38.901_UMa_NLOS` uniform across the grid
- Grid spacing: 2 m
- BS: outside the grid (single sector)
- Grid sizes tested: 3×3 to 20×20 (9 to 400 classes)

**Voronoi Heterogeneous Environment (main study):**
The grid area is partitioned into 4 Voronoi cells, each assigned a distinct 3GPP channel scenario. The diversity is intentional: using identical scenarios in multiple cells adds little localization value.

| Cell | 3GPP Scenario | Channel Type | Points (10×10) |
|------|--------------|--------------|----------------|
| Park | UMi_LOS | Open outdoor LOS | ~101 pts |
| Residential | 50/50 UMi_LOS/NLOS | Mixed suburban | ~35 pts |
| Highway | RMa_LOS | Open rural macro | ~26 pts |
| Shopping center | UMi_NLOS | Dense NLOS | ~8 pts |

**BS placement:** Inside the grid at its center (e.g., `[14,14,10m]` for the 10×10 grid). This enables 360° AoA coverage and high angular variation across grid points.

---

## 3. Feature Metrics

### 3.1 Available Measurements

| Metric | Description | Realistic? |
|--------|-------------|-----------|
| RSS | Wideband received signal strength (dBm) | Yes |
| SINR | Signal-to-interference-plus-noise ratio (dB) | Yes |
| CQI | Channel Quality Indicator (1–15, quantized) | Yes |
| AoA azimuth | Angle of arrival, horizontal plane (degrees) | Yes, with noise model |
| AoA elevation | Angle of arrival, vertical plane (degrees) | Yes, with noise model |
| Timing Advance | Round-trip propagation delay | No — no noise model implemented |

### 3.2 AoA Noise Model

Real-world AoA estimation is subject to angular resolution limits and RF noise. A two-stage impairment model is applied before any AoA value is used as a feature:

```
Step 1 — Gaussian noise:  σ = 4°  (per axis, independent seeds)
Step 2 — Quantization:    Δ = 5°  (codebook resolution)
```

AoA is extracted from QuaDRiGa's `ch.par.AoA_cb` (power-weighted cluster angle). This represents an idealized estimate; a real BS would run array processing (e.g., MUSIC or beamforming) to obtain a direction estimate. The 4°/5° impairment model approximates practical performance under LOS conditions. In NLOS cells the real-world estimate would likely be noisier.

### 3.3 Key Feature Findings

**RSS ≈ SINR without interference.** On a single-BS deployment with no co-channel interferers, both metrics encode only the distance from the BS (concentric rings). Combining them adds no information.

**AoA is the dominant feature.** On the 10×10 Voronoi grid with BS at center (XGBoost, h=1):

| Feature set | Accuracy | MAE |
|-------------|----------|-----|
| RSS only | 23.2% | 5.70 m |
| RSS + SINR | 23.0% | 5.72 m |
| + AoA azimuth | 77.9% | 0.58 m |
| + AoA elevation | **88.5%** | **0.25 m** |

AoA breaks the rotational symmetry of distance-only features: azimuth provides bearing, elevation provides range disambiguation.

**CQI is useless at short range.** At 8–15 m from the BS, all UEs saturate the top CQI quantization bucket, providing no spatial discrimination.

---

## 4. Feature Representation: Absolute Values vs. Deltas

Two representations of the transition history window were considered:

**Absolute values (raw stacking) — current approach:**
```
x = [m_t, m_{t-1}, m_{t-2}, ..., m_{t-h}]
```

**Delta representation:**
```
x = [m_t, m_t - m_{t-1}, m_{t-1} - m_{t-2}, ..., m_{t-h+1} - m_{t-h}]
```

**Why absolute values were used:** Tree-based models (XGBoost, RF) can implicitly compute differences between consecutive features. Providing raw values preserves all information and avoids lossy pre-processing.

**The case for deltas:** Differences between consecutive measurements are expected to be more robust to device-specific and environment-specific offsets. If a new device has a systematic RSS offset (e.g., due to lower antenna gain), the absolute values shift uniformly but the deltas remain approximately unchanged. This suggests:
- With **abundant data from one user**, absolute values perform equally well or better
- With **scarce data** or **multiple heterogeneous users**, deltas may generalize better by allowing data pooling across users whose absolute levels differ

**Open question for future experiments:** A controlled A/B comparison at varying data volumes and across environments with different RSS offsets is needed to quantify this trade-off.

---

## 5. Classification Results

### 5.1 Algorithm Comparison (7×7 grid, RSS+SINR, h=0 vs h=3)

| Algorithm | h=0 Acc | h=3 Acc | MAE h=0 | MAE h=3 |
|-----------|---------|---------|---------|---------|
| Gaussian | 10.9% | 15.5% | 5.03 m | 4.37 m |
| Random Forest | 28.0% | 43.6% | 3.90 m | 2.51 m |
| **XGBoost** | **26.8%** | **45.4%** | **3.93 m** | **2.39 m** |
| MLP | 24.8% | 41.6% | 4.16 m | 2.62 m |

**Transition history improves all four algorithms.** XGBoost achieves the best overall performance.

### 5.2 Scalability (XGBoost, RSS+SINR, uniform NLOS)

| Grid | Classes | h=0 MAE | h=3 MAE | Improvement |
|------|---------|---------|---------|-------------|
| 3×3 | 9 | 1.28 m | 1.05 m | −18% |
| 5×5 | 25 | 2.65 m | 1.89 m | −29% |
| 7×7 | 49 | 3.96 m | 2.64 m | −33% |
| 10×10 | 100 | 4.50 m | 2.64 m | −41% |
| 15×15 | 225 | 8.87 m | 6.21 m | −30% |
| 20×20 | 400 | 10.31 m | 7.50 m | −27% |

Transition history consistently reduces MAE at every scale from 9 to 400 classes. h=1 provides most of the gain; h>1 yields diminishing returns.

### 5.3 Voronoi Environment (XGBoost, RSS+SINR+AoA)

**10×10 Voronoi, 2m spacing, 40k samples:**

| h | Accuracy | MAE |
|---|----------|-----|
| 0 | 84.6% | 0.34 m |
| 1 | **88.5%** | **0.25 m** |
| 2 | 88.1% | 0.26 m |
| 3 | 88.3% | 0.25 m |

**15×15 Voronoi, 2m spacing, 90k samples:**

| h | Accuracy | MAE |
|---|----------|-----|
| 0 | 75.1% | 0.61 m |
| 1 | **80.8%** | **0.46 m** |

### 5.4 Per-Cell Accuracy (10×10, XGBoost h=1, full AoA)

| Cell | Channel | Size | Accuracy | Cross-cell confusion |
|------|---------|------|----------|---------------------|
| Park | UMi_LOS | 101 pts | 95.0% | 3.4% |
| Residential | Mixed | 35 pts | 92.2% | 5.1% |
| Highway | RMa_LOS | 26 pts | 73.4% | 27% |
| Shopping center | UMi_NLOS | 8 pts | 65.8% | 36% |

Cell accuracy correlates strongly with cell size. Small cells suffer from cross-boundary confusion regardless of channel type.

---

## 6. Regression Results

Instead of N² discrete classes, the regression pipeline predicts continuous 3D spherical coordinates (distance, azimuth, elevation) relative to the BS.

**Classification vs. Regression (2m spacing, Voronoi, AoA features):**

| Grid | Classification MAE | Regression MAE | Ratio |
|------|--------------------|----------------|-------|
| 10×10 | 0.25 m (XGB h=1) | 0.40 m (RF h=1) | 1.60× |
| 15×15 | 0.46 m (XGB h=1) | 0.61 m (RF h=1) | 1.33× |
| 20×20 | 0.85 m (XGB h=1) | 0.98 m (RF h=1) | 1.15× |

Classification consistently outperforms regression at 2m grid spacing. The gap narrows progressively (1.60× → 1.15×), with a crossover projected around 28–30×30 (~800–900 classes). At 2m spacing, the ±0.1m position jitter is small relative to grid spacing, giving classification a "grid-snapping" advantage that regression cannot exploit.

---

## 7. Multi-BS Interference Experiment

### 7.1 Motivation

With a single BS and no interference, RSS ≈ SINR. Adding co-channel interferers creates a spatial SINR gradient that may improve fingerprinting — without requiring triangulation.

### 7.2 Setup (v2 — realistic placement)

- Serving BS: `[14,14,10]` (grid center)
- IBS-1: `[-16,14,10]` (30m west)
- IBS-2: `[14,-16,10]` (30m south)

Orthogonal interferer directions create a 2D SINR gradient. SINR range: −4 to +11 dB (serving BS dominant throughout).

### 7.3 Results (XGBoost, h=1, 10×10 Voronoi)

| Feature set | Accuracy | MAE |
|-------------|----------|-----|
| RSS only | 19.5% | 6.53 m |
| RSS + SINR (multi-BS) | 52.8% | 3.16 m |
| RSS + SINR + AoA | **92.8%** | **0.158 m** |

Realistic interference adds +33pp over RSS alone, but remains ~40pp below AoA.

**Feature hierarchy: AoA ≫ interference SINR > single-BS RSS.**

---

## 8. Multi-User Heterogeneous Device Experiment

### 8.1 Motivation

Real networks serve UEs with heterogeneous hardware. If a model trained on one device type is deployed across varied devices, static fingerprint features (whose absolute values depend on device hardware) may degrade. Transition-based features, which capture relative changes, are hypothesized to be more robust.

### 8.2 Setup

**Grid:** 15×15, 2m spacing, 225 grid points, 4-cell Voronoi environment

**Network:** 1 serving BS at grid center + 2 outside-grid interferers (30m ISD), features from serving BS only.

**Device profiles:**

| User | Device type | Antennas | Gain | UE height | Walk seed |
|------|-------------|----------|------|-----------|-----------|
| U1 | Flagship A | 4 | 0 dB | 1.5 m | 100 |
| U2 | Mid-range | 2 | −2 dB | 1.5 m | 200 |
| U3 | Budget/Old | 1 | −4 dB | 1.5 m | 300 |
| U4 | Flagship B | 4 | 0 dB | 1.5 m | 400 |
| U5 | Tablet/IoT | 2 | −1 dB | 0.9 m | 500 |

U1 and U4 share identical hardware parameters but different walk seeds, isolating device effects from trajectory randomness.

**Multi-antenna modelling:** Maximum Ratio Combining (MRC) applied in MATLAB:
$$H_{\text{eff}}(f) = \sqrt{\sum_i |H_i(f)|^2}$$

**Data:** 90,001 samples per user → 450,005 total. Split: 80% chronological train / 20% test, strictly per user.

### 8.3 Experiment Design

| Exp | Features | h | AoA | Device info |
|-----|----------|---|-----|-------------|
| BASE | RSS + SINR | 0 | No | No |
| BASE_dp | RSS + SINR + device params | 0 | No | Yes (n_ant, gain, height) |
| BASE_uid | RSS + SINR + user_id | 0 | No | Oracle ID |
| BASE_H | RSS + SINR stacked | 3 | No | No |
| BASE_H_dp | BASE_H + device params | 3 | No | Yes (n_ant, gain, height) |
| BASE_H_uid | BASE_H + user_id | 3 | No | Oracle ID |
| BASE_A | RSS + SINR + AoA | 0 | Yes | No |
| BASE_A_dp | RSS + SINR + AoA + device params | 0 | Yes | Yes (n_ant, gain, height) |
| BASE_A_uid | RSS + SINR + AoA + user_id | 0 | Yes | Oracle ID |
| BASE_A_H | RSS + SINR + AoA stacked | 3 | Yes | No |
| BASE_A_H_dp | BASE_A_H + device params | 3 | Yes | Yes |

BASE/BASE_H test the core hypothesis. BASE_dp/BASE_uid are new static baselines (h=0) that add device knowledge without transition history — these isolate the contribution of history from device knowledge. BASE_H_dp/BASE_H_uid combine both. BASE_A–BASE_A_H_dp add AoA. BASE_A_H_dp is the full-featured upper bound.

Delta feature variants (BASE_H_delta, BASE_H_dp_delta, BASE_A_H_delta, BASE_A_H_dp_delta) replace absolute lag stacking with differential representations; results are reported in §8.9.

### 8.4 Overall Results

| Exp | XGBoost Acc | XGBoost MAE | RF Acc | RF MAE |
|-----|-------------|-------------|--------|--------|
| BASE | 27.3% | 8.39 m | 43.5% | 5.81 m |
| BASE_dp | 50.2% | 4.36 m | 57.2% | 3.75 m |
| BASE_uid | 48.7% | 4.52 m | 55.7% | 3.88 m |
| BASE_H | 50.4% | 4.53 m | 52.5% | 4.01 m |
| BASE_H_dp | 58.3% | 3.20 m | 61.2% | 2.69 m |
| BASE_H_uid | 57.8% | 3.26 m | 61.6% | 2.85 m |
| BASE_A | 82.2% | 0.44 m | 77.3% | 0.55 m |
| BASE_A_dp | 84.3% | 0.38 m | 84.4% | 0.37 m |
| BASE_A_uid | 84.1% | 0.38 m | 79.7% | 0.49 m |
| BASE_A_H | 83.6% | 0.39 m | 77.1% | 0.53 m |
| **BASE_A_H_dp** | **84.9%** | **0.35 m** | **79.3%** | **0.47 m** |

Key observations:
- BASE→BASE_H (+23pp XGB, +9pp RF): transitions improve over static baseline
- BASE→BASE_dp (+23pp XGB, +14pp RF): device parameters alone match the gain from transition history (no AoA)
- BASE_dp≈BASE_H: device knowledge and h=3 history provide comparable accuracy at h=0; combining them (BASE_H_dp) adds a further +8pp
- BASE_H→BASE_H_dp (+8pp): explicit device parameters provide additional gain on top of history
- BASE_H→BASE_A (+32pp XGB): AoA is the dominant factor, device-independent by geometry
- BASE_A→BASE_A_dp (+2pp XGB, +7pp RF): device params still help slightly with AoA; RF benefits more

### 8.5 Cross-User Generalization (U5 held out)

Model trained on U1–U4, evaluated on U5 (unseen device type):

| Exp | XGBoost | RF |
|-----|---------|-----|
| BASE_H (no AoA) | 46.4% / 5.05 m | 46.3% / 4.92 m |
| BASE_A_H (with AoA) | **76.7% / 0.61 m** | 72.8% / 0.64 m |

BASE_A_H cross-user drops only ~7pp from pooled — **AoA generalizes well across device types** because it is geometrically determined (UE position relative to BS), not electronically determined (device hardware).

The residual 4.1pp gap in BASE_A_H is attributable to U5's lower UE height (0.9m vs 1.5m), which changes the elevation angle — a physical difference, not an electronics calibration issue.

### 8.6 Per-User Breakdown (XGBoost)

| User | BASE_H Acc | BASE_A_H Acc | Gain |
|------|--------|--------|------|
| U1 (4-ant, 0 dB) | 61.6% | 87.6% | +26 pp |
| U2 (2-ant, −2 dB) | 38.5% | 80.2% | +42 pp |
| U3 (1-ant, −4 dB) | 54.7% | 84.8% | +30 pp |
| U4 (4-ant, 0 dB) | 60.7% | 87.0% | +26 pp |
| U5 (tablet, 0.9m) | 36.3% | 78.4% | +42 pp |

Weaker devices (U2, U3, U5) benefit most from AoA — angular information compensates for degraded RSS/SINR due to fewer antennas or lower gain.

### 8.7 Per-Cell Breakdown (XGBoost, BASE_H vs BASE_A)

| Cell | Channel | BASE_H Acc | BASE_A Acc | Gain |
|------|---------|--------|--------|------|
| Park | UMi_LOS | 62.6% | 88.6% | +26 pp |
| Residential | UMi_NLOS | 45.7% | 78.9% | +33 pp |
| Shopping center | UMi_NLOS | 52.1% | 81.0% | +29 pp |
| Highway | RMa_LOS | 37.9% | 76.5% | **+39 pp** |

The highway cell (RMa_LOS) benefits most from AoA. Under Rural Macro LOS, the dominant signal is a single clean ray with negligible multipath — grid points 2m apart produce nearly identical RSS/SINR fingerprints. AoA provides the only reliable spatial discriminant in this environment.

### 8.8 Static Baselines: Device Knowledge vs Transition History

The four new h=0 baselines (BASE_dp, BASE_uid, BASE_A_dp, BASE_A_uid) isolate how much of the gain in BASE_H_dp comes from device knowledge alone, versus requiring transition history.

**No-AoA regime (BASE_dp vs BASE_H):**

| Exp | XGBoost Acc | RF Acc | Note |
|-----|-------------|--------|------|
| BASE | 27.3% | 43.5% | Baseline |
| BASE_dp | 50.2% | 57.2% | h=0, device params |
| BASE_uid | 48.7% | 55.7% | h=0, oracle user ID |
| BASE_H | 50.4% | 52.5% | h=3, no device info |
| BASE_H_dp | 58.3% | 61.2% | h=3 + device params |

Device parameters at h=0 (BASE_dp: +23pp XGB) almost entirely reproduce the gain from 3-step history alone (BASE_H: +23pp XGB). This occurs because the multi-user training set mixes heterogeneous devices; RSS/SINR fingerprints differ systematically across users, and knowing the device type essentially unlocks per-user sub-models implicitly. Adding both together (BASE_H_dp: +31pp) is non-redundant — device knowledge and temporal context capture orthogonal information.

**With-AoA regime (BASE_A_dp vs BASE_A_H):**

| Exp | XGBoost Acc | RF Acc | Note |
|-----|-------------|--------|------|
| BASE_A | 82.2% | 77.3% | AoA only |
| BASE_A_dp | 84.3% | 84.4% | AoA + device params |
| BASE_A_uid | 84.1% | 79.7% | AoA + oracle ID |
| BASE_A_H | 83.6% | 77.1% | AoA + h=3 history |
| BASE_A_H_dp | 84.9% | 79.3% | AoA + h=3 + device |

With AoA, the marginal gains from device params (+2pp XGB) or history (+1.4pp XGB) are small. RF shows a larger device-params gain (+7pp) suggesting tree ensembles may be less efficient at extracting angle information implicitly. The device-physics interpretation: AoA is geometrically determined and hardware-independent, so device knowledge adds little. The ceiling at ~85% is set by the AoA noise floor (4° Gaussian + 5° quantization), not by missing device info.

**Per-user breakdown (XGBoost, BASE_dp):**

| User | BASE | BASE_dp | Gain |
|------|------|---------|------|
| U1 (4-ant, 0 dB) | 40.7% | 53.6% | +12.9 pp |
| U2 (2-ant, −2 dB) | 13.4% | 47.5% | **+34.1 pp** |
| U3 (1-ant, −4 dB) | 25.2% | 49.5% | **+24.3 pp** |
| U4 (4-ant, 0 dB) | 40.0% | 52.8% | +12.8 pp |
| U5 (tablet, 0.9m) | 17.0% | 47.6% | **+30.6 pp** |

Weaker devices (U2, U3, U5) gain far more from device-parameter conditioning than flagship devices (U1, U4). This confirms that RSS/SINR fingerprints are device-dependent, and knowing the device effectively recalibrates the feature space to a per-type absolute reference.

### 8.9 Delta Features: Absolute vs Differential Representation

Delta features replace absolute lag stacking with first-order differences: lag-0 is the current absolute value, lags 1..h are `rss[t−(k−1)] − rss[t−k]`. This representation is invariant to device-induced RSS/SINR offsets — a device with lower gain produces systematically lower absolute values but identical deltas if moving at the same speed through the same trajectory. The hypothesis was that deltas would improve cross-device generalization, particularly at low data volumes.

#### 8.9.0 Full Absolute vs Delta Results

| Experiment | XGBoost Acc | XGBoost MAE | RF Acc | RF MAE |
|------------|-------------|-------------|--------|--------|
| BASE_H (absolute) | 50.4% | 4.53 m | 52.5% | 4.01 m |
| BASE_H_delta | 48.8% | 4.85 m | 40.1% | 5.69 m |
| BASE_H_dp (absolute) | 58.3% | 3.20 m | 61.2% | 2.69 m |
| BASE_H_dp_delta | 57.7% | 3.35 m | 55.8% | 3.38 m |
| BASE_A_H (absolute) | 83.6% | 0.39 m | 77.1% | 0.53 m |
| BASE_A_H_delta | 83.4% | 0.40 m | 74.4% | 0.63 m |
| BASE_A_H_dp (absolute) | 84.9% | 0.35 m | 79.3% | 0.47 m |
| BASE_A_H_dp_delta | 84.7% | 0.37 m | 79.0% | 0.50 m |

**Gap (absolute − delta):**

| Experiment pair | XGBoost Δpp | RF Δpp |
|-----------------|-------------|--------|
| BASE_H vs BASE_H_delta | **+1.6 pp** | **+12.4 pp** |
| BASE_H_dp vs BASE_H_dp_delta | +0.6 pp | +5.4 pp |
| BASE_A_H vs BASE_A_H_delta | +0.2 pp | +2.7 pp |
| BASE_A_H_dp vs BASE_A_H_dp_delta | +0.2 pp | +0.3 pp |

The gap shrinks as more context is added: device params reduce it by 10pp (RF) and adding AoA reduces it to near-zero. When AoA is available, the representation choice is immaterial — AoA dominates and the model is insensitive to whether RSS/SINR history is absolute or differential.

#### 8.9.1 Data Volume Sweep: Absolute vs Delta (BASE_H, h=3)

Training set subsampled at 10%, 25%, 50%, 100% of the 80% chronological training window. Test set always 100%.

| Model | Representation | 10% | 25% | 50% | 100% |
|-------|----------------|-----|-----|-----|------|
| XGBoost | Absolute | 44.6% / 5.07 m | 47.8% / 4.79 m | 49.1% / 4.61 m | 50.4% / 4.53 m |
| XGBoost | Delta | 42.5% / 5.39 m | 46.1% / 5.06 m | 47.7% / 4.90 m | 48.8% / 4.85 m |
| RF | Absolute | 36.5% / 5.78 m | 44.1% / 5.03 m | 49.0% / 4.38 m | 52.5% / 4.01 m |
| RF | Delta | 27.8% / 7.06 m | 32.7% / 6.59 m | 37.6% / 5.94 m | 40.1% / 5.69 m |

Key findings:

1. **Absolute stacking outperforms delta at every data volume and for both models.** The device-invariance hypothesis is not supported in this multi-user setup.

2. **XGBoost gap is small (~1.5–2 pp)**: Tree models learn threshold-based splits that are implicitly scale-invariant; the model can compensate for device offsets internally via per-device subtrees. Delta representation removes a source of useful absolute positioning information without adding benefit.

3. **RF gap is large (~8–12 pp) and grows with more data**: RF is more sensitive to the offset removal. At 100% data, RF-delta is 12.4 pp below RF-absolute, while XGBoost-delta trails by only 1.6 pp.

4. **No crossover at low data volume**: Delta does not win even at 10% training data, where offset-invariance was expected to help most. The per-device absolute RSS/SINR fingerprint is informative, not a nuisance.

5. **Both representations show diminishing returns** beyond 50% training data. XGBoost saturates at ~50% (49.1% → 50.4% from 50%→100%); RF continues to improve (~52.5% at 100%), suggesting RF needs more data to build high-quality splits for 225 classes.

**Implication:** In this heterogeneous multi-user environment, device-specific RSS/SINR offsets carry localization-relevant information (they are consistent fingerprints for each device type). Removing them via delta representation hurts, not helps. The right way to handle device heterogeneity is to add device parameters explicitly (BASE_H_dp) rather than to remove absolute information (BASE_H_delta).

---

## 9. BS Placement Effect on AoA Informativeness (NE-Corner Experiment)

### 9.1 Motivation

In §8, the serving BS sat at the exact center of the 15×15 grid, covering ~360° of azimuth angles. AoA proved to be the dominant feature, adding +55pp over RSS+SINR. This raised a critical question: **was that gain due to genuine angular diversity, or was it an artefact of the full-circle geometry?**

In a real deployment, BSs are often mounted at walls or corridor ends — covering only a narrow angular sector. This experiment tests AoA informativeness when the BS is placed outside the grid corner.

### 9.2 Setup

| Parameter | Center BS (§8) | NE-Corner BS (§9) |
|-----------|----------------|-------------------|
| BS position | (19, 19, 10) — grid center | (48, 48, 10) — 15m NE of corner |
| Azimuth span | ~360° | ~52° (SW quadrant only) |
| d_min to grid | 0 m (BS above grid) | 21.2 m (NE corner) |
| d_max to grid | 28.3 m (corners) | 60.8 m (SW corner) |
| d_max / d_min | ∞ | 2.9 |
| Interferers | IBS-1: west, IBS-2: south | IBS-1: south, IBS-2: west |
| Grid, devices, seeds | — | Identical to §8 |

With the NE placement, **every grid point lies within the same 52° azimuth wedge** as seen from the BS. Azimuth variation within that sector is limited; UEs in the NE corner appear at ~225° and SW corner at ~251° — only a 26° spread across the full diagonal.

### 9.3 Research Questions — Answers

**Q1 — AoA gain with compressed angular spread (primary)**

| Experiment | Center BS XGB | NE BS XGB | Center BS RF | NE BS RF |
|---|---|---|---|---|
| BASE_H | 50.4% / 4.53 m | 62.7% / 2.79 m | 52.5% / 4.01 m | 62.2% / 2.63 m |
| BASE_A_H | 83.6% / 0.39 m | 69.6% / 1.27 m | 77.1% / 0.53 m | 65.1% / 1.36 m |
| **AoA gain** | **+33.2 pp** | **+6.9 pp** | **+24.6 pp** | **+2.9 pp** |

**AoA gain drops from +33 pp to +7 pp (XGB) and from +25 pp to +3 pp (RF).** This confirms that the center-BS AoA advantage was primarily geometric: full angular coverage gave AoA near-perfect discriminative power. With a 52° sector, azimuth variation is minimal and AoA contributes little beyond what RSS+SINR already encode.

The residual ~7 pp (XGB) gain is attributable to **elevation angle**, which encodes rough distance (elevation spans ~9°–31° across the grid diagonal from the NE BS at height 10 m) and remains informative even when azimuth is compressed.

**Q2 — History compensation**

| Metric | Center BS | NE BS |
|---|---|---|
| BASE_H − BASE (XGB) | +23.1 pp | **+23.2 pp** |
| BASE_H − BASE (RF) | +9.0 pp | **+10.3 pp** |

Transition history gain is **identical** regardless of BS placement. History captures trajectory dynamics that are independent of the angular coverage of the BS. This strengthens the core thesis: the transition benefit is not a geometry artefact.

**Q3 — RSS/SINR discrimination with edge BS**

BASE accuracy is *higher* with the NE placement (XGB: 39.5% vs 27.3%; RF: 51.9% vs 43.5%). The NE BS creates a larger RSS dynamic range (d_min=21m vs 0m, d_max=61m vs 28m), making distance-based RSS differentiation more effective. Points near the NE corner have clearly stronger RSS than SW-corner points, providing a natural gradient fingerprint.

**Q4 — Spatial MAE distribution (NE dead zone)**

Per-Voronoi-cell results (XGBoost, BASE_H):

| Cell | NE BS Acc | NE BS MAE | Center BS Acc | Center BS MAE |
|------|-----------|-----------|---------------|---------------|
| 1 | 66.3% | 3.66 m | 37.9% | 4.84 m |
| 2 | 54.8% | 3.16 m | 52.1% | 6.01 m |
| 3 | 85.0% | 0.93 m | 45.7% | 6.04 m |
| 4 | 86.5% | 0.94 m | 62.6% | 3.47 m |

Cells 3 and 4 (closer to the NE BS) achieve 85–87% accuracy with sub-metre MAE — better than any cell in the center-BS experiment without AoA. Cells 1 and 2 (farther from the NE BS, in the SW/W part of the grid) are significantly worse. The **spatial gradient from NE (high accuracy) to SW (lower accuracy)** is clear, confirming the dead-zone hypothesis. Adding device parameters (BASE_H_dp) largely recovers cells 1–2 to 74–74% accuracy.

**Q5 — Elevation AoA**

The residual +6.9 pp AoA gain without history (BASE_A − BASE: XGB 63.1% − 39.5% = **+23.6 pp**) demonstrates that even in a 52° azimuth sector, AoA provides meaningful information. Given that azimuth contributes minimally in a narrow sector, this gain is driven primarily by **elevation angle encoding distance**. This is consistent with the BS height of 10 m and the 8.5 m height differential to UEs (1.5 m height, 10 − 1.5 = 8.5 m vertical gap), which maps cleanly to distance via arctan(8.5/d).

### 9.4 Overall Results

| Exp | NE XGB Acc | NE XGB MAE | Center XGB Acc | Center XGB MAE | NE RF Acc | NE RF MAE | Center RF Acc | Center RF MAE |
|-----|-----------|-----------|----------------|----------------|-----------|-----------|----------------|----------------|
| BASE | 39.5% | 6.15 m | 27.3% | 8.39 m | 51.9% | 4.93 m | 43.5% | 5.81 m |
| BASE_dp | 61.4% | 3.16 m | 50.2% | 4.36 m | 65.1% | 2.89 m | 57.2% | 3.75 m |
| BASE_uid | 59.7% | 3.30 m | 48.7% | 4.52 m | 63.8% | 3.02 m | 55.7% | 3.88 m |
| BASE_H | 62.7% | 2.79 m | 50.4% | 4.53 m | 62.2% | 2.63 m | 52.5% | 4.01 m |
| BASE_H_dp | 68.3% | 2.02 m | 58.3% | 3.20 m | 69.3% | 1.73 m | 61.2% | 2.69 m |
| BASE_A | 63.1% | 1.97 m | 82.2% | 0.44 m | 60.1% | 2.11 m | 77.3% | 0.55 m |
| BASE_A_H | 69.6% | 1.27 m | 83.6% | 0.39 m | 65.1% | 1.36 m | 77.1% | 0.53 m |
| BASE_A_H_dp | 73.1% | 1.06 m | 84.9% | 0.35 m | 67.6% | 1.16 m | 79.3% | 0.47 m |

Key observations:
- **BASE is *better* with NE BS** (+12 pp XGB, +8 pp RF) — larger RSS dynamic range compensates for AoA loss
- **BASE_H is *better* with NE BS** (+12 pp XGB, +10 pp RF) — same reason; history amplifies an already stronger RSS gradient
- **BASE_A is *much worse* with NE BS** (−19 pp XGB, −17 pp RF) — AoA loses most of its power in a 52° sector
- **BASE_A_H is *much worse* with NE BS** (−14 pp XGB, −12 pp RF) — AoA ceiling is lower; history partially compensates
- **The NE BS makes experiments converge**: without AoA, NE ≥ center; with AoA, center >> NE. The gap between AoA and non-AoA experiments shrinks from ~33 pp (center) to ~7 pp (NE)

### 9.5 Cross-User Generalization

| Exp | NE XGB | Center XGB | NE RF | Center RF |
|-----|--------|------------|-------|-----------|
| cross_user_BASE_H | 53.9% / 3.89 m | 46.4% / 5.05 m | 52.9% / 3.81 m | 46.3% / 4.92 m |
| cross_user_BASE_A_H | 59.5% / 2.02 m | 76.7% / 0.61 m | 56.5% / 1.84 m | 72.8% / 0.64 m |

Cross-user BASE_H generalizes *better* with NE BS (+7 pp) — the stronger RSS gradient provides a more device-independent fingerprint. However, cross-user BASE_A_H drops dramatically (−17 pp XGB) — AoA generalizes well when it is the dominant feature, but with a weaker AoA signal the model falls back on RSS/SINR, which varies across devices.

### 9.6 Delta Features with NE BS

| Pair | NE XGB Δpp | NE RF Δpp | Center XGB Δpp | Center RF Δpp |
|------|-----------|-----------|----------------|----------------|
| BASE_H vs BASE_H_delta | +0.1 pp | +12.7 pp | +1.6 pp | +12.4 pp |
| BASE_A_H vs BASE_A_H_delta | +0.1 pp | +9.8 pp | +0.2 pp | +2.7 pp |

Delta disadvantage for RF is **larger with NE BS in the AoA case** (+9.8 pp vs +2.7 pp center). With weaker AoA signal, RF relies more on absolute RSS/SINR values — removing offsets via delta representation is correspondingly more harmful. The XGBoost result confirms the pattern seen with the center BS: tree models are nearly insensitive to the absolute/delta choice.

---

## 10. Key Findings

1. **Transition history improves all algorithms at every scale** — verified across 6 grid sizes (9–400 classes), 4 ML algorithms, and 2 feature sets. h=1 captures most of the gain; h>1 yields diminishing returns.

2. **AoA informativeness is geometry-dependent** — with a center BS (full 360° coverage), AoA adds +33 pp over RSS+SINR+history. With a NE-corner BS (52° sector), AoA adds only +7 pp. The gain is driven by azimuth diversity; without it, only elevation angle contributes (encoding rough distance via the BS height).

3. **Transition history gain is geometry-independent** — BASE_H − BASE is +23 pp (XGBoost) in both BS placements. History captures trajectory dynamics that are orthogonal to angular BS coverage. This makes transition features more deployable than AoA: they work regardless of BS mounting position.

4. **Edge BS improves RSS/SINR discrimination** — the NE BS placement creates a larger distance dynamic range (21–61 m vs 0–28 m), making BASE and BASE_H stronger baselines than with the center BS (+12 pp XGBoost). The geometry trades AoA informativeness for better amplitude-based discrimination.

5. **RSS ≈ SINR without interference** — combining them adds nothing. Realistic co-channel interference creates a useful 2D SINR gradient (+33pp over RSS alone), but remains far below AoA with center BS.

6. **Classification outperforms regression at fine grid spacing** — by 1.15–1.60× depending on grid size; gap narrows toward ~800–900 classes.

7. **AoA is device-independent when it is strong** — cross-user generalization drops only ~7 pp with AoA (center BS). With NE BS, the weaker AoA signal causes the model to fall back on RSS/SINR, increasing cross-user sensitivity; BASE_A_H cross-user drops by ~17 pp compared to center BS.

8. **Device parameters as features help** — BASE_H_dp adds +8–12 pp over BASE_H; weakest devices benefit most (U2: +34 pp at h=0). Device knowledge and transition history capture orthogonal information: BASE_dp ≈ BASE_H in accuracy, but BASE_H_dp outperforms both.

9. **Cell size dominates per-cell accuracy** — small Voronoi cells (~8 pts) suffer 36% cross-cell confusion; large cells (~100 pts) achieve 95%.

10. **Absolute stacking beats delta features** — device-specific RSS/SINR offsets are consistent location fingerprints, not noise. Delta features hurt RF by ~12 pp (no AoA); the gap is near-zero with AoA+device params. With NE BS and weak AoA, the RF delta gap widens to ~10 pp even in the AoA case.

---

## 10. Open Questions and Future Work

1. **Absolute values vs. deltas:** *(Complete — §8.9)* Absolute stacking outperforms delta at every data volume. Gap: large without AoA (XGB +1.6 pp, RF +12.4 pp), near-zero with AoA+device params (≤0.3 pp). With NE BS and weak AoA, RF delta gap widens to ~10 pp. Device-specific offsets are informative fingerprints, not confounders.

2. **AoA vs. BS placement:** *(Complete — §9)* AoA gain drops from +33 pp (center BS) to +7 pp (NE BS, 52° sector). History gain is stable at ~23 pp in both placements. Elevation angle accounts for the residual AoA benefit at NE BS. The transition feature is geometry-robust; AoA is not.

3. **Environmental variability:** *(Pending)* Run U1 three times (same walk, different QuaDRiGa seeds 101/102/103), train on runs 1+2, test on run 3. Tests whether transition features are robust to day-to-day channel drift. MATLAB script ready (`run_env_variability_15x15.m`), simulation not yet run.

4. **Hyperparameter optimisation (Optuna):** *(Planned)* Current models use conservative fixed hyperparameters (`n_estimators=50`). Tune once on BASE_H, freeze for all experiments. Expected gain: ~5–8 pp from `n_estimators=200–300` alone. Optuna for systematic search of depth/learning rate.

5. **Hierarchical classification:** Two-stage classifier (Voronoi cell → point within cell) as a scalability strategy for larger grids.

4. **Real-world validation:** Transferability of simulation results to physical hardware deployments.

---

## Appendix: Technical Notes

### A. SINR Bug Fix (multi-BS experiment)

Version 1 of the multi-BS experiment had a 30 dB SINR error: interferer power was computed against a 0 dBm reference while the actual TX power was 30 dBm. Fixed by:
```
interference = |H_IBS|² × (1e-3 × rel_power)
rel_power = 10^((IBS_TX_dBm − serving_TX_dBm) / 10)
```

### B. Memory Fix (Gaussian model)

At h=3 on a 10×10 grid, the Gaussian broadcast `norm.logpdf(N=8000, P=35952, H=3)` required 6.43 GB. Fixed with chunked batch processing:
```python
_MEM_BUDGET = 256 * 1024 * 1024  # 256 MB per chunk
chunk_size = max(1, int(_MEM_BUDGET / (P * history_len * 8)))
```

### C. Performance Optimizations

Batch prediction rewrites reduced experiment runtime by 71–1647×:

| Model | Before | After | Speedup |
|-------|--------|-------|---------|
| Random Forest | 175.6 s | 0.107 s | 1,647× |
| XGBoost | 7.8 s | 0.110 s | 71× |
| Gaussian h=3 | ~600 s | 1.75 s | ~340× |
| MLP | ~300 s | ~0.5 s | ~600× |

Full 7×7 experiment matrix (71 configs) reduced from 8+ hours to ~10 minutes.
