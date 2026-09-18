# 5G NR CSI Localization: Handover Knowledge Base & Project Synthesis

> **Status:** Current, Validated & Fully Committed on branch `main`  
> **Last Updated:** 2026-09-18  
> **Workspace Root:** `experiments/09_grid_localization/`  
> **Primary References:**  
> - Detailed Technical Document: [`docs/Project_documentation/technical_documentation.md`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/Project_documentation/technical_documentation.md)  
> - High-Level Research Overview: [`docs/Project_documentation/research_documentation.md`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/Project_documentation/research_documentation.md)  
> - Presentation Slide Deck: [`docs/Project_documentation/PRESENTATION_SLIDES.md`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/Project_documentation/PRESENTATION_SLIDES.md)  
> - Discussion Transcript with Alon Levin: [`data/meeting_20_08_26.txt`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/data/meeting_20_08_26.txt)

---

## 0. Start here (added 2026-09-18, machine transition)

Read these two files **before** citing any number or writing into the report:

| File | Why |
| :--- | :--- |
| **`CORRECTIONS_LEDGER.md`** | Ten claims that were once in these documents and have since been measured and withdrawn. The superseded numbers are still sitting in `results_of_record/` and in older Google Doc snapshots, so they are easy to reintroduce by accident. |
| **`MATLAB_RERUN_RUNBOOK.md`** | The only work still outstanding: two MATLAB + QuaDRiGa jobs, with prerequisites, commands and sanity checks. |

**State as of this hand-off:**

* Every Python experiment is complete — Tier A (A1–A5), Tier B (B1–B5), and a
  regenerated master-benchmark scorecard. See `EXPERIMENTS_BACKLOG.md`.
* Two MATLAB jobs remain. They were blocked on an **expired MATLAB trial licence**
  (not hardware): every `INCREMENT` line in `licenses/trial_*.lic` expired
  16-Nov-2025. QuaDRiGa 2.8.1 was installed and fine. The failure mode is
  misleading — `matlab -batch` hangs for minutes, then exits `0x00000001` with an
  empty log.
* `results/` is gitignored. The ablation scripts need
  `results/grid_localization/grid_25x25/sim_data_300users_*` to exist locally; see
  `SHARING.md` for how to obtain it.

**Three claims in this document's own §1 and §2 are now stale** and are corrected in
the ledger: the $\Delta	ext{MAE} = -15.7\%$ headline is now measured per family as
$11.0$–$14.7\%$ with confidence intervals (§5.7 of the report); the "4 Voronoi
propagation areas: Park (LOS), Highway (LOS)…" line in §2 below describes what the
config *declares*, not what was simulated — Campaign B is uniformly NLOS; and the
$h=5$ window should be described in metres of path, not seconds.

---

## 1. Executive Summary & Research Positioning

### 1.1 The Core Scientific Question
Can temporal transition history ($h$) and physical inductive biases resolve the fundamental **distance-ring ambiguity** inherent to single-Base Station (BS) cellular localization without private UE-side telemetry (GPS or internal IMUs)?

### 1.2 Research Positioning (Aligned with Alon Levin's Guidance)
In our research discussion with Alon Levin on August 20, 2026, we established the strategic framing for this project:

1. **Avoid the "Single Best Model" Pitfall:**
   - *Alon's Advice:* *"Are we positioning it as: we are introducing a method to improve the accuracy of any such model… or are we looking at: we are making the best model? If you claim you have the best model, someone can say 'everybody creates a new model every day'. Whereas if you just suggest an improvement to the mechanism… you don't need to show you have the best results, just that you're improving the results for every single model."*
   - *Our Position:* We frame transition history ($h$) as a **universal physical-kinematic mechanism**. Adding sequential history breaks the distance-ring symmetry and systematically reduces positioning error ($\Delta\text{MAE} = -15.7\%$) across **all** explored model families (Tree Ensembles, RNNs, 1D-CNNs, Transformers).

2. **Decouple Hardware Cohort Physics ($N \ge 2$ vs. $N=1$):**
   - *Alon's Advice:* *"The single antenna case is an outlier precisely because it has no AoA information available whatsoever… Instead of doing aggregate results across all these devices, do a per-device class statistical summary and plot them against each other… The one antenna case is completely off the charts, and then you explain it because it's missing AoA."*
   - *Our Position:* We show that modern multi-antenna smartphones ($85\%$ of traffic) achieve **`14.58 m` MAE / `12.31 m` Median** ($3.5^\circ$ angle error). Single-antenna IoT devices ($15\%$ mix) have zero AoA observability, suffering radial distance smearing ($34.5\text{m}$ MAE) that inflates the aggregate mean to $19.3\text{m}$.

3. **Distill Insights into Clean Figures:**
   - Rather than dense text dumps, we summarize the research through two publication-grade dual-panel figures: universal $\Delta\text{MAE}$ curves across all models and per-antenna cohort CDFs.

---

## 2. Experimental Environment & Setup

* **Simulation Engine:** QuaDRiGa 5G Channel Simulator (realistic spatial consistency, 3GPP 38.901 Urban Macro).
* **Carrier Frequency:** 3.0 GHz (5G NR Sub-6 GHz), 100 MHz bandwidth.
* **Spatial Grid:** $100\text{m} \times 100\text{m}$ area ($25 \times 25$ grid, $4\text{m}$ resolution).
* **BS Infrastructure:**
  - Single serving Base Station at $[116, 116, 10]\text{m}$ (Top-Right / North-East).
  - Pushed South-West interfering towers at $[-60, 53, 10]\text{m}$ and $[53, -60, 10]\text{m}$.
  - 4 Voronoi propagation areas: Park (LOS), Highway (LOS), Shopping District (NLOS), Residential (NLOS).
* **User Population:** 300 unseen mobile users. **Not random walks** — four trajectory patterns (billiards 35%, momentum walk 35%, waypoint tour 20%, straight transit 10%) and four speed classes (pedestrian 40% at $1.0$–$1.5\,$m/s, jogger 25% at $2.5$–$4.5$, vehicle 25% at $8$–$15$, static 10% at $0.1$–$0.5$). All four patterns are heading-persistent.
* **Window duration is user-dependent:** step duration is spacing/speed, so a fixed $h$ is *not* a fixed time window. Per-user $\Delta t$ spans $0.27$–$32.5\,$s, making the $h=5$ window anywhere from $1.3\,$s to $162\,$s (median $13.5\,$s).
* **Interference:** users are batched 25 per shared QuaDRiGa layout, but SINR counts only the two interfering base stations plus noise. **No user-to-user interference is modelled.**
* **Evaluation Protocol:** Strict 80/20 train/test split on **unseen users** (User ID disjoint, Seed=42).
* **Hardware Cohorts (Standard 3GPP Rel-15/16 Evaluation Benchmark):**
  - **85% Multi-Antenna Devices:** 4-antenna and 2-antenna smartphones (beamforming-capable, active AoA estimation).
  - **15% Single-Antenna Devices:** Budget IoT devices (no beamforming, dummy $0^\circ$ AoA).

---

## 3. Key Empirical Findings & Master Benchmark

### 3.1 History Depth Sweep & $\Delta\text{MAE}$ Analysis ($h \in [0, 10]$)

Adding sequence history systematically reduces positioning error. Two distinct deltas are reported and must not be conflated:

* **Step $\Delta$MAE** — change vs. the *previous* history depth in the sweep (marginal value of the extra frames).
* **Cumulative $\Delta$MAE** — change vs. the $h=0$ snapshot baseline (headline gain of the mechanism).

| History $h$ | MAE | P50 | P90 | Step $\Delta$MAE (vs. prev. $h$) | Cumulative $\Delta$MAE (vs. $h=0$) | Cumulative gain |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| $h = 0$ (snapshot baseline) | `22.846 m` | `20.170 m` | `41.488 m` | — | — | — |
| $h = 1$ | `21.284 m` | `18.397 m` | `39.378 m` | `-1.562 m` | `-1.562 m` | **$+6.8\%$** |
| $h = 3$ | `20.026 m` | `16.654 m` | `38.647 m` | `-1.258 m` | `-2.820 m` | **$+12.3\%$** |
| $h = 5$ | **`19.260 m`** | **`15.228 m`** | **`38.005 m`** | `-0.766 m` | `-3.586 m` | **$+15.7\%$** 🏆 |
| $h = 10$ | `20.215 m` | `16.485 m` | `37.472 m` | `+0.955 m` | `-2.631 m` | $+11.5\%$ (regresses) |

*Sign convention: negative $\Delta\text{MAE}$ (metres) = error reduced. The **Cumulative gain** column reports the same reduction as a positive percentage, matching `technical_documentation.md` §8.*

Interpretation:
* $h = 1$ is where the model first gains instantaneous velocity $\mathbf{v}$ — the single largest step gain, and the point at which distance-ring symmetry is broken.
* $h = 5$ is the **empirical sweet spot for this model**; all master-benchmark models in §3.2 are evaluated there. Note this is *six samples*, not a fixed duration — window length spans $1.3$–$162\,$s across the population (§2), so any statement of the form '$h=5 \approx 2.5\text{s}$' holds for one speed class only.
* $h = 10$ *regresses* for this model (positive step $\Delta$). This is **not universal**: the 1D-CNN and $k$-NN turn at $h=10$, while XGBoost and Random Forest keep improving through $h=10$ on the same data. Fixed-window estimators must consume every lag; tree ensembles can decline to split on an uninformative one. Any claim that $h=5$ is a shared optimum is unsupported.

### 3.2 Master Cross-Model Benchmark Scorecard (Apples-to-Apples at $h=5$)

*Evaluated on identical 300-user unseen test splits ($100\text{m} \times 100\text{m}$ grid, 15% single-antenna mix, Seed=42)*:

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
  - Boundary crossings between Voronoi cells cost nothing: crossing samples average $18.33\text{m}$ MAE against $19.34\text{m}$ within-cell steady state, i.e. marginally *better*. QuaDRiGa spatial consistency prevents transient jumps, so scenario changes are not corrupting the sequences.

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

## 4.5 September 2026 ablations — what changed

Five experiments run 2026-09-13 (scripts in `src/python/experiments_ablation/`,
summaries in `docs/results_of_record/ablations_2026_09/`). Three of them revised
claims that had been stated elsewhere in this knowledge base:

| Finding | Effect on earlier claims |
| :--- | :--- |
| **History gain is 3.3× larger in LOS** (+15.98%) than NLOS (+4.84%) | New confirmatory evidence. Also explains why NLOS posts *lower absolute* error: those positions are more identifiable from a snapshot, so they start better and have less to gain |
| **Noise floor measured**: marginal seed spread 1.85 m, seed-paired CI ±0.29 m | The top-four model ranking in the master scorecard is a **statistical tie**. "GRU is best" (18.518 vs 1D-CNN 19.330) is a 0.812 m gap and is not established |
| **AoA masking does not generalise** — helps 1 of 3 non-convolutional models | The masking contribution is scoped to architectures *without* conditional structure. Trees already branch on `n_antennas`, so the validity flag is redundant for them |
| **Tree ensembles saturate rather than turn** — h ∈ [10,30] spans 0.053 m | Earlier wording of "still improving at h=10" is replaced by "saturates by h≈10, flat to h=30" |
| **Path-loss constants fitted**: γ = 3.26, σ = 10.11 dB, R² = 0.20 | Replaces assumed γ=4 / 6 dB. Naive-ranging bound rises from 32.9 m to 67.9 m, so the model beats it by ~5× rather than 2.4×. The R² is itself a result: range explains only 20% of RSS variance |

**Also fixed in this period:** a defect where the Kalman/RTS smoother received
z-scored `delta_t` instead of seconds, clamping 85.8% of steps to 0.01 s (commit
`dee50dd`). Every pre-fix smoothing number was measuring that bug; all raw MAE
results are unaffected.

---

## 5. Recommended Next Steps for the New Chat

1. **Review and Rehearse Presentation Slides:**
   - Walk through [`docs/Project_documentation/PRESENTATION_SLIDES.md`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/Project_documentation/PRESENTATION_SLIDES.md).
   - Ensure the narrative transitions cleanly across the 3 acts: (1) Single-BS Distance-Ring Ambiguity, (2) Universal $\Delta\text{MAE}$ gain via History, (3) Hardware Cohort Discontinuity and AoA Masking.
2. **Draft the Final Project Report / Paper Sections:**
   - Use [`docs/Project_documentation/technical_documentation.md`](file:///d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/docs/Project_documentation/technical_documentation.md) (Sections 8 and 9) as the source of truth for the methodology and empirical evaluation chapters.
