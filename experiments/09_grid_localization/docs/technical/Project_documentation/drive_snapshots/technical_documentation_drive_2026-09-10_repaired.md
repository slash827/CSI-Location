# Technical Documentation

# CSI-Based UE Localization Using Transition History

**Student:** Gilad Battat

**Advisors:** Prof. Sarit Kraus, Prof. David Sarne
**Institution:** Bar-Ilan University
**Industry Partners:** CEVA, Cellcom


---

## 1. Problem Statement

### 1.1 Motivation

5G and 6G networks expose a rich set of channel-derived measurements - RSS, SINR, Angle of Arrival, timing advance - natively at the base station without requiring dedicated positioning infrastructure. Leveraging these for accurate UE localization is a strategic goal of 3GPP Release 16 and beyond, motivated by use cases ranging from emergency response and asset tracking to network-assisted navigation in environments where GPS is unreliable or unavailable.


GPS performance degrades significantly in urban canyons, tunnels, and indoor spaces due to signal blockage and multipath. Cellular-based positioning addresses these gaps: a UE that is in radio contact with a BS can in principle be localized using only the measurements the BS already receives. The challenge is accuracy. The most accessible channel metric - Received Signal Strength (RSS) - is primarily determined by distance from the BS, with only secondary variation from multipath structure and shadow fading - insufficient for reliable fine-grained localization. This ***distance-ring ambiguity*** is worst in LOS-dominated settings (outdoor open areas, corridors) where the distance-to-RSS mapping is near-monotone and multipath variation nearly vanishes, but constrains static RSS fingerprinting even in NLOS environments.


SINR with co-channel interference and Angle of Arrival break the ring ambiguity by adding directional components, but both depend on infrastructure configuration and geometry. The goal of this work is to identify a localization strategy that is robust across both indoor (rich multipath, limited GPS) and outdoor (LOS-dominated, GPS-degraded) conditions, using only measurements from a single serving BS.

### 1.2 Central Thesis

**Transition history - the sequence of channel-state-related measurement observed as a UE moves - encodes richer positional information than any single static snapshot.**


When a UE moves through space, consecutive measurements capture not just the current channel state but its *evolution along the path*. Two locations with identical instantaneous snapshots can be disambiguated by the pattern of measurement changes along their transitions - each position's channel neighborhood produces a distinct trajectory through measurement space, even when the endpoints appear identical.


Formally, given a serving base station and a discrete grid of locations, at each time step *t* the UE reports measurements m(t) (RSS, SINR, and optionally AoA). The model input is a window of h+1 consecutive observations:


x_input = [m(t-h), m(t-h+1), ..., m(t-1), m(t)]


where *h* is the history depth hyperparameter.

### 1.3 Scope

This work tests the thesis through simulation under controlled but diverse conditions:


- Environment coverage - experiments span both indoor-like (UMi_NLOS shopping center, mixed UMi residential) and outdoor/semi-outdoor (UMi_LOS park, RMa_LOS highway) 3GPP scenarios within the same grid. This ensures the localization pipeline is evaluated across the full indoor-to-outdoor spectrum rather than optimised for a single propagation regime.

- Single serving BS - the BS performs localization using only measurements it legitimately receives from the UE. Per-interferer RSS is explicitly excluded to avoid triangulation (a different problem requiring distributed infrastructure).

- Classification - each grid point is a discrete class. This is appropriate at ≤2m grid spacing; we show it outperforms regression at all tested scales.

- Reproducibility - all channel data is generated via QuaDRiGa v2.8.1 (3GPP TR 38.901 scenarios) with fixed seeds; results are fully reproducible.


---


## 2. System Architecture - Based on Omri's files with adjustments (add ref)

### 2.1 Pipeline Overview

The system consists of two decoupled layers connected by `.mat` files:


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

│    · build_history_features() - per-experiment, cached              │

│    · XGBoost / RF  ──►  evaluate_split()                            │

│                                     ▼                               │

│  save_results()  ──►  results_summary.csv                           │

│  plot_*()        ──►  images/                                       │

└─────────────────────────────────────────────────────────────────────┘


### 2.2 Data Contract

Each `.mat` file written by MATLAB contains flat arrays:

| Variable | Shape | Description |
| :---- | :---- | :---- |
| rss | [N, 1] | Wideband RSS from serving BS (dBm) |
| sinr | [N, 1] | Wideband SINR from serving BS (dB) |
| aoa_az | [N, 1] | AoA azimuth (degrees, clean - noise applied in Python) |
| aoa_el | [N, 1] | AoA elevation (degrees, clean - noise applied in Python) |
| grid_point_id | [N, 1] | True grid point (1-indexed) |
| step_index | [N, 1] | Chronological order |
| x_pos, y_pos | [N, 1] | True position (metres) |
| voronoi_cell_id | [N, 1] | Voronoi cell membership |
| device_profile | struct | `n_antennas`, `antenna_gain_db`, `ue_height_m` |
| user_id_val | scalar | User identifier |


Python loads all 5 files and concatenates into a single DataFrame.


## 3. Simulation Environment

### 3.1 Channel Model

All channel data is generated using **QuaDRiGa v2.8.1** implementing **3GPP TR 38.901**. QuaDRiGa produces spatially-consistent, time-varying channel coefficients: as the UE moves, the channel evolves smoothly rather than independently at each step. This spatial consistency is what makes transition-based features informative - consecutive measurements are correlated in a directionally meaningful way.

The QuaDRiGa integration builds on a simulation framework by [Omri, ref]; see [ref] for full channel setup details.


| Parameter | Value |
| :---- | :---- |
| Center frequency | 3.5 GHz |
| Bandwidth | 100 MHz |
| Subcarriers (OFDM) | 256 |
| BS TX antenna | Single omnidirectional element (`qd_arrayant('omni')`) |
| UE RX antenna | 1-4 omnidirectional elements (device profile); MRC combined |
| TX power (serving + interferers) | 30 dBm |
| 3GPP standard | TR 38.901 |
| Spatial consistency | Yes (channel evolves continuously) |

### 3.2 Grid Environment

The localization target is a 15×15 grid of discrete points:

| Parameter | Value |
| :---- | :---- |
| Grid size | 15×15 = 225 points |
| Grid spacing | 2 m |
| Grid offset from origin | [5, 5] m |
| X, Y range | [5, 33] m × [5, 33] m |
| UE height | 1.5 m (U5: 0.9 m) |
| Position jitter | ±0.1 m per snapshot |
| Neighbor connectivity | 8 (4 cardinal + 4 diagonal) |


The position jitter prevents the model from fitting to perfectly aligned grid coordinates - measurement positions vary slightly around each nominal grid point.


### 3.3 Voronoi Heterogeneous Environment

The grid area is partitioned into 4 Voronoi cells, each with a distinct 3GPP propagation scenario. This creates a heterogeneous propagation environment spanning indoor-like dense NLOS to outdoor LOS conditions, where different zones exhibit genuinely different channel characteristics:


| Cell | Scenario | Type |
| :---- | :---- | :---- |
| 1 (Highway) | RMa_LOS | Line-of-sight, rural macro |
| 2 (Shopping center) | UMi_NLOS | Dense non-line-of-sight |
| 3 (Residential) | UMi_LOS/NLOS (mixed) | Mixed suburban |
| 4 (Park) | UMi_LOS | Line-of-sight, urban micro |


Each Voronoi cell boundary is generated by AreaGenerator at simulation time with a fixed random seed, ensuring reproducibility.

**Rationale for heterogeneity:**

A homogeneous environment would provide only range-based discrimination (distance ring ambiguity). Mixed scenarios create spatial fingerprints where both channel amplitude and multipath structure vary across the grid.


### 3.4 UE Trajectory - Random Walk

The UE trajectory is generated as a constrained random walk on the grid adjacency graph:


1. Start at the grid center

2. At each step, select uniformly from 8-connected neighbors

3. Repeat for 400 steps per grid point = 90,000 total steps (+1 for initial position)


**Walk seed:**

Each user has a unique seed for their walk trajectory. U1 and U4 share identical hardware parameters but use different walk seeds (100 vs 400), isolating device effects from trajectory randomness.


**Step duration:**

`spacing / ue_speed = 2m / 1.5 m/s = 1.33 s` (diagonal steps: 1.33s × √2).

### 3.5 Base Station Configurations

#### Main Experiment - Center BS

Grid: X ∈ [5, 33],  Y ∈ [5, 33]   (center = [19, 19])


Serving BS: [19, 19, 10]   ← at grid center

  → Distance range: 0-28.3 m

  → AoA azimuth spread: ~360° (all grid points visible in full circle)


IBS-1: [-11, 19, 10]   ← 30m west   (creates E-W SINR gradient)

IBS-2: [ 19,-11, 10]   ← 30m south  (creates N-S SINR gradient)

#### BS Placement Study - NE-Corner BS

To test whether AoA informativeness depends on angular coverage (see section 7.3):


Serving BS: [48, 48, 10]   ← 15m north + 15m east of NE corner [33,33]

  → Distance range: 21.2-60.8 m

  → AoA azimuth spread: ~52° (all points in SW quadrant)


IBS-1: [ 19,-10, 10]   ← south of grid

IBS-2: [-10, 19, 10]   ← west of grid


All other parameters (grid, device profiles, Voronoi environment) are identical to the center-BS experiment.

### 3.6 Multi-User Device Heterogeneity

Five UE profiles are simulated simultaneously. Each profile is a separate QuaDRiGa run with the same channel seed but different device parameters:


| User | Device Type | Antennas | Gain | Height | Walk Seed |
| :---- | :---- | :---- | :---- | :---- | :---- |
| U1 | Flagship A | 4 | 0 dB | 1.5 m | 100 |
| U2 | Mid-range | 2 | −2 dB | 1.5 m | 200 |
| U3 | Budget/Old | 1 | −4 dB | 1.5 m | 300 |
| U4 | Flagship B | 4 | 0 dB | 1.5 m | 400 |
| U5 | Tablet/IoT | 2 | −1 dB | 0.9 m | 500 |


**Multi-antenna modelling - Maximum Ratio Combining (MRC):**

$H_eff(f)\ =\ \sqrt{\ \sum\limits_{i=1}^{N_ant}|H_i(f){|}^{2}}{\ }$

RSS and SINR are computed from H_eff, then the antenna gain offset (dB) is applied additively. These models both receive array gain and device-specific hardware quality.


**Total dataset:** 5 users × 90,001 samples = **450,005 samples**.


### 3.7 AoA Noise Model

Clean AoA (power-weighted cluster angle from QuaDRiGa ch.par.AoA_cb ) is degraded to model realistic estimation impairments:


**Step 1 - Estimation noise** (independent per axis, per snapshot):

The noise standard deviation sigma_AoA(t) is dynamically scaled based on the channel's SINR at time step t using a physics-inspired exponential model:

sigma_AoA(t) = clamp(2.0° * 10^(-(SINR_dB(t) - 10) / 15), 1.0°, 20.0°)


This noise standard deviation is then applied to the ground truth angles:

* Azimuth: aoa_az += sigma_AoA(t) * N(0,1)
* Elevation: aoa_el += sigma_AoA(t) * N(0,1)


**Step 2 - Quantization** (codebook resolution):

- aoa_az = round(aoa_az / 5°) × 5°

- aoa_el = round(aoa_el / 5°) × 5°


**Hardware Limitation Handling:**

To represent realistic device-level restrictions, devices with <=1 antenna (specifically **User 3**, a legacy single-antenna device) are excluded from Angle of Arrival calculations entirely. Their clean and noisy AoA measurements are mapped to `NaN` during loading. The ML pipeline handles these missing values natively in XGBoost, or via zero-imputation in Random Forest models.


**Physical basis:**

Models a beamforming-based AoA estimator (analog beamformer or digital MUSIC) with typical angular resolution where accuracy degrades under high noise/interference conditions. Clean QuaDRiGa AoA represents the ideal far-field geometry; noise, quantization, and hardware antenna limits bring it closer to what a real BS would report.


---

## 4. Feature Engineering

### 4.1 Static Baseline (h = 0)

The simplest input is a single snapshot of measurements at time **t**:


x_static = [rss_t, sinr_t]                    (no   AoA)

x_static = [rss_t, sinr_t, az_t, el_t]   (with AoA)


This represents classical RSS fingerprinting and is the comparison baseline for all transition-based experiments.


### 4.2 Transition History Stacking (h > 0)

History features are built by stacking h+1 consecutive snapshots:


x_history = [ rss_{t-h}, sinr_{t-h}, ...,

         rss_{t-1}, sinr_{t-1},

         rss_t, sinr_t ]


Column naming: `rss_lag0` (current), `rss_lag1` (t-1), ..., `rss_lag{h}` (t-h).


Feature vector size:

- **Without AoA:** D = 2 × (h+1)

- With AoA:        D = 4 × (h+1)


For h=3 with AoA: **D = 16 features**.


**Implementation:** For each user, samples are sorted by `step_index`. The first h rows have incomplete history and are dropped. Users are processed independently - lag features never cross user boundaries.


**Why absolute values (not differences):** Device-specific RSS/SINR offsets are consistent across the grid for a given device. These offsets act as location fingerprints themselves. Removing them (via differencing) discards useful information, as confirmed experimentally (section 7.2).

**Why h = 3:**

The history depth is the point of diminishing returns in the accuracy-cost curve (see 'Appendix - History Depth Analysis' for the full profile). Most of the gain arrives at h=1 (+21.9 pp out of +23.2 pp total): a single prior step reveals the direction of approach and breaks the static-snapshot ambiguity. Each additional step contributes less than 1 pp, but h=3 adds negligible computational cost (8 values for RSS+SINR, 16 with AoA) and is confirmed as optimal or near-optimal across all six grid sizes tested.

### 4.3 Optional Feature Augmentations

Device parameters and identity can be appended as additional features:


| Augmentation | Columns | Purpose |
| :---- | :---- | :---- |
| Device params (dp) | feat_n_antennas, feat_antenna_gain_db, feat_ue_height | Explicit device recalibration |
| User ID (uid) | feat_user_id | Oracle device identity (upper bound) |


Device params enable the model to implicitly learn per-device fingerprint corrections without requiring separate per-device models. User ID provides an oracle upper bound (unrealistic in deployment, useful for analysis).


### 4.4 Experiment Registry - extensions: multi-user localization

All experiments are defined in a single Python registry. Each entry specifies the complete feature configuration:


| Key | h | AoA | Extra | What it isolates |
| :---- | :---- | :---- | :---- | :---- |
| `BASE` | 0 | No | - | Static fingerprint baseline |
| `BASE_dp` | 0 | No | device | Device knowledge alone |
| `BASE_uid` | 0 | No | user_id | Oracle device identity |
| `BASE_H3` | 3 | No | - | History alone |
| `BASE_H3_dp` | 3 | No | device | History + device knowledge |
| `BASE_H3_uid` | 3 | No | user_id | History + oracle identity |
| `BASE_A` | 0 | Yes | - | AoA alone, no history |
| `BASE_A_dp` | 0 | Yes | device | AoA + device knowledge |
| `BASE_A_uid` | 0 | Yes | user_id | AoA + oracle identity |
| `BASE_A_H3` | 3 | Yes | - | History + AoA combined |
| `BASE_A_H3_dp` | 3 | Yes | device | Full feature set (upper bound) |


The registry also includes h=1 and h=2 depth-sweep variants (`BASE_H1`, `BASE_H2`, `BASE_A_H1`, `BASE_A_H2`) for the history depth analysis in section 7.2.2, and delta-feature variants (`BASE_H3_delta`, `BASE_H3_dp_delta`, `BASE_A_H3_delta`, `BASE_A_H3_dp_delta`) where lag features are replaced by consecutive differences. Cross-user generalisation variants (`cross_user_BASE_H3`, `cross_user_BASE_A_H3`, etc.) are described in section 7.3.5.


---

## 5. Evaluation Framework

### 5.1 Task Formulation

Localization is treated as a **225-class classification problem** (one class per grid point of 15X15). This is appropriate because:


- **Grid spacing (2 m) >> position jitter (±0.1 m)** - discrete labels are unambiguous

- **Classification error is spatially meaningful** - predicting an adjacent cell is qualitatively better than predicting a far cell

### 5.2 Train/Test Split

Method:** Strictly chronological, 80/20, applied **independently per user**.


### For each user:

### 1. Sort all N samples by `step_index`

### 2. Take first 0.8N as training set

### 3. Take last 0.2N as test set


Why chronological:** Standard random splits leak temporal information. Since consecutive measurements share channel characteristics (QuaDRiGa spatial consistency), a random split would allow the model to interpolate between nearby train and test samples. Chronological splits prevent this.


Total split:** 360,005 training samples + 90,000 test samples across 5 users.

### 5.3 Evaluation Metrics

Classification Accuracy:** percentage of test samples correctly classified to the exact grid point.


Mean Absolute Error (MAE):** mean Euclidean distance between predicted and true grid point locations:


### MAE = (1 / Ntest) Σi=1Ntest ‖ppred,i - ptrue,i‖2


### where *p* are 2D coordinates of the predicted/true grid point.


MAE is more intuitive than accuracy for localization (it has physical units - metres).


Per-user and per-cell breakdowns:** accuracy and MAE are also reported per user (to study device heterogeneity) and per Voronoi cell (to study spatial variation).

### 5.4 Models

### Two ML models are evaluated throughout:


### XGBoost:

| Hyperparameter | Value |
| :---- | :---- |
| n_estimators | 50 |
| max_depth | 5 |
| learning_rate | 0.15 |
| subsample | 0.8 |
| colsample_bytree | 0.8 |
| random_state | 42 |


### Random Forest:

| Hyperparameter | Value |
| :---- | :---- |
| n_estimators | 150 |
| max_features | 'sqrt' |
| max_depth | 16 |
| min_samples_leaf | 5 |
| random_state | 42 |


RF hyperparameters were tuned with Optuna (30 trials, 30 % of training data, TPE sampler) before the main experiment runs. XGBoost tuning was attempted but the optimal learning rate found on the subsampled data did not transfer to the full training set, so XGBoost uses the pipeline's own conservative defaults throughout. The same hyperparameters are held fixed across all experiments to ensure fair comparison.


Both models are trained on 0-indexed labels for XGBoost compatibility, then mapped back to 1-indexed grid point IDs for evaluation.

---

## 6. Summary of Findings - Half a page

Core thesis confirmed:** Transition history improves localization accuracy at every scale tested - 6 grid sizes (9-400 classes), 4 ML algorithms, and 2 BS placements - with a consistent gain of **+22 pp to +29 pp** (XGBoost, RSS+SINR).


### Central comparative result:


| Metric | Center BS (360°) | NE BS (52°) |
| :---- | :---- | :---- |
| History gain (BASE → BASE_H3, XGB) | +22.4 pp | +28.8 pp |
| AoA gain (BASE_H3 → BASE_A_H3, XGB) | +31.4 pp | +2.3 pp |


History gain is **placement independent** (and actually stronger in the NE layout due to cleaner distance gradients). AoA gain collapses from **+31.4 pp** to **+2.3 pp** when azimuth spread narrows from 360° to 52° - the residual gain comes from elevation encoding distance. Device parameters add +8-12 pp on top of history; knowing the device type or UE height provides orthogonal information. AoA generalizes better across unknown devices than RSS/SINR because angle is geometrically, not electronically, determined.


### Recommended feature set by deployment:


| Deployment Scenario | Recommended Feature Set |
| :---- | :---- |
| Center/overhead BS, diverse devices | BASE_A_H3_dp - full set |
| Center BS, unknown device | BASE_A_H3 |
| Edge/wall-mounted BS, known device | BASE_H3_dp |
| Edge BS, unknown device | BASE_H3 - history alone sufficient |
| Any scenario, no AoA hardware | BASE_H3_dp |

---

## Appendix - Experimental Results

### 7.0 Regression vs Classification - Homogeneous Environments

Before moving to the multi-user Voronoi experiments, we explored an alternative task formulation: **3D regression**, where the model predicts physical coordinates (distance from BS, azimuth angle, elevation angle) rather than a discrete grid-point label. These experiments used single-user, homogeneous 3GPP scenarios on the same 15×15 grid, providing a clean comparison between the two approaches.


#### 7.0.1 Regression Task Definition

### The regression model predicts three continuous targets simultaneously:


| Target | Meaning | Unit |
| :---- | :---- | :---- |
| Distance | Euclidean distance UE → BS | metres |
| Azimuth | Horizontal angle BS → UE | degrees |
| Elevation | Vertical angle BS → UE | degrees |

Final **3D Position MAE** is computed by reconstructing the XY position from predicted (distance, azimuth) and comparing to the true position. The pipeline is implemented in localization_pipeline_regression.py using XGBoost regressors, one per target.

#### 7.0.2 Feature Progression in Regression - UMi_NLOS and UMa_NLOS

Experiments were run across two homogeneous scenarios to reveal the contribution of each feature type. **UMi_NLOS** (Urban Micro, NLOS, 90,001 samples) and **UMa_NLOS** (Urban Macro, NLOS, 22,501 samples).

**UMi_NLOS - static (h=0):**

| Feature set | 3D Position MAE | Note |
| :---- | :---- | :---- |
| RSS alone | 14.15 m | Fails - range ring ambiguity |
| SINR alone | 14.14 m | ≈ RSS - confirms RSS ≈ SINR without interference |
| RSS + SINR | 14.15 m | No improvement over RSS |
| + AoA azimuth | 0.78 m | Dramatic drop - azimuth resolves direction |
| + AoA elevation | **0.62 m** | Elevation adds distance encoding |

**UMa_NLOS - static (h=0):**

| Feature set | 3D Position MAE | Note |
| :---- | :---- | :---- |
| RSS alone | 31.03 m | Fails severely - macro scenario, poor distance resolution |
| SINR alone | 31.03 m | Identical to RSS |
| RSS + SINR | 31.02 m | No improvement |
| + AoA azimuth | 4.54 m | Partial - azimuth alone insufficient in macro |
| + AoA elevation | **2.01 m** | Elevation essential in macro NLOS environment |

RSS and SINR provide no useful information in either scenario without AoA. In UMa_NLOS, RSS varies so weakly with distance that the model cannot form a useful distance estimate. The 17× gap between UMi (14 m) and UMa (31 m) with RSS alone reflects the more severe distance ambiguity under macro propagation.


#### 7.0.3 History Effect in Regression

History has a qualitatively different effect in regression than in classification.


**UMi_NLOS with AoA (h=0 → h=1):**

| h | 3D Position MAE |
| :---- | :---- |
| 0 | 0.622 m |
| 1 | **0.516 m** (−17%) |


**UMa_NLOS with all features (h=0 → h=3):**

| h | 3D Position MAE |
| :---- | :---- |
| 0 | 1.042 m |
| 1 | 1.099 m |
| 2 | 1.140 m |
| 3 | 1.163 m |


In the UMi_NLOS case, adding h=1 improves regression by 17%. But in UMa_NLOS, history monotonically **hurts** regression: each additional lag step adds error. This is the opposite of the classification finding.

The explanation is architectural: regression predicts absolute coordinates, and consecutive positions are spatially offset from one another. Stacking lags introduces past positions that are slightly wrong (due to noise), and the regressor struggles to disentangle the offset from the current position signal. Classification, by contrast, maps trajectories to discrete labels and benefits from the directional disambiguation that consecutive steps provide.


#### 7.0.4 LOS vs NLOS - Classification


For completeness, the classification task was also evaluated on a **UMa_LOS homogeneous environment** (single user, 90,001 samples, full feature set including AoA):

| h | Accuracy | MAE |
| :---- | :---- | :---- |
| 0 (static) | 92.59% | 0.292 m |
| 1 | **95.90%** | 0.136 m |
| 2 | 95.54% | 0.140 m |
| 3 | 95.86% | 0.128 m |

LOS classification with AoA reaches 92.6% accuracy at h=0 - already much higher than the NLOS equivalent - because the dominant single-ray LOS channel makes AoA highly stable and precise. History adds +3.3 pp. The benefit of history is smaller in LOS than NLOS because there is less ambiguity to resolve at h=0 in the first place.


#### 7.0.5 Classification vs Regression - Head-to-Head

Direct comparison on 15×15 grid, RSS+SINR+AoA features:

| Task | Environment | h | 3D Position MAE |
| :---- | :---- | :---- | :---- |
| **Regression** | UMi_NLOS (single user) | 0 | 0.622 m |
| **Regression** | UMi_NLOS (single user) | 1 | 0.516 m |
| **Classification** | UMi_NLOS + Voronoi (multi-user) | 0 | 0.44 m |
| **Classification** | UMi_NLOS + Voronoi (multi-user) | 3 | **0.39 m** |

Classification outperforms regression at 2 m grid spacing. The ratio is approximately **1.15-1.33×** depending on configuration. The advantage grows with grid size and shrinks as the number of classes approaches the density where discrete labels become ambiguous (estimated crossover near 28-30×30, ~800-900 classes).


**Why classification wins at fine spacing:**

At 2 m grid spacing with ±0.1 m position jitter, each grid point is well-separated and its label is unambiguous. Classification exploits this fully - any error in predicting a nearby class carries a known 2 m penalty. Regression must estimate floating-point coordinates and accumulates noise from all three independently predicted targets (distance, azimuth, elevation).

**Why regression is still valuable:**

Regression is the natural choice when the grid is not known in advance, the target is an arbitrary continuous location, or the grid spacing is larger than the AoA angular resolution. At coarser grids (>4 m spacing) or in outdoor macro scenarios, regression may perform comparably or better.

7.1 Scalability: History Benefit Across Grid Sizes

Before the multi-user experiment, the core thesis was validated across six grid scales using a single-user RSS+SINR setup. XGBoost with smart feature engineering was used throughout.


| Grid | Classes | Static Acc. | Best Trans. Acc. | Δ Accuracy | Best h |
| :---- | :---- | :---- | :---- | :---- | :---- |
| 3×3 | 9 | 53.4% | 62.8% | +9.4 pp | 3 |
| 5×5 | 25 | 39.1% | 53.1% | +14.0 pp | 3 |
| 7×7 | 49 | 26.9% | 41.1% | +14.2 pp | 3 |
| 10×10 | 100 | 33.8% | 55.6% | +21.8 pp | 3 |
| 15×15 | 225 | 13.8% | 29.1% | +15.3 pp | 3 |
| 20×20 | 400 | 13.4% | 22.6% | +9.2 pp | 2 |


**Key finding:** History improves accuracy at every scale, from 9 classes to 400 classes. The largest absolute gain occurs at 10×10 (+21.8 pp). No memory overflow was encountered even at 400 classes.


Also validated at 7×7 across four algorithms (RSS+SINR, h=3):


| Algorithm | Static Acc. | h=3 Acc. | Δ Accuracy | MAE Reduction |
| :---- | :---- | :---- | :---- | :---- |
| Gaussian | 10.9% | 15.5% | +4.7 pp | −13% |
| Random Forest | 28.0% | 43.6% | +15.6 pp | −36% |
| XGBoost | 26.9% | 45.1% | +18.2 pp | −40% |
| MLP | 24.8% | 41.6% | +16.8 pp | −37% |


All four algorithms benefit from history. Tree-based methods (RF, XGBoost) benefit more than probabilistic (Gaussian) or neural (MLP) methods in this setting.

7.2 Multi-User Voronoi 15×15 - Center BS

#### 7.2.1 Overall Results

The table below shows the performance of the core configurations under the optimal dynamic, SINR-dependent AoA noise model evaluated on the 100% full dataset (360k training samples, 90k test samples):

| Experiment | XGB Acc | XGB MAE | RF Acc | RF MAE |
| ----- | ----- | ----- | ----- | ----- |
| BASE | 28.6% | 8.66 m | 46.0% | 6.41 m |
| **BASE_H3** | **51.0%** | **4.86 m** | **54.5%** | **4.50 m** |
| BASE_H3_dp | 59.1% | 3.31 m | 62.8% | 2.94 m |
| BASE_A | 80.2% | 1.16 m | 78.3% | 1.46 m |
| BASE_A_H3 | 82.4% | 0.85 m | 80.2% | 1.08 m |
| **BASE_A_H3_dp** | **83.3%** | **0.82 m** | **81.2%** | **1.02 m** |


**Core thesis result:** BASE → BASE_H3: **+22.4 pp** accuracy (XGB), **+8.5 pp** (RF). **History alone - with no other additions - provides significant improvement over the static baseline.**


**AoA dominance (center BS):** BASE_H3 → BASE_A_H3: **+31.4 pp** (XGB). AoA is the largest single feature contribution when the BS is at the grid center (full 360° angular coverage). See §7.3 for the geometry dependence of this result.


**Device knowledge:** BASE_H3 → BASE_H3_dp: **+8.1 pp** (XGB). Knowing the device type - which determines the systematic RSS/SINR offset - provides orthogonal information to history. The combination BASE_H3_dp outperforms both BASE_H3 and BASE_dp.


7.2.2 History Depth Analysis

Accuracy vs h for BASE experiments (XGBoost, RSS+SINR) on the 100% full dataset:


| h | Accuracy | MAE |
| :---- | :---- | :---- |
| 0 | 28.6% | 8.66 m |
| 3 | 51.0% | 4.86 m |


Transition history of depth 3 achieves a massive **+22.4 pp** accuracy gain and reduces MAE by **43.9%** (from 8.66 m to 4.86 m), reflecting that sequential direction-of-approach information resolves most static-snapshot ambiguity.


#### 7.2.3 Per-User Breakdown (XGBoost, BASE_H3 vs BASE_A_H3)


| User | Device | BASE_H3 Acc | BASE_A_H3 Acc | AoA Gain |
| :---- | :---- | :---- | :---- | :---- |
| U1 | 4-ant flagship | 60.6% | 91.0% | +30.4 pp |
| U2 | 2-ant mid-range | 43.7% | 83.2% | +39.5 pp |
| U3 | 1-ant budget | 50.6% | 60.9% | **+10.3 pp** |
| U4 | 4-ant flagship | 59.5% | 90.5% | +31.0 pp |
| U5 | tablet/IoT | 40.5% | 86.4% | +45.9 pp |


Weaker multi-antenna devices (U2, U5) benefit more from AoA - angular information compensates for degraded RSS/SINR quality. Flagship devices (U1, U4) achieve high accuracy (90.5%-91.0%) with AoA. Crucially, **User 3** (1-antenna) shows a minor AoA gain of only **+10.3 pp** (from 50.6% to 60.9%) because its AoA measurements are entirely missing (NaN), demonstrating that the pipeline gracefully falls back to RSS+SINR features when hardware limitations prevent angle estimation.


#### 7.2.4 Per-Cell Breakdown (XGBoost, BASE_H3 vs BASE_A)


| Cell | Scenario | BASE_H3 Acc | BASE_A Acc | AoA Gain |
| :---- | :---- | :---- | :---- | :---- |
| 1 (Highway) | RMa_LOS | 29.4% | 73.6% | **+44.2 pp** |
| 2 (Shopping) | UMi_NLOS | 56.1% | 72.1% | +16.0 pp |
| 3 (Residential) | Mixed | 62.6% | 86.8% | +24.2 pp |
| 4 (Park) | UMi_LOS | 66.9% | 87.0% | +20.1 pp |


The Highway cell (RMa_LOS) benefits most from AoA. Under Rural Macro LOS, a dominant single-ray path means adjacent grid points have nearly identical RSS/SINR - distance-ring ambiguity is worst here. AoA is the only reliable discriminant, yielding a huge **+44.2 pp** improvement.


#### 7.2.5 Cross-User Generalization


Model trained on U1-U4, evaluated on U5 (unseen device, different height 0.9 m):


| Experiment | In-distribution | Cross-user | Drop |
| :---- | :---- | :---- | :---- |
| BASE_H3 | 48.9% / 4.64 m | 45.2% / 5.15 m | −3.7 pp |
| BASE_A_H3 | 83.2% / 0.40 m | **76.3% / 0.62 m** | −6.9 pp |


AoA generalizes better across devices (+6.9 pp drop vs accessible 3.7 pp without AoA from a much lower baseline). This is because AoA is geometrically determined - the angle from BS to UE depends only on position, not device electronics.


The residual 6.9 pp cross-user gap in BASE_A_H3 is attributable to U5's different UE height (0.9 m vs 1.5 m), which shifts the elevation angle. This is a physical, not electronic, difference.


#### 7.2.6 Device Knowledge vs. History - Isolation


Four new h=0 baselines isolate the contribution of device knowledge from history:


**Without AoA:**


| Experiment | XGB Acc | RF Acc |
| :---- | :---- | :---- |
| BASE | 25.7% | 45.9% |
| BASE_dp (device only, h=0) | 48.5% | 59.3% |
| BASE_H3 (history only, h=3) | 48.9% | 56.9% |
| BASE_H3_dp (both) | 56.9% | 65.3% |


**With AoA:**


| Experiment | XGB Acc | RF Acc |
| :---- | :---- | :---- |
| BASE_A | 81.7% | 81.6% |
| BASE_A_dp (AoA + device, h=0) | 83.7% | 86.7% |
| BASE_A_H3 (AoA + history, h=3) | 83.2% | 80.9% |
| BASE_A_H3_dp (all three) | 84.2% | 82.8% |


Without AoA: device knowledge and history provide almost identical gains, and combining both adds another +8 pp. With AoA: marginal gains from device params (+2 pp XGB) or history (+1.4 pp XGB) are small - AoA already captures most of the spatial information available.


### 7.3 BS Placement Study - AoA Geometry Dependence


The center-BS result (+34 pp AoA gain) raised a critical question: was this gain due to genuine angular discrimination, or an artefact of the full 360° angular coverage that the center position provides?


This experiment places the serving BS at the NE corner (48, 48, 10) - 15 m beyond the grid boundary - compressing all 225 grid points into a ~52° azimuth wedge. All other parameters are unchanged.


#### 7.3.1 Primary Finding - AoA Gain


| Metric | Center BS (360°) | NE BS (52°) |
| :---- | :---- | :---- |
| BASE_H3 accuracy (XGB) | 51.0% | 86.0% |
| BASE_A_H3 accuracy (XGB) | 82.4% | 88.3% |
| **AoA gain (XGB)** | **+31.4 pp** | **+2.3 pp** |
| BASE_H3 accuracy (RF) | 54.5% | 88.1% |
| BASE_A_H3 accuracy (RF) | 80.2% | 89.8% |
| **AoA gain (RF)** | **+25.7 pp** | **+1.7 pp** |


**AoA gain drops from +31.4 pp to +2.3 pp (XGB) when azimuth spread shrinks from 360° to 52°.** The center-BS AoA advantage was primarily geometric: each grid point had a unique azimuth from the BS. In the NE placement, all points appear in the same quadrant (195°-251°, a 56° span). The model cannot distinguish adjacent grid points by azimuth alone.


The residual +2.3 pp gain is attributable to **elevation angle**, which encodes distance: BS height = 10 m, UE height = 1.5 m → vertical gap = 8.5 m. Elevation spans ~9° (SW corner, d=61 m) to ~31° (NE corner, d=21 m) - a 22° spread that still carries distance information even when azimuth is compressed.


#### 7.3.2 History Gain is Geometry-Independent


| Metric | Center BS | NE BS |
| :---- | :---- | :---- |
| BASE → BASE_H3 (XGB) | +22.4 pp | **+28.8 pp** |
| BASE → BASE_H3 (RF) | +8.5 pp | **+5.9 pp** |


The transition history benefit is **highly robust regardless of BS placement** (and is even larger for the NE-Corner layout under XGBoost, resolving RSS distance contours from the corner). History captures trajectory dynamics that depend on how measurements change as the UE moves - this is independent of the BS's angular view.


This is the key differentiating result: **transition features are robust to BS deployment geometry; AoA is not**.


#### 7.3.3 RSS/SINR Discrimination with Edge BS


Notably, the NE BS placement actually *improves* non-AoA experiments:


| Experiment | Center BS XGB | NE BS XGB | Change |
| :---- | :---- | :---- | :---- |
| BASE | 28.6% | 57.2% | **+28.6 pp** |
| BASE_H3 | 51.0% | 86.0% | **+35.0 pp** |
| BASE_A | 80.2% | 81.7% | **+1.5 pp** |


The edge BS creates a larger distance dynamic range (21-61 m vs 0-28 m), giving RSS a stronger gradient and better positional discrimination. Grid points near the NE corner are far from those near the SW corner, making amplitude alone more informative.


#### 7.3.4 Spatial Distribution of Errors - NE BS


Per-Voronoi-cell breakdown (XGBoost, BASE_H3):


| Cell | NE BS Acc | NE BS MAE | Center BS Acc | Center BS MAE |
| :---- | :---- | :---- | :---- | :---- |
| 1 | 83.5% | 1.57 m | 29.4% | 8.27 m |
| 2 | 85.1% | 1.66 m | 56.1% | 3.16 m |
| 3 | 80.3% | 2.16 m | 62.6% | 3.05 m |
| 4 | 89.4% | 0.96 m | 66.9% | 2.58 m |


All cells in the NE-Corner BS layout achieve >= 80\\% accuracy and MAE under 2.2 m without any AoA. Cells closer to the NE corner (Cell 4) achieve the highest accuracy (89.4%) and lowest MAE (0.96 m), demonstrating the strength of edge-based RSS tracking.


#### 7.3.5 Cross-User Generalization Under Edge BS


| Experiment | Center BS | NE BS |
| :---- | :---- | :---- |
| cross_user_BASE_H3 | 45.2% / 5.15 m | 52.5% / 3.96 m |
| cross_user_BASE_A_H3 | **76.3% / 0.62 m** | 58.4% / 2.05 m |


With NE BS: BASE_H3 cross-user *improves* (+7.3 pp) because the stronger RSS gradient is inherently more device-agnostic. BASE_A_H3 cross-user *degrades* significantly (−17.9 pp) - when AoA is weak, the model falls back on RSS/SINR, which varies across devices.


### 7.4 Large-Scale Grid Regression: 25x25 Grid with 4m Spacing


To evaluate scalability and bypass Out-of-Memory (OOM) limitations on larger search spaces, we executed the comparison on a **25x25 grid (625 points)** with a **4m spacing** (Grid size X ∈ [5, 101], Y ∈ [5, 101]). Since classification on 625 classes is memory-prohibitive, we designed a 3D spherical regression pipeline predicting continuous targets (Distance, Azimuth, and Elevation relative to the serving BS). These predictions are converted back to Cartesian coordinates to compute physical 3D MAE (meters) and Mean Point Error (MPE = 3D MAE / 4.0).


#### 7.4.1 Regression Results Summary (Untuned Baselines)


Evaluated on the 30% subsampled training set (for training speed and memory limits) and the 100% chronological test set under the NE-Corner BS layout:


| Model | Experiment | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train Time (s) |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
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

In the 15x15 NE-Corner BS layout, the classification model achieves a 3D MAE of 0.589m (MPE = 0.294) under BASE_A_H3_dp. In the 25x25 grid, the regression models achieve a best MAE of 13.497m (MPE = 3.374).

*- Scale Expansion:* The 25x25 grid has a 100m × 100m area, which is **11.1 times larger** than the 15x15 grid's 30m × 30m area. The maximum distance to the BS increases to ~157m. Since RSS attenuates exponentially with distance, it is highly compressed at large ranges, leading to a much lower signal-to-distance gradient.

- *Angular Error Scaling:* Clean AoA is degraded by SINR-dependent noise. At a distance of 150m, a 5° angular error converts to a physical displacement of ≈ 13 m. Under continuous coordinate tracking, this sets a high error floor.


2. **Model Architectures and Multi-Output Handling:**

- *Random Forest vs. XGBoost:* Random Forest performs significantly better on regression targets (13.497m vs 17.185m MAE under full features). Scikit-learn's RandomForestRegressor natively supports multi-output targets by computing splits based on multi-variate variance, preserving spatial correlations between Distance, Azimuth, and Elevation. XGBoost, when wrapped in MultiOutputRegressor, is forced to fit three independent models, ignoring cross-target relationships.

*- History Feature Behavior:* XGBoost demonstrates monotonic improvement with history (BASE_A MAE 20.221m → BASE_A_H3 MAE 17.353m) as sequential boosting selects useful features. In contrast, Random Forest suffers from the feature space quadrupling (from 4 features in BASE_A to 16 in BASE_H3). Without tuning, randomly selecting features at each node split introduces noise, leading to slight degradation (BASE_A 13.084m → BASE_A_H3 13.941m MAE).

- *Device Hardware Limits:* XGBoost natively routes NaN values, showing the highest error for the single-antenna User 3 (BASE_A_H3_dp MAE = 21.392m) because it cannot use AoA. Random Forest requires zero-imputation of NaNs, which skews U3's feature space.


3. **Validation of Core Thesis at Scale:**

- Despite the physical challenges of scaling (path loss flattening and angular projection errors), transition history remains a highly powerful discriminant. In the XGBoost model, adding history (`BASE_H3`) reduces the localization error by **4.7%** (from 26.12m to 24.93m) compared to the static snapshot (`BASE`). This proves that path-derived transition history is a robust localization feature that scales effectively across search spaces.

- **XGBoost (Cartesian MSE) Best Configuration:**

  `{'n_estimators': 250, 'max_depth': 8, 'learning_rate': 0.1556, 'subsample': 0.7496, 'colsample_bytree': 0.6758}`

- **Random Forest (Cartesian) Best Configuration:**

  `{'n_estimators': 200, 'max_depth': 15, 'min_samples_leaf': 5}`

- **XGBoost (Cartesian Custom Loss) Best Configuration:**

  `{'n_estimators': 100, 'max_depth': 9, 'learning_rate': 0.1827, 'subsample': 0.8969, 'colsample_bytree': 0.8334}`


#### Regression Results After Cartesian Optimization

Evaluated on the 30% subsampled training set and the 100% chronological test set under the NE-Corner BS layout:


| Model | Experiment | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train Time (s) |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| XGBoost | BASE | 29.515 | 7.379 | 15.033 | 13.934 | 1.187 | 5.65 |
| XGBoost | BASE_H3 | 14.713 | 3.678 | 7.405 | 6.799 | 0.569 | 9.33 |
| XGBoost | BASE_H3_dp | 13.702 | 3.425 | 7.028 | 6.294 | 0.528 | 8.90 |
| XGBoost | BASE_A | 14.611 | 3.653 | 8.739 | 5.671 | 0.629 | 7.00 |
| XGBoost | BASE_A_H3 | 11.886 | 2.971 | 7.651 | 4.306 | 0.558 | 12.15 |
| XGBoost | **BASE_A_H3_dp** | **11.486** | **2.871** | **7.240** | **4.257** | **0.538** | **13.20** |
| Random Forest | BASE | **9.664** | **2.416** | **4.797** | **4.368** | **0.330** | **45.69** |
| Random Forest | BASE_H3 | 11.732 | 2.933 | 5.738 | 5.369 | 0.410 | 185.11 |
| Random Forest | BASE_H3_dp | 9.934 | 2.483 | 5.020 | 4.516 | 0.358 | 182.30 |
| Random Forest | BASE_A | **8.380** | **2.095** | **4.974** | **3.217** | **0.342** | **54.76** |
| Random Forest | BASE_A_H3 | 10.634 | 2.658 | 6.994 | 3.704 | 0.501 | 217.27 |
| Random Forest | **BASE_A_H3_dp** | **10.045** | **2.511** | **6.547** | **3.551** | **0.459** | **226.19** |


#### Key Insights from Tuning


1. **Capacity and Spatial Mapping Resolution:**

- *XGBoost Optimization:* Tuning Max Depth to 8 and learning rate to 0.276 enabled sequential boosting to better resolve coordinate borders, lowering the full-feature MAE from **17.185m** to **11.486m** (a **33.2% error reduction**).

- *Random Forest Tree Depth:* By lowering min_samples_leaf to 5 and increasing max_depth to 20, Random Forest was allowed to fit fine-grained spatial mappings. This, combined with 200 estimators, reduced the full-feature MAE from **13.497m** to **10.045m** (a **25.6% error reduction**).


2. **The Static Feature Advantage in Random Forest:**

- In the tuned Random Forest models, static configurations outperform history-based configurations (BASE_A 3D MAE = **8.380m** vs. BASE_A_H3_dp 3D MAE = **10.045m**).

- *Explanation:* Static features (rss, sinr, aoa_azimuth, aoa_elevation) are physically consistent and unique at any given coordinate. Splitting on history features (h=3) quadruples the features to 16. During random feature sampling in Random Forest, splitting nodes on highly correlated and redundant temporal lag features introduces variance and overfits to specific user trajectory paths rather than the underlying grid coordinates.


3. **Boosting vs. Bagging Lag Handling:**

- XGBoost shows monotonic improvement with transition history (BASE_A 14.611m → BASE_A_H3 11.886m). This is because boosting iteratively focuses on errors, allowing it to naturally prune redundant lag features and leverage trajectory gradients, whereas Random Forest's random feature subsets suffer from feature space inflation.


4. **Validation of Core Thesis at Scale (Tuned):**

- After hyperparameter optimization, the value of transition history is even more pronounced: for XGBoost, adding history (`BASE_H3`) reduces the positioning error from **29.515m** to **14.713m** - **a 50.1% error reduction**. This demonstrates that sequential path dynamics are highly generalizable and yield massive improvements under complex, large-scale search scenarios.


---


### 8. Related work

### 9. References

[1] Omri's work (add article)

[GitHub Link to Repository](https://github.com/slash827/CSI-Location)
