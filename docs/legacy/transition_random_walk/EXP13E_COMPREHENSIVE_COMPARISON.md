# Experiment 13E: Comprehensive Comparison
## Transition-Based vs Static Localization (LOS vs NLOS)

**Date:** January 1, 2026  
**Experiments Compared:**
- **LOS Run:** `exp13e_2026-01-01_09-57-36` (Duration: 23.8s)
- **NLOS Run:** `exp13e_2026-01-01_10-21-13` (Duration: 32.8s)

### Run Details

| Parameter | LOS Value | NLOS Value | Same? |
|:----------|:----------|:-----------|:------|
| Scenario | `3GPP_38.901_UMa_LOS` | `3GPP_38.901_UMa_NLOS` | ❌ |
| Grid Size | 3×3 | 3×3 | ✅ |
| Spacing | 2.0 m | 2.0 m | ✅ |
| Random Steps | 10,000 | 10,000 | ✅ |
| UE Speed | 1.5 m/s | 1.5 m/s | ✅ |
| Position Jitter | ±0.1 m | ±0.1 m | ✅ |
| Frequency | 3.0 GHz | 3.0 GHz | ✅ |
| Bandwidth | 100 MHz | 100 MHz | ✅ |
| Train/Test Split | 8001/2000 | 8001/2000 | ✅ |
| Random Seed | Fixed | Fixed | ✅ |

**Validation:** ✅ All parameters identical except propagation scenario — fair comparison.

---

## Executive Summary

This document compares the performance of **static absolute RSS localization** vs **transition-based (delta) localization** across two propagation environments: **Line-of-Sight (LOS)** and **Non-Line-of-Sight (NLOS)**.

### Key Finding
**Static localization consistently outperforms transition-based localization in both environments**, with the gap widening in NLOS conditions.

---

## Experimental Setup

### Common Configuration
- **Grid:** 3×3 points, 2.0m spacing
- **Random Walk:** 10,000 steps
- **UE Speed:** 1.5 m/s
- **Position Jitter:** ±0.1 m
- **Frequency:** 3.0 GHz
- **Bandwidth:** 100 MHz
- **Classification:** Maximum Likelihood (80% train, 20% test)
- **Random Seed:** Fixed (reproducible results)

### Scenarios
1. **LOS:** `3GPP_38.901_UMa_LOS` - Direct propagation path dominates
2. **NLOS:** `3GPP_38.901_UMa_NLOS` - Multipath reflections dominate

---

## Results Comparison

### Classification Accuracy

| Metric | **LOS Static** | **LOS Transition** | **NLOS Static** | **NLOS Transition** |
|:-------|:---------------|:-------------------|:----------------|:--------------------|
| **RSS** | **97.70%** ✓ | 42.62% | **32.45%** ✓ | 12.75% |
| **SINR** | **97.70%** ✓ | 42.62% | **32.45%** ✓ | 12.75% |
| **CQI** | 7.85% | 4.60% | 7.00% | ~4-5% |
| **Advantage** | +55.08% | - | +19.70% | - |

**Key Observations:**
- Static localization is **2.3× better** in LOS and **2.5× better** in NLOS
- LOS provides **3× higher accuracy** than NLOS for static localization (97.7% vs 32.5%)
- CQI is unusable in both scenarios (saturates at max value = 15)

### Variance Comparison

| Metric | LOS Static | LOS Transition | NLOS Static | NLOS Transition |
|:-------|:-----------|:---------------|:------------|:----------------|
| **RSS Std (σ)** | 0.06 dB | 0.08 dB | 1.07 dB | 1.56 dB |
| **Variance Ratio** | 1.00 | **1.33×** ↑ | 1.00 | **1.46×** ↑ |

**Analysis:**
- Transition variance is **33-46% higher** than static variance
- This confirms: `Var(A - B) ≈ Var(A) + Var(B)` (fading is uncorrelated at 2m spacing)
- LOS has **18× lower variance** than NLOS (0.06 vs 1.07 dB)

### Separability (Bhattacharyya Distance)

| Environment | Static (Adjacent Points) | Transition (All Edges) | Ratio |
|:------------|:------------------------|:-----------------------|:------|
| **LOS** | 44.650 | 45.813 | 1.03× |
| **NLOS** | 0.630 | 0.633 | 1.00× |

**Analysis:**
- LOS has **70× higher separability** than NLOS (44.6 vs 0.6)
- Transition separability is marginally higher, but this is negated by having 24 classes instead of 9

---

## Environment-Specific Insights

### LOS (Line-of-Sight)

**Characteristics:**
- Direct path dominates → minimal fading
- Extremely low variance (σ = 0.06 dB)
- Very high separability (D_B = 44.6)
- Monotonic signal gradient away from BS

**Static Localization:**
- **Near-perfect accuracy: 97.70%**
- Each grid point has a distinct, stable "fingerprint"
- Errors are minimal and typically to adjacent points only

**Transition Localization:**
- **Moderate accuracy: 42.62%**
- Deltas are small (0.2-1.3 dB) but consistent
- Fails due to class confusion (24 vs 9)

**Verdict:** ✅ **LOS is ideal for static RSS localization**

---

### NLOS (Non-Line-of-Sight)

**Characteristics:**
- Multipath reflections dominate
- High variance (σ = 1.07 dB) due to constructive/destructive interference
- Low separability (D_B = 0.63)
- Significant overlap between neighboring points

**Static Localization:**
- **Moderate accuracy: 32.45%**
- Distributions overlap heavily
- Still better than random guessing (11.1%)

**Transition Localization:**
- **Poor accuracy: 12.75%**
- Many near-zero deltas (|Δ| < 0.5 dB)
- High variance (σ = 1.56 dB) drowns out useful signal
- Barely better than random (4.2%)

**High-Confidence Transitions (|Δ| > 3 dB):**
In NLOS, the following edges showed strong gradients:
- **4→1:** Δ = +3.80 ± 1.54 dB (moving toward BS)
- **1→4:** Δ = -3.86 ± 1.53 dB (moving away from BS)

These are radial movements near the base station and could be used as "anchor" features.

**Verdict:** ⚠️ **NLOS degrades both methods, but static remains superior**

---

## Why Static Outperforms Transitions

### 1. Class Complexity
- **Static:** 9 classes (grid points)
- **Transition:** 24 classes (directed edges)
- With comparable separability, fewer classes = higher accuracy
- Random guessing: Static = 11.1%, Transition = 4.2%

### 2. Variance Amplification
When fading is uncorrelated over 2m, the delta variance is:
```
Var(Δ) = Var(RSS_after - RSS_before) 
       = Var(RSS_after) + Var(RSS_before) 
       ≈ 2σ²
```
This **doubles the noise**, making classification harder.

**Evidence:**
- LOS: σ_static = 0.06 dB → σ_transition = 0.08 dB (1.33×)
- NLOS: σ_static = 1.07 dB → σ_transition = 1.56 dB (1.46×)

### 3. Ambiguous Deltas
Many transitions have near-zero mean (moving sideways relative to BS):
- **LOS:** 6 out of 24 transitions have |Δ| < 0.5 dB
- **NLOS:** 10 out of 24 transitions have |Δ| < 0.5 dB

These edges are indistinguishable from noise.

### 4. No Correlation Benefit
The original hypothesis assumed that fading would be correlated over 2m, leading to:
```
Var(A - B) < Var(A) + Var(B)  [Expected]
```
**Reality:** Fading is uncorrelated at this spatial scale, so:
```
Var(A - B) ≈ Var(A) + Var(B)  [Actual]
```
No variance reduction occurred.

---

## Practical Recommendations

### ✅ **Do Use:**
1. **Static absolute RSS** for primary localization
2. **SINR** interchangeably with RSS (they're linearly related)
3. **LOS environments** when possible (3× accuracy improvement)

### ❌ **Don't Use:**
1. **Transition-based localization** as a standalone method
2. **CQI** in high-SNR scenarios (saturates at max)
3. **Deltas alone** for classification (too noisy)

### 💡 **Potential Hybrid Approach:**

While transitions failed as a primary method, they could serve as auxiliary features:

1. **ML Feature Augmentation:**
   - Train XGBoost/Random Forest with **both** static RSS + delta as features
   - The model might learn to weight high-gradient transitions appropriately

2. **Particle Filter Confidence Resets:**
   - When |Δ| > 3 dB detected → narrow particle distribution to radial movements
   - Acts as a "sanity check" or position reset

3. **Movement Direction Hints:**
   - Large positive Δ → moving toward BS
   - Large negative Δ → moving away from BS
   - Could improve trajectory prediction

---

## Statistical Summary

### Overall Performance by Approach

| Approach | LOS Accuracy | NLOS Accuracy | Avg Accuracy | LOS/NLOS Ratio | Variance Penalty |
|:---------|:-------------|:--------------|:-------------|:---------------|:-----------------|
| **Static** | 97.70% | 32.45% | **65.08%** | **3.01×** | 1.00× (baseline) |
| **Transition** | 42.62% | 12.75% | 27.69% | **3.34×** | 1.40× (40% higher σ) |
| **Improvement** | +55.08% | +19.70% | **+37.39%** | - | - |

### Environment Impact Analysis (LOS vs NLOS)

#### **Static Approach Comparison**

| Metric | **LOS** | **NLOS** | **Degradation** | Explanation |
|:-------|:--------|:---------|:----------------|:------------|
| Accuracy | **97.70%** | 32.45% | **-66.8%** | Multipath destroys separability |
| Variance (σ) | 0.06 dB | 1.07 dB | **+17.8×** | Constructive/destructive interference |
| Separability (D_B) | 44.650 | 0.630 | **-98.6%** | Distributions heavily overlap |
| Performance vs Random | 8.8× better | 2.9× better | - | Still better than chance (11.1%) |

**Key Finding:** NLOS causes a **67% drop in static accuracy** due to fading variance increasing by 18×.

#### **Transition Approach Comparison**

| Metric | **LOS** | **NLOS** | **Degradation** | Explanation |
|:-------|:--------|:---------|:----------------|:------------|
| Accuracy | 42.62% | 12.75% | **-70.1%** | More sensitive to noise |
| Variance (σ) | 0.08 dB | 1.56 dB | **+19.5×** | Doubled variance (2σ²) |
| Separability (D_B) | 45.813 | 0.633 | **-98.6%** | Same root cause as static |
| Performance vs Random | 10.2× better | 3.0× better | - | Barely above chance (4.2%) |

**Key Finding:** NLOS causes a **70% drop in transition accuracy** — even more severe than static degradation.

### Approach Comparison Within Each Environment

#### **LOS Environment: Static vs Transition**

| Metric | Static | Transition | Static Advantage |
|:-------|:-------|:-----------|:-----------------|
| Accuracy | **97.70%** | 42.62% | **+55.08%** (2.29×) |
| Variance (σ) | 0.06 dB | 0.08 dB | 1.33× lower |
| Separability | 44.650 | 45.813 | -2.6% (slightly worse) |
| # Classes | 9 points | 24 edges | 2.67× fewer |

**Verdict:** Static wins by **55%** due to fewer classes, despite marginally lower separability.

#### **NLOS Environment: Static vs Transition**

| Metric | Static | Transition | Static Advantage |
|:-------|:-------|:-----------|:-----------------|
| Accuracy | **32.45%** | 12.75% | **+19.70%** (2.55×) |
| Variance (σ) | 1.07 dB | 1.56 dB | 1.46× lower |
| Separability | 0.630 | 0.633 | ~0% (equivalent) |
| # Classes | 9 points | 24 edges | 2.67× fewer |

**Verdict:** Static wins by **20%** — smaller gap than LOS, but still decisive.

### Cross-Environment Comparison Matrix

|  | LOS Static | NLOS Static | LOS Transition | NLOS Transition |
|:---|:-----------|:------------|:---------------|:----------------|
| **Accuracy** | **97.70%** ⭐ | 32.45% | 42.62% | 12.75% ❌ |
| **vs Best** | Baseline | -67% | -56% | -87% |
| **vs Random** | 8.8× | 2.9× | 10.2× | 3.0× |
| **Variance** | **0.06 dB** ⭐ | 1.07 dB | 0.08 dB | 1.56 dB ❌ |

**Ranking (Best to Worst):**
1. 🥇 **LOS Static:** 97.70% accuracy
2. 🥈 **LOS Transition:** 42.62% accuracy
3. 🥉 **NLOS Static:** 32.45% accuracy
4. ❌ **NLOS Transition:** 12.75% accuracy

**Insight:** The **environment (LOS vs NLOS) has a bigger impact than the approach (static vs transition)**. LOS transition (42.6%) beats NLOS static (32.5%) despite transitions being inferior within each environment.

---

## Detailed Distribution Comparison

### Static RSS Distributions (LOS vs NLOS)

#### Point-by-Point Comparison

| Point | LOS Mean | LOS Std | NLOS Mean | NLOS Std | Mean Diff | Std Ratio |
|:-----:|:--------:|:-------:|:---------:|:--------:|:---------:|:---------:|
| 1 | -47.01 dBm | 0.06 dB | -54.85 dBm | 1.23 dB | -7.84 dB | **20.5×** |
| 2 | -47.20 dBm | 0.07 dB | -57.27 dBm | 0.52 dB | -10.07 dB | **7.4×** |
| 3 | -47.44 dBm | 0.06 dB | -57.24 dBm | 1.20 dB | -9.80 dB | **20.0×** |
| 4 | -47.84 dBm | 0.05 dB | -58.72 dBm | 0.91 dB | -10.88 dB | **18.2×** |
| 5 | -48.21 dBm | 0.03 dB | -57.65 dBm | 1.08 dB | -9.44 dB | **36.0×** |
| 6 | -48.37 dBm | 0.07 dB | -58.69 dBm | 1.45 dB | -10.32 dB | **20.7×** |
| 7 | -48.78 dBm | 0.04 dB | -59.27 dBm | 0.66 dB | -10.49 dB | **16.5×** |
| 8 | -49.18 dBm | 0.07 dB | -60.30 dBm | 1.56 dB | -11.12 dB | **22.3×** |
| 9 | -49.66 dBm | 0.05 dB | -59.13 dBm | 1.01 dB | -9.47 dB | **20.2×** |
| **Avg** | **-48.19** | **0.06** | **-58.12** | **1.07** | **-9.93** | **20.2×** |

**Key Observations:**
- **Path Loss Increase:** NLOS adds ~10 dB average path loss (multipath scattering)
- **Variance Explosion:** NLOS variance is **20× higher** on average (0.06 → 1.07 dB)
- **Point 5 (center):** Most stable in LOS (σ = 0.03), but still 36× worse in NLOS
- **Point 8 (far corner):** Worst variance in both cases (σ_LOS = 0.07, σ_NLOS = 1.56)

### Transition Delta Distributions (LOS vs NLOS)

#### Top Transitions by Magnitude

**LOS Top 5:**
| Transition | RSS Δ | Std | Direction |
|:----------:|:-----:|:---:|:----------|
| 9→6 | +1.29 dB | 0.08 dB | Toward BS |
| 6→9 | -1.29 dB | 0.08 dB | Away from BS |
| 5→2 | +1.01 dB | 0.07 dB | Toward BS |
| 2→5 | -1.00 dB | 0.07 dB | Away from BS |
| 8→5 | +0.97 dB | 0.07 dB | Toward BS |

**NLOS Top 5:**
| Transition | RSS Δ | Std | Direction |
|:----------:|:-----:|:---:|:----------|
| 1→4 | -3.86 dB | 1.53 dB | Away from BS |
| 4→1 | +3.80 dB | 1.54 dB | Toward BS |
| 8→5 | +2.65 dB | 1.88 dB | Toward BS |
| 5→8 | -2.60 dB | 1.92 dB | Away from BS |
| 2→1 | +2.44 dB | 1.33 dB | Toward BS |

**Key Observations:**
- **LOS deltas:** Small (< 1.3 dB), highly consistent (σ ~ 0.08 dB)
- **NLOS deltas:** Larger (up to 3.9 dB), but 19× noisier (σ ~ 1.5 dB)
- **Strongest NLOS transitions:** Points 1↔4 (radial movement near BS)
- **LOS consistency:** All transitions have similar low variance
- **NLOS chaos:** Variance ranges from 0.5 to 1.9 dB depending on edge

### Sample Distribution Analysis

| Point | LOS Samples | NLOS Samples | Difference | Notes |
|:-----:|:-----------:|:------------:|:-----------|:------|
| 1 | 781 | 781 | 0 | Closest to BS |
| 2 | 1208 | 1208 | 0 |  |
| 3 | 808 | 808 | 0 |  |
| 4 | 1239 | 1239 | 0 |  |
| 5 | 1690 | 1690 | 0 | Center (most visits) |
| 6 | 1259 | 1259 | 0 |  |
| 7 | 853 | 853 | 0 |  |
| 8 | 1294 | 1294 | 0 |  |
| 9 | 869 | 869 | 0 | Farthest from BS |
| **Total** | **10001** | **10001** | **0** | Identical (same seed) |

**Validation:** ✅ Sample counts are identical because both runs used the **same random seed**, ensuring the random walk path was identical. This makes the comparison fair and eliminates trajectory bias.

---

## Conclusions

### Primary Findings

1. **Static localization is superior** in both LOS and NLOS environments
   - LOS: 97.70% vs 42.62% (+55.08% absolute advantage, 2.29× ratio)
   - NLOS: 32.45% vs 12.75% (+19.70% absolute advantage, 2.55× ratio)
   - Static wins regardless of propagation conditions

2. **Transition-based hypothesis is rejected:**
   - Transitions do NOT reduce variance — they **amplify it by 33-46%**
   - Transitions do NOT improve separability (marginally equivalent or worse)
   - Transitions introduce **2.67× more classes** (24 edges vs 9 points)
   - No correlation benefit at 2m spacing (fading is uncorrelated)

3. **Environment has greater impact than approach:**
   - LOS vs NLOS causes **67-70% accuracy drop** (both approaches)
   - NLOS variance is **18-20× higher** than LOS
   - LOS separability is **71× better** than NLOS
   - **LOS transition (42.6%)** beats **NLOS static (32.5%)** — environment matters more!

4. **RSS and SINR are perfectly correlated:**
   - Identical accuracy, variance, and separability metrics
   - Linear relationship (RSS = SINR - constant)
   - Use either interchangeably for localization

5. **CQI is unusable in high-SNR scenarios:**
   - Saturates at maximum value (15) for all points
   - Provides no separability (all distributions identical)
   - Accuracy near random guessing (~7% vs 11.1% chance)

### Quantitative Comparison Summary

| Comparison | LOS | NLOS | Interpretation |
|:-----------|:----|:-----|:---------------|
| **Static vs Transition Gap** | +55.08% | +19.70% | Static dominance is stronger in LOS |
| **LOS vs NLOS (Static)** | 97.70% → 32.45% | -67% drop | Environment destroys performance |
| **LOS vs NLOS (Transition)** | 42.62% → 12.75% | -70% drop | Transitions degrade worse in NLOS |
| **Variance Penalty (Transition)** | +33% | +46% | NLOS suffers more from noise amplification |
| **Path Loss Increase (NLOS)** | - | +9.93 dB | Multipath scattering/reflection |
| **Best Overall** | LOS Static | 97.70% | Near-perfect localization |
| **Worst Overall** | NLOS Transition | 12.75% | Barely better than random (4.2%) |
   - Perfect correlation (linear relationship)
   - Use either interchangeably

5. **CQI is unusable:**
   - Saturates at maximum value in both scenarios
   - No discrimination power

### Theoretical Insight

The failure of the transition approach stems from a **spatial correlation assumption violation**:

**Assumption:** Small-scale fading is correlated over 2m → deltas cancel noise  
**Reality:** Fading is uncorrelated over 2m → deltas amplify noise

At 3 GHz (λ ≈ 10 cm), the **coherence distance** is approximately 0.3-0.5m. At 2m spacing, the channel realizations are essentially independent, causing:
```
Var(Δ) = Var(RSS₁) + Var(RSS₂) - 2·Cov(RSS₁, RSS₂)
       ≈ 2σ²  (since Cov ≈ 0)
```

### Future Work

1. **Test smaller grid spacing (0.5m):**
   - May fall within coherence distance
   - Could enable variance cancellation

2. **Hybrid ML models:**
   - Use transitions as auxiliary features, not primary predictors
   - XGBoost with [RSS, SINR, Δ_RSS, position_history]

3. **Sequential tracking:**
   - Particle filters with transition-based motion models
   - Use high-gradient edges as confidence resets

4. **Multi-frequency analysis:**
   - Test at 5 GHz (smaller coherence distance)
   - Test at sub-6 GHz (larger coherence distance)

5. **Real-world validation:**
   - Indoor environments with controlled geometry
   - Actual smartphone measurements

---

## Reproducibility

All results are reproducible using:
```matlab
% For LOS
config.scenario = '3GPP_38.901_UMa_LOS';
run('experiments/08_static_vs_walk/exp13e_transition_based_localization.m')

% For NLOS
config.scenario = '3GPP_38.901_UMa_NLOS';
run('experiments/08_static_vs_walk/exp13e_transition_based_localization.m')
```

**Random seed:** Fixed (rng(42)) for consistency

---

## References

- QuaDRiGa Channel Model: Jaeckel et al., 2014
- 3GPP 38.901 UMa Scenario: 3GPP TR 38.901 V14.0.0
- Bhattacharyya Distance: Bhattacharyya, 1943
- Maximum Likelihood Estimation: Duda, Hart & Stork, 2001

---

*Report generated: January 1, 2026*  
*Experiments: exp13e (LOS & NLOS comparison)*
