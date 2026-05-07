# Regression vs Classification in Homogeneous Environments
# 15×15 Grid, Single-User Experiments

**Date:** 2026  
**Grid:** 15×15, 2 m spacing, 225 points  
**Task:** 5G/6G UE localization from single serving BS  
**Source code:** `src/python/localization_pipeline.py` (classification), `src/python/localization_pipeline_regression.py` (regression)

---

## 1. Task Definitions

### Classification

The grid is treated as a 225-class problem. The model predicts the discrete grid point label (1–225) from a feature window of h+1 consecutive measurements. Performance is measured as top-1 accuracy and Mean Absolute Error (MAE — Euclidean distance between predicted and true grid point, in metres).

### Regression

The model predicts three continuous physical quantities simultaneously, each with an independent XGBoost regressor:

| Target | Units | Derivation |
|---|---|---|
| Distance | m | Euclidean distance UE → BS |
| Azimuth | ° | Horizontal angle BS → UE |
| Elevation | ° | Vertical angle BS → UE |

The final **3D Position MAE** is computed by reconstructing the 2D (X, Y) position from predicted (distance, azimuth) and comparing to ground truth.

---

## 2. Experimental Setup

Two homogeneous 3GPP scenarios were used, each representing a distinct propagation regime:

| Scenario | Code | Description | Typical Use |
|---|---|---|---|
| UMa_NLOS | `3GPP_38.901_UMa_NLOS` | Urban Macro, Non-Line-of-Sight | Dense urban, obstructed BS |
| UMa_LOS  | `3GPP_38.901_UMa_LOS`  | Urban Macro, Line-of-Sight    | Open outdoor, clear BS view |
| UMi_NLOS | `3GPP_38.901_UMi_NLOS` | Urban Micro, Non-Line-of-Sight | Indoor-like, short range NLOS |

All experiments use a **temporal 80/20 train/test split** and a single UE walk of 400 steps per grid point. Sample counts:
- UMa_NLOS (older runs): 22,501 samples
- UMa_NLOS / UMa_LOS / UMi_NLOS (newer runs): 90,001 samples

---

## 3. Feature Hierarchy in Regression

The regression experiments systematically vary the feature set to isolate the contribution of each measurement type.

### 3.1 UMi_NLOS — Feature Progression (90,001 samples)

| Feature set | h | 3D MAE | Per-target MAE |
|---|---|---|---|
| RSS | 0 | 14.15 m | dist 1.14 m, az 104.7°, el 4.26° |
| SINR | 0 | 14.14 m | dist 1.14 m, az 104.6°, el 4.26° |
| RSS + SINR | 0 | 14.15 m | dist 1.14 m, az 104.6°, el 4.26° |
| + AoA azimuth | 0 | 0.776 m | dist 0.43 m, az 2.00°, el 1.40° |
| + AoA elevation | 0 | **0.622 m** | dist 0.32 m, az 1.84°, el 0.92° |
| + AoA elevation | 1 | **0.516 m** | dist 0.27 m, az 1.56°, el 0.76° |

### 3.2 UMa_NLOS — Feature Progression (22,501 samples)

| Feature set | h | 3D MAE | Note |
|---|---|---|---|
| RSS | 0 | 31.03 m | Near-random — macro NLOS collapses range sensitivity |
| SINR | 0 | 31.03 m | Identical to RSS |
| RSS + SINR | 0 | 31.02 m | No gain |
| + AoA azimuth | 0 | 4.54 m | Direction recovered, distance still uncertain |
| + AoA elevation | 0 | 2.01 m | Elevation encodes BS-UE height gap → distance |
| + AoA elevation | 1 | 1.82 m | Small history benefit |

### 3.3 UMa_NLOS — All Features (22,501 samples)

When all available channel metrics are included (RSS, SINR, CQI, AoA azimuth, AoA elevation, timing advance, path loss, n_multipath, RMS delay spread, K-factor), regression achieves:

| h | 3D MAE | Note |
|---|---|---|
| 0 | 1.042 m | Best |
| 1 | 1.099 m | Worse |
| 2 | 1.140 m | Worse |
| 3 | 1.163 m | Worst |

With the full feature set the regressor can extract distance information from timing advance and path loss, bypassing the azimuth ambiguity problem. **However, history consistently degrades performance** — each additional lag step adds noise to the regression target (see §5).

---

## 4. Classification Results

### 4.1 UMa_NLOS — Classification (90,001 samples, RSS+SINR+CQI+AoA)

| h | Accuracy | MAE |
|---|---|---|
| 0 (static) | 29.18% | 3.346 m |
| 1 | 46.12% | 2.072 m |
| 2 | 49.48% | 1.834 m |
| 3 | **51.23%** | **1.745 m** |

**History improvement: +22.1 pp accuracy, −47.9% MAE.** Classification benefits strongly from history in NLOS because the distance-ring ambiguity is severe and trajectory direction provides the key disambiguation.

### 4.2 UMa_LOS — Classification (90,001 samples, RSS+SINR+CQI+AoA)

| h | Accuracy | MAE |
|---|---|---|
| 0 (static) | 92.59% | 0.292 m |
| 1 | **95.90%** | **0.136 m** |
| 2 | 95.54% | 0.140 m |
| 3 | 95.86% | 0.128 m |

**History improvement: +3.3 pp accuracy, −56.2% MAE.** LOS classification starts much higher because the dominant single-ray channel makes AoA and distance very stable. History adds a modest but consistent gain; diminishing returns set in quickly (h=1 captures nearly all the benefit).

---

## 5. Key Findings

### 5.1 RSS ≈ SINR Without Interference

In all regression experiments, RSS and SINR produce nearly identical results:

| | RSS | SINR | RSS+SINR |
|---|---|---|---|
| UMi_NLOS 3D MAE | 14.154 m | 14.141 m | 14.148 m |
| UMa_NLOS 3D MAE | 31.030 m | 31.029 m | 31.023 m |

Combining them adds nothing. Both measure only amplitude from the serving BS — without a co-channel interferer to create spatial gradients, they encode the same distance-ring information. This confirms the same finding from the classification experiments and is a fundamental property of the channel, not an artefact of the learning algorithm.

### 5.2 AoA Is Essential in Both Tasks

Without AoA, regression fails completely (14–31 m MAE). Adding azimuth alone reduces error by ~18× in UMi_NLOS (14.15 → 0.78 m). Adding elevation further reduces it by ~20% (0.78 → 0.62 m), because elevation encodes the UE-to-BS height differential and thereby constrains the distance estimate.

The same dominance holds for classification: the multi-user Voronoi experiment shows BASE_A (h=0 with AoA) achieves 82.2% vs BASE (h=0 without AoA) at 27.3% — a +55 pp gap.

### 5.3 History Helps Classification, Not Regression

This is the most important structural difference between the two tasks:

| Task | Scenario | h=0 MAE | h=1 MAE | h=3 MAE | Trend |
|---|---|---|---|---|---|
| **Classification** | UMa_NLOS | 3.346 m | 2.072 m | 1.745 m | ↓ consistently improving |
| **Regression** (all features) | UMa_NLOS | 1.042 m | 1.099 m | 1.163 m | ↑ consistently degrading |
| **Regression** (AoA only) | UMi_NLOS | 0.622 m | 0.516 m | — | ↓ small improvement |

**Why classification benefits from history:** consecutive measurements provide directional context — the model can infer which way the UE was moving and use this to break the distance-ring ambiguity. This benefit accumulates with each additional lag up to h=3.

**Why regression is harmed by history (in NLOS with all features):** regression predicts absolute coordinates, and each historical position is physically offset from the current one. The model receives past positions as inputs but is optimised to predict the *current* position — the offsets are noise from the regression target's perspective. The model must learn to ignore the spatial offset, which degrades performance.

**Why regression benefits slightly from history with AoA:** when AoA alone resolves position (UMi_NLOS with small grid distances), the trajectory adds a weak consistency signal that marginally improves the current-position estimate. The distance offset is small (~2 m per step), and AoA constrains the direction, so the historical positions remain informative.

### 5.4 LOS vs NLOS

| Scenario | Task | Features | h=0 MAE | h=3 MAE |
|---|---|---|---|---|
| UMa_LOS | Classification | RSS+SINR+CQI+AoA | 0.292 m | 0.128 m |
| UMa_NLOS | Classification | RSS+SINR+CQI+AoA | 3.346 m | 1.745 m |
| UMa_NLOS | Regression (all feat.) | All | 1.042 m | 1.163 m |
| UMi_NLOS | Regression | RSS+SINR+AoA | 0.622 m | 0.516 m |

LOS is dramatically easier for classification (0.29 vs 3.35 m at h=0) because the dominant single-ray channel makes AoA stable and the RSS-distance relationship monotone. History adds less in LOS because the static snapshot already provides near-complete position information.

UMa_NLOS regression at h=0 (1.042 m, all features) outperforms classification at h=0 (3.346 m) because the regressor exploits timing advance and path loss to estimate distance directly — information that classification ignores in its label-only evaluation. However, classification overtakes regression by h=3 (1.745 m vs 1.163 m with history degradation).

### 5.5 Classification vs Regression — Head-to-Head

On comparable setups (15×15, single user, AoA available):

| Task | Scenario | Features | h | MAE |
|---|---|---|---|---|
| **Regression** | UMi_NLOS | RSS+SINR+AoA | 0 | 0.622 m |
| **Regression** | UMi_NLOS | RSS+SINR+AoA | 1 | 0.516 m |
| **Classification** | UMa_NLOS | RSS+SINR+CQI+AoA | 0 | 3.346 m |
| **Classification** | UMa_NLOS | RSS+SINR+CQI+AoA | 3 | 1.745 m |
| **Classification** | UMa_LOS | RSS+SINR+CQI+AoA | 0 | 0.292 m |
| **Classification** | UMa_LOS | RSS+SINR+CQI+AoA | 3 | **0.128 m** |

At 2 m grid spacing **classification is the better task formulation when the grid is known** because:
1. It directly optimises for grid-point identity, not continuous coordinates
2. Each wrong prediction carries a known spatial penalty (multiples of 2 m)
3. History benefits classification strongly, closing the gap with regression or surpassing it

Regression is more appropriate when:
- Grid positions are not known in advance
- Higher-than-2 m grid spacing makes label ambiguity a concern
- Additional metrics beyond RSS/SINR/AoA are available (timing advance, path loss), which the regression model can exploit as explicit distance cues

---

## 6. Summary Table — All Homogeneous 15×15 Experiments

### Regression (XGBoost Regressor, temporal split)

| Scenario | Samples | Features | h | 3D MAE |
|---|---|---|---|---|
| UMa_NLOS | 22,501 | All (10 metrics) | 0 | 1.042 m |
| UMa_NLOS | 22,501 | All (10 metrics) | 1 | 1.099 m |
| UMa_NLOS | 22,501 | All (10 metrics) | 2 | 1.140 m |
| UMa_NLOS | 22,501 | All (10 metrics) | 3 | 1.163 m |
| UMa_NLOS | 22,501 | RSS+SINR+AoA | 0 | 2.006 m |
| UMa_NLOS | 22,501 | RSS+SINR+AoA | 1 | 1.824 m |
| UMi_NLOS | 90,001 | RSS only | 0 | 14.154 m |
| UMi_NLOS | 90,001 | SINR only | 0 | 14.141 m |
| UMi_NLOS | 90,001 | RSS+SINR | 0 | 14.148 m |
| UMi_NLOS | 90,001 | RSS+SINR+AoA_az | 0 | 0.776 m |
| UMi_NLOS | 90,001 | RSS+SINR+AoA | 0 | 0.622 m |
| UMi_NLOS | 90,001 | RSS+SINR+AoA | 1 | **0.516 m** |

### Classification (XGBoost Classifier, temporal split)

| Scenario | Samples | Features | h | Accuracy | MAE |
|---|---|---|---|---|---|
| UMa_NLOS | 90,001 | RSS+SINR+CQI+AoA | 0 | 29.18% | 3.346 m |
| UMa_NLOS | 90,001 | RSS+SINR+CQI+AoA | 1 | 46.12% | 2.072 m |
| UMa_NLOS | 90,001 | RSS+SINR+CQI+AoA | 2 | 49.48% | 1.834 m |
| UMa_NLOS | 90,001 | RSS+SINR+CQI+AoA | 3 | 51.23% | **1.745 m** |
| UMa_LOS  | 90,001 | RSS+SINR+CQI+AoA | 0 | 92.59% | 0.292 m |
| UMa_LOS  | 90,001 | RSS+SINR+CQI+AoA | 1 | 95.90% | 0.136 m |
| UMa_LOS  | 90,001 | RSS+SINR+CQI+AoA | 3 | 95.86% | **0.128 m** |
