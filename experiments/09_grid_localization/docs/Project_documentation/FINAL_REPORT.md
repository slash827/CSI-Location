# Transition History as a Universal Mechanism for Single-BS 5G NR CSI Localization

**Author:** Gilad Battat
**Advisors:** Prof. Sarit Kraus, Prof. David Sarne
**Institution:** Bar-Ilan University
**Industry Partners:** CEVA, Cellcom
**Status:** Draft v1 — academic project report (target: conference paper)
**Code & data provenance:** branch `main`, `experiments/09_grid_localization/` (run `git log -1 -- experiments/09_grid_localization/` for the exact revision)

---

## Abstract

Network-assisted positioning from 5G NR channel state information (CSI) is attractive because it reuses measurements the base station (BS) already receives — no GPS, no UE-side IMU, no dedicated positioning infrastructure. In a **single serving BS** deployment, however, the dominant measurement (received signal strength, RSS) is largely a function of range, so all positions on an iso-power ring around the tower are close to indistinguishable. We call this the **distance-ring ambiguity**, and it is the accuracy ceiling of static fingerprinting.

This work does not propose a new positioning model. It proposes and evaluates a **mechanism**: feeding a short window of *transition history* — the last $h$ consecutive CSI observations of a moving UE — to whatever regressor or classifier is already deployed. Because consecutive observations of a spatially-consistent channel encode the UE velocity vector $\mathbf{v} \approx \Delta\mathbf{r}/\Delta t$ and the radial path-loss derivative $d\text{RSS}/dt$, history supplies exactly the degree of freedom the static snapshot lacks, breaking the ring symmetry.

Using QuaDRiGa (3GPP TR 38.901) simulations across two campaigns — a controlled $15\times15$ grid classification study (5 device profiles, 450k samples) and a large-scale $100\,\text{m}\times100\,\text{m}$ macro-cell regression study (300 unseen users, $25\times25$ grid) — we report three principal results:

1. **Universality.** Transition history reduces positioning error in *every* model family tested: tree ensembles (Random Forest, XGBoost), recurrent networks (GRU), 1D-CNNs, and CNN+temporal-attention. On the macro-cell study the 1D-CNN improves from $22.846\,\text{m}$ MAE at $h=0$ to $19.260\,\text{m}$ at $h=5$ — a $\Delta\text{MAE}$ of $-3.586\,\text{m}$ ($15.7\%$). The largest marginal step is $h=0\!\to\!h=1$ ($-1.562\,\text{m}$), exactly where velocity first becomes computable. In the controlled classification study the same mechanism yields $+22$ to $+29$ percentage points of exact-cell accuracy, and it holds at every grid size from 9 to 400 classes.
2. **A hardware discontinuity that must be reported separately, not averaged.** Under a realistic 3GPP Rel-15/16 population mix, multi-antenna smartphones ($85\%$ of users, AoA-capable) reach $14.58\,\text{m}$ MAE / $12.31\,\text{m}$ median, while single-antenna IoT devices ($15\%$) plateau at $34.54\,\text{m}$ / $30.23\,\text{m}$ — a $2.3\times$ gap that inflates the naive population mean to $\approx 19.3\,\text{m}$. An exhaustive outlier audit shows $100\%$ of the five worst users are 1-antenna devices and $100\%$ of the five best are multi-antenna; the failure mode is azimuthal smearing along a correctly-estimated range ring, not corrupted data.
3. **A cheap architectural fix for the AoA-blind cohort.** Single-antenna UEs are conventionally fed dummy $(0^\circ,0^\circ)$ AoA, which makes $\cos(0^\circ)=1$ and injects a false boresight anchor. Explicitly masking the trigonometric embeddings to $(\sin\theta,\cos\theta)=(0,0)$ — mathematically off the unit circle — and adding a binary `has_valid_aoa` channel reduces single-antenna error by $-1.42\,\text{m}$ ($4.2\%$) to $32.19\,\text{m}$ while slightly *improving* multi-antenna accuracy to $15.28\,\text{m}$.

The contribution is therefore a portable, model-agnostic input transformation with a physical justification, together with the evaluation protocol (per-antenna-cohort disaggregation) needed to measure it honestly.

---

## 1. Introduction

### 1.1 Motivation

3GPP Release 16 and beyond treat positioning as a first-class network service. The BS already measures RSS, SINR, timing advance, and — where the UE has an antenna array — angle of arrival (AoA). Reusing these for localization is attractive precisely where GNSS fails: urban canyons, tunnels, industrial halls, indoor complexes.

The obstacle is accuracy. RSS, the most universally available metric, is dominated by path loss and therefore encodes range far more strongly than bearing. Given a single serving BS, the set of positions consistent with an observed RSS is approximately an annulus. Shadow fading and multipath perturb this, but not enough to identify a position: this is the **distance-ring ambiguity**. It is worst in LOS-dominated geometries, where the range-to-RSS map is near-monotone and multipath diversity is minimal.

SINR (through co-channel interference geometry) and AoA both add bearing information and both break the ambiguity — but conditionally. SINR depends on interferer placement and calibration; AoA depends on UE beamforming hardware that a large fraction of connected devices simply does not have. Neither is a universal answer.

### 1.2 Hypothesis and framing

> **A moving UE's measurement *sequence* encodes more positional information than any single snapshot, and this holds regardless of the estimator applied on top.**

Two positions on the same iso-power ring produce the same instantaneous RSS but *different trajectories through measurement space*, because the channel neighbourhood around each is different and evolves differently as the UE moves. A window of $h+1$ observations makes the first and second temporal derivatives of the measurement vector observable, and those derivatives carry bearing information that the snapshot does not.

The framing of this work follows directly from a research discussion with Alon Levin (2026-08-20). Positioning the work as *"we built the best localization model"* is a weak claim: model leaderboards turn over constantly, and our absolute error is not state of the art. Positioning it as *"here is a mechanism that improves every model"* is a stronger and more defensible claim, and it is falsifiable: a single model family where history does not help would refute it. We therefore report **$\Delta\text{MAE}$ against each model's own $h=0$ baseline** as the primary metric, and treat absolute MAE as secondary context.

### 1.3 Contributions

* **C1 — Mechanism, cross-validated across paradigms.** A history-stacking input transformation, evaluated at fixed protocol across seven estimators spanning four algorithmic paradigms, with $\Delta\text{MAE}$ reported per model rather than only in aggregate.
* **C2 — A model-class account of the optimum.** We show the gain is not monotone in $h$ for *fixed-window* estimators: the 1D-CNN and $k$-NN peak at $h=5$ and regress at $h=10$, while tree ensembles improve monotonically through $h=10$. The optimum is a property of how an estimator consumes the window, not of the propagation physics alone — a tree can decline to split on an uninformative lag, whereas a convolution over a fixed window and a distance metric over a fixed vector cannot ignore one.
* **C3 — Cohort-disaggregated evaluation.** We show that aggregate MAE over a mixed-hardware population is a mixture artifact, and give the per-antenna-tier decomposition (including error CDFs) that makes results interpretable.
* **C4 — AoA validity masking.** A two-line feature-pipeline change that removes the dummy-boresight bias for AoA-blind devices, with measured benefit to *both* cohorts.
* **C5 — Reproducible artifact.** Full simulation configs, notebooks, shared utilities, and fixed seeds.

### 1.4 Scope and non-goals

* **Single serving BS only.** Per-interferer RSS is deliberately excluded from the feature set: using it would constitute multilateration, a different problem requiring coordinated distributed infrastructure. Interferers affect the observations only through SINR, as they would in a real network.
* **No UE-side telemetry.** No GPS, no IMU, no dead reckoning. All inputs are BS-side measurements.
* **Simulation, not field trial.** All results are QuaDRiGa 3GPP TR 38.901 with fixed seeds. See §9.

---

## 2. Related Work and Positioning

**Fingerprinting.** Classical RSS fingerprinting matches a snapshot against a survey database. It is the direct baseline for our $h=0$ condition, and its known failure mode — poor discrimination between equidistant points — is exactly the distance-ring ambiguity we target. Our $k$-NN $h=0$ regressor ($27.857\,\text{m}$ MAE) stands in for this family.

**Geometric methods (ToA/TDoA/AoA multilateration).** These solve position from an explicit geometric system, but require either multiple synchronized BSs or high-quality angle estimates. Our single-BS, single-AoA-source setting is precisely the regime where the geometric system is underdetermined, which is why the $15\%$ single-antenna cohort collapses to a range-only estimate.

**Sequence models for CSI.** Recurrent and convolutional temporal models have been applied to CSI-based tracking. The usual framing is architectural — a new network achieves lower error. Our framing is orthogonal: we hold the architecture family variable and vary only the *input window*, so the claim transfers to architectures we did not test.

**Hybrid kinematic/radio fusion.** A related line of work (e.g. concurrent work by Raz Weintock under Julian's supervision) fuses a separate motion-tracking estimator with a CSI-based estimator, compensating for NLOS gaps with kinematics. That approach balances two structurally separate models. Ours instead raises the *dimensionality of the input* to a single existing model, so it requires no second estimator, no fusion weighting, and no additional sensor. The two are complementary rather than competing: our mechanism is a drop-in for the radio branch of such a hybrid.

**Positioning statement.** We claim a mechanism, not a leaderboard entry. The evidence required is therefore breadth (many model families, many operating points) rather than a single record-setting number.

---

## 3. System Model and Problem Formulation

### 3.1 Measurement model

At discrete step $t$ the serving BS observes a measurement vector for the UE:

$$\mathbf{m}(t) = \big[\text{RSS}(t),\; \text{SINR}(t),\; \theta_{az}(t),\; \theta_{el}(t)\big]$$

with $(\theta_{az},\theta_{el})$ present only for UEs whose antenna count $N_{ant}\ge 2$. Multi-antenna UEs are modelled by maximum-ratio combining over the per-element channel:

$$H_{\text{eff}}(f) = \sqrt{\textstyle\sum_{i=1}^{N_{ant}} |H_i(f)|^2}$$

with a device-specific antenna gain offset applied additively in dB.

### 3.2 The distance-ring ambiguity

Let $r = \|\mathbf{p}_{UE} - \mathbf{p}_{BS}\|$. Under a log-distance path-loss model, $\text{RSS} \approx P_{tx} - 10\gamma\log_{10} r + \chi$ with $\chi$ shadow fading. The inverse map $\text{RSS}\mapsto\mathbf{p}$ is therefore one-to-many: it identifies $r$ (up to $\chi$) and leaves bearing $\phi$ entirely unconstrained. In polar coordinates the snapshot observes one of the two degrees of freedom it needs.

### 3.3 Why history restores the missing degree of freedom

With a window $\mathcal{W}_h(t) = [\mathbf{m}(t-h),\dots,\mathbf{m}(t)]$, the estimator can form finite differences. Two are physically decisive:

* **Radial velocity.** $\frac{d\text{RSS}}{dt} \propto -\frac{10\gamma}{\ln 10}\cdot\frac{\dot r}{r}$ gives the component of motion along the BS bearing.
* **Angular rate.** $\dot\theta_{az} = \frac{v_\perp}{r}$ (where available) gives the tangential component and, jointly with $\dot r$, pins the heading.

For a UE moving at roughly constant speed, the pair $(\dot r, \dot\theta)$ constrains the position to the intersection of a range ring and a *motion-consistent* arc, a far smaller set than the ring. Even without AoA, the *shape* of the RSS/SINR trajectory over $h+1$ steps is a signature of the local channel neighbourhood, which is spatially non-uniform and therefore discriminative. This is the mechanism the empirical results test.

### 3.4 Task formulations

* **Classification** (Campaign A): predict one of $G$ discrete grid cells. Appropriate when grid spacing ($2\,\text{m}$) greatly exceeds position jitter ($\pm0.1\,\text{m}$).
* **Spherical regression** (Campaign B): predict continuous $(\text{range}, \theta_{az}, \theta_{el})$ relative to the serving BS, converted back to Cartesian for a 2D/3D MAE in metres. Used at $625$ cells where classification becomes memory-prohibitive and where evaluation is on *unseen users*, not seen grid points.

---

## 4. Methodology

### 4.1 Two experimental campaigns

| | **Campaign A — Controlled grid** | **Campaign B — Macro-cell population** |
| :--- | :--- | :--- |
| Purpose | Isolate the mechanism under clean, repeatable conditions | Stress it under realistic scale, hardware mix, and unseen users |
| Grid | $15\times15 = 225$ cells, $2\,\text{m}$ spacing | $25\times25 = 625$ cells, $4\,\text{m}$ spacing, $\approx 100\,\text{m}\times100\,\text{m}$ |
| Task | Classification (exact cell) | Spherical regression → Cartesian MAE |
| Population | 5 device profiles, 450,005 samples | 300 users, four mobility patterns, mixed speeds |
| Split | Chronological 80/20 **per user** | 80/20 over **disjoint user IDs** (zero-shot users) |
| Carrier | $3.5\,\text{GHz}$ | $3.0\,\text{GHz}$ Sub-6 |
| BS geometry | Center BS $[19,19,10]$ and NE BS $[48,48,10]$ | Serving BS $[116,116,10]$; interferers $[-60,53,10]$, $[53,-60,10]$ |
| Primary metric | Accuracy (pp) + MAE | 2D MAE / P50 / P90, disaggregated by cohort |

> **Note for the final paper:** the two campaigns use different carrier frequencies ($3.5$ vs $3.0\,\text{GHz}$) as recorded in `technical_documentation.md` §3.1 vs §8.1. This is a campaign difference, not a typo to be silently harmonised — confirm against the generation configs before submission and state it explicitly in the paper's setup table.

### 4.2 Channel simulation

All data is generated with **QuaDRiGa v2.8.1** implementing 3GPP TR 38.901, $100\,\text{MHz}$ bandwidth, 256 OFDM subcarriers, $30\,\text{dBm}$ TX power for serving and interfering sites, omnidirectional BS element. QuaDRiGa's **spatial consistency** is essential to this study: the channel evolves continuously along the trajectory rather than being redrawn independently per step, which is the physical precondition for transition features to carry information at all.

The service area is partitioned into **four Voronoi propagation zones**, each assigned a distinct 3GPP scenario, so a single grid spans the indoor-like-NLOS to open-LOS spectrum:

| Zone | Scenario | Character |
| :--- | :--- | :--- |
| Highway | RMa_LOS | Rural macro, line of sight |
| Shopping district | UMi_NLOS | Dense NLOS, rich multipath |
| Residential | UMi mixed LOS/NLOS | Suburban transition |
| Park | UMi_LOS | Urban micro, line of sight |

Zone boundaries are generated at simulation time from a fixed seed.

**What "interference" means here.** Campaign B's 300 users are generated in shared QuaDRiGa layouts of 25 users each, with three transmitters per layout: the serving BS and the two interfering sites. SINR is computed as

$$\text{SINR} = \frac{P_{\text{serving}}}{P_{\text{IBS-1}} + P_{\text{IBS-2}} + P_{\text{noise}}}, \qquad P_{\text{noise}} = -104\,\text{dBm}$$

so interference comes **only from the two interfering base stations**. No user-to-user coupling is modelled: co-scheduled UEs in the same layout do not interfere with one another, and a user's SINR is unchanged by how many other users share its layout. Batching users into shared layouts is a simulation-efficiency measure that also lets users in a batch share large-scale parameter maps; it is not a multi-user interference model. Uplink multi-user interference, pilot contamination, and scheduling effects are all out of scope.

![Figure 1: Macro-cell spatial environment](../figures/environment_spatial_layout.png)
*Figure 1 — Campaign B deployment layout: $100\,\text{m}\times100\,\text{m}$ service area, serving BS at $[116,116,10]\,\text{m}$ (north-east, off-grid), two pushed south-west interferers, and the four Voronoi propagation zones.*

### 4.3 Mobility model

The two campaigns use **different mobility models**, and the distinction governs how the history results must be read.

**Campaign A** uses constrained random walks on the 8-connected grid adjacency graph, starting at the grid centre, at $1.5\,\text{m/s}$. Step duration is $\text{spacing}/v$ ($1.33\,\text{s}$ for a cardinal $2\,\text{m}$ step, $\times\sqrt2$ diagonally). This walk carries no persistent heading.

**Campaign B is not a random walk.** Each of the 300 users draws one of four trajectory patterns and one of four speed classes (`runners/run_multi_user_300_25x25.m`, `lib/generate_diverse_trajectories.m`):

| Pattern | Share | Character |
| :--- | :---: | :--- |
| Billiards | 35% | straight-line street navigation with boundary bounces |
| Momentum walk | 35% | random walk with 70% probability of continuing straight |
| Waypoint tour | 20% | directed transit between five sampled waypoints |
| Straight transit | 10% | arterial crossing, entering and leaving at the boundary |

| Speed class | Share | Range |
| :--- | :---: | :--- |
| Pedestrian | 40% | $1.0$–$1.5\,\text{m/s}$ |
| Jogger | 25% | $2.5$–$4.5\,\text{m/s}$ |
| Vehicle | 25% | $8.0$–$15.0\,\text{m/s}$ |
| Static | 10% | $0.1$–$0.5\,\text{m/s}$ |

**All four patterns carry heading persistence**, and two of them — billiards and straight transit — are strongly persistent. Campaign B is therefore *favourable* to transition history rather than adversarial to it, which is the opposite of what a "random walk" description would imply.

A direct consequence, easy to miss: because step duration is $\text{spacing}/v$ and speed spans two orders of magnitude across the population, **a fixed history depth is not a fixed time window.** Measured over the 232 users retained after cohort downsampling, per-user $\Delta t$ ranges from $0.27\,\text{s}$ to $32.5\,\text{s}$ (median $2.71\,\text{s}$), so an $h=5$ window covers $1.3\,\text{s}$ for the fastest vehicle and $162\,\text{s}$ for the slowest static user, with a median of $13.5\,\text{s}$. Statements of the form "$h=5 \approx 2.5\,\text{s}$" hold for one speed class only and are avoided throughout this report.

Position jitter of $\pm0.1\,\text{m}$ per snapshot prevents the estimator from latching onto exactly-aligned coordinates.

### 4.4 Device heterogeneity and the AoA impairment model

Campaign A simulates five profiles (4-ant flagship $\times2$ with different walk seeds, 2-ant mid-range, 1-ant budget, 2-ant tablet at $0.9\,\text{m}$ height). Campaign B uses a 3GPP-representative population mix: **$85\%$ multi-antenna** ($\approx45\%$ 4-antenna, $\approx40\%$ 2-antenna) and **$15\%$ single-antenna** IoT/budget devices.

Clean QuaDRiGa cluster angles are degraded in Python at load time (so clean-vs-degraded can be compared without re-simulating):

1. **SINR-dependent estimation noise**, per axis, per snapshot:
   $$\sigma_{\text{AoA}}(t) = \operatorname{clamp}\!\left(2.0^\circ \cdot 10^{-\frac{\text{SINR}_{dB}(t)-10}{15}},\; 1.0^\circ,\; 20.0^\circ\right)$$
2. **Codebook quantization** to $5^\circ$ steps on both azimuth and elevation.
3. **Hardware capability gating.** Devices with $N_{ant}\le1$ have no beamforming and are excluded from AoA entirely — this is a capability limit, not noise, and §7.6 shows how it must be encoded.

### 4.5 Feature construction

**Snapshot ($h=0$):** $[\text{rss},\text{sinr}]$, optionally $+[\theta_{az},\theta_{el}]$.

**History stacking ($h>0$):** $h+1$ consecutive snapshots concatenated as `rss_lag0 … rss_lag{h}`, etc. Feature dimension $D = 2(h+1)$ without AoA, $4(h+1)$ with. Lags are built per user after sorting by step index; the first $h$ rows of each user are dropped and lags never cross user boundaries.

*Absolute values are stacked, not differences.* Device-specific RSS/SINR offsets are stable across the grid and act as fingerprints in their own right; differencing removes them and measurably hurts (Campaign A delta-feature variants).

**Derived BS-side physical features (Campaign B, 13 channels):** on top of the 5 raw channels (`rss, sinr, aoa_az, aoa_el, delta_t`) we add $\sin/\cos$ of both angles (removing the $\pm180^\circ$ wrap discontinuity), geometric ray projections $(\text{ray}_x,\text{ray}_y)$ combining a path-loss range estimate with the AoA unit vector, and first differences $(d\text{rss}, d\theta_{az}, d\text{ray}_x, d\text{ray}_y)$. These are inductive biases: every one of them is computable by the network from the raw channels in principle, but supplying them directly measurably helps (§5.2).

### 4.6 Estimators

| Family | Model | Notes |
| :--- | :--- | :--- |
| Instance-based | $k$-NN regressor | $h=0$ classical fingerprinting baseline |
| Tree ensemble | Random Forest | 150 trees, `max_depth` 16, `min_samples_leaf` 5, Optuna-tuned (30 trials, TPE) |
| Tree ensemble | XGBoost | 50 estimators, depth 5, lr $0.15$, subsample/colsample $0.8$ |
| Recurrent | 2-layer GRU | sequence input, early stopping |
| Convolutional | 1D-CNN | temporal convolution over the window (NB06) |
| Convolutional + attention | 1D-CNN + temporal self-attention | NB07 |
| Convolutional, masked | Mask-aware 1D-CNN | AoA validity masking (§7.6) |

Hyperparameters are held fixed across all history depths so that the only varying factor is the input window. Seed $=42$ throughout.

### 4.7 Evaluation protocol

* **Campaign A split:** strictly chronological per user (first $80\%$ train, last $20\%$ test). A random split would leak: spatial consistency makes temporally adjacent samples near-duplicates.
* **Campaign B split:** user-disjoint. Test users are never seen in training — a zero-shot generalization test over trajectories *and* devices, which is materially harder than held-out steps of known users.
* **Metrics:** exact-cell accuracy (A); 2D MAE, median (P50), and P90 in metres (B). We report P50/P90 alongside the mean throughout because the mixed-hardware population is bimodal and the mean alone is misleading (§7.1).
* **Primary comparison:** $\Delta\text{MAE}$ against the same model's own $h=0$ result.

---

## 5. Results I — The Mechanism

### 5.1 History depth sweep and $\Delta\text{MAE}$

Two deltas are reported and must not be conflated. **Step $\Delta$MAE** is the change against the previous depth in the sweep (marginal value of the added frames); **cumulative $\Delta$MAE** is the change against the $h=0$ snapshot baseline (headline gain of the mechanism).

*1D-CNN, Campaign B, 13 derived channels, 300 unseen users:*

| History $h$ | Window $L$ | Duration | 2D MAE | P50 | P90 | Step $\Delta$MAE | Cumulative $\Delta$MAE | Cumulative gain |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| $h=0$ (snapshot) | 1 | $\approx0.5\,$s | 22.846 m | 20.170 m | 41.488 m | — | — | baseline |
| $h=1$ | 2 | $\approx1.0\,$s | 21.284 m | 18.397 m | 39.378 m | $-1.562$ m | $-1.562$ m | **6.8%** |
| $h=3$ | 4 | $\approx2.0\,$s | 20.026 m | 16.654 m | 38.647 m | $-1.258$ m | $-2.820$ m | **12.3%** |
| $h=5$ | 6 | $\approx2.5\,$s | **19.260 m** | **15.228 m** | **38.005 m** | $-0.766$ m | $-3.586$ m | **15.7%** |
| $h=10$ | 11 | $\approx5.0\,$s | 20.215 m | 16.485 m | 37.472 m | $+0.955$ m | $-2.631$ m | 11.5% |

*Sign convention: negative $\Delta\text{MAE}$ (metres) = error reduced; the gain column expresses the same reduction as a positive percentage.*

Three observations:

1. **The largest marginal gain is the first step.** $h=0\!\to\!1$ contributes $-1.562\,\text{m}$, $44\%$ of the total achievable reduction, from a single extra frame. This is exactly the transition at which velocity becomes computable, and it is the strongest direct evidence for the mechanism as stated in §3.3.
2. **Middle depths refine rather than transform.** $h=1\!\to\!5$ adds a further $-2.024\,\text{m}$; the temporal convolution is now averaging over Rayleigh fast-fading nulls and angular estimation noise as well as reading velocity.
3. **The curve turns — for this model.** At $h=10$ the 1D-CNN's error *increases* by $+0.955\,\text{m}$. P90 continues to fall slightly ($37.472\,\text{m}$), i.e. long windows still help the hardest samples while hurting typical ones — a smoothing-versus-staleness trade-off rather than a pure capacity artifact.

**The turn is not universal, and §5.4 shows it is a property of the estimator rather than of the data.** $h=5$ is nonetheless fixed for all cross-model comparisons that follow, because it is the depth at which the master benchmark was run.

![Figure 2: Universal ΔMAE curves across model families](../figures/universal_delta_mae_history_curves.png)
*Figure 2 — The universality result. $\Delta\text{MAE}$ vs. history depth for four algorithmic paradigms (1D-CNN, XGBoost, Random Forest, GRU). Left: absolute 2D error in metres. Right: normalized improvement against each model's own $h=0$ baseline. Every family improves at every depth. The **location** of each family's optimum differs, however — see §5.4.*

### 5.2 Feature-set ablation: physical inductive bias

At fixed $h=5$, comparing raw sensor channels against the full BS-side derived set:

| Feature set | Channels | 2D MAE | P50 | P90 | Gain |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Raw | 5 | 19.686 m | 16.299 m | 37.954 m | baseline |
| Full derived | 13 | **19.260 m** | **15.228 m** | 38.005 m | **+2.2%** (P50 $-1.07\,$m) |

The mean improves modestly but the **median improves by $1.07\,\text{m}$** — the derived features help typical samples substantially while leaving the hard tail (P90) unchanged. Mechanistically: $(\sin\theta,\cos\theta)$ removes the wrap-around cliff at $\pm180^\circ$, and the ray projections give the network a first-order geometric anchor instead of requiring it to learn trigonometry from scratch.

### 5.3 The mechanism in the controlled classification campaign

Campaign A confirms the same effect in a different task formulation and a different metric. Across 6 grid sizes (9 to 400 classes), 4 algorithms, and 2 BS placements, history yields a consistent **$+22$ to $+29$ percentage points** of exact-cell accuracy (XGBoost, RSS+SINR). Crucially:

| Effect | Center BS ($360^\circ$ AoA spread) | NE-corner BS ($52^\circ$ spread) |
| :--- | :---: | :---: |
| History gain (`BASE`→`BASE_H3`) | $+22.4$ pp | $+28.8$ pp |
| AoA gain (`BASE_H3`→`BASE_A_H3`) | $+31.4$ pp | $+2.3$ pp |

**AoA's value is geometry-dependent and collapses by an order of magnitude** when the BS sits at a corner and all grid points fall inside a $52^\circ$ wedge. **History's value does not** — it is slightly *larger* in the harder geometry. This is the strongest available argument that history is a mechanism rather than a configuration-specific trick: it survives the deployment change that destroys the competing information source.

### 5.4 Where the optimum sits, and why it moves

Running the sweep across estimator families shows that history helps everywhere, but the depth at which the benefit saturates is not shared. Two independent sweeps from July (7 raw channels) and a fresh sweep (13 derived channels) agree:

| Estimator | Channels | $h=0$ | $h=5$ | $h=10$ | Behaviour at $h=10$ |
| :--- | :---: | :---: | :---: | :---: | :--- |
| 1D-CNN | 13 | 22.846 m | **19.260 m** | 20.215 m | **turns** ($+0.955$ m) |
| $k$-NN | 13 | 27.440 m | **23.983 m** | 24.485 m | **turns** ($+0.502$ m) |
| XGBoost | 13 | 22.349 m | 19.434 m | **19.027 m** | still improving |
| XGBoost (Jul) | 5 raw | 28.325 m | 25.404 m | **25.002 m** | still improving |
| Random Forest (Jul) | 5 raw | 27.704 m | 25.945 m | **25.880 m** | still improving |

**Fixed-window estimators turn; tree ensembles do not.** The explanation is architectural rather than physical. A tree ensemble performs implicit feature selection: a lag that carries no signal is simply never split on, so an over-long window costs nothing but training time. A 1D convolution consumes every position in its receptive field, and $k$-NN measures distance over the whole concatenated vector — for both, an uninformative lag actively injects noise into the representation.

This matters for how the contribution is stated. The *mechanism* claim — history reduces error in every family — is supported without qualification. A claim that "$h=5$ is the universal optimum" is not supported, and the honest version is: **the useful window is bounded for fixed-window estimators and effectively unbounded (over the range tested) for estimators that can ignore inputs.**

### 5.5 Does the gain survive per-depth hyperparameter re-tuning?

Earlier runs contained configurations where added history made tree ensembles worse, raising the concern that the history gain is confounded with capacity: enlarging the input space without re-fitting capacity and regularization is not a controlled comparison. We tested this directly on XGBoost with Optuna (TPE, 20 trials per depth). Tuning used training users only, split further into sub-train and validation by user id; test users were touched exactly once, for the final evaluation.

| $h$ | Fixed defaults | Per-depth tuned | Gain, defaults | Gain, tuned |
| :---: | :---: | :---: | :---: | :---: |
| 0 | 22.349 m | 21.906 m | — | — |
| 1 | 21.117 m | 21.199 m | $+5.51\%$ | $+3.23\%$ |
| 3 | 19.801 m | 19.657 m | $+11.40\%$ | $+10.27\%$ |
| 5 | 19.434 m | 19.072 m | $+13.04\%$ | $+12.94\%$ |
| 10 | **19.027 m** | **18.968 m** | $+14.87\%$ | $+13.41\%$ |

**The confound does not materialise.** History helps monotonically under both regimes, and per-depth tuning buys at most $0.44\,\text{m}$ — at $h=1$ it is slightly negative, which is tuning noise (the tuned configuration won on validation users and lost on test users). The history gain is therefore not a capacity artifact, and no "provided the model is re-tuned" qualifier is needed for this campaign.

---

## 6. Results II — The Cross-Model Scorecard

All models below are evaluated under one identical protocol: Campaign B, $h=5$, 300 users, user-disjoint 80/20 split, seed 42, realistic $85/15$ hardware mix.

| Model | History | Params | Train time | 2D MAE | P50 | P90 | Multi-ant (85%) | Single-ant (15%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| $k$-NN regressor (baseline) | $h=0$ | — | 0.0 s | 27.857 m | 23.892 m | 53.323 m | 25.356 m | 37.142 m |
| Random Forest | $h=5$ | 6.5 M | 121.1 s | 20.884 m | 16.801 m | 41.326 m | 16.032 m | 38.904 m |
| XGBoost | $h=5$ | 12.8 K | 26.0 s | 19.314 m | 15.469 m | 37.425 m | 15.199 m | 34.598 m |
| **GRU (2-layer)** | $h=5$ | 187.8 K | 255.0 s | **18.518 m** | **14.560 m** | 37.313 m | **14.500 m** | 33.440 m |
| 1D-CNN (NB06) | $h=5$ | 66.5 K | 333.1 s | 19.330 m | 15.430 m | 37.841 m | 15.394 m | 33.946 m |
| 1D-CNN + attention (NB07) | $h=5$ | 199.7 K | 231.2 s | 19.172 m | 15.377 m | 37.744 m | 15.233 m | 33.801 m |
| Mask-aware 1D-CNN | $h=5$ | 66.7 K | 173.2 s | 19.250 m | 15.959 m | 37.713 m | 15.713 m | **32.383 m** |

**Readings:**

1. **Deep temporal models lead, but not by much.** GRU is best overall at $18.518\,\text{m}$; the CNN variants cluster at $19.2$–$19.3\,\text{m}$. Recurrent gates and 1D convolutions extract motion derivatives that axis-aligned tree splits struggle to express.
2. **XGBoost is the deployment recommendation.** $19.314\,\text{m}$ MAE with **12.8 K parameters and 26 s of training** — within $4\%$ of the best deep model at roughly $1/15$ the parameters and $1/10$ the training time. For BS-edge compute this is the operating point that matters. This is also the practical form of the universality claim: you do not need a large model to collect the history gain.
3. **Random Forest is the outlier.** At $20.884\,\text{m}$ with 6.5 M parameters it is both the largest and the weakest of the $h=5$ models, and it is the *only* model whose single-antenna error ($38.904\,\text{m}$) is worse than the $h=0$ $k$-NN baseline's ($37.142\,\text{m}$). Axis-aligned splits on stacked lag features apparently fragment rather than integrate the temporal signal.
4. **The snapshot baseline is far behind.** $k$-NN at $h=0$ gives $27.857\,\text{m}$; every $h=5$ model beats it by $7$–$9\,\text{m}$. Part of that is model capacity, but §5.1 isolates the history component within a single fixed architecture.
5. **The cohort columns diverge everywhere.** In every row, multi-antenna error is $14.5$–$16.0\,\text{m}$ and single-antenna error is $32.4$–$38.9\,\text{m}$. No architecture closes this gap, because it is not an architectural gap. That is §7.

---

## 7. Results III — Error Decomposition and Physical Limits

### 7.1 The hardware cohort discontinuity

| Cohort | Share | AoA capability | 2D MAE | P50 | P90 |
| :--- | :---: | :--- | :---: | :---: | :---: |
| 4-antenna UEs | $\approx45\%$ | full az + el | 14.843 m | 12.607 m | 28.555 m |
| 2-antenna UEs | $\approx40\%$ | full az + el | 14.371 m | 12.074 m | 28.020 m |
| **Multi-antenna combined** | **85%** | complete | **14.580 m** | **12.310 m** | **28.250 m** |
| **1-antenna UEs (IoT/budget)** | **15%** | **none** | **34.538 m** | **30.232 m** | **65.991 m** |
| 100% multi-ant dedicated model | 100% | complete | 15.507 m | 13.342 m | 29.288 m |

This is a $2.3\times$ discontinuity, and it is **not a gradient in antenna count** — 2-antenna and 4-antenna devices are statistically indistinguishable ($14.37$ vs $14.84\,\text{m}$). The break is binary: $N_{ant}\ge2$ (bearing observable) versus $N_{ant}=1$ (bearing unobservable). Reporting a single population mean of $\approx19.3\,\text{m}$ therefore describes no actual device: it is a mixture of two well-separated modes.

**Operational consequence.** For a modern smartphone on this network the honest accuracy figure is $\approx14.6\,\text{m}$ mean / $12.3\,\text{m}$ median. For an AoA-blind IoT device it is $\approx34.5\,\text{m}$. Publishing only the blend understates the former by $\approx25\%$ and overstates the latter by $\approx44\%$.

Interestingly, a model trained and tested *exclusively* on multi-antenna users performs slightly **worse** ($15.507\,\text{m}$) than the multi-antenna slice of the mixed-population model ($14.580\,\text{m}$). The mixed population apparently acts as a regularizer, forcing the network to learn a robust RSS-range estimator that also benefits AoA-capable devices.

![Figure 3: Per-cohort error CDF](../figures/antenna_cohort_error_cdf.png)
*Figure 3 — Per-antenna-cohort error CDFs. The multi-antenna and single-antenna distributions are separated across their entire support, not merely in the tail; over $34\%$ of multi-antenna steps land within $10\,\text{m}$.*

### 7.2 Angular tracking audit — capability, not corruption

| Cohort | Mean angular error | P90 angular | 2D MAE |
| :--- | :---: | :---: | :---: |
| 4-antenna | $3.53^\circ$ | $7.08^\circ$ | 15.50 m |
| 2-antenna | $3.69^\circ$ | $7.61^\circ$ | 15.23 m |
| 1-antenna | $15.76^\circ$ | $33.94^\circ$ | 33.80 m |

![Figure 4: Angular tracking, multi vs single antenna](../figures/diagnostic_angular_tracking_multi_vs_single.png)
*Figure 4 — Azimuth tracking from the serving BS. Multi-antenna UEs hold a tight 1:1 alignment; single-antenna UEs collapse entirely, because dummy $(0^\circ,0^\circ)$ input carries no directional observability.*

The single-antenna estimator predicts **range correctly and bearing not at all** — the error smears along the arc of the correct distance ring. This is the distance-ring ambiguity, observed directly and in isolation, in a real cohort. It validates the central premise of the work from the negative direction: remove the bearing information and the ambiguity returns in full.

### 7.3 Outlier audit — is the data bad?

An automated audit over all unseen test users:

| Rank | User | Antennas | Samples | 2D MAE | P50 | P90 | Mechanism |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| Worst 1 | 134 | **1** | 724 | 52.87 m | 56.60 m | 79.48 m | zero AoA, ring smearing |
| Worst 2 | 275 | **1** | 694 | 46.45 m | 45.21 m | 78.98 m | zero AoA, ring smearing |
| Worst 3 | 138 | **1** | 584 | 38.99 m | 39.34 m | 64.03 m | zero AoA, ring smearing |
| Worst 4 | 100 | **1** | 615 | 37.42 m | 32.87 m | 64.89 m | zero AoA, ring smearing |
| Worst 5 | 250 | **1** | 529 | 33.50 m | 30.16 m | 58.35 m | zero AoA, ring smearing |
| Best 1 | 119 | 2 | 530 | 10.42 m | 10.23 m | 16.15 m | precise AoA alignment |
| Best 2 | 211 | 2 | 697 | 11.34 m | 10.06 m | 20.47 m | precise AoA alignment |
| Best 3 | 279 | 2 | 645 | 11.59 m | 9.91 m | 21.62 m | precise AoA alignment |
| Best 4 | 265 | 4 | 725 | 11.68 m | 9.92 m | 22.71 m | precise AoA alignment |
| Best 5 | 72 | 4 | 699 | 11.82 m | 10.17 m | 21.23 m | precise AoA alignment |

**$100\%$ of the worst five are single-antenna; $100\%$ of the best five are multi-antenna.** The tail is fully explained by a known hardware capability, with no residual unexplained outliers.

Two further audits confirm the data is sound:

* **Voronoi boundary crossings.** Within-cell $19.34\,\text{m}$ vs. crossing $18.33\,\text{m}$ — crossings are, if anything, marginally *easier*. QuaDRiGa spatial consistency prevents transient discontinuities, so scenario changes are not corrupting the sequences.
* **Sharp direction reversals.** Straight ($<30^\circ$ turn) $18.74\,\text{m}$; moderate ($30$–$90^\circ$) $20.14\,\text{m}$; sharp ($\ge90^\circ$) $22.02\,\text{m}$, a $+3.29\,\text{m}$ penalty. This is a *predicted* consequence of the mechanism, not a defect: a reversal invalidates the heading evidence in the window, so a history-based estimator must briefly lag. (An earlier draft of this section claimed attention layers and RTS smoothing partially compensate. Neither claim is supported by the recorded results — see §7.7 for what the smoother actually does — and both are withdrawn.)

![Figure 5: Best-case trajectory](../figures/diagnostic_BEST_user_119_ant2.png)
*Figure 5 — User 119 (2-antenna, $10.42\,\text{m}$ MAE). Left: ground truth (black), 1D-CNN prediction (blue), and the RTS-smoothed path (green) produced with the notebook's default filter settings. Right: per-step error and model uncertainty, stable at $\approx10\,\text{m}$. Note that the smoothed track is shown for continuity with the source notebooks; at these settings smoothing *increases* population MAE (§7.7).*

![Figure 6: Worst-case trajectory](../figures/diagnostic_WORST_user_250_ant1.png)
*Figure 6 — User 250 (1-antenna, $33.50\,\text{m}$ MAE). Range is tracked correctly; predictions smear along the arc. The failure is geometric, not statistical.*

### 7.4 Spatial structure

**Propagation regime:**

| Regime | Zones | Test samples | 2D MAE | P50 | P90 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| LOS | Park (UMi_LOS), Highway (RMa_LOS) | 21,707 (73%) | 19.401 m | 15.664 m | 38.651 m |
| NLOS | Shopping (UMi_NLOS), Residential (mixed) | 7,862 (27%) | **18.868 m** | **14.204 m** | **36.442 m** |

**NLOS outperforms LOS.** This is counter-intuitive under a naive "NLOS is harder" assumption, and it is a direct corollary of §3.2: rich multipath gives each position a distinctive channel signature that breaks the ring symmetry, whereas open LOS gives a clean monotone range map and nothing else. Under AoA noise, the LOS geometry is the ambiguous one. This result deserves prominence — it is the clearest evidence that the limiting factor here is *observability of bearing*, not *channel quality*.

**Range to serving BS:**

| Zone | Range | Samples | 2D MAE | P50 | P90 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| Near | $<40\,$m | 1,200 | **13.186 m** | **9.861 m** | **23.845 m** |
| Mid | $40$–$80\,$m | 7,898 | 19.093 m | 16.381 m | 37.516 m |
| Far | $80$–$120\,$m | 16,547 | 18.368 m | 14.122 m | 36.148 m |
| Corner | $>120\,$m | 3,924 | 25.212 m | 21.969 m | 45.538 m |

Error grows with range as angular uncertainty translates into linear uncertainty: at $R=120\,\text{m}$, a $5^\circ$ AoA error subtends $R\tan5^\circ \approx 10.5\,\text{m}$ of cross-range displacement. The corner zone's $25.2\,\text{m}$ is therefore close to a geometric floor for this BS placement, not a modelling failure. (Mid slightly exceeding Far is likely a composition effect of unequal sample counts and zone mix; worth confirming before publication.)

### 7.5 Why Campaign B is two orders of magnitude harder than Campaign A

The two campaigns report wildly different numbers — Campaign A reaches $0.39\,\text{m}$ MAE with its best configuration, Campaign B's best model reaches $18.5\,\text{m}$. Taken side by side without explanation that looks like a collapse. It is not: the two are measuring different tasks at different scales under different generalization demands. This section enumerates the gaps and then shows, by decomposing the error geometrically, which of them actually account for the difference.

#### The eight differences

| # | Axis | Campaign A | Campaign B | Factor |
| :---: | :--- | :--- | :--- | :--- |
| 1 | Task | classification, 225 cells | continuous regression | error quantised vs. not |
| 2 | Service area | $28 \times 28\,\text{m}$ = $784\,\text{m}^2$ | $96 \times 96\,\text{m}$ = $9{,}216\,\text{m}^2$ | $\mathbf{11.8\times}$ |
| 3 | Range to serving BS | $0$–$19.8\,\text{m}$ (centre BS) | $21.2$–$157.0\,\text{m}$, mean $93.2$ | $\mathbf{\approx 9\times}$ |
| 4 | Grid pitch | $2\,\text{m}$ | $4\,\text{m}$ | $2\times$ coarser |
| 5 | Generalization | same users, same cells, later timesteps | **disjoint users**, unseen trajectories and devices | zero-shot |
| 6 | Device population | 5 fixed profiles, all seen in training | 232 users, gain $-3.97$ to $+1.99\,\text{dB}$, height $0.80$–$1.80\,\text{m}$, $N_{ant} \in \{1,2,4\}$ | continuous, unseen |
| 7 | Training density | $\approx1{,}600$ samples per cell | $178$ samples per cell (median) | $\mathbf{9\times}$ sparser |
| 8 | Mobility | uniform $1.5\,\text{m/s}$ random walk | 4 patterns, $0.12$–$14.89\,\text{m/s}$ | $\Delta t$ spans $0.27$–$32.5\,\text{s}$ |

Two further differences work *in Campaign B's favour* and so cannot explain the gap: its AoA impairment is milder (fixed $4^\circ$ + $5^\circ$ quantisation, against Campaign A's SINR-dependent $1$–$20^\circ$), and all 625 cells are covered in training with no test sample falling in an unvisited cell.

#### Decomposing the error: it is range, not bearing

Splitting Campaign B's XGBoost error into the component along the BS bearing (range error) and the component perpendicular to it (bearing error) separates the two cohorts cleanly:

| Cohort | Total | Radial (range) | Tangential (bearing) | Radial share of variance |
| :--- | ---: | ---: | ---: | ---: |
| All users | 19.43 m | 14.93 m | 9.14 m | 73% |
| **Multi-antenna** | 15.29 m | **13.69 m** | 4.71 m | **89%** |
| **Single-antenna** | 34.81 m | 19.53 m | **25.60 m** | 37% |

This is the central diagnostic of the whole study, and it reverses the naive reading:

* **For the 85% multi-antenna cohort, bearing is essentially solved.** Tangential error is $4.71\,\text{m}$, which matches the geometric prediction from the measured $3.5^\circ$ angular error at the mean range of $93.2\,\text{m}$: $R\tan(3.5^\circ) = 5.70\,\text{m}$. The distance-ring ambiguity is *not* what limits modern handsets. **$89\%$ of their error is range error.**
* **For the 15% single-antenna cohort the opposite holds.** Tangential error is $25.60\,\text{m}$, against a geometric prediction of $R\tan(15.8^\circ) = 26.36\,\text{m}$. The agreement is close enough to say the failure is purely geometric: these devices estimate range acceptably and have no bearing information at all. This is the distance-ring ambiguity, isolated.

#### Why range error explodes with scale

Range is inferred from path loss, and the sensitivity of RSS to range falls off as $1/r$:

$$\frac{d\,\text{RSS}}{dr} = \frac{10\gamma}{r \ln 10} \quad \text{dB/m}$$

Under $\gamma = 4$ and $6\,\text{dB}$ shadow fading, the implied $1\sigma$ range uncertainty is:

| Operating range | dB per metre | $\sigma_{\text{range}}$ |
| :--- | ---: | ---: |
| Campaign A, centre BS (~$10\,\text{m}$) | 1.737 | $3.5\,\text{m}$ |
| Campaign A, NE BS (~$40\,\text{m}$) | 0.434 | $13.8\,\text{m}$ |
| Campaign B, $p_{10}$ ($56\,\text{m}$) | 0.309 | $19.4\,\text{m}$ |
| **Campaign B, median ($95\,\text{m}$)** | **0.182** | **$32.9\,\text{m}$** |
| Campaign B, $p_{90}$ ($126\,\text{m}$) | 0.138 | $43.6\,\text{m}$ |

At Campaign B's median range, one metre of displacement changes RSS by $0.18\,\text{dB}$ — far below the shadow-fading noise floor. The measured multi-antenna radial error of $13.69\,\text{m}$ is in fact *substantially better* than the $32.9\,\text{m}$ this naive bound predicts, which is itself evidence that history, SINR and elevation are contributing real range information beyond raw path loss.

#### What this means for the history result

The $9\times$ range increase and the switch to continuous regression account for most of the absolute gap; the zero-shot user split and the $9\times$ sparser training density account for much of the rest. None of them undermine the mechanism claim, because **$\Delta\text{MAE}$ is measured within each campaign against that campaign's own $h=0$ baseline**. History delivers $+22$ to $+29$ pp in Campaign A and $13$–$15\%$ in Campaign B; the two are not expected to be equal, and the comparison that matters is each against its own control.

It does, however, sharpen the framing. The mechanism is introduced as resolving the distance-ring ambiguity, and for AoA-blind devices that is exactly what the decomposition shows it doing. For AoA-capable devices at macro range, bearing is already resolved and history's contribution is mostly to **range** estimation — through the radial path-loss derivative $d\text{RSS}/dt$, which is observable from a sequence and not from a snapshot. Both are the same mechanism supplying the missing degree of freedom; which degree of freedom is missing depends on the hardware.

### 7.6 Architectural mitigation: explicit AoA validity masking

**Problem.** Feeding dummy $(0^\circ,0^\circ)$ AoA to AoA-blind devices is not neutral. The derived features compute $\cos(0^\circ)=1.0$ and $\text{ray}_y = r_{est}\cos(0^\circ) = r_{est}$, which asserts a *confident* bearing along the positive-$y$ (north-east) axis. The network is not merely uninformed about these devices, it is actively misinformed, and the false anchor also pollutes shared convolutional kernels via gradients.

**Fix (Option A).** For $\texttt{has\_valid\_aoa}=0$:

1. Zero the trigonometric embeddings: $(\sin\theta,\cos\theta)=(0,0)$. Since $\sin^2\theta+\cos^2\theta=0 \ne 1$, this point lies strictly off the unit circle of physically realizable angles, so the filters can learn to distinguish "no angle" from "angle $=0^\circ$" — which they cannot do with the dummy encoding.
2. Zero the geometric ray projections $(\text{ray}_x,\text{ray}_y)=(0,0)$.
3. Add an explicit binary `has_valid_aoa` channel to both the temporal sequence and the static device embedding.

**Result:**

| Metric | Unmasked | Masked (Option A) | $\Delta$ | Improvement |
| :--- | :---: | :---: | :---: | :---: |
| Overall 2D MAE | 19.269 m | **18.866 m** | $-0.403$ m | **2.09%** |
| Multi-antenna (85%) | 15.408 m | **15.279 m** | $-0.129$ m | 0.84% |
| Single-antenna (15%) | 33.607 m | **32.188 m** | $-1.419$ m | **4.22%** |
| Single-antenna angular error | $15.84^\circ$ | **$14.83^\circ$** | $-1.01^\circ$ | better range/angle decoupling |

Both cohorts improve. The single-antenna gain is the intended effect — with the false anchor removed the network optimizes range purely from path-loss gradients. The multi-antenna gain is a side effect worth naming: **cross-cohort gradient protection**, i.e. corrupted single-antenna gradients were degrading the shared kernels that multi-antenna devices also use. The cost is one extra input channel and $0.2\,\text{K}$ parameters.

### 7.7 Kinematic post-processing: a defective time base, not a useless filter

> **Status: results being regenerated.** The investigation below uncovered a defect
> in the feature pipeline that invalidates every smoothing number previously
> recorded — including the master benchmark's, and including the re-tuning sweeps
> described later in this section. The defect and its fix are documented here
> because the diagnosis stands; the numeric tables are being re-run against the
> corrected time base and must not be cited until they are replaced.

**The defect.** `DerivedCSI1DDataset` standardises `SIGNAL_COLS` in place, and
`delta_t` is one of those columns — it is legitimately a model input. But the
per-sample `delta_t` handed downstream to the Kalman/RTS smoother was read out of
the frame *after* that standardisation, so the smoother received z-scores rather
than seconds:

| | min | max | mean | negative |
| :--- | ---: | ---: | ---: | ---: |
| `delta_t` in the dataframe (seconds) | 0.267 | 32.491 | 3.231 | 0 |
| `delta_t` handed to the smoother | −0.632 | 4.778 | 0.000 | **25,370 (85.8%)** |

`run_kalman_and_rts_2d` guards with `dt = max(0.01, dt)`, so **85.8% of all steps
were assigned a 0.01 s time step**. The state-transition matrix
$F = \begin{psmallmatrix}1&0&dt&0\\0&1&0&dt\\0&0&1&0\\0&0&0&1\end{psmallmatrix}$
and the process-noise term $Q = \operatorname{diag}(q\,dt^2, q\,dt^2, q, q)$ are
both functions of $dt$, so the filter was propagating a motion model over
essentially zero elapsed time while the UE actually moved metres between samples.
That is sufficient on its own to explain a large, uniform degradation.

**This also resolves the three-way discrepancy.** The July XGBoost and Random
Forest sweeps did not use `DerivedCSI1DDataset`; they built features through
`build_history_features` and read `delta_t` from an unnormalised frame, so their
time base was correct — and they recorded smoothing behaving sanely ($+3.6\%$
falling to $-0.1\%$ as the estimator improves, which is exactly what a smoother
should do). The master benchmark went through the dataset class and recorded
$-28\%$ to $-48\%$. The two pictures were never in conflict about the filter; they
differed in whether the filter was given real seconds.

**The fix** (`utils/csi_dataset.py`) captures `delta_t` in seconds before
standardisation and hands that to the smoother, leaving the normalised channel
untouched as a model input. Verified after the fix: time steps range 0.269–32.491 s
with no negatives, and the 13-channel input tensor is unchanged.

The remainder of this section records the pre-fix investigation. Its
*qualitative* finding — that a single global process noise cannot serve a
population spanning $0.1$ to $15\,\text{m/s}$ — is unaffected by the defect and is
being re-tested directly, alongside a per-user $q_u \propto v_u$ variant.

#### Corrected results

With the time base repaired, the smoother behaves as kinematic post-processing should. Re-running all six families at $h=5$ (10 process-noise values $	imes$ 6 measurement-noise values each):

| Model | Raw MAE | RTS at notebook default ($Q{=}0.5$, $R{=}15$) | Best RTS found | Best $Q$ |
| :--- | ---: | ---: | ---: | :---: |
| $k$-NN | 23.983 m | 21.501 m ($+10.35\%$) | 21.330 m ($+11.06\%$) | 1.0 |
| Random Forest | 19.417 m | 19.759 m ($-1.77\%$) | 18.933 m ($+2.49\%$) | 4.0 |
| XGBoost | 19.434 m | 19.366 m ($+0.35\%$) | 18.588 m ($+4.35\%$) | 2.0 |
| 1D-CNN | 19.076 m | 19.095 m ($-0.10\%$) | 18.380 m ($+3.65\%$) | 4.0 |
| GRU | 19.258 m | 19.296 m ($-0.20\%$) | 18.543 m ($+3.72\%$) | 2.0 |
| 1D-CNN + attention | 18.857 m | 18.714 m ($+0.76\%$) | 17.964 m ($+4.74\%$) | 4.0 |

Three things change relative to the defective run:

1. **The default settings are roughly neutral, not catastrophic.** They range from $-1.8\%$ to $+10.4\%$ rather than $-28\%$ to $-48\%$. The published $-44\%$ figures were measuring the broken time base, nothing else.
2. **The optimum moved from $Q pprox 128$ to $Q pprox 1$–$4$.** With a correct $dt$ the filter needs only modest process noise; the enormous $Q$ the defective run preferred was compensating for a state transition that assumed $0.01\,	ext{s}$ had elapsed.
3. **The gain now shrinks as the estimator improves** — $+11\%$ for $k$-NN at $23.98\,	ext{m}$ down to $+3.7\%$ for the GRU at $19.26\,	ext{m}$ — which is the expected behaviour of a smoother and matches what the July sweeps recorded ($+3.6\%$ decaying to $-0.1\%$). All three pictures in the record are now consistent.

Properly configured, kinematic post-processing is worth **$2.5\%$ to $4.7\%$** on the trained models. That is a real but secondary effect next to the $13$–$15\%$ from transition history, and it is complementary: history operates inside the estimator, smoothing outside it.

#### A single global process noise is the wrong model

The population spans $0.12$ to $14.89\,	ext{m/s}$ (§4.3), yet $Q$ is applied globally. The same $q$ is simultaneously too tight to track a manoeuvring vehicle and too loose for a near-static user. Scaling process noise by each user's own speed, $q_u = k \cdot v_u$, beats the best global setting for every model tested:

| Model | Best global $Q$ | Best per-user $q_u = k v_u$ | Gain from going per-user |
| :--- | ---: | ---: | ---: |
| $k$-NN | $+11.06\%$ ($Q{=}1$) | $+13.52\%$ ($k{=}0.3$) | $+2.5$ pp |
| Random Forest | $+2.46\%$ ($Q{=}4$) | $+3.20\%$ ($k{=}0.5$) | $+0.7$ pp |
| XGBoost | $+4.35\%$ ($Q{=}2$) | $+5.66\%$ ($k{=}0.3$–$0.5$) | $+1.3$ pp |

Both grids were extended until the optima were interior rather than at a boundary, so these are located optima and not grid-edge artifacts. The change is small and physically motivated — the filter's assumed manoeuvre magnitude should scale with how fast the target actually moves — and it is free at inference time, since $v_u$ is already estimated by the model's own speed head.

It also reinforces the report's central theme from a second direction: population *heterogeneity* is what must be modelled explicitly, whether the axis is antenna count (§7.1, §7.6) or speed. A single global constant is the wrong object in both cases.

**Caveat.** These are oracle settings: $Q$, $R$ and $k$ were selected on the same test users they are evaluated on. The comparison between global and per-user is fair — both were tuned identically — but the absolute gains are optimistic and a deployed system would need the constants fixed in advance or fitted on training users.


---

## 8. Discussion

**What the evidence supports.** History reduces error in every model family tested, at every grid size tested, under both BS placements tested, in both task formulations, and — unlike AoA — its benefit does not collapse when the deployment geometry degrades. The marginal-gain profile ($44\%$ of the total from the single first extra frame) matches the velocity-observability account rather than a generic "more features help" account, which would predict a smoother, more monotone curve.

**What the evidence does not support.** We do not claim state-of-the-art absolute accuracy; $14.58\,\text{m}$ for multi-antenna devices at $100\,\text{m}$ range is respectable for single-BS operation but is not competitive with multi-BS or UWB systems. We also do not claim the gain is unbounded in $h$ — it demonstrably is not.

**The non-monotonicity belongs to the estimator, not to the physics.** §5.4 shows the turn at $h=10$ appears for the 1D-CNN and $k$-NN and not for tree ensembles, on the same data. An account resting on heading decorrelation alone cannot explain that split, since all families see identical trajectories. The architectural account — fixed-window consumers cannot ignore a stale lag, tree ensembles can — does explain it, and it predicts that any estimator with implicit feature selection should keep improving with depth until the feature count itself becomes the binding constraint.

**On the tree-ensemble anomaly.** Earlier runs contained configurations where added history degraded XGBoost and Random Forest, which raised the possibility that the history gain was confounded with model capacity. §5.5 tested this directly and **the anomaly does not reproduce on Campaign B**: history helps XGBoost monotonically whether or not each depth gets its own hyperparameters, and re-tuning is worth at most $0.44\,\text{m}$. The degradation documented in the tuned 25×25 regression study (`technical_documentation.md` §7.4, where Random Forest `BASE` at $9.664\,\text{m}$ beats `BASE_H3` at $11.732\,\text{m}$) is therefore specific to Random Forest under that task formulation, not a general property of tree ensembles, and the report's own explanation there — static features are physically unique per coordinate, so splitting on lags fragments the sample without adding information — remains the best account. The Random Forest row in §6 ($20.884\,\text{m}$, and the worst single-antenna error in the table) is consistent with the same weakness.

**Deployment guidance.** From Campaign A's placement study plus Campaign B's cost/accuracy profile:

| Scenario | Recommended configuration |
| :--- | :--- |
| Center/overhead BS, diverse devices | full set: history + AoA + device params |
| Center BS, unknown device | history + AoA |
| Edge/corner-mounted BS | history + device params — AoA contributes little at narrow angular spread |
| No AoA hardware in the population | history alone; masking channel mandatory |
| BS-edge compute constrained | XGBoost at $h=5$: $96\%$ of best-model accuracy, $12.8\,$K params |

---

## 9. Limitations and Threats to Validity

1. **Simulation only.** All results are QuaDRiGa TR 38.901. Spatial consistency — the precondition for the entire mechanism — is a model property here; real channels exhibit it but with additional non-stationarity, hardware impairments, and calibration drift. Field validation is not yet performed.
2. **Synthetic mobility.** Campaign B's four patterns (§4.3) are heading-persistent and speed-diverse, so unlike Campaign A they are not adversarial to history — but they are still generated on an 8-connected grid graph, not drawn from measured traces. Real mobility has road geometry, stop-and-go dynamics, and dwell behaviour that none of the four patterns reproduce.
3. **A fixed $h$ is not a fixed time window.** Because speed varies by two orders of magnitude and step duration is $\text{spacing}/v$, the $h=5$ window spans $1.3\,\text{s}$ to $162\,\text{s}$ across users (§4.3). Every history result is therefore an average over widely different temporal horizons, and per-speed-class sweeps would be needed to separate "how many samples" from "how much elapsed time". This is the most significant unexamined confound in the study.
4. **Cohort mix is assumed, not measured.** The $85/15$ split is a 3GPP-representative assumption; results are sensitive to it, which is exactly why §7.1 reports the components separately.
5. **Two campaigns differ in more than scale.** Carrier frequency, grid spacing, task formulation, and split protocol all differ between A and B, so cross-campaign numbers are not directly comparable — only within-campaign $\Delta$'s are.
6. **Single interference geometry per campaign.** SINR informativeness depends on interferer placement; only one configuration per campaign was swept.
7. **Statistical reporting.** Results are single-seed point estimates. Confidence intervals over repeated seeds are needed before publication, particularly for the smaller deltas (§5.2's $+2.2\%$ and §7.6's $+0.84\%$).

---

## 10. Conclusion and Future Work

Single-BS CSI localization is limited by an observability problem, not primarily a modelling problem: a static RSS snapshot determines range and leaves bearing free. This work shows that a short window of transition history supplies the missing constraint, that the benefit appears across four algorithmic paradigms and seven estimators, and that it survives the deployment geometry change ($360^\circ \to 52^\circ$ angular spread) that reduces AoA's contribution by an order of magnitude. The mechanism is a drop-in input transformation: no new sensor, no UE cooperation, no second estimator.

The same lens explains the population's error structure. Devices that can observe bearing directly reach $14.58\,\text{m}$ MAE; devices that cannot plateau at $34.54\,\text{m}$, with $100\%$ of severe outliers drawn from that cohort and a failure mode that is visibly arc-shaped. Reporting these separately, and encoding "angle unavailable" honestly rather than as $0^\circ$, is worth $1.42\,\text{m}$ to the blind cohort at essentially zero cost.

**Priority follow-ups, in order:**

1. **Disentangle history depth from elapsed time.** Sweep $h$ *within* each speed class, so that "six samples" and "thirteen seconds" stop being confounded (§9.3). This is now the highest-value experiment, because every history number in the report is currently averaged over a $1.3$–$162\,\text{s}$ spread of temporal horizons.
2. **Resolve the smoothing discrepancy** (§7.7) across all model families, then either adopt re-tuned kinematic post-processing or report it as a clean negative result. Three inconsistent pictures currently exist in the record.
3. **A targeted LOS→blocked→LOS scenario**: a UE walking a straight sidewalk past a blocking building. This isolates the case where history should be decisive — the estimator can localize the blocked interval using evidence from $t\pm k$. It also connects naturally to non-causal (smoothed) operation, which is legitimate for many use cases.
4. **Seed-repeated runs with confidence intervals** on all reported deltas.
5. **Extend the depth sweep past $h=10$ for tree ensembles**, which had not saturated at the deepest window tested (§5.4) — the true optimum for that family is still unknown.
6. **Field or measured-trace validation.**

---

## Appendix A — Reproducibility

| Asset | Path |
| :--- | :--- |
| 1D-CNN baseline notebook | `src/python/notebooks/Multi-User-Environment/06_cnn_h5_derived_features.ipynb` |
| CNN + attention notebook | `src/python/notebooks/Multi-User-Environment/07_cnn_attn_h5_derived_features.ipynb` |
| Dataset / feature utilities | `src/python/utils/csi_dataset.py` (`build_derived_features`, `load_and_prepare_data`, `DerivedCSI1DDataset`) |
| Training utilities | `src/python/utils/training_utils.py` (`EarlyStopping`, `run_kalman_and_rts_2d`, `collect_test_predictions`) |
| Environment analysis | `src/python/utils/environment_viz.py` |
| Simulation engine | `src/matlab/core/generate_simulation_data.m` |
| Configs | `experiments/09_grid_localization/configs/*.jsonc` |
| Figures | `docs/figures/` |
| Detailed results of record | `docs/Project_documentation/technical_documentation.md` §7–9 |
| Revision | branch `main` — `git log -1 -- experiments/09_grid_localization/` |

Seeds: global seed 42; per-user walk seeds distinct per profile. Simulation results live under `results/` and are gitignored — regenerate from the runners in `src/matlab/runners/`.

## Appendix B — Model hyperparameters

**XGBoost:** `n_estimators=50`, `max_depth=5`, `learning_rate=0.15`, `subsample=0.8`, `colsample_bytree=0.8`, `random_state=42`.

**Random Forest:** `n_estimators=150`, `max_features='sqrt'`, `max_depth=16`, `min_samples_leaf=5`, `random_state=42` (Optuna, 30 trials, TPE, 30% subsample).

**Deep models:** early stopping on validation loss; GRU 2 layers (187.8 K params); 1D-CNN (66.5 K); CNN + attention (199.7 K); mask-aware CNN (66.7 K).

XGBoost tuning was attempted but the learning rate found on subsampled data did not transfer to the full training set; conservative defaults are used throughout. See §8 for why this matters.
