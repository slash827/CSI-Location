# Multi-User Diversity, Mobility Physics & Uncertainty Quantification

This document details the architecture, roadmap, and mathematical formulations for the **200-User Diversity Simulation Framework**, **Delta-Time ($\Delta t$) Feature Integration**, **Multi-Task Speed Prediction**, and **90% Confidence Radius Estimation (Google Maps Confidence Circle)**.

---

## 1. Roadmap of Current Execution Steps

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Step 1: 200-User Diversity MATLAB Simulation                                     │
│  - 200 users, N_steps ~ U(400, 600) (~100,000 sequence samples)                  │
│  - Mobility Classes: Pedestrians (1-1.5 m/s), Joggers (2.5-4.5), Vehicles (8-15) │
│  - Trajectory Patterns: Billiards/Road, Momentum Walk, Waypoints, Transit        │
│  - Hardware Profiles: 1, 2, 4 antennas, gain [-4, +2] dB, height [0.8, 1.8] m    │
└─────────────────────────────────────────┬────────────────────────────────────────┘
                                          │
                                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Step 2: Timestamp & Delta-Time (Δt) Feature Pipeline                             │
│  - Sequence Input: [RSS, SINR, AoA_Azimuth, AoA_Elevation, Delta_t]              │
│  - Explicit velocity scaling: (ΔCSI / Δt)                                        │
└─────────────────────────────────────────┬────────────────────────────────────────┘
                                          │
                                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Step 3: Multi-Task Learning Architecture (3 Outputs)                             │
│  - Head 1 (Primary): 3D Relative Cartesian Position (x, y, z) [meters]           │
│  - Head 2 (Auxiliary): Instantaneous Physical UE Speed v(t) [m/s]                │
│  - Head 3 (Uncertainty): 90% Confidence Radius Bounds R_90 [meters]              │
└─────────────────────────────────────────┬────────────────────────────────────────┘
                                          │
                                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Step 4: Unseen Cross-User Evaluation Split                                       │
│  - 160 Training Users (80%)  vs.  40 Completely Unseen Test Users (20%)          │
│  - Evaluates zero-shot hardware, trajectory, and mobility generalization         │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Confidence Radius Estimation ($R_{90}$): Concept & Purpose

In real-world cellular positioning (3GPP Rel-17/18 ISAC) and commercial navigation (Google Maps / Apple Maps), a predicted coordinate $(\hat{x}, \hat{y}, \hat{z})$ is incomplete without an **uncertainty boundary circle**:
* **High Certainty (Clean LOS, 4-antenna device, near BS):** Predicted $R_{90} \approx 2.1\text{ m}$ (Tight blue circle).
* **Low Certainty (Deep Multipath, 1-antenna device, far distance):** Predicted $R_{90} \approx 12.5\text{ m}$ (Large blue circle).

---

## 3. Mathematical Comparison of the Two Estimation Approaches

### Approach 1: Quantile Pinball Loss Regression ($q = 0.90$)

#### Mathematical Formulation
Let $e_i = \|\mathbf{y}_i - \hat{\mathbf{y}}_i\|_2$ be the true 3D Euclidean positioning error for sample $i$. Head 3 predicts a scalar radius $\hat{R}_{90, i}$.

We optimize Head 3 using the **Pinball (Quantile) Loss** at quantile $q = 0.90$:

$$\mathcal{L}_{\text{pinball}}(e_i, \hat{R}_{90, i}) = \begin{cases} 
q \cdot (e_i - \hat{R}_{90, i}) & \text{if } e_i \ge \hat{R}_{90, i} \quad (\text{Underestimation penalty}) \\
(1 - q) \cdot (\hat{R}_{90, i} - e_i) & \text{if } e_i < \hat{R}_{90, i} \quad (\text{Overestimation penalty})
\end{cases}$$

#### Key Advantages
1. **Non-Parametric & Distribution-Free:** Makes **zero assumption** about the underlying shape of the error distribution (Gaussian, Rayleigh, or Rician).
2. **Direct 90% Guarantee:** The loss function mathematically guarantees that the predicted radius $\hat{R}_{90}$ bounds exactly $90\%$ of empirical test errors.
3. **Robust to Outliers:** Unlike squared error, pinball loss is linear and resilient to extreme multipath spikes.

#### Limitations
* Predicts only a single fixed quantile boundary ($q=0.90$). If the application later asks for $R_{95}$ or $R_{50}$, a separate quantile must be trained or interpolated.

---

### Approach 2: Heteroscedastic Gaussian Negative Log-Likelihood (NLL)

#### Mathematical Formulation
Head 1 predicts mean coordinates $\hat{\mathbf{y}}_i = [\hat{x}_i, \hat{y}_i, \hat{z}_i]$ and Head 3 predicts standard deviation $\hat{\sigma}_i > 0$ (using a Softplus activation: $\hat{\sigma}_i = \text{softplus}(z_i) + \epsilon$).

We optimize Head 1 and Head 3 jointly using the **Negative Log-Likelihood (NLL)** loss:

$$\mathcal{L}_{\text{NLL}}(\mathbf{y}_i, \hat{\mathbf{y}}_i, \hat{\sigma}_i) = \frac{\|\mathbf{y}_i - \hat{\mathbf{y}}_i\|_2^2}{2\hat{\sigma}_i^2} + \log \hat{\sigma}_i$$

The 90% confidence radius is directly derived as:

$$R_{90, i} = k_{90} \cdot \hat{\sigma}_i \quad \text{where } k_{90} \approx 2.15 \text{ (for 3D Chi/Rayleigh error bounds)}$$

#### Key Advantages
1. **Full Probabilistic Variance ($\hat{\sigma}^2$):** Outputs a continuous variance parameter $\hat{\sigma}^2$ that can be directly plugged into **Kalman Filters**, Extended Kalman Filters (EKF), or multi-sensor fusion engines.
2. **Smooth Joint Gradient:** Automatically balances coordinate prediction and uncertainty; when coordinate error is high, the model increases $\hat{\sigma}_i$ to prevent loss explosion.

#### Limitations
1. **Gaussian Residual Assumption:** Assumes positioning errors follow an isotropic 3D Gaussian distribution, which may slightly underestimate heavy-tailed multipath error spikes.

---

## 4. Comparison Summary & Recommendation

| Dimension | Approach 1: Quantile Pinball Loss ($q=0.90$) | Approach 2: Heteroscedastic Gaussian NLL |
| :--- | :--- | :--- |
| **Error Distribution Assumption** | **None** (Distribution-Free) | Assumes 3D Gaussian / Rayleigh noise |
| **Target Variable** | True Euclidean Error $e_i = \|\mathbf{y}_i - \hat{\mathbf{y}}_i\|_2$ | Coordinates $\mathbf{y}_i$ & Variance $\hat{\sigma}_i^2$ |
| **90% Coverage Guarantee** | **Direct & Exact** via Pinball Loss | Analytical conversion ($R_{90} = 2.15 \hat{\sigma}$) |
| **Use Case in Industry** | **Google Maps blue circle UI** | **Kalman Filter & Sensor Fusion** |
| **Implementation Complexity** | Simple (Custom 4-line PyTorch Loss) | Simple (Custom NLL PyTorch Loss) |

### Recommended Plan of Action:
* **Primary Recommendation:** Implement **Approach 1 (Quantile Pinball Loss at $q=0.90$)** in our Multi-Task GRU/CNN notebook. It directly optimizes for the exact 90% confidence radius requested without making strong noise distribution assumptions.
* **Ablation Comparison:** We can compare both approaches in the notebook to report which provides tighter, more accurate 90% confidence circles on the 40 unseen test users!
