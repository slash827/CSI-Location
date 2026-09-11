# Option A: Explicit AoA Validity Masking Experiment Report

**Date:** `2026-08-20_17-23-13`  
**Dataset:** 300-User 25x25 Grid ($100\text{m} \times 100\text{m}$), 15% Single-Antenna Mix  

---

## 1. Head-to-Head Comparison

| Cohort / Metric | Unmasked Baseline | AoA-Masked Mitigation (Option A) | Delta | Improvement |
| :--- | :---: | :---: | :---: | :---: |
| **Overall 2D MAE** | `19.269 m` | **`18.866 m`** | **`-0.403 m`** | **`+2.09%`** |
| **Multi-Antenna MAE (85% share)** | `15.408 m` | **`15.279 m`** | **`-0.129 m`** | **`+0.84%`** |
| **Single-Antenna MAE (15% share)** | `33.607 m` | **`32.188 m`** | **`-1.419 m`** | **`+4.22%`** |
| **Single-Antenna Angular Error** | `15.84°` | **`14.83°`** | **`-1.02°`** | Angular Disambiguation |

---

## 2. Key Physical Takeaways

1. **Eliminating Dummy Boresight Bias:** By zeroing out $(\sin\theta, \cos\theta)$ such that $\sin^2 + \cos^2 = 0$ for single-antenna UEs, the network no longer mistakes dummy $(0°, 0°)$ for a physical direction vector toward the North-East axis.
2. **Single-Antenna Accuracy:** Single-antenna MAE changed from `33.61m` to `32.19m` (-1.42m), preventing misleading ray vector interference with RSS distance rings.
3. **Multi-Antenna Precision:** Multi-antenna UEs remain at high precision (`15.28m`), benefiting from clean gradient separation between beamforming-capable smartphones and IoT single-antenna devices.
