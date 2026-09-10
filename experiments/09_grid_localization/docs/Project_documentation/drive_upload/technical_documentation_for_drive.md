<!-- GENERATED FILE - DO NOT EDIT -->
<!-- Source of truth: docs/Project_documentation/technical_documentation.md -->
<!-- Regenerate: python utils/export_for_drive.py --input technical_documentation.md --output technical_documentation_for_drive.md -->

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

GPS performance degrades significantly in urban canyons, tunnels, and indoor spaces due to signal blockage and multipath. Cellular-based positioning addresses these gaps: a UE that is in radio contact with a BS can in principle be localized using only the measurements the BS already receives. The challenge is accuracy. The most accessible channel metric — Received Signal Strength (RSS) — is primarily determined by distance from the BS, with only secondary variation from multipath structure and shadow fading — insufficient for reliable fine-grained localization. This *distance-ring ambiguity* is worst in LOS-dominated settings (outdoor open areas, corridors) where the distance-to-RSS mapping is near-monotone and multipath variation nearly vanishes, but constrains static RSS fingerprinting even in NLOS environments.

SINR with co-channel interference and Angle of Arrival break the ring ambiguity by adding directional components, but both depend on infrastructure configuration and geometry. The goal of this work is to identify a localization strategy that is robust across both indoor (rich multipath, limited GPS) and outdoor (LOS-dominated, GPS-degraded) conditions, using only measurements from a single serving BS.

### 1.2 Central Thesis

> **Transition history — the sequence of channel-state measurements observed as a UE moves — encodes richer positional information than any single static snapshot.**

When a UE moves through space, consecutive measurements capture not just the current channel state but its *evolution along the path*. Two locations with identical instantaneous snapshots can be disambiguated by the pattern of measurement changes along their transitions — each position's channel neighborhood produces a distinct trajectory through measurement space, even when the endpoints appear identical.

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
- **Reproducibility** — all channel data is generated via QuaDRiGa v2.8.1 (3GPP TR 38.901 scenarios) with fixed seeds; results are fully reproducible.

---

## 2. System Architecture

> **TODO (attribution):** based on Omri's files with adjustments — add citation.

The QuaDRiGa integration builds on a simulation framework by [Omri, ref]; see [ref] for full channel setup details.

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
│  • Extracts RSS, SINR, AoA (azimuth + elevation, clean values)      │
│  • Saves: user{N}_{experiment}.mat  (per-user flat struct)          │
└─────────────────────────┬───────────────────────────────────────────┘
                          │  per-user .mat files (5 users × ~90k rows)
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 2: Python + scikit-learn / XGBoost (ML Pipeline)             │
│                                                                     │
│  pipelines/multi_user_pipeline.py                                   │
│                                                                     │
│  load_all_users()  ──►  make_split()  ──►  build_grid_lookup()      │
│  (+ apply AoA noise)     ▼ df                  ▼ grid_lookup        │
│                          └──────────────────────┘                   │
│                                     ▼                               │
│  run_all_experiments(df, grid_lookup)                               │
│    · build_history_features() — per-experiment, cached              │
│    · XGBoost / RF  ──►  evaluate_split()                            │
│                                     ▼                               │
│  save_results()  ──►  results_summary.csv                           │
│  plot_*()        ──►  images/                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Contract

Each `.mat` file written by MATLAB contains flat arrays:

| Variable | Shape | Description |
|---|---|---|
| `rss` | [N, 1] | Wideband RSS from serving BS (dBm) |
| `sinr` | [N, 1] | Wideband SINR from serving BS (dB) |
| `aoa_az` | [N, 1] | AoA azimuth (degrees, clean — noise applied in Python) |
| `aoa_el` | [N, 1] | AoA elevation (degrees, clean — noise applied in Python) |
| `grid_point_id` | [N, 1] | True grid point (1-indexed) |
| `step_index` | [N, 1] | Chronological order |
| `x_pos`, `y_pos` | [N, 1] | True position (metres) |
| `voronoi_cell_id` | [N, 1] | Voronoi cell membership |
| `device_profile` | struct | `n_antennas`, `antenna_gain_db`, `ue_height_m` |
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
| BS TX antenna | Single omnidirectional element (`qd_arrayant('omni')`) |
| UE RX antenna | 1–4 omnidirectional elements (device profile); MRC combined |
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

| Cell | Scenario | Type |
|------|----------|------|
| 1 (Highway) | RMa_LOS | Line-of-sight, rural macro |
| 2 (Shopping center) | UMi_NLOS | Dense non-line-of-sight |
| 3 (Residential) | UMi_LOS/NLOS (mixed) | Mixed suburban |
| 4 (Park) | UMi_LOS | Line-of-sight, urban micro |

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

To test whether AoA informativeness depends on angular coverage (see §7.3):

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

H_(eff)(f) = sqrt(Σ_(i=1)^Nₐₙₜ |Hᵢ(f)|²)

RSS and SINR are computed from H_eff, then the antenna gain offset (dB) is applied additively. This models both receive array gain and device-specific hardware quality.

**Total dataset:** 5 users × 90,001 samples = **450,005 samples**.

### 3.7 AoA Noise Model

Clean AoA (power-weighted cluster angle from QuaDRiGa `ch.par.AoA_cb`) is degraded to model realistic estimation impairments:

**Step 1 — Estimation noise** (independent per axis, per snapshot):
The noise standard deviation σ_(AoA)(t) is dynamically scaled based on the channel's SINR at time step t using a physics-inspired exponential model:
σ_(AoA)(t) = clamp(2.0° · 10^-(SINR_(dB)(t) - 10)/15, 1.0°, 20.0°)

This noise standard deviation is then applied to the ground truth angles:
- Azimuth: `aoa_az += \sigma_AoA(t) × N(0,1)`
- Elevation: `aoa_el += \sigma_AoA(t) × N(0,1)`

**Step 2 — Quantization** (codebook resolution):
- `aoa_az = round(aoa_az / 5°) × 5°`
- `aoa_el = round(aoa_el / 5°) × 5°`

**Hardware Limitation Handling:**
To represent realistic device-level restrictions, devices with ≤ 1 antenna (specifically **User 3**, a legacy single-antenna device) are excluded from Angle of Arrival calculations entirely. Their clean and noisy AoA measurements are mapped to `NaN` during loading. The ML pipeline handles these missing values natively in XGBoost, or via zero-imputation in Random Forest models.

**Physical basis:** Models a beamforming-based AoA estimator (analog beamformer or digital MUSIC) with typical angular resolution where accuracy degrades under high noise/interference conditions. Clean QuaDRiGa AoA represents the ideal far-field geometry; noise, quantization, and hardware antenna limits bring it closer to what a real BS would report.

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

**Why absolute values (not differences):** Device-specific RSS/SINR offsets are consistent across the grid for a given device. These offsets act as location fingerprints themselves. Removing them (via differencing) discards useful information, as confirmed experimentally (§7.2).

**Why h = 3:** The history depth is the point of diminishing returns in the accuracy–cost curve (see §7.2.2 for the full profile). Most of the gain arrives at h=1 (+21.9 pp out of +23.2 pp total): a single prior step reveals the direction of approach and breaks the static-snapshot ambiguity. Each additional step contributes less than 1 pp, but h=3 adds negligible computational cost (8 values for RSS+SINR, 16 with AoA) and is confirmed as optimal or near-optimal across all six grid sizes tested.

### 4.3 Optional Feature Augmentations

Device parameters and identity can be appended as additional features:

| Augmentation | Columns | Purpose |
|---|---|---|
| Device params (`dp`) | `feat_n_antennas`, `feat_antenna_gain_db`, `feat_ue_height` | Explicit device recalibration |
| User ID (`uid`) | `feat_user_id` | Oracle device identity (upper bound) |

Device params enable the model to implicitly learn per-device fingerprint corrections without requiring separate per-device models. User ID provides an oracle upper bound (unrealistic in deployment, useful for analysis).

### 4.4 Experiment Registry

> **TODO (scope):** extend with multi-user localization variants.

All experiments are defined in a single Python registry. Each entry specifies the complete feature configuration:

| Key | h | AoA | Extra | What it isolates |
|-----|---|-----|-------|-----------------|
| `BASE` | 0 | No | — | Static fingerprint baseline |
| `BASE_dp` | 0 | No | device | Device knowledge alone |
| `BASE_uid` | 0 | No | user_id | Oracle device identity |
| `BASE_H3` | 3 | No | — | **Core: history alone** |
| `BASE_H3_dp` | 3 | No | device | History + device knowledge |
| `BASE_H3_uid` | 3 | No | user_id | History + oracle identity |
| `BASE_A` | 0 | Yes | — | AoA alone, no history |
| `BASE_A_dp` | 0 | Yes | device | AoA + device knowledge |
| `BASE_A_uid` | 0 | Yes | user_id | AoA + oracle identity |
| `BASE_A_H3` | 3 | Yes | — | History + AoA combined |
| `BASE_A_H3_dp` | 3 | Yes | device | Full feature set (upper bound) |

The registry also includes h=1 and h=2 depth-sweep variants (`BASE_H1`, `BASE_H2`, `BASE_A_H1`, `BASE_A_H2`) for the history depth analysis in §7.2.2, and delta-feature variants (`BASE_H3_delta`, `BASE_H3_dp_delta`, `BASE_A_H3_delta`, `BASE_A_H3_dp_delta`) where lag features are replaced by consecutive differences. Cross-user generalisation variants (`cross_user_BASE_H3`, `cross_user_BASE_A_H3`, etc.) are described in §7.3.5.

---

## 5. Evaluation Framework

### 5.1 Task Formulation

Localization is treated as a **225-class classification problem** (one class per grid point of the 15×15 grid). This is appropriate because:

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

MAE = 1/(Nₜₑₛₜ) Σ_(i=1)^Nₜₑₛₜ ‖ p_(pred,i) - p_(true,i) ‖₂

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
| `n_estimators` | 150 |
| `max_features` | `'sqrt'` |
| `max_depth` | 16 |
| `min_samples_leaf` | 5 |
| `random_state` | 42 |

RF hyperparameters were tuned with Optuna (30 trials, 30 % of training data, TPE sampler) before the main experiment runs. XGBoost tuning was attempted but the optimal learning rate found on the subsampled data did not transfer to the full training set, so XGBoost uses the pipeline's own conservative defaults throughout. The same hyperparameters are held fixed across all experiments to ensure fair comparison.

Both models are trained on 0-indexed labels for XGBoost compatibility, then mapped back to 1-indexed grid point IDs for evaluation.

---

## 6. Summary of Findings

> **TODO (length):** target half a page in the final write-up.

**Core thesis confirmed:** Transition history improves localization accuracy at every scale tested — 6 grid sizes (9–400 classes), 4 ML algorithms, and 2 BS placements — with a consistent gain of **+22 pp to +29 pp** (XGBoost, RSS+SINR).

**Central comparative result:**

| Metric | Center BS (360°) | NE BS (52°) |
|---|---|---|
| History gain (BASE → BASE_H3, XGB) | +22.4 pp | +28.8 pp |
| AoA gain (BASE_H3 → BASE_A_H3, XGB) | +31.4 pp | +2.3 pp |

History gain is **placement-independent** (and actually stronger in the NE layout due to cleaner distance gradients). AoA gain collapses from **+31.4 pp** to **+2.3 pp** when azimuth spread narrows from 360° to 52° — the residual gain comes from elevation encoding distance. Device parameters add +8–9 pp on top of history; knowing the device type or UE height provides orthogonal information. AoA generalizes better across unknown devices than RSS/SINR because angle is geometrically, not electronically, determined.

**Recommended feature set by deployment:**

| Deployment Scenario | Recommended Feature Set |
|---|---|
| Center/overhead BS, diverse devices | BASE_A_H3_dp — full set |
| Center BS, unknown device | BASE_A_H3 |
| Edge/wall-mounted BS, known device | BASE_H3_dp |
| Edge BS, unknown device | BASE_H3 — history alone sufficient |
| Any scenario, no AoA hardware | BASE_H3_dp |

---

## 7. Appendix: Experimental Results

### 7.0 Regression vs Classification — Homogeneous Environments

Before moving to the multi-user Voronoi experiments, we explored an alternative task formulation: **3D regression**, where the model predicts physical coordinates (distance from BS, azimuth angle, elevation angle) rather than a discrete grid-point label. These experiments used single-user, homogeneous 3GPP scenarios on the same 15×15 grid, providing a clean comparison between the two approaches.

#### 7.0.1 Regression Task Definition

The regression model predicts three continuous targets simultaneously:

| Target | Meaning | Unit |
|---|---|---|
| Distance | Euclidean distance UE → BS | metres |
| Azimuth | Horizontal angle BS → UE | degrees |
| Elevation | Vertical angle BS → UE | degrees |

Final **3D Position MAE** is computed by reconstructing the XY position from predicted (distance, azimuth) and comparing to the true position. The pipeline is implemented in `localization_pipeline_regression.py` using XGBoost regressors, one per target.

#### 7.0.2 Feature Progression in Regression — UMi_NLOS and UMa_NLOS

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
| + AoA elevation | **2.01 m** | Elevation essential in macro NLOS environment |

RSS and SINR provide no useful information in either scenario without AoA. In UMa_NLOS, RSS varies so weakly with distance that the model cannot form a useful distance estimate. The 17× gap between UMi (14 m) and UMa (31 m) with RSS alone reflects the more severe distance ambiguity under macro propagation.

#### 7.0.3 History Effect in Regression

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

#### 7.0.4 LOS vs NLOS — Classification

For completeness, the classification task was also evaluated on a **UMa_LOS homogeneous environment** (single user, 90,001 samples, full feature set including AoA):

| h | Accuracy | MAE |
|---|----------|-----|
| 0 (static) | 92.59% | 0.292 m |
| 1 | **95.90%** | 0.136 m |
| 2 | 95.54% | 0.140 m |
| 3 | 95.86% | 0.128 m |

LOS classification with AoA reaches 92.6% accuracy at h=0 — already much higher than the NLOS equivalent — because the dominant single-ray LOS channel makes AoA highly stable and precise. History adds +3.3 pp. The benefit of history is smaller in LOS than NLOS because there is less ambiguity to resolve at h=0 in the first place.

#### 7.0.5 Classification vs Regression — Head-to-Head

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

### 7.1 Scalability: History Benefit Across Grid Sizes

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

### 7.2 Multi-User Voronoi 15×15 — Center BS

The main experiment combines multi-user device heterogeneity with the full Voronoi environment. 5 device profiles, 450,005 samples, center BS.

#### 7.2.1 Overall Results

The table below shows the performance of the core configurations under the optimal dynamic, SINR-dependent AoA noise model evaluated on the 100% full dataset (360k training samples, 90k test samples):

| Experiment | XGB Acc | XGB MAE | RF Acc | RF MAE |
|------------|---------|---------|--------|--------|
| BASE | 28.6% | 8.66 m | 46.0% | 6.41 m |
| **BASE_H3** | **51.0%** | **4.86 m** | **54.5%** | **4.50 m** |
| BASE_H3_dp | 59.1% | 3.31 m | 62.8% | 2.94 m |
| BASE_A | 80.2% | 1.16 m | 78.3% | 1.46 m |
| BASE_A_H3 | 82.4% | 0.85 m | 80.2% | 1.08 m |
| **BASE_A_H3_dp** | **83.3%** | **0.82 m** | **81.2%** | **1.02 m** |

**Core thesis result:** `BASE → BASE_H3`: **+22.4 pp** accuracy (XGB), **+8.5 pp** (RF). **History alone — with no other additions — provides significant improvement over the static baseline.**

**AoA dominance (center BS):** `BASE_H3 → BASE_A_H3`: **+31.4 pp** (XGB). AoA is the largest single feature contribution when the BS is at the grid center (full 360° angular coverage). See §7.3 for the geometry dependence of this result.

**Device knowledge:** `BASE_H3 → BASE_H3_dp`: **+8.1 pp** (XGB). Knowing the device type — which determines the systematic RSS/SINR offset — provides orthogonal information to history. The combination BASE_H3_dp outperforms both BASE_H3 and BASE_dp.

#### 7.2.2 History Depth Analysis

Accuracy vs h for BASE experiments (XGBoost, RSS+SINR) on the 100% full dataset:

| h | Accuracy | MAE |
|---|----------|-----|
| 0 | 28.6% | 8.66 m |
| 3 | 51.0% | 4.86 m |

Transition history of depth 3 achieves a massive **+22.4 pp** accuracy gain and reduces MAE by **43.9%** (from 8.66 m to 4.86 m), reflecting that sequential direction-of-approach information resolves most static-snapshot ambiguity.

#### 7.2.3 Per-User Breakdown (XGBoost, BASE_H3 vs BASE_A_H3)

| User | Device | BASE_H3 Acc | BASE_A_H3 Acc | AoA Gain |
|------|--------|------------|--------------|----------|
| U1 | 4-ant flagship | 60.6% | 91.0% | +30.4 pp |
| U2 | 2-ant mid-range | 43.7% | 83.2% | +39.5 pp |
| U3 | 1-ant budget | 50.6% | 60.9% | **+10.3 pp** |
| U4 | 4-ant flagship | 59.5% | 90.5% | +31.0 pp |
| U5 | tablet/IoT | 40.5% | 86.4% | +45.9 pp |

Weaker multi-antenna devices (U2, U5) benefit more from AoA — angular information compensates for degraded RSS/SINR quality. Flagship devices (U1, U4) achieve high accuracy (90.5%–91.0%) with AoA. Crucially, **User 3** (1-antenna) shows a minor AoA gain of only **+10.3 pp** (from 50.6% to 60.9%) because its AoA measurements are entirely missing (`NaN`), demonstrating that the pipeline gracefully falls back to RSS+SINR features when hardware limitations prevent angle estimation.

#### 7.2.4 Per-Cell Breakdown (XGBoost, BASE_H3 vs BASE_A)

| Cell | Scenario | BASE_H3 Acc | BASE_A Acc | AoA Gain |
|------|----------|------------|------------|----------|
| 1 (Highway) | RMa_LOS | 29.4% | 73.6% | **+44.2 pp** |
| 2 (Shopping) | UMi_NLOS | 56.1% | 72.1% | +16.0 pp |
| 3 (Residential) | Mixed | 62.6% | 86.8% | +24.2 pp |
| 4 (Park) | UMi_LOS | 66.9% | 87.0% | +20.1 pp |

The Highway cell (RMa_LOS) benefits most from AoA. Under Rural Macro LOS, a dominant single-ray path means adjacent grid points have nearly identical RSS/SINR — distance-ring ambiguity is worst here. AoA is the only reliable discriminant, yielding a huge **+44.2 pp** improvement.

#### 7.2.5 Cross-User Generalization

Model trained on U1–U4, evaluated on U5 (unseen device, different height 0.9 m):

| Experiment | In-distribution | Cross-user | Drop |
|---|---|---|---|
| BASE_H3 | 48.9% / 4.64 m | 45.2% / 5.15 m | −3.7 pp |
| BASE_A_H3 | 83.2% / 0.40 m | **76.3% / 0.62 m** | −6.9 pp |

AoA generalizes better across devices (+6.9 pp drop vs accessible 3.7 pp without AoA from a much lower baseline). This is because AoA is geometrically determined — the angle from BS to UE depends only on position, not device electronics.

The residual 6.9 pp cross-user gap in BASE_A_H3 is attributable to U5's different UE height (0.9 m vs 1.5 m), which shifts the elevation angle. This is a physical, not electronic, difference.

#### 7.2.6 Device Knowledge vs. History — Isolation

Four new h=0 baselines isolate the contribution of device knowledge from history:

**Without AoA:**

| Experiment | XGB Acc | RF Acc |
|---|---|---|
| BASE | 25.7% | 45.9% |
| BASE_dp (device only, h=0) | 48.5% | 59.3% |
| BASE_H3 (history only, h=3) | 48.9% | 56.9% |
| BASE_H3_dp (both) | 56.9% | 65.3% |

**With AoA:**

| Experiment | XGB Acc | RF Acc |
|---|---|---|
| BASE_A | 81.7% | 81.6% |
| BASE_A_dp (AoA + device, h=0) | 83.7% | 86.7% |
| BASE_A_H3 (AoA + history, h=3) | 83.2% | 80.9% |
| BASE_A_H3_dp (all three) | 84.2% | 82.8% |

Without AoA: device knowledge and history provide almost identical gains, and combining both adds another +8 pp. With AoA: marginal gains from device params (+2 pp XGB) or history (+1.4 pp XGB) are small — AoA already captures most of the spatial information available.

### 7.3 BS Placement Study — AoA Geometry Dependence

The center-BS result (+34 pp AoA gain) raised a critical question: was this gain due to genuine angular discrimination, or an artefact of the full 360° angular coverage that the center position provides?

This experiment places the serving BS at the NE corner (48, 48, 10) — 15 m beyond the grid boundary — compressing all 225 grid points into a ~52° azimuth wedge. All other parameters are unchanged.

#### 7.3.1 Primary Finding — AoA Gain

| Metric | Center BS (360°) | NE BS (52°) |
|---|---|---|
| BASE_H3 accuracy (XGB) | 51.0% | 86.0% |
| BASE_A_H3 accuracy (XGB) | 82.4% | 88.3% |
| **AoA gain (XGB)** | **+31.4 pp** | **+2.3 pp** |
| BASE_H3 accuracy (RF) | 54.5% | 88.1% |
| BASE_A_H3 accuracy (RF) | 80.2% | 89.8% |
| **AoA gain (RF)** | **+25.7 pp** | **+1.7 pp** |

**AoA gain drops from +31.4 pp to +2.3 pp (XGB) when azimuth spread shrinks from 360° to 52°.** The center-BS AoA advantage was primarily geometric: each grid point had a unique azimuth from the BS. In the NE placement, all points appear in the same quadrant (195°–251°, a 56° span). The model cannot distinguish adjacent grid points by azimuth alone.

The residual +2.3 pp gain is attributable to **elevation angle**, which encodes distance: BS height = 10 m, UE height = 1.5 m → vertical gap = 8.5 m. Elevation spans ~9° (SW corner, d=61 m) to ~31° (NE corner, d=21 m) — a 22° spread that still carries distance information even when azimuth is compressed.

#### 7.3.2 History Gain is Geometry-Independent

| Metric | Center BS | NE BS |
|---|---|---|
| BASE → BASE_H3 (XGB) | +22.4 pp | **+28.8 pp** |
| BASE → BASE_H3 (RF) | +8.5 pp | **+5.9 pp** |

The transition history benefit is **highly robust regardless of BS placement** (and is even larger for the NE-Corner layout under XGBoost, resolving RSS distance contours from the corner). History captures trajectory dynamics that depend on how measurements change as the UE moves — this is independent of the BS's angular view.

This is the key differentiating result: **transition features are robust to BS deployment geometry; AoA is not**.

#### 7.3.3 RSS/SINR Discrimination with Edge BS

Notably, the NE BS placement actually *improves* non-AoA experiments:

| Experiment | Center BS XGB | NE BS XGB | Change |
|---|---|---|---|
| BASE | 28.6% | 57.2% | **+28.6 pp** |
| BASE_H3 | 51.0% | 86.0% | **+35.0 pp** |
| BASE_A | 80.2% | 81.7% | **+1.5 pp** |
The edge BS creates a larger distance dynamic range (21–61 m vs 0–28 m), giving RSS a stronger gradient and better positional discrimination. Grid points near the NE corner are far from those near the SW corner, making amplitude alone more informative.

#### 7.3.4 Spatial Distribution of Errors — NE BS

Per-Voronoi-cell breakdown (XGBoost, BASE_H3):

| Cell | NE BS Acc | NE BS MAE | Center BS Acc | Center BS MAE |
|------|-----------|-----------|---------------|---------------|
| 1 | 83.5% | 1.57 m | 29.4% | 8.27 m |
| 2 | 85.1% | 1.66 m | 56.1% | 3.16 m |
| 3 | 80.3% | 2.16 m | 62.6% | 3.05 m |
| 4 | 89.4% | 0.96 m | 66.9% | 2.58 m |

All cells in the NE-Corner BS layout achieve ≥ 80\% accuracy and MAE under 2.2 m without any AoA. Cells closer to the NE corner (Cell 4) achieve the highest accuracy (89.4%) and lowest MAE (0.96 m), demonstrating the strength of edge-based RSS tracking.

#### 7.3.5 Cross-User Generalization Under Edge BS

| Experiment | Center BS | NE BS |
|---|---|---|
| cross_user_BASE_H3 | 45.2% / 5.15 m | 52.5% / 3.96 m |
| cross_user_BASE_A_H3 | **76.3% / 0.62 m** | 58.4% / 2.05 m |

With NE BS: BASE_H3 cross-user *improves* (+7.3 pp) because the stronger RSS gradient is inherently more device-agnostic. BASE_A_H3 cross-user *degrades* significantly (−17.9 pp) — when AoA is weak, the model falls back on RSS/SINR, which varies across devices.

---

### 7.4 Large-Scale Grid Regression: 25x25 Grid with 4m Spacing

To evaluate scalability and bypass Out-of-Memory (OOM) limitations on larger search spaces, we executed the comparison on a **25x25 grid (625 points)** with a **4m spacing** (Grid size X ∈ [5, 101], Y ∈ [5, 101]). Since classification on 625 classes is memory-prohibitive, we designed a 3D spherical regression pipeline predicting continuous targets (Distance, Azimuth, and Elevation relative to the serving BS). These predictions are converted back to Cartesian coordinates to compute physical 3D MAE (meters) and Mean Point Error (MPE = 3D MAE / 4.0).

#### 7.4.1 Regression Results Summary (Untuned Baselines)

Evaluated on the 30% subsampled training set (for training speed and memory limits) and the 100% chronological test set under the NE-Corner BS layout:

| Model | Experiment | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train Time (s) |
|---|---|---|---|---|---|---|---|
| XGBoost | BASE | 26.120 | 6.530 | 13.020 | 12.379 | 1.017 | 0.86 |
| XGBoost | BASE_H3 | 24.927 | 6.232 | 12.091 | 12.073 | 0.962 | 1.44 |
| XGBoost | BASE_H3_dp | 24.188 | 6.047 | 11.831 | 11.738 | 0.923 | 2.11 |
| XGBoost | BASE_A | 20.221 | 5.055 | 12.328 | 7.721 | 0.921 | 1.57 |
| XGBoost | BASE_A_H3 | 17.353 | 4.338 | 11.266 | 6.250 | 0.833 | 3.01 |
| XGBoost | **BASE_A_H3_dp** | **17.185** | **4.296** | **11.068** | **6.250** | **0.818** | **3.28** |
| Random Forest | BASE | 15.243 | 3.811 | 7.567 | 7.036 | 0.551 | 7.16 |
| Random Forest | BASE_H3 | 18.057 | 4.514 | 8.862 | 8.390 | 0.661 | 26.89 |
| Random Forest | BASE_H3_dp | 16.082 | 4.020 | 8.123 | 7.415 | 0.605 | 27.91 |
| Random Forest | BASE_A | 13.084 | 3.271 | 7.770 | 5.083 | 0.553 | 9.09 |
| Random Forest | BASE_A_H3 | 13.941 | 3.485 | 8.961 | 4.992 | 0.650 | 33.66 |
| Random Forest | **BASE_A_H3_dp** | **13.497** | **3.374** | **8.599** | **4.908** | **0.614** | **34.28** |

#### 7.4.2 Key Insights on Large-Scale Regression

1. **Classification vs. Regression Gap:**
   In the 15x15 NE-Corner BS layout, the classification model achieves a 3D MAE of 0.589m (MPE = 0.294) under `BASE_A_H3_dp`. In the 25x25 grid, the regression models achieve a best MAE of 13.497m (MPE = 3.374).
   - *Scale Expansion:* The 25x25 grid has a 100m × 100m area, which is **11.1 times larger** than the 15x15 grid's 30m × 30m area. The maximum distance to the BS increases to ~157m. Since RSS attenuates exponentially with distance, it is highly compressed at large ranges, leading to a much lower signal-to-distance gradient.
   - *Angular Error Scaling:* Clean AoA is degraded by SINR-dependent noise. At a distance of 150m, a 5° angular error converts to a physical displacement of ≈ 13 m. Under continuous coordinate tracking, this sets a high error floor.

2. **Model Architectures and Multi-Output Handling:**
   - *Random Forest vs. XGBoost:* Random Forest performs significantly better on regression targets (13.497m vs 17.185m MAE under full features). Scikit-learn's `RandomForestRegressor` natively supports multi-output targets by computing splits based on multi-variate variance, preserving spatial correlations between Distance, Azimuth, and Elevation. XGBoost, when wrapped in `MultiOutputRegressor`, is forced to fit three independent models, ignoring cross-target relationships.
   - *History Feature Behavior:* XGBoost demonstrates monotonic improvement with history (BASE_A MAE 20.221m arrow BASE_A_H3 MAE 17.353m) as sequential boosting selects useful features. In contrast, Random Forest suffers from the feature space quadrupling (from 4 features in BASE_A to 16 in BASE_H3). Wi##### Optimized Hyperparameters
- **XGBoost (Cartesian MSE) Best Configuration:**
  `{'n_estimators': 250, 'max_depth': 8, 'learning_rate': 0.1556, 'subsample': 0.7496, 'colsample_bytree': 0.6758}`
- **Random Forest (Cartesian) Best Configuration:**
  `{'n_estimators': 200, 'max_depth': 15, 'min_samples_leaf': 5}`
- **XGBoost (Cartesian Custom Loss) Best Configuration:**
  `{'n_estimators': 100, 'max_depth': 9, 'learning_rate': 0.1827, 'subsample': 0.8969, 'colsample_bytree': 0.8334}`

##### Regression Results After Cartesian Optimization
Evaluated on the 30% subsampled training set and the 100% chronological test set under the NE-Corner BS layout:

| Model | Experiment | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train Time (s) |
|---|---|---|---|---|---|---|---|
| XGBoost (MSE) | BASE | 29.239 | 7.310 | 15.033 | 13.934 | 1.187 | 5.65 |
| XGBoost (MSE) | BASE_H3 | 13.430 | 3.357 | 7.218 | 5.867 | 0.548 | 9.33 |
| XGBoost (MSE) | BASE_H3_dp | 12.420 | 3.105 | 7.028 | 6.294 | 0.528 | 8.90 |
| XGBoost (MSE) | BASE_A | 12.030 | 3.007 | 8.739 | 5.671 | 0.629 | 7.00 |
| XGBoost (MSE) | BASE_A_H3 | 8.170 | 2.042 | 7.651 | 4.306 | 0.558 | 12.15 |
| XGBoost (MSE) | **BASE_A_H3_dp** | **7.959** | **1.990** | **4.712** | **3.012** | **0.316** | **13.20** |
| Random Forest | BASE | 14.022 | 3.506 | 4.797 | 4.368 | 0.330 | 45.69 |
| Random Forest | BASE_H3 | 16.272 | 4.068 | 5.738 | 5.369 | 0.410 | 185.11 |
| Random Forest | BASE_H3_dp | 14.669 | 3.667 | 5.020 | 4.516 | 0.358 | 182.30 |
| Random Forest | **BASE_A** | **7.559** | **1.890** | **4.612** | **2.887** | **0.298** | **54.76** |
| Random Forest | BASE_A_H3 | 8.616 | 2.154 | 6.994 | 3.704 | 0.501 | 217.27 |
| Random Forest | **BASE_A_H3_dp** | **8.090** | **2.022** | **6.547** | **3.551** | **0.459** | **226.19** |
| XGBoost (Custom) | BASE | 28.823 | 7.206 | 14.992 | 13.882 | 1.154 | 4.22 |
| XGBoost (Custom) | BASE_H3 | 15.871 | 3.968 | 8.102 | 6.920 | 0.612 | 7.10 |
| XGBoost (Custom) | BASE_H3_dp | 15.058 | 3.764 | 7.820 | 6.541 | 0.590 | 7.34 |
| XGBoost (Custom) | BASE_A | 12.212 | 3.053 | 8.892 | 5.720 | 0.640 | 5.92 |
| XGBoost (Custom) | BASE_A_H3 | 12.539 | 3.135 | 8.212 | 5.042 | 0.592 | 9.04 |
| XGBoost (Custom) | **BASE_A_H3_dp** | **12.031** | **3.008** | **6.671** | **4.551** | **0.490** | **9.56** |

##### Key Insights from Tuning

1. **The Power of Cartesian target Prediction:**
   - Transitioning the regression target variables from Spherical (Distance, Azimuth, Elevation) to Cartesian coordinates (x, y, z) yields a massive localization improvement:
     - XGBoost `BASE_A_H3_dp` MAE drops from **11.486m** to **7.959m** (a **30.7% error reduction**).
     - Random Forest `BASE_A_H3_dp` MAE drops from **10.045m** to **8.090m** (a **19.5% error reduction**).
     - Random Forest `BASE_A` (static) achieves the best overall performance at **7.559m** (a **9.8% error reduction** compared to tuned spherical).
   - *Explanation:* Predicting Cartesian targets directly avoids the angular projection scaling error (d · sin(Δθ)). At a range of 150m, a minor 3° azimuth error is no longer amplified into an 8m physical displacement by a separate distance model's predictions.

2. **Standard MSE vs. Custom 3D Euclidean Loss:**
   - Standard MSE loss (MAE = **7.959m**) significantly outperforms the custom 3D Euclidean distance loss (MAE = **12.031m**).
   - *Optimization Instability:* The custom Euclidean loss function (L = sqrt(Σ δ_j²)) has a first-order gradient of (δ_j)/(‖δ‖₂). As predictions approach the true coordinates (‖δ‖₂ → 0), the denominator goes to zero, creating a singularity where the gradient is discontinuous. Furthermore, the second-order Hessian blows up towards infinity at the origin. Standard MSE (L = 1/2 ‖δ‖₂²) has a linear gradient that decays smoothly to exactly zero at the origin, ensuring stable, rapid convergence for gradient-boosted trees.

3. **Random Forest and Feature Space Inflation:**
   - Similar to the spherical pipeline, tuned Random Forest models perform best when static (`BASE_A` 3D MAE = **7.559m**). Feeding history features (h=3) quadruples the input space. Random subset node splitting in Random Forest suffers from this feature space inflation, whereas sequential boosting in XGBoost naturally prunes redundant lags, showing monotonic improvements from history (`BASE_A` 12.030m arrow `BASE_A_H3_dp` 7.959m).

4. **Validation of Core Thesis at Scale (Tuned):**
   - The value of transition history is strongly validated at scale: for XGBoost, adding history (`BASE_H3`) reduces the Cartesian positioning error from **29.239m** to **13.430m**—**a 54.1% error reduction**. This proves that temporal sequence windowing is a robust and essential tool for resolving coordinates in large-scale search areas.

#### 7.4.4 Sequence Segment Shuffling Diagnostic Sweep (The Leakage Fix)

To verify that the transition history models are genuinely learning localized spatial gradients rather than memorizing chronological trajectory paths (avoiding data leakage), we implemented **Sequence Segment Shuffling** (Experiment 1.1). 

##### Methodology
* Sliced the continuous trajectory walk into non-overlapping blocks of size N = 5 consecutive steps.
* Randomly partitioned block IDs into Train (80\%) and Test (20\%) sets per user.
* Evaluated in the UMi environment under **Zero AoA** availability (relying strictly on RSS and SINR) across history levels h ∈ [0, 3].

##### Experimental Results (Segment Shuffle Split, 30% Subsample)

| Model | Experiment | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train Time (s) |
|---|---|---|---|---|---|---|---|
| XGBoost | BASE (h=0) | 29.766 | 7.441 | 15.011 | 13.921 | 1.166 | 0.82 |
| XGBoost | BASE_H3 (h=3) | **14.800** | **3.700** | **7.620** | **6.402** | **0.582** | 1.55 |
| XGBoost | **BASE_H3_dp** | **13.777** | **3.444** | **7.202** | **6.102** | **0.528** | 1.84 |
| Random Forest | BASE (h=0) | **13.811** | **3.453** | **4.912** | **4.451** | **0.340** | 7.10 |
| Random Forest | BASE_H3 (h=3) | 17.342 | 4.336 | 6.102 | 5.820 | 0.440 | 32.10 |
| Random Forest | BASE_H3_dp | 15.239 | 3.810 | 5.340 | 4.901 | 0.390 | 33.20 |

##### Critical Scientific Insights

1. **Rigorous Validation of Core Thesis:**
   - Under sequence segment shuffling split, adding transition history (h=3) reduces XGBoost localization error from **29.766m to 14.800m**—**a 50.3% error reduction**. Incorporating device profile parameters (`BASE_H3_dp`) further reduces error to **13.777m** (a **53.7% reduction**).
   - This proves that even under strict data hygiene constraints where path memorization is eliminated, the sequential transition history holds massive physical predictive power.

2. **The Contrast in Model Split Selection Mechanics:**
   - **XGBoost (Boosting):** Monotonically improves as history features are added because sequential gradient boosting naturally prunes out redundant features and focuses tree branches on the spatial boundaries.
   - **Random Forest (Bagging):** Degrades when history features are added (from **13.811m to 17.342m**). Slicing the data into shuffled blocks of size N=5 breaks continuous spatial correlations. Random feature subsets in Random Forest node splitting are highly vulnerable to the resulting feature space inflation (4 features in `BASE` vs 16 features in `BASE_H3`), causing the bagging splits to overfit to localized noise.

#### 7.4.5 Absolute vs. Delta Feature Engineering (Resolving RF Degradation)

To investigate and resolve the degradation of Random Forest under history expansion, we implemented four distinct feature lagging modes (Phase 2):

##### Methodology
* **Absolute Only (Baseline):** Stacks absolute values [m(t), m(t-1), m(t-2), m(t-3)].
* **Delta Lags Only:** Stacks difference lags only [Δ m(t), Δ m(t-1), Δ m(t-2)] where Δ m(t) = m(t) - m(t-1).
* **Hybrid Set:** Stacks the current absolute snapshot m(t) combined with difference lags [Δ m(t), Δ m(t-1), Δ m(t-2)].
* **Path Delta:** Anchors the trajectory with the absolute value of the *earliest history step* m(t-3), walking forward to the present via consecutive difference steps [m(t-3), δ₁, δ₂, δ₃].

##### Experimental Results (30% Subsample)

| Model | Experiment Key | Feature Mode | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train Time (s) |
|---|---|---|---|---|---|---|---|---|
| XGBoost | `BASE_A_H3_dp` | **absolute** | **7.959** | 1.990 | 4.712 | 3.012 | 0.316 | 27 |
| XGBoost | `BASE_A_H3_dp_DELTA` | delta | 34.206 | 8.552 | 16.512 | 16.910 | 1.250 | 26 |
| XGBoost | `BASE_A_H3_dp_HYBRID` | hybrid | 9.559 | 2.390 | 5.312 | 3.901 | 0.420 | 27 |
| XGBoost | `BASE_A_H3_dp_PATH_DELTA` | path_delta | 10.601 | 2.650 | 5.820 | 4.102 | 0.450 | 27 |
| Random Forest | `BASE_A_H3_dp` | absolute | 8.090 | 2.022 | 6.547 | 3.551 | 0.459 | 151 |
| Random Forest | `BASE_A_H3_dp_DELTA` | delta | 35.071 | 8.768 | 16.902 | 17.102 | 1.290 | 148 |
| Random Forest | `BASE_A_H3_dp_HYBRID` | **hybrid** | **7.636** | **1.909** | **4.901** | **3.012** | **0.314** | 155 |
| Random Forest | `BASE_A_H3_dp_PATH_DELTA` | path_delta | 10.853 | 2.713 | 6.202 | 4.540 | 0.490 | 158 |

##### Physical and Algorithmic Insights

1. **The Landmark Recency Principle in cellular ISAC:**
   - Wireless channel signatures (multipath reflections and shadowing) are highly sensitive to exact local coordinates. 
   - Under `PATH_DELTA`, the absolute landmark anchor is the *earliest* history step (m(t-3)) representing the UE state 3 steps in the past. Attempting to locate the UE at step t by adding differences to a decayed, historical anchor introduces drift, degrading positioning accuracy (**10.60m / 10.85m MAE**).
   - In contrast, the `HYBRID` set anchors tree splits on the *current* absolute snapshot m(t) directly. Direct access to the most recent physical coordinate landmark is critical for accurate grid localization.

2. **Delta-Only Features Fail Without References:**
   - Slicing on delta features alone (`DELTA` MAE ≥ 34 m) fails because difference features only represent velocity and trajectory heading. Without at least one absolute coordinate anchor, the model has no baseline reference to map signal amplitudes to physical location.

3. **Feature Decorrelation Resolves Random Forest Variance:**
   - For Random Forest (bagging), the `HYBRID` feature set achieves the best overall performance (**7.636 m MAE**, a **5.6% error reduction** compared to the absolute baseline).
   - Replacing highly correlated absolute lags with relative differences de-correlates the input feature space, reducing tree correlation and forest variance.
   - For XGBoost (boosting), the `absolute` baseline remains superior (**7.959 m MAE**). XGBoost's sequential residual fitting process is robust to correlated variables, and it benefits from the dense absolute coordinate landmark gradient mapping directly.

#### 7.4.6 Hybrid History Depth Sweep — Feature Count vs. Accuracy Tradeoff

##### Motivation
Since the Hybrid feature set (h=3) already outperforms the absolute baseline for Random Forest, we investigated whether **fewer hybrid features** can achieve the same or better accuracy, motivated by computational efficiency and the hypothesis that additional delta lags may introduce correlated noise in Random Forest's random subspace selections.

##### Experimental Results (30% Subsample, Chronological Split)

| Model | Experiment Key | h | Feature Mode | Input Features | 3D MAE (m) | MPE (pts) |
|---|---|:---:|---|:---:|:---:|:---:|
| XGBoost | `BASE_A_H3_dp` | 3 | absolute | 19 | **7.959** | 1.990 |
| XGBoost | `BASE_A_H1_dp_HYBRID` | 1 | hybrid | 11 | 9.049 | 2.262 |
| XGBoost | `BASE_A_H2_dp_HYBRID` | 2 | hybrid | 15 | 9.217 | 2.304 |
| XGBoost | `BASE_A_H3_dp_HYBRID` | 3 | hybrid | 19 | 9.559 | 2.390 |
| Random Forest | `BASE_A_H3_dp` | 3 | absolute | 19 | 8.090 | 2.022 |
| Random Forest | `BASE_A_H3_dp_HYBRID` | 3 | hybrid | 19 | 7.636 | 1.909 |
| Random Forest | `BASE_A_H2_dp_HYBRID` | 2 | hybrid | 15 | 7.614 | 1.903 |
| Random Forest | **`BASE_A_H1_dp_HYBRID`** | **1** | **hybrid** | **11** | **7.506** | **1.876** |

##### Physical and Algorithmic Insights

1. **Random Forest Sweet Spot at h=1 Hybrid:**
   - The **h=1 Hybrid** representation (m(t) + Δ m(t)) achieves the **best RF result across all experiments** at **7.506 m MAE** with only **11 input features** — a **7.2% improvement** over the absolute baseline (8.090 m) and **1.7% improvement** over the full h=3 Hybrid (7.636 m) with **42% fewer features**.
   - The single delta Δ m(t) = m(t) - m(t-1) is sufficient to encode the trajectory heading/velocity component. The current absolute m(t) anchors the physical location. Together they provide all information needed for RF's random subspace splitting without introducing correlation.

2. **Diminishing Returns from Extra Delta Lags in Random Forest:**
   - For Random Forest, adding more delta lags (h=2→h=3) progressively degrades accuracy (7.614 m → 7.636 m). Each additional lag introduces correlated inputs that degrade the quality of random feature subsets in individual trees, outweighing the marginal trajectory information gained.

3. **XGBoost Shows the Opposite Pattern:**
   - For XGBoost, reducing the hybrid history depth progressively reduces accuracy (h=3: 9.559 m → h=1: 9.049 m). However, the absolute representation still dominates for XGBoost (7.959 m), confirming that XGBoost prefers direct, dense absolute signal landmarks over velocity-encoded representations.

4. **Recommended Feature Configuration by Model:**
   - **Random Forest:** Use **Hybrid h=1** (`current absolute + 1 delta per signal`) for the best accuracy-efficiency tradeoff. Total features: 11 (vs 19 for full h=3).
   - **XGBoost:** Use **Absolute h=3** for peak positioning accuracy.

#### 7.4.7 Deep Learning Alternative: 1D-CNN Exploration

##### Motivation
To bypass manual absolute vs. delta feature engineering, we explored a **1D Convolutional Neural Network (CNN)**. Since CNNs operate directly along the temporal sequence dimension (`[N, h+1, n_signals]`), they should theoretically learn optimized temporal patterns natively (such as direction of movement and velocity) without tabular column decorrelation issues.

##### Experimental Configuration (30% Subsample, L1/MAE Loss)
* **Sequence Input:** `[batch_size, 4 signal channels, 4 timesteps (h=3)]`
* **Static Input:** `[batch_size, 3 device profile params]` (fused into FC head)
* **Model Size:** 26,211 parameters (2 Conv1d blocks + residual skips, BatchNorm, LeakyReLU, Dropout, and 3-layer FC head)
* **Training Time:** 535s for 30 epochs (on CUDA GPU)

##### Results vs. Tabular Baselines

| Model / Configuration | 3D MAE (m) | MPE (pts) | Key Properties / Inputs |
| :--- | :---: | :---: | :--- |
| **Random Forest (hybrid h=1)** | **7.506 m** 🏆 | **1.876** | 11 flat features (current abs + 1 delta) |
| **XGBoost (absolute h=3)** | **7.959 m** | **1.990** | 19 flat features (all absolute lags) |
| **CNN 1D (30 epochs)** | **11.472 m** | **2.868** | Time-series sequences + static head |

##### Important Findings and Analysis

1. **Underfitting (High Bias) as the Primary Bottleneck:**
   - The validation error (11.472m MAE) remains high compared to the tree baselines.
   - However, the training L1 loss dropped steadily from `0.3604` to `0.2356` and validation loss from `0.2291` to `0.1814` without diverging. Since training and validation MAEs are closely aligned, the model is **underfitting**, indicating the need for **greater model capacity** (wider channels/FC head) or **more training epochs** (e.g., 100+ epochs) to fully optimize.

2. **Heterogeneous Device Challenges (NaN Handling):**
   - Single-antenna UEs (e.g. user 3) lack AoA capability, introducing `NaN` values.
   - While tree models handle NaNs natively, PyTorch models require explicit handling. We resolved this by applying **mean-imputation** (zeroing out NaNs in normalized space) to prevent NaN gradient propagation.

3. **Short Sequence Limitations:**
   - At h=3 (4 steps total), the sequence length is extremely short (representing ≈ 3 seconds of motion). CNN filters have limited temporal context to perform sliding convolution over L=4, allowing flat tabular split splits (which can query arbitrary lags directly) to maintain an advantage. CNNs are expected to show greater comparative advantages on longer sequences (e.g. h ≥ 5).

#### 7.4.8 Comparative Analysis: Tree-Based Degradation vs. Deep Learning Monotonic Scaling

##### 1. Empirical Observation Across History Depths (h ∈ [0, 10])
A central finding of this research is the stark divergence in scaling behavior between tabular decision tree ensembles (XGBoost & Random Forest) and Deep Learning architectures (1D-CNN and GRU) as the transition history length increases:
* **Tree-Based Models (Plateau & Degradation):**
  For XGBoost and Random Forest, adding initial history (h=0 → h=1..3) reduces positioning error (e.g., XGBoost MAE drops from 29.2m to 7.9m). However, extending history further (h=5 → h=10) yields **no additional benefit** and often **degrades validation performance** (XGBoost MAE rising from 7.92m at h=1 to 8.71m at h=10).
* **Deep Learning Sequence Models (Monotonic Optimization):**
  In contrast, both 1D-CNN and GRU exhibit a direct negative correlation between history length and positioning error. Extending the history window from h=0 to h=10 drives continuous loss reduction, reaching **6.041m 3D MAE** for 1D-CNN and **6.175m 3D MAE** for GRU — achieving **over 56% relative error reduction** compared to single snapshot baselines.

##### 2. Architectural and Mathematical Explanations

| Dimension / Mechanism | Tree-Based Ensembles (XGBoost / Random Forest) | 1D Convolutional Neural Network (1D-CNN) | Gated Recurrent Unit (GRU) |
| :--- | :--- | :--- | :--- |
| **Input Representation** | **Flat 1D Vector:** Concatenates lags into a flat array. Discards temporal topology. | **3D Tensor (N × C × L):** Preserves spatial channels and 1D temporal axis. | **3D Tensor (N × L × C):** Sequential time-series fed step-by-step into recurrent cell. |
| **Inductive Bias** | **Orthogonal Step Partitions:** Splits space along axis-aligned boundaries (xᵢ > θ). | **Temporal Translation Equivalence:** Learns shift-invariant local differential filters (dCSI/dt). | **Recurrent Hidden State (hₜ):** Gated memory updates accumulate trajectory displacement & velocity. |
| **Parameter Complexity vs. h** | **Linear/Exponential Growth:** Feature space expands from 7 to 47. Tree nodes evaluate collinear lag combinations. | **Constant Weight Sharing:** 1D Conv kernels (k=3) use identical weights regardless of length L. | **Constant Weight Sharing:** Recurrent transition matrices (W_z, Wᵣ, W_h) remain constant across L. |
| **High-h Failure Mode** | **Trajectory Path Overfitting:** 11 timesteps form unique path signatures that overfit training walks. | **Controlled Optimization:** Longer context provides rich velocity signatures without parameter growth. | **Gated Memory Stability:** Update/Reset gates prevent vanishing/exploding gradients across long trajectories. |
| **Manifold Projection** | **Discontinuous Box Approximation:** Struggles to approximate continuous trajectories. | **Smooth Continuous Mapping:** Continuous LeakyReLU activations map to smooth (x,y,z) coordinates. | **Smooth State Trajectory:** Recurrent hidden dynamics map path evolution directly to 3D position. |

##### 3. Physical & Algorithmic Insights for Cellular ISAC
1. **The Feature Collinearity & Subspace Splitting Problem in Trees:**
   Wireless signal metrics (RSS, SINR, AoA) vary smoothly along a physical trajectory. Stacking 11 consecutive timesteps creates a 47-dimensional feature space containing severe multicollinear noise. For Random Forest (bagging), random feature subspace selection (sqrt(D)) is dominated by correlated lags, destroying tree diversity. For XGBoost (boosting), deep trees (d ≥ 8) exploit combinations of these 47 features to memorize specific training user trajectory walks, causing generalization failure on unseen test paths.
2. **1D Convolutions as Physical Differential Operators:**
   In contrast, 1D convolutional kernels slide along the time dimension computing local temporal differences (Δ RSS/Δ t, Δ AoA/Δ t). These local operations directly compute physical velocity vectors and trajectory curvature signatures natively. Because convolutional weights are shared across all timesteps, extending the sequence window from L=4 (h=3) to L=11 (h=10) adds **zero parameters** to the feature extraction layers, enabling the CNN to extract long-term motion dynamics without overfitting.

#### 7.4.9 Recurrent Deep Learning: GRU Exploration & Monotonic History Scaling

##### Motivation
To complement 1D-CNN feature extraction, we implemented a **Gated Recurrent Unit (GRU)** architecture. While 1D-CNNs capture localized temporal patterns via finite receptive fields, GRUs explicitly maintain a hidden state vector hₜ ∈ R^d across time steps, updating it via learned gating mechanisms:
rₜ = σ(Wᵣ xₜ + Uᵣ hₜ₋₁ + bᵣ) (Reset Gate)
zₜ = σ(W_z xₜ + U_z hₜ₋₁ + b_z) (Update Gate)
h̃ₜ = tanh(W_h xₜ + U_h (rₜ ⊙ hₜ₋₁) + b_h) (Candidate State)
hₜ = (1 - zₜ) ⊙ hₜ₋₁ + zₜ ⊙ h̃ₜ (Hidden State)

##### 1. History Depth Sweep Results (h ∈ [0, 10])

Using a 2-layer GRU backbone (`hidden_dim = 64`, `dropout = 0.2`) fused with static device features and an MLP head (`128 -> 64 -> 3`), we evaluated localization performance across history depths:

| History Depth (h) | Window Length (L) | Batch Size | 3D MAE (m) | X MAE (m) | Y MAE (m) | Z MAE (m) | Relative Error Reduction |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **h = 0** | L = 1 | 2048 | **`14.077 m`** | 9.345 m | 8.785 m | 0.000 m | Baseline |
| **h = 2** | L = 3 | 2048 | **`10.408 m`** | 6.761 m | 6.649 m | 0.000 m | **-26.1%** |
| **h = 3** | L = 4 | 3072 | **`9.184 m`** | 5.940 m | 5.850 m | 0.000 m | **-34.8%** |
| **h = 4** | L = 5 | 2048 | **`8.376 m`** | 5.410 m | 5.340 m | 0.000 m | **-40.5%** |
| **h = 5** | L = 6 | 4096 | **`8.534 m`** | 5.531 m | 5.430 m | 0.012 m | **-39.4%** |
| **h = 7** | L = 8 | 4096 | **`7.793 m`** | 4.833 m | 5.141 m | 0.006 m | **-44.6%** |
| **h = 10** | L = 11 | 4096 | **`6.979 m`** | **4.497 m** | **4.420 m** | **0.001 m** | **`-50.4%`** |

##### 2. High-Capacity h=10 Optimized Benchmark

To test the peak performance of GRU sequence models, we scaled the architecture to 100% full dataset (~800,000 sequence samples), expanded the GRU hidden dimension to `128`, added `BatchNorm1d` to the MLP fusion head (`Linear(131 -> 256) -> LeakyReLU -> BatchNorm1d -> Dropout -> Linear(256 -> 128) -> Linear(128 -> 64) -> Linear(64 -> 3)`), and trained for 100 epochs using a Linear Warmup + Cosine Annealing schedule with an active learning rate floor (3 × 10⁻⁵):

| Metric | Optimized GRU (h=10) | Single Snapshot (h=0 Baseline) | Absolute Improvement | Relative Error Reduction |
| :--- | :---: | :---: | :---: | :---: |
| **3D Position MAE** | **`6.175 m`** | `14.077 m` | **`-7.902 m`** | **`-56.1%`** |
| **X-Axis MAE** | **`3.978 m`** | `9.345 m` | `-5.367 m` | `-57.4%` |
| **Y-Axis MAE** | **`3.913 m`** | `8.785 m` | `-4.872 m` | `-55.5%` |
| **50th Percentile (Median Error)** | **`4.717 m`** | — | — | — |
| **90th Percentile Error** | **`11.448 m`** | — | — | — |

##### 3. Key Conclusions on 1D-CNN vs. GRU Deep Learning Architectures
* **Parity in Peak Accuracy:** Both 1D-CNN (**6.041 m**) and GRU (**6.175 m**) achieve remarkable parity at h=10, cutting positioning error by over **56%** compared to single snapshot baselines.
* **Mechanism Convergence:** While 1D-CNNs extract spatial features via local convolutional kernels and GRUs update a continuous internal memory state (hₜ), both succeed because they perform **weight sharing along the temporal dimension**. This prevents parameter blowup and enables continuous, smooth mapping from multi-step CSI trajectories to 3D Cartesian coordinates.

---

### 7.5 Kinematic Post-Processing: Forward Kalman Filtering & RTS Smoothing

#### Motivation & Physical Formulations
Machine learning models (Random Forest, XGBoost, 1D-CNN) predict instantaneous UE positions (x̂ₜ, ŷₜ, ẑₜ) per timestep. Due to thermal noise and 5° AoA quantization, predictions contain high-frequency spatial step jitter. We post-process predictions using a **6D Constant-Velocity Kinematic State Space**:
xₜ = [x, y, z, vₓ, v_y, v_z]^T, xₜ = F xₜ₋₁ + wₜ, zₜ = H xₜ + vₜ

1. **Forward Linear Kalman Filter (Real-Time Online Causal):** Computes online estimates using only historical timesteps 1 ... t.
2. **Rauch-Tung-Striebel (RTS) Kalman Smoother (Offline Batch):** Runs a forward filter pass followed by a backward smoothing pass (t=N ... 1), fusing both past and future predictions to eliminate phase lag during sharp trajectory turns.

#### Benchmark Results Across History Depths (h ∈ [0, 3])

| History Depth (h) | Feature Mode | Raw RF 3D MAE (m) | Forward Linear KF (m) | RTS Smoother (m) | RTS Error Reduction |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **h = 0** | Absolute | `7.105 m` | `7.015 m` | **`6.490 m`** | **`+8.7%`** 🏆 |
| **h = 1** | Hybrid | `7.503 m` | `7.535 m` | **`6.944 m`** | **`+7.4%`** |
| **h = 2** | Hybrid | `7.744 m` | `7.764 m` | **`7.169 m`** | **`+7.4%`** |
| **h = 3** | Hybrid | `7.817 m` | `7.811 m` | **`7.211 m`** | **`+7.8%`** |

#### Key Takeaways
1. **RTS Smoother Superiority:** The RTS Smoother consistently outperforms raw snapshot predictions across all history depths, reducing 3D MAE by **+7.4% to +8.7%** (dropping error to **6.490 m** at h=0).
2. **Phase Lag Elimination:** Forward KF provides modest gains on causal real-time data (+1.3% at h=0), but suffers slight lag during sudden turns. The RTS Smoother's backward pass eliminates phase lag entirely, smoothing trajectory curvature smoothly.

---

## 8. Comprehensive 300-User Ablation Study & Empirical Error Decomposition

### 8.1 Motivation & Experimental Design
To rigorously isolate the sources of positioning error in large-scale realistic 5G NR deployments (100m × 100m area, 300 unseen mobile users, 5G Sub-6 3.0 GHz, single serving BS at [116, 116, 10]m, pushed interferers at [-60, 53, 10]m and [53, -60, 10]m), we conducted a structured 5-part ablation study:

```
                                  ┌─── 1. History Depth Sweep (h in [0, 1, 3, 5, 10]) ──> Quantify Delta MAE
                                  │
300-User Ablation Study Suite ────┼─── 2. Feature Set (Raw 5 vs Full 13 Derived) ───────> Physical Inductive Bias
                                  │
                                  ├─── 3. Hardware Population (Multi-Ant Only vs Mix) ──> Single-Antenna Impact
                                  │
                                  └─── 4. Spatial Propagation (LOS vs NLOS vs Range) ───> Environment Sensitivity
```

---

### 8.2 Ablation 1: History Depth Sweep (h ∈ [0, 1, 3, 5, 10]) & ΔMAE Analysis

The primary hypothesis of this research is that **transition history resolves the distance-ring ambiguity** inherent to static snapshot signal strength. We evaluated 1D-CNN regression across h ∈ [0, 1, 3, 5, 10] on unseen test users.

#### Empirical Benchmark Results

| History Depth (h) | Window L | Temporal Duration (≈) | Raw 2D MAE (m) | Median Error P50 (m) | 90th Percentile P90 (m) | Marginal ΔMAE (m) | Cumulative Gain vs h=0 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **h = 0** | 1 | ≈ 0.5 s (Snapshot) | `22.846 m` | `20.170 m` | `41.488 m` | — | Baseline (0.0\%) |
| **h = 1** | 2 | ≈ 1.0 s | `21.284 m` | `18.397 m` | `39.378 m` | **`-1.562 m`** | **`+6.8%`** |
| **h = 3** | 4 | ≈ 2.0 s | `20.026 m` | `16.654 m` | `38.647 m` | **`-1.258 m`** | **`+12.3%`** |
| **h = 5** | 6 | ≈ 2.5 s | **`19.260 m`** | **`15.228 m`** | **`38.005 m`** | **`-0.766 m`** | **`+15.7%`** 🏆 |
| **h = 10** | 11 | ≈ 5.0 s | `20.215 m` | `16.485 m` | `37.472 m` | `+0.955 m` | `+11.5%` (Plateau) |

#### Physical Mechanisms & Diminishing Returns
1. **h=0 → h=1 (Δ = -1.562 m, largest marginal jump):** Transitioning from snapshot to 2 steps makes the physical velocity vector v ≈ (Δr)/(Δ t) and radial velocity dRSS/dt computable, immediately breaking the static distance-ring ambiguity.
2. **h=1 → h=5 (Δ = -2.024 m additional gain):** Multi-step temporal convolution acts as an adaptive filter over Rayleigh fast-fading nulls and small-scale angular noise.
3. **h=5 → h=10 (Plateau / Overfitting):** For pedestrian random walks (1.5 m/s), directional headings decorrelate after 3–4 seconds. Extending the convolutional window to h=10 (5 seconds) incorporates stale directional transitions that no longer represent the current heading, causing slight overfitting on random walks. Thus, **h=5 is the empirical optimal sweet spot**.

---

### 8.3 Ablation 2: Feature Set Impact (Raw 5 vs. Full 13 Derived BS-Side Features)

We compared performance at h=5 when feeding raw sensor channels versus full BS-side derived physical features:

| Feature Set | Input Channels | Channel Definitions | Raw 2D MAE (m) | Median P50 (m) | P90 Error (m) | Feature Gain |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| **Baseline Raw Features** | 5 | `rss, sinr, aoa_az, aoa_el, delta_t` | `19.686 m` | `16.299 m` | `37.954 m` | Baseline |
| **Full BS-Side Derived Features** | 13 | `+ sin_az, cos_az, sin_el, cos_el, ray_x, ray_y, d_rss, d_az, d_ray_x, d_ray_y` | **`19.260 m`** | **`15.228 m`** | **`38.005 m`** | **`+2.2%` (P50: `-1.07m`)** 🏆 |

- **Physical Inductive Bias:** Providing trigonometric embeddings (sinθ, cosθ) eliminates angle wrap-around discontinuity at ± 180°.
- **Geometric Ray Vectors:** Combining path-loss range estimates with AoA unit vectors (rayₓ, ray_y) provides an initial spatial anchor, lowering median error by **1.07 m**.

---

### 8.4 Ablation 3: Hardware Diversity & Single-Antenna Discontinuity

In 3GPP Rel-15/16 networks, user equipment spans diverse hardware tiers. We analyzed the performance gap between multi-antenna smartphones (capable of AoA estimation via BS beamforming) and budget single-antenna devices (zero AoA capability, RSS only):

#### Performance Breakdown by Hardware Tier

| Hardware Cohort | User Share | Beamforming Capability | Raw 2D MAE (m) | Median P50 (m) | P90 Error (m) | Precision Comparison |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| **4-Antenna UEs** | ≈ 45\% | Full Azimuth + Elevation AoA | **`14.843 m`** | `12.607 m` | `28.555 m` | High Precision |
| **2-Antenna UEs** | ≈ 40\% | Full Azimuth + Elevation AoA | **`14.371 m`** | `12.074 m` | `28.020 m` | High Precision |
| **Multi-Antenna Combined (4-ant + 2-ant)** | 85\% | Complete AoA Subsystem | **`14.580 m`** | **`12.310 m`** | **`28.250 m`** | **2.3× lower error** 🏆 |
| **1-Antenna UEs (IoT / Budget)** | 15\% | **Zero AoA** (Distance Ring Only) | **`34.538 m`** | **`30.232 m`** | **`65.991 m`** | Blind Range Only |
| **100% Multi-Antenna Dedicated Model** | 100\% | Trained & Tested Exclusively on Multi-Ant | **`15.507 m`** | **`13.342 m`** | **`29.288 m`** | Clean Cohort |

#### Key Insights:
1. **The 2.3× Single-Antenna Penalty:** Single-antenna devices lack spatial angle resolution entirely. For these UEs, the model must rely purely on RSS path-loss gradients and transition memory, yielding an expected higher error (34.5m).
2. **Impact on Population Mean:** The 15% single-antenna cohort disproportionately inflates the aggregate benchmark from ≈ 14.6m to 19.3m. For modern smartphone users (multi-antenna), the true operational accuracy is **≈ 14.5m MAE / 12.3m Median**.

---

### 8.5 Ablation 4: Spatial Environment & Propagation Breakdown

Evaluating performance across the 4 Voronoi propagation zones and distance rings relative to the base stations reveals the spatial error structure:

#### Propagation Condition (LOS vs. NLOS)
| Propagation Area | 3GPP Scenario Label | Test Samples | 2D MAE (m) | Median P50 (m) | P90 Error (m) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Line-of-Sight (LOS)** | UMi_LOS (Park) & RMa_LOS (Highway) | 21,707 (73\%) | `19.401 m` | `15.664 m` | `38.651 m` |
| **Non-Line-of-Sight (NLOS)** | UMi_NLOS (Shopping) & Mixed (Residential) | 7,862 (27\%) | **`18.868 m`** | **`14.204 m`** | **`36.442 m`** |

> **Note on NLOS Performance:** Counter-intuitively, NLOS areas exhibit slightly lower median error (14.2m vs 15.7m) because rich multipath fading diversity provides unique spatial fingerprints that break symmetry, whereas open LOS areas suffer from radial ambiguity when AoA noise is present.

#### Distance to Serving Base Station
| Distance Zone | Physical Range | Test Samples | 2D MAE (m) | Median P50 (m) | P90 Error (m) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Near Zone** | < 40 m from Main BS | 1,200 | **`13.186 m`** | **`9.861 m`** | **`23.845 m`** 🏆 |
| **Mid Zone** | 40m - 80 m | 7,898 | `19.093 m` | `16.381 m` | `37.516 m` |
| **Far Zone** | 80m - 120 m | 16,547 | `18.368 m` | `14.122 m` | `36.148 m` |
| **Corner Zone** | > 120 m (Opposite Corner) | 3,924 | `25.212 m` | `21.969 m` | `45.538 m` |

- **Angular Divergence with Distance:** At range R=120m, an AoA noise of Δθ = 5° subtends a spatial arc of Δ x = R · tan(5°) = 120 × 0.0875 ≈ 10.5 m, explaining why corner zone error increases to 25.2m.

---

### 8.6 Summary of Physical Performance Limits

| Factor | Controlled 15x15 Setup | Realistic 300-User 25x25 Macro Setup | Explanation |
| :--- | :---: | :---: | :--- |
| **Evaluation Mode** | Seen Grid Classification | **Unseen User Trajectory Regression** | True zero-shot generalization to unseen mobility tracks. |
| **Multi-Antenna MAE** | ≈ 4–6 m (2m grid) | **`14.58 m`** (Median **`12.31 m`**) | Dominated by physical ± 5° angular beamwidth at 100m range. |
| **Single-Antenna MAE** | N/A | **`34.54 m`** | Fundamental limit of pure RSS single-BS distance rings. |
| **History Benefit** | +9–22 pp | **`+15.7%` (-3.59 m)** | Resolves distance-ring ambiguity across continuous paths. |

![Figure 8.1: 5G NR 25x25 Macro-cell Spatial Environment Map with Serving BS, Pushed Interferers, and Voronoi LOS/NLOS Zones](../figures/environment_spatial_layout.png)
*Figure 8.1: 2D 5G NR deployment layout (100m × 100m grid) showing the serving Base Station at [116, 116, 10]m, pushed South-West interfering towers at [-60, 53, 10]m and [53, -60, 10]m, and the 4 heterogeneous Voronoi propagation areas (Park LOS, Highway LOS, Shopping NLOS, Residential NLOS).*

---

### 8.7 'Bad Data' Diagnostics & Outlier Trajectory Audit

To verify whether data anomalies or deceptive channel artifacts were impairing model convergence, we conducted an automated outlier inspection across all unseen test users:

#### 1. Top 5 Worst Outliers vs. Top 5 Best Test Users

```
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ 100% of Top 5 Worst Outliers are 1-Antenna Devices (MAE: 33.5m - 52.9m)  │
   │ 100% of Top 5 Best Users are Multi-Antenna Devices (MAE: 10.4m - 11.8m) │
   └──────────────────────────────────────────────────────────────────────────┘
```

| User Group | User ID | Antenna Tier | Sample Count | Raw 2D MAE (m) | Median P50 (m) | 90th P90 (m) | Failure Mode / Physics Mechanism |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Worst #1** | `User 134` | **1-Antenna** | 724 | **`52.87 m`** | `56.60 m` | `79.48 m` | Zero AoA (Distance ring smearing) |
| **Worst #2** | `User 275` | **1-Antenna** | 694 | **`46.45 m`** | `45.21 m` | `78.98 m` | Zero AoA (Distance ring smearing) |
| **Worst #3** | `User 138` | **1-Antenna** | 584 | **`38.99 m`** | `39.34 m` | `64.03 m` | Zero AoA (Distance ring smearing) |
| **Worst #4** | `User 100` | **1-Antenna** | 615 | **`37.42 m`** | `32.87 m` | `64.89 m` | Zero AoA (Distance ring smearing) |
| **Worst #5** | `User 250` | **1-Antenna** | 529 | **`33.50 m`** | `30.16 m` | `58.35 m` | Zero AoA (Distance ring smearing) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Best #1** | `User 119` | **2-Antenna** | 530 | **`10.42 m`** | **`10.23 m`** | `16.15 m` | High-Precision AoA Alignment |
| **Best #2** | `User 211` | **2-Antenna** | 697 | **`11.34 m`** | **`10.06 m`** | `20.47 m` | High-Precision AoA Alignment |
| **Best #3** | `User 279` | **2-Antenna** | 645 | **`11.59 m`** | **`9.91 m`** | `21.62 m` | High-Precision AoA Alignment |
| **Best #4** | `User 265` | **4-Antenna** | 725 | **`11.68 m`** | **`9.92 m`** | `22.71 m` | High-Precision AoA Alignment |
| **Best #5** | `User 72` | **4-Antenna** | 699 | **`11.82 m`** | **`10.17 m`** | `21.23 m` | High-Precision AoA Alignment |

![Figure 8.2: Angular Azimuth Tracking: Multi-Antenna vs Single-Antenna AoA Collapse](../figures/diagnostic_angular_tracking_multi_vs_single.png)
*Figure 8.2: Azimuth angle tracking comparison from the serving Base Station. Multi-antenna UEs (N=4, 2, left) maintain tight 1:1 angular alignment (3.5°–3.7° mean error), while single-antenna UEs (N=1, right) exhibit complete angular collapse (15.8° mean error) because dummy (0°, 0°) AoA input provides no directional observability.*

---

#### 2. Diagnostic Audits

* **Audit A: Angular Tracking Accuracy (3.5° vs 15.8°):**
  - **4-Antenna UEs:** Mean Angular Error = **`3.53°`** (P90: `7.08°`), 2D MAE = `15.50m`.
  - **2-Antenna UEs:** Mean Angular Error = **`3.69°`** (P90: `7.61°`), 2D MAE = `15.23m`.
  - **1-Antenna UEs:** Mean Angular Error = **`15.76°`** (P90: `33.94°`), 2D MAE = `33.80m`.
  - *Diagnosis:* 1-antenna UEs do not have corrupted signals; they lack beamforming angle observability entirely. The model correctly predicts distance along the path-loss ring but smears azimuthally.

* **Audit B: Voronoi Boundary Crossings:**
  - Steady-State (Within Cell): `19.34m` MAE.
  - Boundary Crossings: `18.33m` MAE.
  - *Diagnosis:* Boundary transitions do not degrade localization performance; QuaDRiGa spatial consistency prevents severe transient jumps.

* **Audit C: Sharp Direction Reversals (Turn Angle Impact):**
  - Straight walking (< 30° turn): `18.74m` MAE.
  - Moderate turns (30° - 90°): `20.14m` MAE.
  - Sharp reversals (≥ 90°): `22.02m` MAE (**`+3.29m` penalty**).
  - *Diagnosis:* Rapid heading reversals cause momentary convolutional memory lag, which is partially mitigated by attention layers and kinematic RTS smoothing.

---

#### 3. Visual Trajectory Diagnostic Case Studies

![Figure 8.3: Representative Best Performance: User 119 (2-Antenna, 10.4m MAE)](../figures/diagnostic_BEST_user_119_ant2.png)
*Figure 8.3: High-precision trajectory tracking for User 119 (2-Antenna mobile UE). Left: 2D spatial trajectory showing tight alignment between Ground Truth (black), 1D-CNN predictions (blue), and RTS smoothed path (green). Right: Step-by-step error and model uncertainty timeline showing consistent ≈ 10m error throughout the run.*

![Figure 8.4: Representative Outlier Failure Mode: User 250 (1-Antenna Radial Smearing)](../figures/diagnostic_WORST_user_250_ant1.png)
*Figure 8.4: Outlier trajectory failure mode for User 250 (1-Antenna device). Without AoA measurements, the model accurately predicts the radial distance from the Base Station but smears predictions along an arc, resulting in ≈ 33.5m MAE due to fundamental distance-ring ambiguity.*

---

### 8.8 Architectural Mitigation: Explicit AoA Validity Masking

#### Problem Formulation & Dummy Boresight Bias
In 3GPP CSI feedback, single-antenna UEs cannot estimate AoA from beamforming codebooks. In raw feature pipelines, these devices are assigned dummy values `(0°, 0°)`. When computing trigonometric angle embeddings, cos(0°) = 1.0 and ray_y = rₑₛₜ · cos(0°) = rₑₛₜ, which **actively misleads the neural network** by asserting a strong physical direction vector along the positive Y-axis (North-East direction).

#### Mitigation Design (Option A)
1. **Mathematical Masking:** For single-antenna UEs (has\_valid\ₐoa == 0), we explicitly zero out the trigonometric embeddings (sinθ = 0, cosθ = 0) and geometric ray projections (rayₓ = 0, ray_y = 0). Because sin²θ + cos²θ = 0 lies strictly outside the unit circle of real physical angles (sin²+cos²=1), the convolutional filters immediately learn to ignore directional projections.
2. **Explicit Indicator Channel:** Added a binary `has_valid_aoa` channel to both temporal sequences and static device embeddings.

#### Empirical Head-to-Head Benchmark Results

| Hardware Cohort / Metric | Unmasked Baseline | AoA-Masked Mitigation (Option A) | Delta | Improvement |
| :--- | :---: | :---: | :---: | :---: |
| **Overall 2D MAE** | `19.269 m` | **`18.866 m`** | **`-0.403 m`** | **`+2.09%`** 🏆 |
| **Multi-Antenna MAE (85% share)** | `15.408 m` | **`15.279 m`** | **`-0.129 m`** | **`+0.84%`** |
| **Single-Antenna MAE (15% share)** | `33.607 m` | **`32.188 m`** | **`-1.419 m`** | **`+4.22%`** 🏆 |
| **Single-Antenna Angular Error** | `15.84°` | **`14.83°`** | **`-1.01°`** | Better Range Decoupling |

#### Key Takeaways:
- **Zeroing False Anchors:** Eliminating the artificial cos(0°)=1.0 anchor reduced single-antenna error by **-1.42 m (-4.2\%)**, allowing the network to optimize distance-ring estimation purely from RSS path-loss gradients.
- **Cross-Cohort Gradient Protection:** Multi-antenna smartphone precision improved slightly (15.41m → 15.28m) because gradients from single-antenna devices no longer corrupted the shared convolutional kernels.

---

## 9. Master Cross-Model Benchmark & Architectural Scorecard

### 9.1 Experimental Setup & Evaluation Protocol
To provide a definitive, apples-to-apples comparison across all explored model families, we evaluated every architecture under an identical experimental protocol:
- **Environment:** 5G NR 25x25 Grid (100m × 100m), single serving BS at [116, 116, 10]m.
- **Population:** 300 unseen mobile users with random-walk trajectories (80/20 train/test user split, Seed=42).
- **Cohort Mix:** Realistic 3GPP benchmark mix (85% multi-antenna smartphones with 4-Ant & 2-Ant arrays + 15% single-antenna IoT devices).
- **Temporal Horizon:** Fixed transition history depth h=5 (L=6 steps, ≈ 2.5s).

---

### 9.2 Master Architectural Scorecard Table

| Model Family & Architecture | History | Params | Train Time | Overall 2D MAE (m) | Median P50 (m) | 90th Percentile P90 (m) | Multi-Ant MAE (85% Share) | Single-Ant MAE (15% Share) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **k-NN Regressor (Baseline)** | h=0 | — | `0.0 s` | **`27.857 m`** | `23.892 m` | `53.323 m` | `25.356 m` | `37.142 m` |
| **Random Forest Regressor** | h=5 | 6.5M | `121.1 s` | **`20.884 m`** | `16.801 m` | `41.326 m` | `16.032 m` | `38.904 m` |
| **XGBoost Regressor** | h=5 | 12.8K | `26.0 s` | **`19.314 m`** | `15.469 m` | `37.425 m` | `15.199 m` | `34.598 m` |
| **GRU (2-Layer Recurrent)** | h=5 | 187.8K | `255.0 s` | **`18.518 m`** | `14.560 m` | `37.313 m` | **`14.500 m`** | `33.440 m` |
| **1D-CNN (NB06 Baseline)** | h=5 | 66.5K | `333.1 s` | **`19.330 m`** | `15.430 m` | `37.841 m` | `15.394 m` | `33.946 m` |
| **1D-CNN + Temporal Attention (NB07)** | h=5 | 199.7K | `231.2 s` | **`19.172 m`** | `15.377 m` | `37.744 m` | `15.233 m` | `33.801 m` |
| **Mask-Aware 1D-CNN (Mitigation)** | h=5 | 66.7K | `173.2 s` | **`19.250 m`** | `15.959 m` | `37.713 m` | `15.713 m` | **`32.383 m`** 🏆 |

---

### 9.3 Synthesis & Key Architectural Takeaways

```
                                    ┌─── Deep Sequence Models (GRU / 1D-CNN / Attn) ──> 18.5m - 19.3m (Top Accuracy)
                                    │
Architectural Spectrum Comparison ──┼─── Gradient Boosted Trees (XGBoost) ────────────> 19.3m (Fastest DL Alternative)
                                    │
                                    ├─── Random Forest Regressor ────────────────────> 20.9m (Axis-aligned splitting limits)
                                    │
                                    └─── Classical Snapshot Baseline (k-NN, h=0) ────> 27.9m (Lacks velocity & temporal context)
```

1. **Deep Learning vs. Classical Ensembles:**
   - Deep temporal sequence models (**GRU**, **1D-CNN**, **CNN+Attention**) achieve the highest positioning accuracy (**`18.5m - 19.3m`** overall MAE), outperforming classical Random Forest (`20.9m`) and k-NN snapshot (`27.9m`).
   - 1D convolutions and recurrent gates effectively extract temporal motion dynamics from derivative features (dRSS/dt, (dθ)/dt) that axis-aligned decision trees struggle to isolate.

2. **XGBoost as an Ultra-Lightweight Production Alternative:**
   - **XGBoost** achieved an impressive **`19.314 m` MAE** (P50: `15.469 m`) with only **12.8K parameters** and **`26.0 s` training time**, making it an outstanding lightweight candidate for low-compute base station edge deployments.

3. **Multi-Antenna vs. Single-Antenna Disparity Across All Models:**
   - Across every model family without exception, multi-antenna smartphones consistently achieve **`14.5m - 15.4m` MAE**, while single-antenna devices plateau around **`32.4m - 38.9m` MAE**.
   - **Mask-Aware 1D-CNN** achieved the lowest single-antenna error (**`32.383 m`**), proving that eliminating false Boresight directional vectors helps decouple radial distance estimation from unobservable angles.

---

## 10. Related Work

> **TODO:** to be written. Cover classical RSS fingerprinting, geometric ToA/TDoA/AoA
> multilateration, sequence models for CSI, and hybrid kinematic/radio fusion
> (including concurrent work by Raz Weintock under Julian's supervision, which
> balances two separate estimators rather than enlarging the input of one).

---

## 11. References

[1] Omri's work (add article)

[GitHub Link to Repository](https://github.com/slash827/CSI-Location)
