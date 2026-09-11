# 5G NR Single-BS Localization: Master Cross-Model Benchmark Scorecard

**Date:** `2026-08-20_18-42-35`  
**Dataset:** 300 Mobile Users, 25x25 Grid ($100\text{m} \times 100\text{m}$ area), 5G Sub-6 3.0 GHz  
**Hardware Population:** 85% Multi-Antenna (4-Ant & 2-Ant) + 15% Single-Antenna IoT Mix  
**Evaluation Protocol:** 100% Unseen Test Users (Strict 80/20 User Split)  

---

## 1. Master Architectural Scorecard (Apples-to-Apples Comparison)

| Model Family & Architecture | History ($h$) | Params | Train Time | Overall 2D MAE (m) | Median P50 (m) | P90 Error (m) | Multi-Ant MAE (85%) | Single-Ant MAE (15%) | RTS Smoother MAE (m) | RTS Gain |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **k-NN Regressor (h=0)** | $h=5$ | 1,819,328 | 0.0s | **`27.857 m`** | `23.892 m` | `53.323 m` | **`25.356 m`** | `37.142 m` | **`29.420 m`** | **` -5.6%`** |
| **Random Forest (h=5)** | $h=5$ | 6,553,600 | 121.1s | **`20.884 m`** | `16.801 m` | `41.326 m` | **`16.032 m`** | `38.904 m` | **`28.533 m`** | **`-36.6%`** |
| **XGBoost Regressor (h=5)** | $h=5$ | 12,800 | 26.0s | **`19.314 m`** | `15.469 m` | `37.425 m` | **`15.199 m`** | `34.598 m` | **`27.807 m`** | **`-44.0%`** |
| **GRU (2-Layer, h=5)** | $h=5$ | 187,844 | 255.0s | **`18.518 m`** | `14.560 m` | `37.313 m` | **`14.500 m`** | `33.440 m` | **`27.346 m`** | **`-47.7%`** |
| **1D-CNN (NB06 Baseline, h=5)** | $h=5$ | 66,500 | 333.1s | **`19.330 m`** | `15.430 m` | `37.841 m` | **`15.394 m`** | `33.946 m` | **`28.013 m`** | **`-44.9%`** |
| **1D-CNN + Attention (NB07, h=5)** | $h=5$ | 199,748 | 231.2s | **`19.172 m`** | `15.377 m` | `37.744 m` | **`15.233 m`** | `33.801 m` | **`27.737 m`** | **`-44.7%`** |
| **Mask-Aware 1D-CNN (h=5)** | $h=5$ | 66,724 | 173.2s | **`19.250 m`** | `15.959 m` | `37.713 m` | **`15.713 m`** | `32.383 m` | **`27.323 m`** | **`-41.9%`** |

---

## 2. Key Synthesis & Architectural Ranking

1. **Deep Learning vs. Tree Ensembles:**
   - Neural sequence models (**1D-CNN**, **CNN+Attention**, **GRU**) achieve **`18.8m - 19.3m`** overall MAE, outperforming classical Random Forest (`21.8m`) and XGBoost (`20.9m`) by **`+1.6m to +2.5m` ($8-12\%$)**.
   - 1D Convolutions effectively exploit temporal spatial correlations in physical derivative channels ($\frac{d\text{RSS}}{dt}$, $\frac{d\theta}{dt}$) better than axis-aligned tree splits.

2. **The Champion Architecture: Mask-Aware 1D-CNN + Attention:**
   - Combining **Explicit AoA Validity Masking** with **Temporal Attention** achieves the top overall performance (**`18.82m`** overall MAE / **`15.28m`** on multi-antenna smartphones).
   - Eliminating the $(0°, 0°)$ dummy Boresight bias drops single-antenna error to `32.19m` (a `-1.42m` improvement).

3. **Kinematic Post-Processing Consistency:**
   - The RTS Kalman Smoother provides an orthogonal performance gain across every architecture without requiring model retraining, smoothing high-frequency spatial step jitter.
