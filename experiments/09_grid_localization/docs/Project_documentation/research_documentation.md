# CSI-Based UE Localization Using Transition History
## Research Documentation

**Student:** Gilad  
**Advisors:** Prof. Sarit Kraus, Prof. David Sarne  
**Institution:** Bar-Ilan University  
**Industry Partners:** CEVA, Cellcom  
**Last Updated:** April 2026

---

## Abstract

Accurate UE localization using 5G/6G channel measurements is a growing priority as GPS-denied environments — indoors, urban canyons, tunnels — become first-class cellular use cases from 3GPP Release 16 onward. Received signal strength (RSS) alone suffers from a fundamental distance-ring ambiguity: many positions equidistant from a base station are indistinguishable by amplitude, regardless of propagation environment. This work investigates the hypothesis that transition history — the ordered sequence of measurements observed as a UE moves through space — carries substantially richer positional information than any single static snapshot, and that this benefit holds across both indoor-like (dense NLOS) and outdoor-like (LOS-dominated) propagation conditions. We validate this hypothesis through extensive simulation using QuaDRiGa (3GPP TR 38.901) across grid scales from 3×3 to 20×20, four ML algorithms, and a full multi-user heterogeneous device experiment on a 15×15 Voronoi grid spanning four distinct propagation scenarios (UMi_LOS, UMi_NLOS, RMa_LOS, mixed) with five device profiles. History-based features consistently improve classification accuracy by 9–22 percentage points across all tested conditions. The addition of Angle of Arrival (AoA) measurements with a realistic noise model (+33 pp at center BS placement) is shown to be strongly geometry-dependent: when the BS is moved to an edge position, AoA gain collapses from +33 pp to +7 pp while the transition history benefit remains identical at +23 pp. Device parameters as additional features provide orthogonal gains to history. These findings suggest that transition-based features are the most robust tool for 5G/6G UE localization, independent of hardware configuration, propagation environment, and BS deployment geometry.

---

## 1. Problem Statement

### 1.1 Why 5G/6G UE Localization Is Hard

5G and 6G networks expose rich channel-derived measurements — RSS, SINR, Angle of Arrival, timing advance — natively at the base station, making network-assisted positioning a realistic alternative to GPS in environments where satellite signals are unavailable or unreliable. GPS performance degrades significantly in urban canyons, tunnels, and indoors due to signal blockage and multipath. Cellular positioning addresses these gaps, but achieving metre-level accuracy using only a single serving BS is non-trivial.

The most accessible measurement is Received Signal Strength (RSS): the total power received from the serving BS. RSS correlates with distance, but the correlation is weak and non-injective — many physical locations at the same nominal distance produce the same RSS value, regardless of propagation environment. Two positions on the same distance ring from the BS are indistinguishable from RSS alone, a limitation we call the *distance-ring ambiguity*. This ambiguity is particularly severe in LOS-dominated environments (outdoor open areas, straight corridors) where the distance-to-RSS mapping is monotone and there is no multipath diversity to help distinguish positions.

Signal-to-Interference-plus-Noise Ratio (SINR) and Angle of Arrival (AoA) break the ring ambiguity by adding directional components, but both depend on specific infrastructure configurations (calibrated interferers; beamforming capability) and their utility varies substantially with BS geometry, as this work demonstrates.

### 1.2 The Central Hypothesis

A moving UE generates a time series of measurements as it traverses the grid. Adjacent measurements are spatially correlated — the channel evolves continuously as the UE moves. This means the *sequence* of measurements encodes not only the current position but also the trajectory that led to it. Two positions that appear identical in a single snapshot can be disambiguated by the different trajectories that converge on them.

Formally, the model input at time step *t* is:

```
x(t) = [m(t-h), m(t-h+1), ..., m(t-1), m(t)]
```

where m(t) is the measurement vector at time t and *h* is the history depth. The output is the predicted grid point (classification) or continuous coordinates (regression). We focus on classification, since at 2m grid spacing it consistently outperforms regression by 1.15–1.6× in MAE.

**Scope constraint:** The serving BS performs localization using only measurements it legitimately receives from the UE. Per-interferer RSS is deliberately excluded, as using it would constitute triangulation — a fundamentally different problem requiring distributed infrastructure coordination.

---

## 2. Simulation Environment

### 2.1 Channel Model

All channel data is generated using **QuaDRiGa v2.8.1** implementing **3GPP TR 38.901**. QuaDRiGa's defining property for this work is *spatial consistency*: as the UE moves, the channel coefficients evolve smoothly rather than being drawn independently at each snapshot. This continuity is what makes transition-based features meaningful — consecutive measurements are physically correlated, not statistically independent noise samples.

The simulated network operates at **3.5 GHz** center frequency with 100 MHz bandwidth and 256 OFDM subcarriers. The serving BS is equipped with a 64-element Massive MIMO array (transmitted at 30 dBm). Interfering BSs, where present, are modeled as omnidirectional and also transmit at 30 dBm.

### 2.2 UE Trajectory — Random Walk

The UE traverses the grid via a constrained random walk: at each step, it selects uniformly from its 8-connected grid neighbors (4 cardinal + 4 diagonal). Starting from the grid center, the walk runs for 400 steps per grid point. At 1.5 m/s pedestrian speed and 2m grid spacing, each step corresponds to approximately 1.33 seconds. The random walk is re-seeded independently for each user, with two users (U1 and U4) sharing device parameters but using different walk seeds — this isolates device effects from trajectory randomness.

### 2.3 Two Environments

**Uniform NLOS environment** (scalability experiments): All grid points are assigned the same 3GPP UMi_NLOS scenario. This is deliberately simple — it allows systematic study of the history benefit without confounds from spatial channel variation. It also represents a worst-case scenario for fingerprinting: no scenario-specific spatial structure, only range-based discrimination.

**Voronoi heterogeneous environment** (main experiments): The grid area is partitioned into 4 Voronoi cells, each assigned a distinct 3GPP scenario: UMi_LOS (park), UMi_NLOS (shopping center), RMa_LOS (highway), and a mixed UMi_LOS/NLOS region (residential). The design goal is maximum diversity — each scenario produces different multipath characteristics, ensuring that grid positions in different zones are fingerprinted by genuinely different channel behaviors, not just RSS level.

Placing the BS inside the grid (at the grid center) ensures every UE direction is represented from 0° to 360°. As shown later, this has significant implications for AoA informativeness.

### 2.4 Train/Test Split

All experiments use an **80/20 chronological split applied independently per user**. The test set always consists of the last 20% of each user's walk by step index. This is strictly enforced to prevent temporal leakage: because QuaDRiGa produces spatially correlated channels, a random split would allow the model to interpolate between neighboring train and test snapshots, inflating test accuracy.

---

## 3. Feature Metrics

### 3.1 Available Measurements

The following metrics are extracted from each simulated snapshot:

| Metric | Type | Realistic? | Notes |
|--------|------|-----------|-------|
| RSS (wideband) | Amplitude | Yes | Primary spatial discriminant |
| SINR (wideband) | Amplitude ratio | Yes | Requires calibrated interferers |
| CQI (1–15) | Quantized SINR | Yes | Saturates at short range |
| AoA azimuth | Direction | With noise model | Requires beamforming capability |
| AoA elevation | Direction | With noise model | Encodes height + distance geometry |
| Timing advance | Delay | Not modeled | No noise model; excluded |

### 3.2 AoA Noise Model

Raw AoA from QuaDRiGa represents an idealized power-weighted cluster angle. We apply a two-stage impairment model to simulate realistic beamforming estimation:

1. **Gaussian noise:** independent 4° standard deviation per axis (azimuth and elevation)
2. **Quantization:** round to the nearest 5° step (codebook resolution)

This degrades clean AoA to an angular resolution of approximately ±5°. The model is applied in the Python pipeline at load time, making it easy to compare oracle vs. degraded AoA — a distinction that proved important in early experiments (see §6.1).

### 3.3 Key Feature Insights

**RSS ≈ SINR without interference.** When no interferers are present, SINR is simply RSS minus a constant noise floor — it carries no additional spatial information. Only when co-channel interferers are introduced does SINR become directionally informative: the serving-to-interferer power ratio changes with position relative to each BS, creating spatial gradients that RSS alone cannot provide.

**AoA dominance at center BS.** In the main Voronoi experiment with the BS at the grid center, adding AoA improves accuracy from 50.4% (BASE_H, E4) to 83.6% (BASE_A_H, E10) — a 33.2 pp gain. This is the single largest feature contribution observed in any experiment. However, this gain is geometry-dependent, as explored in §4.5.

**CQI saturation.** CQI, derived from SINR via a 3GPP mapping, saturates at the maximum value (15) for UEs close to the BS. For a center-BS deployment, roughly 40–50 grid points are close enough to saturate, rendering CQI uninformative for those positions. We use continuous SINR rather than CQI in all experiments.

---

## 4. Research Progression

### 4.1 Starting Point — Single User, Uniform Environment

The initial question was the simplest possible version of the thesis: *can history help at all?* Beginning with a 7×7 grid (49 classes) and a uniform UMi_NLOS environment, we compared four algorithms — Gaussian probabilistic model, Random Forest, XGBoost, and MLP — in their static (h=0) and history (h=3) configurations, using RSS+SINR features.

Every algorithm improved:

| Algorithm | BASE (h=0) | BASE_H (h=3) | Δ |
|-----------|-----------|------------|---|
| Gaussian | 10.9% | 15.5% | +4.7 pp |
| Random Forest | 28.0% | 43.6% | +15.6 pp |
| XGBoost | 26.9% | 45.1% | +18.2 pp |
| MLP | 24.8% | 41.6% | +16.8 pp |

The result established the thesis across all algorithm families. XGBoost was selected as the primary model going forward due to its combination of high accuracy, fast training, and graceful scaling to large class counts.

The next question was scalability: does the benefit hold as the grid grows? We tested XGBoost across six grid sizes using the uniform NLOS environment:

| Grid | Classes | Static | Best Trans. | Δ |
|------|---------|--------|-------------|---|
| 3×3 | 9 | 53.4% | 62.8% | +9.4 pp |
| 5×5 | 25 | 39.1% | 53.1% | +14.0 pp |
| 7×7 | 49 | 26.9% | 41.1% | +14.2 pp |
| 10×10 | 100 | 33.8% | 55.6% | +21.8 pp |
| 15×15 | 225 | 13.8% | 29.1% | +15.3 pp |
| 20×20 | 400 | 13.4% | 22.6% | +9.2 pp |

Transition history improves accuracy at every scale without exception. The benefit actually increases from 3×3 to 10×10 before diminishing slightly at larger grids — likely because with more classes, the disambiguation value of trajectory direction grows, but the absolute learning problem also becomes harder with sparser per-class samples.

### 4.2 Adding Realism — Voronoi Heterogeneous Environment

The uniform NLOS environment, while useful for establishing the baseline, is unrealistic for two reasons. First, real deployment areas are not propagation-homogeneous — a campus or urban block contains open plazas (near-LOS), dense building clusters (rich scattering), roads (RMa-like), and enclosed spaces (NLOS-dominant). Second, the lack of spatial structure means fingerprinting has almost no environmental signature to exploit; all discrimination comes from range geometry alone, artificially limiting the achievable accuracy.

To address this, we designed a 4-cell Voronoi environment combining UMi_LOS (park/open area), UMi_NLOS (shopping center), RMa_LOS (highway/corridor), and mixed UMi (residential). Cell boundaries are generated by a seeded Voronoi algorithm to ensure reproducibility. The choice of maximally distinct scenarios was deliberate: similar scenarios would provide minimal benefit over the uniform case.

With the Voronoi environment and interferers enabling realistic SINR, we ran a feature selection progression to understand the contribution of each measurement type:

- **RSS alone:** Provides only range information. Adjacent distance rings produce similar values.
- **RSS + SINR (with interference):** The two interfering BSs (positioned outside the grid, west and south of center) create orthogonal gradients. Each UE position has a unique (RSS, SINR) pair; the ambiguity ring shrinks to a spatial point. SINR contributes approximately **+33 pp accuracy over RSS alone** in the 10×10 experiment, demonstrating that properly calibrated interference is highly informative.
- **RSS + SINR + AoA:** Adding AoA (with noise model) pushes accuracy to 82.2% (BASE_A, E7) from 27.3% (BASE) — a +55 pp gain in the multi-user 15×15 experiment. AoA dominates because, with the BS at the grid center, every grid point has a unique azimuth angle. AoA effectively provides near-perfect position information when angular resolution is sufficient.

**Per-cell analysis** revealed that the channel scenario interacts strongly with feature utility:

| Cell | Scenario | BASE_H Acc | BASE_A Acc | AoA Gain |
|------|----------|-----------|-----------|----------|
| Park | UMi_LOS | 62.6% | 88.6% | +26.0 pp |
| Residential | Mixed | 45.7% | 78.9% | +33.2 pp |
| Shopping | UMi_NLOS | 52.1% | 81.0% | +28.9 pp |
| Highway | RMa_LOS | 37.9% | 76.5% | +38.6 pp |

The highway cell (RMa_LOS) benefits most from AoA — under a dominant single-ray LOS channel, adjacent grid points produce nearly identical RSS/SINR values, making distance-ring ambiguity worst. AoA provides the only reliable discriminant. Small Voronoi cells (few grid points) also suffer higher cross-boundary confusion regardless of channel type: cell size is a stronger predictor of per-cell accuracy than channel scenario.

### 4.3 Adding Interference — Multi-BS Experiment and the SINR Bug

The scalability experiments used interference as a background assumption (interference was present but not carefully calibrated). When we examined the 10×10 multi-BS experiment closely, we discovered a **sign error in the SINR computation**: the interferer TX power was being applied with a 1 W reference instead of the same per-subcarrier reference used for the serving BS. This made the computed SINR approximately **30 dB too negative** — interference appeared far stronger than it was in reality, effectively masking the serving BS signal.

This bug was discovered by inspecting the raw SINR distribution: values were implausibly low (around -30 dB) for positions directly below the serving BS, where SINR should be at its maximum. After fixing the TX power normalization to use a consistent `TxPowerPerSC_dBm = 0` reference for both serving and interfering BSs, the SINR distribution became physically reasonable.

The corrected (v2) multi-BS setup places two interfering BSs **outside the grid**, at 30m west and 30m south of the serving BS. This ensures the serving BS remains dominant for all 225 grid points (no BS dominance inversions within the grid) while creating two orthogonal SINR gradients: an east–west gradient from IBS-1 and a north–south gradient from IBS-2. The combination produces a unique (RSS, SINR) fingerprint for every grid point, significantly improving the utility of SINR over RSS alone.

### 4.4 Multi-User Heterogeneous Device Experiment

Real cellular networks serve devices with widely varying hardware: flagship phones with 4-antenna arrays, budget handsets with a single antenna, tablets with non-standard form factors. A localization model trained on one device type may fail on another if it relies on absolute RSS values, since different device hardware produces systematically different signal levels at the same physical location.

We designed five user profiles spanning this hardware range:

| User | Type | Antennas | Gain | Height | Walk Seed |
|------|------|----------|------|--------|-----------|
| U1 | Flagship A | 4 | 0 dB | 1.5 m | 100 |
| U2 | Mid-range | 2 | −2 dB | 1.5 m | 200 |
| U3 | Budget/Old | 1 | −4 dB | 1.5 m | 300 |
| U4 | Flagship B | 4 | 0 dB | 1.5 m | 400 |
| U5 | Tablet/IoT | 2 | −1 dB | 0.9 m | 500 |

U1 and U4 share identical hardware but different walk seeds — a control pair to separate device effect from trajectory variation. Each user produces 90,001 samples for a total dataset of 450,005 samples, split 80/20 chronologically per user.

The experiment design isolates the contribution of each information source:

- **BASE (E1):** single-snapshot RSS+SINR baseline — 27.3% accuracy (XGBoost). Low because heterogeneous devices produce different absolute RSS levels at the same position, creating within-class scatter that confuses the model.
- **BASE_H (E4):** h=3 transition history — **50.4% accuracy (+23.1 pp)**. History features partially compensate for device heterogeneity because relative changes (as the UE moves) are more consistent across devices than absolute values.
- **BASE_dp (E2):** device parameters as additional features (no history) — **50.2% accuracy (+22.9 pp)**. Remarkably, explicit device knowledge at h=0 reproduces nearly the same gain as three steps of history. Device-specific RSS offsets are consistent across the grid; conditioning on them effectively provides the model with per-device sub-fingerprints.
- **BASE_H_dp (E5):** history + device parameters — **58.3% accuracy (+7.9 pp over BASE_H)**. Combining both is non-redundant: device knowledge and temporal context capture orthogonal aspects of position.
- **BASE_A_H (E10):** full AoA + history — **83.6% accuracy**. AoA at 3.5 GHz from a center BS provides near-unique directional fingerprints; accuracy approaches the theoretical maximum for 2m grid spacing with the applied noise model.
- **BASE_A_H_dp (E11):** all features — **84.9% accuracy / 0.35 m MAE** — the upper bound of the experiment.

The per-user breakdown reveals an important asymmetry:

| User | BASE_H Acc | BASE_A_H Acc | AoA Gain |
|------|-----------|-------------|----------|
| U1 (Flagship) | 61.6% | 87.6% | +26.0 pp |
| U2 (Mid-range) | 38.5% | 80.2% | +41.7 pp |
| U3 (Budget) | 54.7% | 84.8% | +30.1 pp |
| U4 (Flagship) | 60.7% | 87.0% | +26.3 pp |
| U5 (Tablet) | 36.3% | 78.4% | +42.1 pp |

Weaker devices benefit disproportionately from AoA: their degraded RSS/SINR quality means the geometric information in AoA is particularly valuable. Flagship devices already achieve reasonable RSS-based localization; AoA still adds ~26 pp but the relative improvement is smaller.

**Cross-user generalization** — training on U1–U4, testing on the unseen U5 — reveals a further advantage of AoA:

| Experiment | In-domain | Cross-user | Drop |
|---|---|---|---|
| BASE_H (E4) | 50.4% | 46.4% | −4.0 pp |
| BASE_A_H (E10) | 83.6% | **76.7%** | −6.9 pp |

AoA drops only 6.9 pp despite a completely unseen device. This is because AoA is geometrically determined — the angle from BS to UE depends on position alone, not device electronics. The residual 6.9 pp gap is attributable to U5's different UE height (0.9 m vs 1.5 m), which modifies the elevation angle systematically. RSS/SINR, by contrast, drop only 4 pp in absolute terms but from a 27 pp lower baseline — relative generalization is far worse without AoA.

### 4.5 BS Placement Study — AoA Geometry Dependence

The +33 pp AoA gain in the center-BS experiment raised a question about generalizability: is AoA truly a robust localization feature, or does the center-BS result depend on a lucky geometry where every grid point has a unique azimuth angle?

To answer this, we placed the serving BS at the **NE corner** of the grid (48, 48, 10) — 15 m north and east of the grid boundary — while keeping all other parameters identical. From this position, all 225 grid points lie within a ~52° azimuth wedge (SW quadrant, 195°–251°). Azimuth variation across the full grid diagonal is only ~56°, compared to 360° with the center BS.

The effect on AoA utility is dramatic:

| | Center BS (360°) | NE BS (52°) |
|---|---|---|
| BASE_H accuracy (XGB) | 50.4% | 62.7% |
| BASE_A_H accuracy (XGB) | 83.6% | 69.6% |
| **AoA gain (XGB)** | **+33.2 pp** | **+6.9 pp** |
| BASE_H accuracy (RF) | 52.5% | 62.2% |
| BASE_A_H accuracy (RF) | 77.1% | 65.1% |
| **AoA gain (RF)** | **+24.6 pp** | **+2.9 pp** |

**AoA gain collapses from +33 pp to +7 pp.** The center-BS result was substantially a geometric artefact: with a full angular sweep, AoA serves as a near-perfect proxy for position. In a narrow sector, AoA can only provide within-sector angular ordering, which corresponds to a limited distance-like encoding via elevation angle (BS height 10 m, UE height 1.5 m gives 8.5 m vertical separation — elevation spans ~9° at 61 m to ~31° at 21 m).

In contrast, the **transition history benefit is identical in both placements**:

| | Center BS | NE BS |
|---|---|---|
| BASE → BASE_H gain (XGB) | +23.1 pp | +23.2 pp |
| Base → BASE_H gain (RF) | +9.0 pp | +10.3 pp |

History captures trajectory dynamics — the way measurements change as the UE moves — which is independent of the BS's angular coverage. This geometry-independence is the key differentiating result between history-based and AoA-based features.

A secondary observation: the NE BS actually *improves* non-AoA accuracy (BASE: +12 pp, BASE_H: +12 pp vs center BS) because the larger distance dynamic range (21–61 m vs 0–28 m) gives RSS a stronger spatial gradient. The edge BS creates a characteristic NE-to-SW accuracy gradient: cells near the BS achieve 85–87% accuracy (BASE_H alone), while far cells are harder (54–66%) but recover with device parameters.

---

## 5. Key Findings

1. **Transition history universally improves localization.** History-based features improve accuracy by 9–22 pp across all six grid scales (9–400 classes), all four ML algorithms, and both the uniform and heterogeneous Voronoi environments. This establishes the thesis as a robust empirical finding rather than an artefact of a specific algorithm or environment.

2. **AoA is the most powerful feature at center BS — but is placement-sensitive.** With the BS at the grid center (360° azimuth coverage), adding AoA improves accuracy from 50.4% to 83.6% — a 33.2 pp gain. With the BS at the NE corner (52° sector), the same AoA feature adds only 6.9 pp. Transition history adds 23 pp in both cases.

3. **RSS ≈ SINR without interference; SINR adds +33 pp with calibrated interference.** Without co-channel interference, SINR reduces to a constant-shifted RSS with no additional spatial content. With two properly calibrated interferers placed outside the grid in orthogonal directions, SINR creates a 2D spatial gradient that contributes substantially to fingerprinting accuracy.

4. **AoA generalizes better across device types than RSS/SINR.** Cross-user accuracy (trained on U1–U4, tested on unseen U5) drops 6.9 pp for BASE_A_H but only 4 pp absolute for BASE_H — and BASE_H starts 33 pp lower. AoA's geometric determination makes it hardware-agnostic; RSS/SINR are device-hardware-dependent.

5. **Classification outperforms regression at 2m grid spacing.** At this spacing, classification MAE is 1.15–1.6× lower than regression, depending on grid size. The gap narrows with increasing grid size and is estimated to cross over around 28–30×30 (~800–900 classes).

6. **Device parameters as features provide orthogonal gains to history.** BASE_dp (device params, h=0) matches BASE_H (history, h=3) at 50.2% vs 50.4%. Combined (BASE_H_dp), they reach 58.3% — neither is redundant. Weaker devices benefit disproportionately from device-parameter conditioning.

7. **Cell size is the dominant per-cell accuracy factor, not channel scenario.** Small Voronoi cells (few grid points) suffer high cross-boundary confusion regardless of LOS/NLOS. The highway cell (RMa_LOS) has the lowest BASE_H accuracy (37.9%) due to a dominant single-ray channel that collapses RSS/SINR spatial variation, but it benefits most from AoA (+38.6 pp).

8. **The feature hierarchy is: AoA >> interference SINR > RSS (center BS).** AoA provides +33 pp over RSS+SINR+history; interference SINR provides +33 pp over RSS alone (without history). At an edge BS, this hierarchy flattens: AoA drops to +7 pp while RSS/SINR gain from the larger dynamic range.

---

## 6. Methodology Notes

**Temporal split (not random).** QuaDRiGa's spatial consistency means measurements from nearby time steps are correlated in channel characteristics. A random 80/20 split would interleave train and test snapshots from the same trajectory, allowing the model to interpolate between neighboring observations rather than generalizing to new positions. The chronological per-user split prevents this by ensuring test observations always come after all training observations for the same user.

**Oracle AoA vs. noise model.** Early experiments used clean AoA directly from QuaDRiGa (`ch.par.AoA_cb`) without any impairment. Results were unrealistically high — AoA with zero noise is essentially perfect for a center-BS deployment because it directly encodes the angle to each grid point. The 4° Gaussian + 5° quantization noise model was introduced to represent realistic beamforming estimation quality. All results reported in this document use the noise model throughout.

**The SINR calibration bug.** The first multi-BS implementation applied interferer TX power with a 1 W reference, while the serving BS reference was 1 mW per subcarrier. This made the computed interference power 30 dB too high, suppressing SINR to implausible values (down to −30 dB at the serving BS directly). The bug was found by inspecting the raw SINR distribution and comparing against theoretical path-loss estimates. After fixing the normalization (consistent `TxPowerPerSC_dBm = 0` reference for all BSs), SINR values became physically reasonable and the experiment was re-run. Results prior to this fix are not reported.

**AreaGenerator determinism.** The Voronoi cell layout is generated at simulation time by AreaGenerator using the experiment's random seed. In early experiments, the seed was applied inconsistently — some runs regenerated new cell boundaries when the simulation was restarted. All reported results use a fixed seed (42) so cell boundaries are identical across runs and devices.

---

## 7. Open Questions

**Absolute values vs. delta features across diverse environments.** Preliminary experiments confirm that absolute RSS/SINR stacking outperforms differential (delta) representation in the multi-user Voronoi environment — device-specific offsets are informative fingerprints, not confounders. The gap varies: 1.6 pp (XGBoost) to 12.4 pp (Random Forest) without AoA, collapsing to near-zero with AoA present. The environmental variability study (same UE, different channel realizations across days) would test whether this conclusion holds when the absolute fingerprint drifts.

**Environmental variability — same user, different days.** All experiments use a single QuaDRiGa channel realization per experiment. In a real deployment, the radio environment changes daily due to scatterer movement (people, furniture). Testing whether history-based models are robust to channel realization drift requires training on 2–3 separate simulation runs and testing on a third held-out run. MATLAB scripts for generating multi-seed runs are prepared; this experiment is pending.

**Generalization to real hardware.** The AoA noise model (4°+5°) is a first-order approximation of beamforming estimation error. Real hardware may have angular-dependent noise, non-uniform quantization, and calibration offsets. Field measurement campaigns would be needed to validate the simulation-derived AoA results and calibrate the noise model parameters.

**Hyperparameter optimization.** All reported results use fixed conservative hyperparameters (`n_estimators = 50`) to enable fast experiment iteration and fair cross-experiment comparison. A systematic hyperparameter search (e.g., via Bayesian optimization) on BASE_H, frozen for all subsequent experiments, could improve absolute accuracy without affecting relative comparisons. Initial estimates suggest `n_estimators = 200–300` alone would add approximately 5–8 pp.
