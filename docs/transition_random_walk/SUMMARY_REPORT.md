**Date:** January 1, 2026
**Scenario:** 3GPP UMa NLOS
**Grid:** 3x3 (2m spacing)
**Steps:** 10,000 (Random Walk)

## 1. Executive Summary
The experiment tested the hypothesis that **RSS transitions (deltas)** between grid points provide better separability and localization accuracy than **static absolute RSS values**.

**Result:** The hypothesis was **not supported** in the NLOS environment.
- **Static Localization Accuracy:** 32.45% (9 classes)
- **Transition Classification Accuracy:** 12.75% (24 classes)

While the transition approach failed to outperform static localization globally, specific transitions (particularly those involving Point 1 near the BS) showed strong directional signatures that could be useful as auxiliary features.

## 2. Statistical Comparison

| Metric | Static RSS | Transitions (Deltas) | Analysis |
| :--- | :--- | :--- | :--- |
| **Avg Std Dev ($\sigma$)** | **1.07 dB** | 1.56 dB | **Negative Result:** The variance of the delta increased rather than decreased. This indicates that small-scale fading at point A and point B is uncorrelated, leading to $Var(A-B) \approx Var(A) + Var(B)$. |
| **Separability (Bhattacharyya)** | 0.630 | 0.633 | **Neutral:** The statistical distance between classes is virtually identical for both methods. |
| **Accuracy** | **32.45%** | 12.75% | **Negative Result:** Static classification is significantly more robust. |

## 3. Detailed Analysis

### A. The "Zero-Mean" Problem
Several transitions had a mean delta close to 0 dB, making them indistinguishable from "staying in place" or moving to another equidistant point.
- **2 $\leftrightarrow$ 3:** $\mu \approx 0.00$ dB (Moving sideways relative to BS)
- **2 $\leftrightarrow$ 5:** $\mu \approx -0.39$ dB
- **4 $\leftrightarrow$ 7:** $\mu \approx -0.64$ dB

In these cases, the geometry of the grid relative to the BS results in similar path losses, so the transition carries no information other than noise.

### B. The "Steep Gradient" Success
Transitions moving radially towards/away from the BS (Point 1 is closest) showed strong signatures:
- **1 $\to$ 4:** $\mu = -3.86$ dB (Strong drop)
- **4 $\to$ 1:** $\mu = +3.80$ dB (Strong rise)
- **1 $\to$ 2:** $\mu = -2.40$ dB
- **2 $\to$ 1:** $\mu = +2.44$ dB

These specific edges are highly reliable. A tracking algorithm could use these large jumps to "reset" or confirm position with high confidence.

### C. Confusion Matrix Insights (Static)
The static classifier struggled with points that have similar path loss:
- **Point 5** ($\mu=-57.65$) was frequently confused with **Point 2** ($\mu=-57.27$) and **Point 4** ($\mu=-58.72$).
- **Point 9** ($\mu=-59.13$) was confused with **Point 7** ($\mu=-59.27$).

## 4. Conclusion & Recommendation
1.  **Pure transition-based localization is not viable** as a standalone method in NLOS because the delta variance is too high and many transitions are ambiguous (zero mean).
2.  **Hybrid Approach:** The strong gradients near the BS (Points 1, 2, 4) are valuable. A particle filter could use standard RSS likelihoods generally, but apply a "Transition Update" when a large delta (> 3 dB) is detected, effectively locking the position to a radial movement near the BS.
