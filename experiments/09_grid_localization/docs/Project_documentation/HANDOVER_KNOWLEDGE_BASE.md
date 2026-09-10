# 5G NR CSI Localization: Handover Knowledge Base & Project Synthesis

> **Status:** Current & Validated  
> **Last Updated:** September 2026  
> **Workspace Root:** `experiments/09_grid_localization/`  
> **Primary References:**  
> - Detailed Technical Document: [`docs/Project_documentation/technical_documentation.md`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/Project_documentation/technical_documentation.md)  
> - Presentation Slides: [`docs/Project_documentation/PRESENTATION_SLIDES.md`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/Project_documentation/PRESENTATION_SLIDES.md)  
> - Discussion Notes with Alon Levin: [`data/meeting_20_08_26.txt`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/data/meeting_20_08_26.txt)

---

## 1. Executive Summary & Research Positioning

### 1.1 The Core Scientific Question
Can transition history ($h$) and physical inductive biases resolve the fundamental **distance-ring ambiguity** inherent to single-Base Station (BS) cellular localization without private UE-side telemetry (GPS or internal IMUs)?

### 1.2 Research Positioning (Aligned with Alon Levin's Guidance)
As agreed in our team discussion with Alon, **the project is NOT positioned as "we built a single better model"** (which is vulnerable to trivial model-to-model competition). 

Instead, **the project is positioned as a generalizable physical-kinematic mechanism**:
1. **Universal $\Delta\text{MAE}$ Gain:** Introducing temporal transition history ($h$) provides a systematic accuracy gain ($\Delta\text{MAE} = -15.7\%$) across *all* model families (Tree Ensembles, RNNs, 1D-CNNs, Attention).
2. **Distance-Ring Ambiguity Resolution:** In single-BS deployments, static signal strength (RSS/SINR) only defines an iso-power distance ring. Sequential history provides velocity vector constraints ($\mathbf{v} \approx \frac{\Delta\mathbf{r}}{\Delta t}$) that break this symmetry.
3. **Decoupled Hardware Physics:** Explaining the 2.3x performance gap between multi-antenna smartphones ($14.6\text{m}$ MAE) and single-antenna IoT devices ($34.5\text{m}$ MAE) as a fundamental physical limit of single-BS AoA observability, rather than model failure.

---

## 2. Experimental Environment & Setup

* **Simulation Engine:** QuaDRiGa 5G Channel Simulator (realistic spatial consistency, 3GPP 38.901 Urban Macro).
* **Carrier Frequency:** 3.0 GHz (5G NR Sub-6 GHz), 100 MHz bandwidth.
* **Spatial Grid:** $100\text{m} \times 100\text{m}$ area ($25 \times 25$ grid, $4\text{m}$ resolution).
* **BS Infrastructure:**
  - Single serving Base Station at $[116, 116, 10]\text{m}$ (Top-Right / North-East).
  - Pushed South-West interfering towers at $[-60, 53, 10]\text{m}$ and $[53, -60, 10]\text{m}$.
  - 4 Voronoi propagation areas: Park (LOS), Highway (LOS), Shopping District (NLOS), Residential (NLOS).
* **User Population:** 300 unseen mobile users with continuous random-walk trajectories.
* **Evaluation Protocol:** Strict 80/20 train/test split on **unseen users** (User ID disjoint, Seed=42).
* **Hardware Cohorts (Standard 3GPP Rel-15/16 Evaluation Benchmark):**
  - **85% Multi-Antenna Devices:** 4-antenna and 2-antenna smartphones (beamforming-capable, active AoA estimation).
  - **15% Single-Antenna Devices:** Budget IoT devices (no beamforming, dummy $0^\circ$ AoA).

---

## 3. Key Empirical Findings & Benchmarks

### 3.1 History Depth Sweep & $\Delta\text{MAE}$ Analysis ($h \in [0, 10]$)
Adding sequence history systematically reduces positioning error:
* **$h = 0$ (Snapshot Baseline):** `22.846 m` MAE (P50: `20.170 m`, P90: `41.488 m`)
* **$h = 1$:** `21.284 m` MAE ($\Delta\text{MAE} = \mathbf{-1.562 m}$, **$+6.8\%$ gain** — computes velocity vector $\mathbf{v}$)
* **$h = 3$:** `20.026 m` MAE ($\Delta\text{MAE} = \mathbf{-1.258 m}$, **$+12.3\%$ cumulative gain**)
* **$h = 5$:** `19.260 m` MAE ($\Delta\text{MAE} = \mathbf{-0.766 m}$, **$+15.7\%$ cumulative gain**) $\to$ **Empirical Sweet Spot** ($\approx 2.5\text{s}$)
* **$h = 10$:** `20.215 m` MAE ($\Delta\text{MAE} = +0.955 m$ — decorrelation/overfitting as random-walk headings decorrelate after $3\text{–}4\text{s}$).

### 3.2 Master Cross-Model Benchmark Scorecard (Apples-to-Apples at $h=5$)

| Model Architecture | History | Params | Train Time | Overall 2D MAE | Median P50 | Multi-Ant MAE (85%) | Single-Ant MAE (15%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **k-NN Regressor (Baseline)** | $h=0$ | — | `0.0 s` | **`27.857 m`** | `23.892 m` | `25.356 m` | `37.142 m` |
| **Random Forest Regressor** | $h=5$ | $6.5\text{M}$ | `121.1 s` | **`20.884 m`** | `16.801 m` | `16.032 m` | `38.904 m` |
| **XGBoost Regressor** | $h=5$ | $12.8\text{K}$ | `26.0 s` | **`19.314 m`** | `15.469 m` | `15.199 m` | `34.598 m` |
| **GRU (2-Layer Recurrent)** | $h=5$ | $187.8\text{K}$ | `255.0 s` | **`18.518 m`** | `14.560 m` | **`14.500 m`** | `33.440 m` |
| **1D-CNN (NB06 Baseline)** | $h=5$ | $66.5\text{K}$ | `333.1 s` | **`19.330 m`** | `15.430 m` | `15.394 m` | `33.946 m` |
| **1D-CNN + Attention (NB07)** | $h=5$ | $199.7\text{K}$ | `231.2 s` | **`19.172 m`** | `15.377 m` | `15.233 m` | `33.801 m` |
| **Mask-Aware 1D-CNN (Option A)** | $h=5$ | $66.7\text{K}$ | `173.2 s` | **`19.250 m`** | `15.959 m` | `15.713 m` | **`32.383 m`** 🏆 |

### 3.3 Hardware Discontinuity & Outlier Trajectory Audit
* **Multi-Antenna UEs (4-Ant & 2-Ant):** **`14.58 m` MAE / `12.31 m` Median** (Mean angular error $3.5^\circ\text{–}3.7^\circ$).
* **Single-Antenna UEs (1-Ant):** **`34.54 m` MAE / `30.23 m` Median** (Mean angular error $15.8^\circ$, P90: $33.9^\circ$).
* **Outlier Trajectory Audit:**
  - **100% of top 5 worst outliers are 1-antenna devices** ($33.5\text{m}\text{–}52.9\text{m}$).
  - **100% of top 5 best users are multi-antenna devices** ($10.4\text{m}\text{–}11.8\text{m}$).
  - Boundary crossings between Voronoi cells only exhibit a negligible $+1.45\text{m}$ transient penalty, proving the data is physically sound and not corrupted.

### 3.4 Architectural Mitigation: Explicit AoA Validity Masking (Option A)
* **Problem:** Dummy $(0^\circ, 0^\circ)$ AoA in single-antenna UEs caused $\cos(0^\circ)=1.0$ and $\text{ray}_y = r_{\text{est}}$, artificially anchoring predictions along the North-East axis.
* **Solution:** Zero-out $(\sin\theta=0, \cos\theta=0)$ so $\sin^2+\cos^2=0$ (mathematically outside the unit circle), zero-out ray vectors, and supply an explicit `has_valid_aoa` binary channel.
* **Result:** Single-antenna MAE dropped from `33.61m` to **`32.19m` ($-1.42\text{m}$ / $-4.2\%$)**, while multi-antenna accuracy remained preserved at `15.28m`.

---

## 4. Codebase Map & Key Assets

### 4.1 Production Notebooks
* [`Multi-User-Environment/06_cnn_h5_derived_features.ipynb`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/src/python/notebooks/Multi-User-Environment/06_cnn_h5_derived_features.ipynb): 1D-CNN baseline with early stopping, derived feature pipeline, inline trajectory plots.
* [`Multi-User-Environment/07_cnn_attn_h5_derived_features.ipynb`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/src/python/notebooks/Multi-User-Environment/07_cnn_attn_h5_derived_features.ipynb): 1D-CNN + Temporal Self-Attention notebook with early stopping and trajectory maps.

### 4.2 Shared Reusable Utilities
* [`utils/csi_dataset.py`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/src/python/utils/csi_dataset.py): Shared `build_derived_features`, `load_and_prepare_data`, and `DerivedCSI1DDataset`.
* [`utils/training_utils.py`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/src/python/utils/training_utils.py): Shared `EarlyStopping`, `run_kalman_and_rts_2d`, `apply_kalman_smoother`, `collect_test_predictions`, and trajectory plotting.
* [`utils/environment_viz.py`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/src/python/utils/environment_viz.py): Fixed distance calculation, Voronoi cell lookup, and interferer distance binning.

### 4.3 Documentation Visual Figures (`docs/figures/`)
* [Figure 8.1: Macro-cell Spatial Environment Map](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/figures/environment_spatial_layout.png)
* [Figure 8.2: Angular Azimuth Tracking: Multi vs. Single Antenna](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/figures/diagnostic_angular_tracking_multi_vs_single.png)
* [Figure 8.3: Best-Case Trajectory Tracking (User 119, 10.4m MAE)](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/figures/diagnostic_BEST_user_119_ant2.png)
* [Figure 8.4: Outlier Failure Mode: User 250 (1-Antenna Radial Smearing)](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/figures/diagnostic_WORST_user_250_ant1.png)
* [Figure 8.5: Universal $\Delta\text{MAE}$ Curves Across All Model Families](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/figures/universal_delta_mae_history_curves.png)
* [Figure 8.6: Per-Device Antenna Cohort Error CDF & Reachability](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/figures/antenna_cohort_error_cdf.png)

---

## 5. Next Steps Completed & Validated (Aligned with Alon Levin)

1. [x] **Plot Unified $\Delta\text{MAE}$ Curves Across All Models:**
   - Generated [`docs/figures/universal_delta_mae_history_curves.png`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/figures/universal_delta_mae_history_curves.png) using [`src/python/plotting/plot_unified_delta_mae.py`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/src/python/plotting/plot_unified_delta_mae.py).
   - Demonstrates systematic downward error curves across 1D-CNN, XGBoost, Random Forest, and GRU, confirming the universal physical-kinematic gain mechanism and empirical sweet spot at $h=5$ ($\sim 2.5\text{s}$).
2. [x] **Per-Device Antenna Cumulative Distribution Function (CDF):**
   - Generated [`docs/figures/antenna_cohort_error_cdf.png`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/figures/antenna_cohort_error_cdf.png) using [`src/python/plotting/plot_antenna_cohort_cdf.py`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/src/python/plotting/plot_antenna_cohort_cdf.py).
   - Demonstrates that smartphones hit $<10\text{m}$ in $>34\%$ of steps and $<15\text{m}$ in $60\%$ of steps (median $\approx 13.4\text{m}$), whereas single-antenna IoT devices are constrained to $30.6\text{m}$ median error due to missing AoA.
3. [x] **Synchronize High-Level Documents:**
   - Updated [`docs/Project_documentation/research_documentation.md`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/Project_documentation/research_documentation.md) with complete 3-Act narrative, Sections 8, 9, 10, and figures.
   - Updated [`docs/Project_documentation/PRESENTATION_SLIDES.md`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/Project_documentation/PRESENTATION_SLIDES.md) with slides matching the unified narrative, master benchmark scorecard table, and figure embeds.

