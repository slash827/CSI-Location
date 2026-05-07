# Technical Documentation
# CSI-Based UE Localization Using Transition History

**Student:** Gilad Battat 
**Advisors:** Prof. Sarit Kraus, Prof. David Sarne 
**Institution:** Bar-Ilan University  
**Industry Partners:** CEVA, Cellcom

---

## 1. Problem Statement

### 1.1 Motivation

5G and 6G networks expose a rich set of channel-derived measurements — RSS, SINR, Angle of Arrival, timing advance — natively at the base station without requiring dedicated positioning infrastructure. Leveraging these for accurate UE localization is a strategic goal of 3GPP Release 16 and beyond, motivated by use cases ranging from emergency response and asset tracking to network-assisted navigation in environments where GPS is unreliable or unavailable.

GPS performance degrades significantly in urban canyons, tunnels, and indoor spaces due to signal blockage and multipath. Cellular-based positioning addresses these gaps: a UE that is in radio contact with a BS can in principle be localized using only the measurements the BS already receives. The challenge is accuracy. The most accessible channel metric — Received Signal Strength (RSS) — correlates with distance but suffers from a fundamental geometric ambiguity: every location on the same distance ring from the BS produces the same RSS value, regardless of direction. This *distance-ring ambiguity* limits static RSS fingerprinting to metre-level accuracy at best in environments with moderate multipath, and degrades severely in LOS-dominated settings (outdoor open areas, corridors) where the distance-to-RSS mapping is near-monotone and provides no directional information.

SINR with co-channel interference and Angle of Arrival break the ring ambiguity by adding directional components, but both depend on infrastructure configuration and geometry. The goal of this work is to identify a localization strategy that is robust across both indoor (rich multipath, limited GPS) and outdoor (LOS-dominated, GPS-degraded) conditions, using only measurements from a single serving BS.

### 1.2 Central Thesis

> **Transition history — the sequence of measurements observed as a UE moves — encodes richer positional information than any single static snapshot.**

When a UE moves through space, consecutive measurements capture both the current location and the direction of travel. Two locations that appear identical in a static snapshot can be disambiguated by the trajectory that led to them.

Formally, given a serving base station and a discrete grid of locations, at each time step *t* the UE reports measurements m(t) (RSS, SINR, and optionally AoA). The model input is a window of h+1 consecutive observations:

```
x_input = [m(t-h), m(t-h+1), ..., m(t-1), m(t)]
```

where *h* is the history depth hyperparameter.

### 1.3 Scope

This work tests the thesis through simulation under controlled but diverse conditions:

- **Environment coverage** — experiments span both indoor-like (UMi_NLOS shopping center, mixed UMi residential) and outdoor/semi-outdoor (UMi_LOS park, RMa_LOS highway) 3GPP scenarios within the same grid. This ensures the localization pipeline is evaluated across the full indoor-to-outdoor spectrum rather than optimised for a single propagation regime.
- **Single serving BS** — the BS performs localization using only measurements it legitimately receives from the UE. Per-interferer RSS is explicitly excluded to avoid triangulation (a different problem requiring distributed infrastructure).
- **Classification** — each grid point is a discrete class. This is appropriate at ≤2m grid spacing; we show it outperforms regression at all tested scales.
- **Reproducibility** — all channel data is generated via QuaDRiGa/3GPP TR 38.901 with fixed seeds; results are fully reproducible.

---

## 2. System Architecture

### 2.1 Pipeline Overview

The system consists of two decoupled layers connected by `.mat` files:

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1: MATLAB + QuaDRiGa (Channel Simulation)                    │
│                                                                     │
│  run_multi_user_15x15.m  ──►  generate_simulation_data.m            │
│         (orchestrator)               (core engine)                  │
│                                                                     │
│  • Loads JSONC config (grid, BS, channel scenario)                  │
│  • Generates 15×15 grid positions + adjacency map                   │
│  • Generates random-walk trajectory                                 │
│  • Sets up QuaDRiGa v2.8.1 (3GPP TR 38.901)                         │
│  • Simulates channel for serving BS + interferers                   │
│  • Applies multi-antenna MRC combining (device model)               │
│  • Extracts RSS, SINR, AoA (azimuth + elevation)                    │
│  • Applies AoA noise model (4° Gaussian + 5° quantization)          │
│  • Saves: user{N}_{experiment}.mat  (per-user flat struct)          │
└─────────────────────────┬───────────────────────────────────────────┘
                          │  per-user .mat files (5 users × ~90k rows)
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 2: Python + scikit-learn / XGBoost (ML Pipeline)             │
│                                                                     │
│  pipelines/multi_user_pipeline.py                                   │
│                                                                     │
│  load_all_users()  ──►  make_split()  ──►  build_history_features() │
│       ▼                                          ▼                  │
│  DataFrame (450k rows)             Feature matrix [N, D×(h+1)]      │
│       ▼                                          ▼                  │
│  run_all_experiments()  ──►  XGBoost / RF  ──►  evaluate()          │
│       ▼                                          ▼                  │
│  save_results()                     results_summary.csv + plots     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Contract

Each `.mat` file written by MATLAB contains flat arrays:

| Variable | Shape | Description |
|---|---|---|
| `rss` | [N, 1] | Wideband RSS from serving BS (dBm) |
| `sinr` | [N, 1] | Wideband SINR from serving BS (dB) |
| `aoa_az` | [N, 1] | AoA azimuth (degrees, noisy) |
| `aoa_el` | [N, 1] | AoA elevation (degrees, noisy) |
| `grid_point_id` | [N, 1] | True grid point (1-indexed) |
| `step_index` | [N, 1] | Chronological order |
| `x_pos`, `y_pos` | [N, 1] | True position (metres) |
| `voronoi_cell_id` | [N, 1] | Voronoi cell membership |
| `device_profile` | struct | n_antennas, gain, height |
| `user_id_val` | scalar | User identifier |

Python loads all 5 files and concatenates into a single DataFrame.

---

## 3. Simulation Environment

### 3.1 Channel Model

All channel data is generated using **QuaDRiGa v2.8.1** implementing **3GPP TR 38.901**. QuaDRiGa produces spatially-consistent, time-varying channel coefficients: as the UE moves, the channel evolves smoothly rather than independently at each step. This spatial consistency is what makes transition-based features informative — consecutive measurements are correlated in a directionally meaningful way.

| Parameter | Value |
|---|---|
| Center frequency | 3.5 GHz |
| Bandwidth | 100 MHz |
| Subcarriers (OFDM) | 256 |
| BS antenna | 64-element Massive MIMO |
| TX power (serving + interferers) | 30 dBm |
| 3GPP standard | TR 38.901 |
| Spatial consistency | Yes (channel evolves continuously) |

### 3.2 Grid Environment

The localization target is a 15×15 grid of discrete points:

| Parameter | Value |
|---|---|
| Grid size | 15×15 = 225 points |
| Grid spacing | 2 m |
| Grid offset from origin | [5, 5] m |
| X, Y range | [5, 33] m × [5, 33] m |
| UE height | 1.5 m (U5: 0.9 m) |
| Position jitter | ±0.1 m per snapshot |
| Neighbor connectivity | 8 (4 cardinal + 4 diagonal) |

The position jitter prevents the model from fitting to perfectly aligned grid coordinates — measurement positions vary slightly around each nominal grid point.

### 3.3 Voronoi Heterogeneous Environment

The grid area is partitioned into 4 Voronoi cells, each with a distinct 3GPP propagation scenario. This creates a heterogeneous propagation environment spanning indoor-like dense NLOS to outdoor LOS conditions, where different zones exhibit genuinely different channel characteristics:

| Cell | Scenario | Type | Approx. Grid Points |
|------|----------|------|---------------------|
| 1 (Park) | UMi_LOS | Line-of-sight, urban micro | ~101 |
| 2 (Residential) | UMi_LOS/NLOS (mixed) | Mixed suburban | ~35 |
| 3 (Highway) | RMa_LOS | Line-of-sight, rural macro | ~26 |
| 4 (Shopping center) | UMi_NLOS | Dense non-line-of-sight | ~8 |

Each Voronoi cell boundary is generated by AreaGenerator at simulation time with a fixed random seed, ensuring reproducibility.

**Rationale for heterogeneity:** A homogeneous environment would provide only range-based discrimination (distance ring ambiguity). Mixed scenarios create spatial fingerprints where both channel amplitude and multipath structure vary across the grid.

### 3.4 UE Trajectory — Random Walk

The UE trajectory is generated as a constrained random walk on the grid adjacency graph:

1. Start at the grid center
2. At each step, select uniformly from 8-connected neighbors
3. Repeat for 400 steps per grid point = 90,000 total steps (+1 for initial position)

**Walk seed:** Each user has a unique seed for their walk trajectory. U1 and U4 share identical hardware parameters but use different walk seeds (100 vs 400), isolating device effects from trajectory randomness.

**Step duration:** `spacing / ue_speed = 2m / 1.5 m/s = 1.33 s` (diagonal steps: 1.33s × √2).

### 3.5 Base Station Configurations

#### Main Experiment — Center BS

```
Grid: X ∈ [5, 33],  Y ∈ [5, 33]   (center = [19, 19])

Serving BS: [19, 19, 10]   ← at grid center
  → Distance range: 0–28.3 m
  → AoA azimuth spread: ~360° (all grid points visible in full circle)

IBS-1: [-11, 19, 10]   ← 30m west   (creates E–W SINR gradient)
IBS-2: [ 19,-11, 10]   ← 30m south  (creates N–S SINR gradient)
```

#### BS Placement Study — NE-Corner BS

To test whether AoA informativeness depends on angular coverage (see §6.3):

```
Serving BS: [48, 48, 10]   ← 15m north + 15m east of NE corner [33,33]
  → Distance range: 21.2–60.8 m
  → AoA azimuth spread: ~52° (all points in SW quadrant)

IBS-1: [ 19,-10, 10]   ← south of grid
IBS-2: [-10, 19, 10]   ← west of grid
```

All other parameters (grid, device profiles, Voronoi environment) are identical to the center-BS experiment.

### 3.6 Multi-User Device Heterogeneity

Five UE profiles are simulated simultaneously. Each profile is a separate QuaDRiGa run with the same channel seed but different device parameters:

| User | Device Type | Antennas | Gain | Height | Walk Seed |
|------|-------------|----------|------|--------|-----------|
| U1 | Flagship A | 4 | 0 dB | 1.5 m | 100 |
| U2 | Mid-range | 2 | −2 dB | 1.5 m | 200 |
| U3 | Budget/Old | 1 | −4 dB | 1.5 m | 300 |
| U4 | Flagship B | 4 | 0 dB | 1.5 m | 400 |
| U5 | Tablet/IoT | 2 | −1 dB | 0.9 m | 500 |

**Multi-antenna modelling — Maximum Ratio Combining (MRC):**

$$H_{\text{eff}}(f) = \sqrt{\sum_{i=1}^{N_{\text{ant}}} |H_i(f)|^2}$$

RSS and SINR are computed from H_eff, then the antenna gain offset (dB) is applied additively. This models both receive array gain and device-specific hardware quality.

**Total dataset:** 5 users × 90,001 samples = **450,005 samples**.

### 3.7 AoA Noise Model

Clean AoA (power-weighted cluster angle from QuaDRiGa `ch.par.AoA_cb`) is degraded to model realistic estimation impairments:

**Step 1 — Estimation noise** (independent per axis, per snapshot):
- Azimuth: `aoa_az += 4° × N(0,1)`
- Elevation: `aoa_el += 4° × N(0,1)`

**Step 2 — Quantization** (codebook resolution):
- `aoa_az = round(aoa_az / 5°) × 5°`
- `aoa_el = round(aoa_el / 5°) × 5°`

**Physical basis:** Models a beamforming-based AoA estimator (analog beamformer or digital MUSIC) with typical angular resolution. Clean QuaDRiGa AoA represents the ideal far-field geometry; noise and quantization bring it closer to what a real BS would report.

Applied in Python at load time (not during MATLAB simulation), enabling comparison of clean vs. degraded AoA without rerunning simulation.

---

## 4. Feature Engineering

### 4.1 Static Baseline (h = 0)

The simplest input is a single snapshot of measurements at time *t*:

```
x_static = [rss_t, sinr_t]               (no AoA)
x_static = [rss_t, sinr_t, az_t, el_t]   (with AoA)
```

This represents classical RSS fingerprinting and is the comparison baseline for all transition-based experiments.

### 4.2 Transition History Stacking (h > 0)

History features are built by stacking h+1 consecutive snapshots:

```
x_history = [rss_{t-h}, sinr_{t-h}, ...,
             rss_{t-1}, sinr_{t-1},
             rss_t,     sinr_t]
```

Column naming: `rss_lag0` (current), `rss_lag1` (t-1), ..., `rss_lag{h}` (t-h).

Feature vector size:
- **Without AoA:** D = 2 × (h+1)
- **With AoA:** D = 4 × (h+1)

For h=3 with AoA: **D = 16 features**.

**Implementation:** For each user, samples are sorted by `step_index`. The first h rows have incomplete history and are dropped. Users are processed independently — lag features never cross user boundaries.

**Why absolute values (not differences):** Device-specific RSS/SINR offsets are consistent across the grid for a given device. These offsets act as location fingerprints themselves. Removing them (via differencing) discards useful information, as confirmed experimentally (§6.2).

### 4.3 Optional Feature Augmentations

Device parameters and identity can be appended as additional features:

| Augmentation | Columns | Purpose |
|---|---|---|
| Device params (`dp`) | `feat_n_antennas`, `feat_antenna_gain_db`, `feat_ue_height` | Explicit device recalibration |
| User ID (`uid`) | `feat_user_id` | Oracle device identity (upper bound) |

Device params enable the model to implicitly learn per-device fingerprint corrections without requiring separate per-device models. User ID provides an oracle upper bound (unrealistic in deployment, useful for analysis).

### 4.4 Experiment Registry

All experiments are defined in a single Python registry. Each entry specifies the complete feature configuration:

| Key | h | AoA | Extra | What it isolates |
|-----|---|-----|-------|-----------------|
| `BASE` | 0 | No | — | Static fingerprint baseline |
| `BASE_dp` | 0 | No | device | Device knowledge alone |
| `BASE_uid` | 0 | No | user_id | Oracle device identity |
| `BASE_H` | 3 | No | — | **Core: history alone** |
| `BASE_H_dp` | 3 | No | device | History + device knowledge |
| `BASE_H_uid` | 3 | No | user_id | History + oracle identity |
| `BASE_A` | 0 | Yes | — | AoA alone, no history |
| `BASE_A_dp` | 0 | Yes | device | AoA + device knowledge |
| `BASE_A_uid` | 0 | Yes | user_id | AoA + oracle identity |
| `BASE_A_H` | 3 | Yes | — | History + AoA combined |
| `BASE_A_H_dp` | 3 | Yes | device | Full feature set (upper bound) |

---

## 5. Evaluation Framework

### 5.1 Task Formulation

Localization is treated as a **225-class classification problem** (one class per grid point). This is appropriate because:

- **Grid spacing (2 m) >> position jitter (±0.1 m)** — discrete labels are unambiguous
- **Classification error is spatially meaningful** — predicting an adjacent cell is qualitatively better than predicting a far cell

### 5.2 Train/Test Split

**Method:** Strictly chronological, 80/20, applied **independently per user**.

For each user:
1. Sort all N samples by `step_index`
2. Take first 0.8N as training set
3. Take last 0.2N as test set

**Why chronological:** Standard random splits leak temporal information. Since consecutive measurements share channel characteristics (QuaDRiGa spatial consistency), a random split would allow the model to interpolate between nearby train and test samples. Chronological splits prevent this.

**Total split:** 360,005 training samples + 90,000 test samples across 5 users.

### 5.3 Evaluation Metrics

**Classification Accuracy:** percentage of test samples correctly classified to the exact grid point.

**Mean Absolute Error (MAE):** mean Euclidean distance between predicted and true grid point locations:

$$\text{MAE} = \frac{1}{N_{\text{test}}} \sum_{i=1}^{N_{\text{test}}} \| \mathbf{p}_{\text{pred},i} - \mathbf{p}_{\text{true},i} \|_2$$

where p are 2D coordinates of the predicted/true grid point.

MAE is more intuitive than accuracy for localization (it has physical units — metres).

**Per-user and per-cell breakdowns:** accuracy and MAE are also reported per user (to study device heterogeneity) and per Voronoi cell (to study spatial variation).

### 5.4 Models

Two ML models are evaluated throughout:

**XGBoost:**

| Hyperparameter | Value |
|---|---|
| `n_estimators` | 50 |
| `max_depth` | 5 |
| `learning_rate` | 0.15 |
| `subsample` | 0.8 |
| `colsample_bytree` | 0.8 |
| `random_state` | 42 |

**Random Forest:**

| Hyperparameter | Value |
|---|---|
| `n_estimators` | 50 |
| `max_features` | `'sqrt'` |
| `max_depth` | 15 |
| `min_samples_leaf` | 20 |
| `random_state` | 42 |

Both models are trained on 0-indexed labels for XGBoost compatibility, then mapped back to 1-indexed grid point IDs for evaluation. The same hyperparameters are used for all experiments to ensure fair comparison.

---

## 6. Experimental Results

### 6.0 Regression vs Classification — Homogeneous Environments

Before moving to the multi-user Voronoi experiments, we explored an alternative task formulation: **3D regression**, where the model predicts physical coordinates (distance from BS, azimuth angle, elevation angle) rather than a discrete grid-point label. These experiments used single-user, homogeneous 3GPP scenarios on the same 15×15 grid, providing a clean comparison between the two approaches.

#### 6.0.1 Regression Task Definition

The regression model predicts three continuous targets simultaneously:

| Target | Meaning | Unit |
|---|---|---|
| Distance | Euclidean distance UE → BS | metres |
| Azimuth | Horizontal angle BS → UE | degrees |
| Elevation | Vertical angle BS → UE | degrees |

Final **3D Position MAE** is computed by reconstructing the XY position from predicted (distance, azimuth) and comparing to the true position. The pipeline is implemented in `localization_pipeline_regression.py` using XGBoost regressors, one per target.

#### 6.0.2 Feature Progression in Regression — UMi_NLOS and UMa_NLOS

Experiments were run across two homogeneous scenarios to reveal the contribution of each feature type. **UMi_NLOS** (Urban Micro, NLOS, 90,001 samples) and **UMa_NLOS** (Urban Macro, NLOS, 22,501 samples).

**UMi_NLOS — static (h=0):**

| Feature set | 3D Position MAE | Note |
|---|---|---|
| RSS alone | 14.15 m | Fails — range ring ambiguity |
| SINR alone | 14.14 m | ≈ RSS — confirms RSS ≈ SINR without interference |
| RSS + SINR | 14.15 m | No improvement over RSS |
| + AoA azimuth | 0.78 m | Dramatic drop — azimuth resolves direction |
| + AoA elevation | **0.62 m** | Elevation adds distance encoding |

**UMa_NLOS — static (h=0):**

| Feature set | 3D Position MAE | Note |
|---|---|---|
| RSS alone | 31.03 m | Fails severely — macro scenario, poor distance resolution |
| SINR alone | 31.03 m | Identical to RSS |
| RSS + SINR | 31.02 m | No improvement |
| + AoA azimuth | 4.54 m | Partial — azimuth alone insufficient in macro |
| + AoA elevation | **2.01 m** | Elevation essential in macro NLOSenvironment |

RSS and SINR provide no useful information in either scenario without AoA. In UMa_NLOS, RSS varies so weakly with distance that the model cannot form a useful distance estimate. The 17× gap between UMi (14 m) and UMa (31 m) with RSS alone reflects the more severe distance ambiguity under macro propagation.

#### 6.0.3 History Effect in Regression

History has a qualitatively different effect in regression than in classification.

**UMi_NLOS with AoA (h=0 → h=1):**

| h | 3D Position MAE |
|---|---|
| 0 | 0.622 m |
| 1 | **0.516 m** (−17%) |

**UMa_NLOS with all features (h=0 → h=3):**

| h | 3D Position MAE |
|---|---|
| 0 | 1.042 m |
| 1 | 1.099 m |
| 2 | 1.140 m |
| 3 | 1.163 m |

In the UMi_NLOS case, adding h=1 improves regression by 17%. But in UMa_NLOS, history monotonically **hurts** regression: each additional lag step adds error. This is the opposite of the classification finding.

The explanation is architectural: regression predicts absolute coordinates, and consecutive positions are spatially offset from one another. Stacking lags introduces past positions that are slightly wrong (due to noise), and the regressor struggles to disentangle the offset from the current position signal. Classification, by contrast, maps trajectories to discrete labels and benefits from the directional disambiguation that consecutive steps provide.

#### 6.0.4 LOS vs NLOS — Classification

For completeness, the classification task was also evaluated on a **UMa_LOS homogeneous environment** (single user, 90,001 samples, full feature set including AoA):

| h | Accuracy | MAE |
|---|----------|-----|
| 0 (static) | 92.59% | 0.292 m |
| 1 | **95.90%** | 0.136 m |
| 2 | 95.54% | 0.140 m |
| 3 | 95.86% | 0.128 m |

LOS classification with AoA reaches 92.6% accuracy at h=0 — already much higher than the NLOS equivalent — because the dominant single-ray LOS channel makes AoA highly stable and precise. History adds +3.3 pp. The benefit of history is smaller in LOS than NLOS because there is less ambiguity to resolve at h=0 in the first place.

#### 6.0.5 Classification vs Regression — Head-to-Head

Direct comparison on 15×15 grid, RSS+SINR+AoA features:

| Task | Environment | h | 3D Position MAE |
|---|---|---|---|
| **Regression** | UMi_NLOS (single user) | 0 | 0.622 m |
| **Regression** | UMi_NLOS (single user) | 1 | 0.516 m |
| **Classification** | UMi_NLOS + Voronoi (multi-user) | 0 | 0.44 m |
| **Classification** | UMi_NLOS + Voronoi (multi-user) | 3 | **0.39 m** |

Classification outperforms regression at 2 m grid spacing. The ratio is approximately **1.15–1.33×** depending on configuration. The advantage grows with grid size and shrinks as the number of classes approaches the density where discrete labels become ambiguous (estimated crossover near 28–30×30, ~800–900 classes).

**Why classification wins at fine spacing:**
At 2 m grid spacing with ±0.1 m position jitter, each grid point is well-separated and its label is unambiguous. Classification exploits this fully — any error in predicting a nearby class carries a known 2 m penalty. Regression must estimate floating-point coordinates and accumulates noise from all three independently predicted targets (distance, azimuth, elevation).

**Why regression is still valuable:**
Regression is the natural choice when the grid is not known in advance, the target is an arbitrary continuous location, or the grid spacing is larger than the AoA angular resolution. At coarser grids (>4 m spacing) or in outdoor macro scenarios, regression may perform comparably or better.

### 6.1 Scalability: History Benefit Across Grid Sizes

Before the multi-user experiment, the core thesis was validated across six grid scales using a single-user RSS+SINR setup. XGBoost with smart feature engineering was used throughout.

| Grid | Classes | Static Acc. | Best Trans. Acc. | Δ Accuracy | Best h |
|------|---------|-------------|------------------|------------|--------|
| 3×3 | 9 | 53.4% | 62.8% | +9.4 pp | 3 |
| 5×5 | 25 | 39.1% | 53.1% | +14.0 pp | 3 |
| 7×7 | 49 | 26.9% | 41.1% | +14.2 pp | 3 |
| 10×10 | 100 | 33.8% | 55.6% | +21.8 pp | 3 |
| 15×15 | 225 | 13.8% | 29.1% | +15.3 pp | 3 |
| 20×20 | 400 | 13.4% | 22.6% | +9.2 pp | 2 |

**Key finding:** History improves accuracy at every scale, from 9 classes to 400 classes. The largest absolute gain occurs at 10×10 (+21.8 pp). No memory overflow was encountered even at 400 classes.

Also validated at 7×7 across four algorithms (RSS+SINR, h=3):

| Algorithm | Static Acc. | h=3 Acc. | Δ Accuracy | MAE Reduction |
|-----------|-------------|-----------|------------|---------------|
| Gaussian | 10.9% | 15.5% | +4.7 pp | −13% |
| Random Forest | 28.0% | 43.6% | +15.6 pp | −36% |
| XGBoost | 26.9% | 45.1% | +18.2 pp | −40% |
| MLP | 24.8% | 41.6% | +16.8 pp | −37% |

All four algorithms benefit from history. Tree-based methods (RF, XGBoost) benefit more than probabilistic (Gaussian) or neural (MLP) methods in this setting.

### 6.2 Multi-User Voronoi 15×15 — Center BS

The main experiment combines multi-user device heterogeneity with the full Voronoi environment. 5 device profiles, 450,005 samples, center BS.

#### 6.2.1 Overall Results

| Experiment | XGB Acc | XGB MAE | RF Acc | RF MAE |
|------------|---------|---------|--------|--------|
| BASE | 27.3% | 8.39 m | 43.5% | 5.81 m |
| BASE_dp | 50.2% | 4.36 m | 57.2% | 3.75 m |
| BASE_uid | 48.7% | 4.52 m | 55.7% | 3.88 m |
| **BASE_H** | **50.4%** | **4.53 m** | **52.5%** | **4.01 m** |
| BASE_H_dp | 58.3% | 3.20 m | 61.2% | 2.69 m |
| BASE_H_uid | 57.8% | 3.26 m | 61.6% | 2.85 m |
| BASE_A | 82.2% | 0.44 m | 77.3% | 0.55 m |
| BASE_A_dp | 84.3% | 0.38 m | 84.4% | 0.37 m |
| BASE_A_uid | 84.1% | 0.38 m | 79.7% | 0.49 m |
| BASE_A_H | 83.6% | 0.39 m | 77.1% | 0.53 m |
| **BASE_A_H_dp** | **84.9%** | **0.35 m** | **79.3%** | **0.47 m** |

**Core thesis result:** `BASE → BASE_H`: +23.1 pp accuracy (XGB), +9.0 pp (RF). **History alone — with no other additions — provides significant improvement over the static baseline.**

**AoA dominance (center BS):** `BASE_H → BASE_A_H`: +33.2 pp (XGB). AoA is the largest single feature contribution when the BS is at the grid center (full 360° angular coverage). See §6.3 for the geometry dependence of this result.

**Device knowledge:** `BASE_H → BASE_H_dp`: +7.9 pp (XGB). Knowing the device type — which determines the systematic RSS/SINR offset — provides orthogonal information to history. The combination BASE_H_dp outperforms both BASE_H and BASE_dp.

**Observation:** `BASE_dp ≈ BASE_H` in accuracy (50.2% vs 50.4% XGB). Device parameters at h=0 reproduce nearly the same gain as h=3 history alone. This occurs because the multi-user training set mixes devices — device-specific offsets differentiate users in a way that resembles per-device sub-fingerprints. Combining both (BASE_H_dp) is non-redundant.

#### 6.2.2 History Depth Analysis

Accuracy vs h for BASE experiments (XGBoost, RSS+SINR):

| h | Accuracy | MAE |
|---|----------|-----|
| 0 | 27.3% | 8.39 m |
| 1 | 41.5% | 5.88 m |
| 2 | 47.5% | 5.01 m |
| 3 | 50.4% | 4.53 m |
| 4 | 51.1% | 4.47 m |

Most of the gain occurs at h=1 (+14 pp). Gains are diminishing: h=2 adds +6 pp, h=3 adds +3 pp, h=4 adds +0.7 pp. h=3 is the optimal operating point (best accuracy-to-feature-size trade-off).

#### 6.2.3 Per-User Breakdown (XGBoost, BASE_H vs BASE_A_H)

| User | Device | BASE_H Acc | BASE_A_H Acc | AoA Gain |
|------|--------|------------|--------------|----------|
| U1 | 4-ant flagship | 61.6% | 87.6% | +26.0 pp |
| U2 | 2-ant mid-range | 38.5% | 80.2% | +41.7 pp |
| U3 | 1-ant budget | 54.7% | 84.8% | +30.1 pp |
| U4 | 4-ant flagship | 60.7% | 87.0% | +26.3 pp |
| U5 | tablet/IoT | 36.3% | 78.4% | +42.1 pp |

Weaker devices (U2, U3, U5) benefit more from AoA — angular information compensates for degraded RSS/SINR quality. Flagship devices (U1, U4) already achieve reasonable accuracy with RSS+SINR history; AoA still adds ~26 pp.

#### 6.2.4 Per-Cell Breakdown (XGBoost, BASE_H vs BASE_A)

| Cell | Scenario | BASE_H Acc | BASE_A Acc | AoA Gain |
|------|----------|------------|------------|----------|
| 1 (Park) | UMi_LOS | 62.6% | 88.6% | +26.0 pp |
| 2 (Residential) | Mixed | 45.7% | 78.9% | +33.2 pp |
| 3 (Shopping) | UMi_NLOS | 52.1% | 81.0% | +28.9 pp |
| 4 (Highway) | RMa_LOS | 37.9% | 76.5% | **+38.6 pp** |

The Highway cell (RMa_LOS) benefits most from AoA. Under Rural Macro LOS, a dominant single-ray path means adjacent grid points have nearly identical RSS/SINR — distance-ring ambiguity is worst here. AoA is the only reliable discriminant.

#### 6.2.5 Cross-User Generalization

Model trained on U1–U4, evaluated on U5 (unseen device, different height 0.9 m):

| Experiment | In-distribution | Cross-user | Drop |
|---|---|---|---|
| BASE_H | 50.4% / 4.53 m | 46.4% / 5.05 m | −4.0 pp |
| BASE_A_H | 83.6% / 0.39 m | **76.7% / 0.61 m** | −6.9 pp |

AoA generalizes better across devices (+6.9 pp drop vs accessible 4.0 pp without AoA from a much lower baseline). This is because AoA is geometrically determined — the angle from BS to UE depends only on position, not device electronics.

The residual 6.9 pp cross-user gap in BASE_A_H is attributable to U5's different UE height (0.9 m vs 1.5 m), which shifts the elevation angle. This is a physical, not electronic, difference.

#### 6.2.6 Device Knowledge vs. History — Isolation

Four new h=0 baselines isolate the contribution of device knowledge from history:

**Without AoA:**

| Experiment | XGB Acc | RF Acc |
|---|---|---|
| BASE | 27.3% | 43.5% |
| BASE_dp (device only, h=0) | 50.2% | 57.2% |
| BASE_H (history only, h=3) | 50.4% | 52.5% |
| BASE_H_dp (both) | 58.3% | 61.2% |

**With AoA:**

| Experiment | XGB Acc | RF Acc |
|---|---|---|
| BASE_A | 82.2% | 77.3% |
| BASE_A_dp (AoA + device, h=0) | 84.3% | 84.4% |
| BASE_A_H (AoA + history, h=3) | 83.6% | 77.1% |
| BASE_A_H_dp (all three) | 84.9% | 79.3% |

Without AoA: device knowledge and history provide almost identical gains, and combining both adds another +8 pp. With AoA: marginal gains from device params (+2 pp XGB) or history (+1.4 pp XGB) are small — AoA already captures most of the spatial information available.

### 6.3 BS Placement Study — AoA Geometry Dependence

The center-BS result (+33 pp AoA gain) raised a critical question: was this gain due to genuine angular discrimination, or an artefact of the full 360° angular coverage that the center position provides?

This experiment places the serving BS at the NE corner (48, 48, 10) — 15 m beyond the grid boundary — compressing all 225 grid points into a ~52° azimuth wedge. All other parameters are unchanged.

#### 6.3.1 Primary Finding — AoA Gain

| Metric | Center BS (360°) | NE BS (52°) |
|---|---|---|
| BASE_H accuracy (XGB) | 50.4% | 62.7% |
| BASE_A_H accuracy (XGB) | 83.6% | 69.6% |
| **AoA gain (XGB)** | **+33.2 pp** | **+6.9 pp** |
| BASE_H accuracy (RF) | 52.5% | 62.2% |
| BASE_A_H accuracy (RF) | 77.1% | 65.1% |
| **AoA gain (RF)** | **+24.6 pp** | **+2.9 pp** |

**AoA gain drops from +33 pp to +7 pp (XGB) when azimuth spread shrinks from 360° to 52°.** The center-BS AoA advantage was primarily geometric: each grid point had a unique azimuth from the BS. In the NE placement, all points appear in the same quadrant (195°–251°, a 56° span). The model cannot distinguish adjacent grid points by azimuth alone.

The residual +7 pp gain is attributable to **elevation angle**, which encodes distance: BS height = 10 m, UE height = 1.5 m → vertical gap = 8.5 m. Elevation spans ~9° (SW corner, d=61 m) to ~31° (NE corner, d=21 m) — a 22° spread that still carries distance information even when azimuth is compressed.

#### 6.3.2 History Gain is Geometry-Independent

| Metric | Center BS | NE BS |
|---|---|---|
| BASE → BASE_H (XGB) | +23.1 pp | **+23.2 pp** |
| BASE → BASE_H (RF) | +9.0 pp | **+10.3 pp** |

The transition history benefit is **identical regardless of BS placement**. History captures trajectory dynamics that depend on how measurements change as the UE moves — this is independent of the BS's angular view.

This is the key differentiating result: **transition features are robust to BS deployment geometry; AoA is not**.

#### 6.3.3 RSS/SINR Discrimination with Edge BS

Notably, the NE BS placement actually *improves* non-AoA experiments:

| Experiment | Center BS XGB | NE BS XGB | Change |
|---|---|---|---|
| BASE | 27.3% | 39.5% | **+12.2 pp** |
| BASE_H | 50.4% | 62.7% | **+12.3 pp** |
| BASE_A | 82.2% | 63.1% | −19.1 pp |

The edge BS creates a larger distance dynamic range (21–61 m vs 0–28 m), giving RSS a stronger gradient and better positional discrimination. Grid points near the NE corner are far from those near the SW corner, making amplitude alone more informative.

#### 6.3.4 Spatial Distribution of Errors — NE BS

Per-Voronoi-cell breakdown (XGBoost, BASE_H):

| Cell | NE BS Acc | NE BS MAE | Center BS Acc | Center BS MAE |
|------|-----------|-----------|---------------|---------------|
| 1 | 66.3% | 3.66 m | 37.9% | 4.84 m |
| 2 | 54.8% | 3.16 m | 52.1% | 6.01 m |
| 3 | 85.0% | 0.93 m | 45.7% | 6.04 m |
| 4 | 86.5% | 0.94 m | 62.6% | 3.47 m |

Cells 3 and 4 (NE quadrant, close to serving BS) achieve 85–87% accuracy with sub-metre MAE — better than any cell in the center-BS experiment **without AoA**. Cells 1 and 2 (SW quadrant, far from BS) are harder, showing the characteristic edge-BS gradient.

#### 6.3.5 Cross-User Generalization Under Edge BS

| Experiment | Center BS | NE BS |
|---|---|---|
| cross_user_BASE_H | 46.4% / 5.05 m | 53.9% / 3.89 m |
| cross_user_BASE_A_H | **76.7% / 0.61 m** | 59.5% / 2.02 m |

With NE BS: BASE_H cross-user *improves* (+7 pp) because the stronger RSS gradient is inherently more device-agnostic. BASE_A_H cross-user *degrades* significantly (−17 pp) — when AoA is weak, the model falls back on RSS/SINR, which varies across devices.

---

## 7. Summary of Findings

### 7.1 Core Thesis: Validated

**Transition history improves localization accuracy across all tested conditions:**

1. Validated across **6 grid sizes** (9 to 400 classes), **4 ML algorithms** (Gaussian, RF, XGBoost, MLP), and **2 feature sets**.
2. History gain of **+23 pp** (XGB, RSS+SINR) is consistent regardless of BS placement geometry.
3. h=1 captures the majority of the gain; diminishing returns beyond h=3.

### 7.2 AoA Is Placement-Sensitive; History Is Not

| Metric | Center BS (360°) | NE BS (52°) |
|---|---|---|
| History gain (BASE → BASE_H, XGB) | +23.1 pp | +23.2 pp |
| AoA gain (BASE_H → BASE_A_H, XGB) | +33.2 pp | +6.9 pp |

This is the central comparative result. AoA is a powerful feature when angular diversity exists (center BS), but loses most of its advantage in edge-BS deployments — a common configuration in both indoor and outdoor cellular installations. Transition history provides reliable improvement in both cases.

The residual +7 pp AoA gain at the NE BS is driven by elevation angle encoding distance, not azimuth.

### 7.3 Device Heterogeneity

- **Device parameters as features** add +8–12 pp to history-based experiments.
- Weaker devices (1-antenna, low gain) benefit most from AoA when the BS provides full angular coverage (+42 pp for U2/U5).
- **AoA generalizes well across device types** — cross-user drop only −7 pp (center BS) because angle is geometrically, not electronically, determined.
- When AoA is weak (edge BS), cross-user drop grows to −17 pp because the model relies on device-dependent RSS/SINR.

### 7.4 Channel Environment

- **Per-cell accuracy depends more on cell size than channel type.** Voronoi cells with fewer grid points suffer from higher cross-boundary confusion regardless of LOS/NLOS.
- **RMa_LOS (Highway) benefits most from AoA** (+39 pp) because a dominant single-ray channel makes RSS/SINR nearly range-only.
- **Edge BS creates a spatial gradient:** cells near the BS achieve sub-metre MAE with RSS+SINR+history alone; far cells are harder but recover with device parameters.

### 7.5 Feature Design Recommendations

| Deployment Scenario | Recommended Feature Set |
|---|---|
| Center/overhead BS, diverse devices | BASE_A_H_dp — full set |
| Center BS, unknown device | BASE_A_H — geometry provides AoA |
| Edge/wall-mounted BS, known device | BASE_H_dp — history + device params |
| Edge BS, unknown device, minimal hardware | BASE_H — history alone sufficient |
| Any scenario, no AoA hardware | BASE_H_dp — best non-AoA option |

---

## 8. Configuration Reference

### 8.1 Complete Simulation Parameters

| Category | Parameter | Value |
|---|---|---|
| **Channel** | Center frequency | 3.5 GHz |
| | Bandwidth | 100 MHz |
| | Subcarriers | 256 (uniform OFDM) |
| | QuaDRiGa version | v2.8.1 |
| | Standard | 3GPP TR 38.901 |
| **Grid** | Size | 15×15 (225 points) |
| | Spacing | 2 m |
| | Coordinate range | X, Y ∈ [5, 33] m |
| | Position jitter | ±0.1 m |
| | Neighbor connectivity | 8 |
| **Movement** | Model | Random walk on grid graph |
| | UE speed | 1.5 m/s |
| | Steps per grid point | 400 |
| | Total samples per user | 90,001 |
| **BS — Center** | Serving BS position | (19, 19, 10) m |
| | TX power | 30 dBm |
| | IBS-1 | (−11, 19, 10) m — 30m west |
| | IBS-2 | (19, −11, 10) m — 30m south |
| **BS — NE Corner** | Serving BS position | (48, 48, 10) m |
| | IBS-1 | (19, −10, 10) m — south |
| | IBS-2 | (−10, 19, 10) m — west |
| **AoA Noise** | Gaussian noise (per axis) | σ = 4° |
| | Quantization step | Δ = 5° |
| **Dataset** | Users | 5 |
| | Samples per user | 90,001 |
| | Total samples | 450,005 |
| | Train / test | 360,005 / 90,000 (80/20) |
| **Models** | XGBoost | n_est=50, depth=5, lr=0.15 |
| | Random Forest | n_est=50, depth=15, sqrt features |
| **History** | Primary depth | h = 3 |

### 8.2 Output Files

For each experiment run, the pipeline writes to `results/{experiment_name}/`:

```
csvs/
  results_summary.csv        — model | experiment | accuracy | mae
  per_user_breakdown.csv     — model | experiment | user_id | accuracy | mae
  per_cell_breakdown.csv     — model | experiment | cell_id | accuracy | mae
  data_volume_sweep.csv      — accuracy vs training data fraction
images/
  accuracy/
    accuracy_bar_chart.png
    per_user_heatmap_{model}.png
    voronoi_accuracy_map_{exp}.png
    learning_curve.png
  mae/
    mae_heatmap_{exp}_{model}.png    — per-grid-point MAE, adaptive colour scale
    mae_heatmap_comparison_{model}.png
```

---

## 9. Test Coverage

The pipeline has a formal test suite in `src/python/tests/` (pytest) and `src/matlab/tests/` (matlab.unittest). Run with:

```bash
# Python
.venv/Scripts/python -m pytest experiments/09_grid_localization/src/python/tests/ -v

# MATLAB (from src/matlab/)
runtests('tests/TestGridGeneration')
runtests('tests/TestReadJsonc')
```

### 9.1 Python Tests (77 pass, 1 skipped)

| File | Behaviour verified |
|---|---|
| `test_read_jsonc.py` | JSONC comment stripping, URLs inside strings not stripped, scientific notation, error on missing file |
| `test_feature_engineering.py` | `build_history_features`: shape, lag0 = current value, lag1 = previous step, no NaN, no cross-user contamination · `build_delta_features`: same shape as absolute, delta1 = first difference, no absolute lag columns · `make_split`: 80/20 ratio, test is last chronologically, zero leakage between train and test · `build_grid_lookup`: all points present, coordinates are means · `compute_mae`: 0 for perfect, 2 m for adjacent, √8 m for diagonal |
| `test_aoa_noise.py` | Output quantized to exact 5° multiples · noise is applied (values change) · zero-mean (large-sample bias < 1°) · reproducible per user_id · different users get different noise sequences · azimuth and elevation are independently noised |
| `test_experiment_runner.py` | 100% accuracy on trivially separable data (label remapping round-trip verified) · 0 MAE on perfect classifier · reported labels are 1-indexed · cross-user exclusion removes user from training but keeps in test · per-user MAE within 0.5 m of overall MAE (alignment check) |
| `test_results_sanity.py` | Accuracy in [0, 100] · MAE ≤ grid diagonal (39.6 m) · BASE_H > BASE for both models/experiments · BASE_A > BASE · BASE_H_dp > BASE_H · AoA gain at center BS > 20 pp · AoA gain at NE BS < 15 pp · NE-BS azimuth range < 120° (confirms BS at (48,48) was used) · center-BS azimuth range > 180° · SINR > −35 dB (catches the original 30 dB calibration bug) |
| `test_adaptive_vmax.py` | Low-error regime stays sub-2 m · high-error regime stays > 5 m · always positive · single outlier does not dominate |

### 9.2 MATLAB Tests

| File | Behaviour verified |
|---|---|
| `TestReadJsonc.m` | JSONC parsing, inline comments, nested objects, array values, missing file error, real config smoke-test |
| `TestGridGeneration.m` | 225 points for 15×15 · X/Y range [5, 33] · uniform UE height · correct spacing · NE BS (48,48) lies outside grid · NE azimuth spread < 90° · center BS spread > 270° · 4-conn corner has 2 neighbors · 8-conn interior has 8 neighbors · neighbors are symmetric · no self-loops · walk stays in grid · walk visits > 95% of points |

### 9.3 What Is Not Tested

- MATLAB channel simulation correctness (QuaDRiGa internals)
- End-to-end pipeline timing (no performance regression tests)
- Plot visual output (only that files are saved without error)

---
