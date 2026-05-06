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

---

## 2. System Architecture

### 2.1 Pipeline Overview

### 2.2 Data Contract

---

## 3. Simulation Environment

### 3.1 Channel Model

### 3.2 Grid Environment

### 3.3 Voronoi Heterogeneous Environment

### 3.4 UE Trajectory — Random Walk

### 3.5 Base Station Configurations

#### Main Experiment — Center BS

#### BS Placement Study — NE-Corner BS

### 3.6 Multi-User Device Heterogeneity

### 3.7 AoA Noise Model

---

## 4. Feature Engineering

### 4.1 Static Baseline (h = 0)

### 4.2 Transition History Stacking (h > 0)

### 4.3 Optional Feature Augmentations

### 4.4 Experiment Registry

---

## 5. Evaluation Framework

### 5.1 Task Formulation

### 5.2 Train/Test Split

### 5.3 Evaluation Metrics

### 5.4 Models

---

## 6. Experimental Results

### 6.1 Scalability: History Benefit Across Grid Sizes

### 6.2 Multi-User Voronoi 15×15 — Center BS

#### 6.2.1 Overall Results

#### 6.2.2 History Depth Analysis

#### 6.2.3 Per-User Breakdown (XGBoost, BASE_H vs BASE_A_H)

#### 6.2.4 Per-Cell Breakdown (XGBoost, BASE_H vs BASE_A)

#### 6.2.5 Cross-User Generalization

#### 6.2.6 Device Knowledge vs. History — Isolation

### 6.3 BS Placement Study — AoA Geometry Dependence

#### 6.3.1 Primary Finding — AoA Gain

#### 6.3.2 History Gain is Geometry-Independent

#### 6.3.3 RSS/SINR Discrimination with Edge BS

#### 6.3.4 Spatial Distribution of Errors — NE BS

#### 6.3.5 Cross-User Generalization Under Edge BS

---

## 7. Summary of Findings

### 7.1 Core Thesis: Validated

### 7.2 AoA Is Placement-Sensitive; History Is Not

### 7.3 Device Heterogeneity

### 7.4 Channel Environment

### 7.5 Feature Design Recommendations

---

## 8. Configuration Reference

### 8.1 Complete Simulation Parameters

### 8.2 Output Files
