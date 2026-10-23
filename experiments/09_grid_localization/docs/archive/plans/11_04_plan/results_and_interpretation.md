# NE-BS Experiment — Results and Interpretation
# BS Placement Effect on AoA Informativeness

**Date:** April 2026  
**Experiment:** `ne_bs_voronoi_15x15`  
**Data:** `results/grid_localization/grid_15x15/sim_data_ne_bs_2026-04-11_20-11-48`  
**ML output:** `results/ne_bs_voronoi_15x15/`  
**Baseline for comparison:** `results/multi_user_voronoi_15x15/` (center BS, March 2026)

---

## 1. Setup Recap

The only change from the center-BS experiment is the serving BS position:

| | Center BS | NE-Corner BS |
|---|---|---|
| Position | (19, 19, 10) — grid center | (48, 48, 10) — 15 m NE of corner |
| Azimuth span to grid | ~360° | ~52° |
| Distance range | 0–28 m | 21–61 m |
| d_max / d_min | ∞ | 2.9 |

Grid, device profiles, walk seeds, channel scenarios, interferer positions — all identical.

---

## 2. Primary Question: Does AoA Gain Depend on Angular Coverage?

**Short answer: yes, strongly.**

| | XGBoost | | Random Forest | |
|---|---|---|---|---|
| | Center BS | NE BS | Center BS | NE BS |
| BASE_H (no AoA) | 50.4% | 62.7% | 52.5% | 62.2% |
| BASE_A_H (with AoA) | 83.6% | 69.6% | 77.1% | 65.1% |
| **AoA gain** | **+33.2 pp** | **+6.9 pp** | **+24.6 pp** | **+2.9 pp** |

With the center BS providing full 360° azimuth coverage, AoA adds 33 pp (XGB) over
RSS+SINR+history. With the NE BS compressing all 225 grid points into a 52° wedge,
the same AoA feature adds only 7 pp.

**Interpretation:** The center-BS AoA result was partially a geometric artefact.
Each grid point had a unique azimuth from the BS — AoA was essentially a
near-perfect proxy for x/y position. In the NE placement, all points appear in the
same southwest quadrant. Within that 52° sector, azimuth variation across the 30 m
diagonal is only ~26°. The model can no longer reliably distinguish adjacent grid
points by angle alone.

The residual 7 pp gain from AoA at the NE BS is likely driven by **elevation angle**,
which encodes rough distance: BS height = 10 m, UE height = 1.5 m → vertical
separation = 8.5 m. Elevation spans ~9° (SW corner, d=61 m) to ~31° (NE corner,
d=21 m). This 22° elevation spread still carries distance information even when
azimuth is compressed.

---

## 3. History Gain Is Geometry-Independent

| | BASE → BASE_H gain | |
|---|---|---|
| | XGBoost | RF |
| Center BS | +23.1 pp | +9.0 pp |
| NE BS | **+23.2 pp** | **+10.3 pp** |

The transition history benefit (+23 pp XGB) is **exactly the same** regardless of
BS placement. This is the more important finding for the thesis: transition features
encode trajectory dynamics that are independent of how the BS sees the UE.

A UE moving between two adjacent grid points creates the same directional signature
whether the BS is overhead or in the corner — it is the *change* in measurements
that matters, not their absolute angular geometry.

---

## 4. Overall Results Table

XGBoost:

| Experiment | NE Acc | NE MAE | Center Acc | Center MAE | Δ Acc | Δ MAE |
|------------|--------|--------|------------|------------|-------|-------|
| BASE | 39.5% | 6.15 m | 27.3% | 8.39 m | +12.2 pp | −2.24 m |
| BASE_dp | 61.4% | 3.16 m | 50.2% | 4.36 m | +11.2 pp | −1.20 m |
| BASE_uid | 59.7% | 3.30 m | 48.7% | 4.52 m | +11.0 pp | −1.22 m |
| BASE_H | 62.7% | 2.79 m | 50.4% | 4.53 m | +12.3 pp | −1.74 m |
| BASE_H_dp | 68.3% | 2.02 m | 58.3% | 3.20 m | +10.0 pp | −1.18 m |
| BASE_H_uid | 68.0% | 2.10 m | 57.8% | 3.26 m | +10.2 pp | −1.16 m |
| BASE_A | 63.1% | 1.97 m | 82.2% | 0.44 m | **−19.1 pp** | +1.53 m |
| BASE_A_dp | 68.9% | 1.50 m | 84.3% | 0.38 m | **−15.4 pp** | +1.12 m |
| BASE_A_uid | 68.9% | 1.53 m | 84.1% | 0.38 m | **−15.2 pp** | +1.15 m |
| BASE_A_H | 69.6% | 1.27 m | 83.6% | 0.39 m | **−14.0 pp** | +0.88 m |
| BASE_A_H_dp | 73.1% | 1.06 m | 84.9% | 0.35 m | **−11.8 pp** | +0.71 m |

RF:

| Experiment | NE Acc | NE MAE | Center Acc | Center MAE | Δ Acc | Δ MAE |
|------------|--------|--------|------------|------------|-------|-------|
| BASE | 51.9% | 4.93 m | 43.5% | 5.81 m | +8.4 pp | −0.88 m |
| BASE_H | 62.2% | 2.63 m | 52.5% | 4.01 m | +9.7 pp | −1.38 m |
| BASE_A | 60.1% | 2.11 m | 77.3% | 0.55 m | **−17.2 pp** | +1.56 m |
| BASE_A_H | 65.1% | 1.36 m | 77.1% | 0.53 m | **−12.0 pp** | +0.83 m |
| BASE_A_H_dp | 67.6% | 1.16 m | 79.3% | 0.47 m | **−11.7 pp** | +0.69 m |

**Pattern:** Non-AoA experiments are uniformly better with the NE BS (+8–12 pp).
AoA experiments are uniformly worse (−12–19 pp). The breakeven is approximately
where RSS+SINR information equals AoA information — around BASE_H with XGB (~63% for both).

---

## 5. Spatial Distribution of Errors

Per-Voronoi-cell breakdown (XGBoost, BASE_H):

| Cell | NE Acc | NE MAE | Center Acc | Center MAE | Notes |
|------|--------|--------|------------|------------|-------|
| 1 | 66.3% | 3.66 m | 37.9% | 4.84 m | Far from NE BS |
| 2 | 54.8% | 3.16 m | 52.1% | 6.01 m | Far from NE BS |
| 3 | 85.0% | 0.93 m | 45.7% | 6.04 m | Near NE BS |
| 4 | 86.5% | 0.94 m | 62.6% | 3.47 m | Near NE BS |

Cells 3 and 4 (NE quadrant, closer to the serving BS) achieve 85–87% accuracy and
sub-metre MAE — better than any cell in the center-BS experiment **without AoA**.
The NE BS creates a strong RSS distance gradient in these cells; the model can
fingerprint them accurately using amplitude alone.

Cells 1 and 2 (SW/W quadrant, farther from BS) are harder: 55–66% accuracy and
3–4 m MAE. These are the "far corner dead zones" predicted in the research plan.
Adding device parameters (BASE_H_dp) largely recovers cell 1 to 74% and cell 2 to 60%.

**With center BS (BASE_H):** all 4 cells were in a narrow band 38–63% accuracy —
more uniform but all mediocre. **With NE BS:** bimodal distribution — near cells
are excellent, far cells are mediocre. This is a characteristic of edge-mounted BSs.

---

## 6. Per-User Breakdown

XGBoost, BASE_H:

| User | NE Acc | Center Acc | Device |
|------|--------|------------|--------|
| U1 (4-ant, flagship) | 71.0% | 61.6% | +9.4 pp |
| U2 (2-ant, mid-range) | 50.6% | 38.5% | +12.1 pp |
| U3 (1-ant, budget) | 60.7% | 54.7% | +6.0 pp |
| U4 (4-ant, flagship) | 69.4% | 60.7% | +8.7 pp |
| U5 (tablet, 0.9m) | 61.8% | 36.3% | +25.5 pp |

All users improve with the NE BS for BASE_H. U5 (tablet at 0.9 m height) benefits
most (+25.5 pp) — possibly because the lower UE height changes the elevation AoA
fallback calculation, or because the larger distance dynamic range is more forgiving
of lower signal quality.

XGBoost, BASE_A_H:

| User | NE Acc | Center Acc | Device |
|------|--------|------------|--------|
| U1 (4-ant, flagship) | 74.7% | 87.6% | −12.9 pp |
| U2 (2-ant, mid-range) | 63.6% | 80.2% | −16.6 pp |
| U3 (1-ant, budget) | 68.3% | 84.8% | −16.5 pp |
| U4 (4-ant, flagship) | 73.2% | 87.0% | −13.8 pp |
| U5 (tablet, 0.9m) | 68.2% | 78.4% | −10.2 pp |

All users lose accuracy with AoA in the NE placement. Weaker devices (U2, U3) that
gained the most from AoA in the center case also lose the most here — they had been
relying most heavily on AoA to compensate for their poor RSS/SINR.

---

## 7. Cross-User Generalization

| Experiment | NE XGB | Center XGB | NE RF | Center RF |
|------------|--------|------------|-------|-----------|
| cross_user_BASE_H | 53.9% / 3.89 m | 46.4% / 5.05 m | 52.9% / 3.81 m | 46.3% / 4.92 m |
| cross_user_BASE_A_H | 59.5% / 2.02 m | 76.7% / 0.61 m | 56.5% / 1.84 m | 72.8% / 0.64 m |

**BASE_H cross-user is better with NE BS** (+7 pp XGB): the stronger RSS gradient
is more consistent across device types than the weaker one, making the model more
device-agnostic implicitly.

**BASE_A_H cross-user is much worse with NE BS** (−17 pp XGB): when AoA is the
dominant feature, it generalises well across devices (it is geometrically determined,
not electronically). When AoA is weak, the model falls back on RSS/SINR, which varies
across devices — cross-user performance degrades.

**Implication for deployment:** In an edge-BS scenario, AoA-based models are less
suitable for cross-device deployment than transition-history models.

---

## 8. Delta Features

| Pair | NE XGB Δpp | Center XGB Δpp | NE RF Δpp | Center RF Δpp |
|------|-----------|----------------|-----------|----------------|
| BASE_H vs BASE_H_delta | +0.1 pp | +1.6 pp | **+12.7 pp** | +12.4 pp |
| BASE_A_H vs BASE_A_H_delta | +0.1 pp | +0.2 pp | **+9.8 pp** | +2.7 pp |

XGBoost: insensitive to absolute vs delta in both placements — consistent with the
center-BS finding that tree splits are implicitly scale-invariant.

RF: the absolute advantage is similar for BASE_H (~12–13 pp) in both placements.
For BASE_A_H, the RF delta penalty is **much larger with NE BS** (+9.8 pp vs +2.7 pp).
With a weaker AoA signal, RF relies more heavily on absolute RSS/SINR values;
removing them via delta representation is more damaging when there is no strong
angular signal to compensate.

---

## 9. Summary and Thesis Implications

### What we set out to test
Whether the +33 pp AoA gain observed in §8 was a genuine measurement advantage
or a geometric artefact of having the BS at the grid center.

### Answer
It was substantially geometric. With a 52° azimuth sector, AoA gain drops to +7 pp.
The finding has two parts:

**Part 1 — AoA is placement-sensitive:**  
AoA is a powerful feature when the BS covers a wide angular sector. It loses most
of its discriminative power when all UEs are in the same directional quadrant. This
limits its practical applicability in edge-BS deployments (wall mounts, corridor ends,
ceiling corners) — which are the common case in indoor environments.

**Part 2 — History is placement-robust:**  
The +23 pp transition history benefit is completely stable across both BS geometries.
This is the key result: transition features work regardless of where the BS is mounted,
making them more practically deployable than AoA in diverse indoor environments.

### Numbers at a glance

| Feature contribution | Center BS (360°) | NE BS (52°) |
|---|---|---|
| History alone (BASE_H − BASE) | +23 pp | **+23 pp** |
| AoA alone (BASE_A − BASE) | +55 pp | **+24 pp** |
| AoA on top of history (BASE_A_H − BASE_H) | +33 pp | **+7 pp** |
| Device params on history (BASE_H_dp − BASE_H) | +8 pp | **+6 pp** |

### Open question
The elevation angle hypothesis (§2) should be tested more directly by running an
experiment with AoA azimuth only vs elevation only. This would confirm how much
of the residual 7 pp comes from elevation vs. azimuth within the narrow sector.
