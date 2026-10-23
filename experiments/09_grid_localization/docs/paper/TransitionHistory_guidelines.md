# Comprehensive Research Plan: Proving the Robustness of CSI Transition History in Cellular ISAC

## PART 1: The Vision and Narrative Storyline

### 1.1 The Central Narrative ("The Red Thread")

The peak performance of complex localization architectures is often a moving target, heavily dependent on proprietary deep learning tweaks and massive datasets. Rather than presenting a heavy, non-interpretable neural network, **this paper establishes a universal, lightweight, plug-and-play temporal augmentation framework for cellular ISAC systems.** Our central narrative is **"Universal Robustness through Temporal History."** We demonstrate that simply appending a short sequence of historical CSI states ($h$) to the input of standard, highly interpretable machine learning baselines (XGBoost, Random Forest) yields massive positioning accuracy leaps.

We prove this across three key pillars:

1. **History compensates for physical/geometric limits:** When Angle of Arrival (AoA) is unavailable (single-antenna legacy UEs) or highly degraded, temporal transition history acts as a robust physical fail-safe.
2. **History overrides base station deployment constraints:** If a base station is constrained to a corner of a sector (narrow angular spread), the spatial-temporal transitions reconstruct absolute coordinates better than static measurements.
3. **Low-overhead deployability:** The approach requires zero structural changes to existing base station estimators—it is a pure feature-engineering step.

---

### 1.2 Proposed Paper Structure and Outline

* **Section 1: Introduction & Motivation**
* Introduce cellular-based positioning using existing base station measurements.
* Highlight the **"Distance-Ring Ambiguity"** inherent to single-BS setups, where static fingerprints (RSS/SINR) fail to uniquely identify coordinates due to multipath mapping issues.
* State our contribution: Showing that CSI transition history acts as a universal, lightweight augmentation layer for standard ML algorithms.


* **Section 2: System Architecture & Channel Modeling**
* Describe the 3GPP QuaDRiGa-driven channel environments (**UMa** and **UMi** setups). Detail how spatial consistency guarantees that consecutive measurements are directionally and physically correlated.
* Formally define the transition history sliding window: $x_{\text{input}} = [m(t-h), \dots, m(t)]$.


* **Section 3: The "Absolute vs. Delta" Paradox**
* Address the counterintuitive finding: Why absolute measurements serve as spatial landmarks (anchoring the model within the specific propagation profile of the UMa/UMi grid), whereas delta features lose absolute location reference.


* **Section 4: Compensating for Physical and Geometric Degradation**
* Prove the failure of AoA-dependent models when the BS is physically constrained (e.g., NE-Corner) or when noise scales up dynamically. Highlight history as a robust defense mechanism.


* **Section 5: Empirical Comparison: Classification vs. Regression**
* Present a clean, direct comparison of standard Random Forest and XGBoost architectures across Classification (grid-based discretization) and Regression (direct coordinate mapping).
* Provide computational and memory footprint details to outline real-world deployability trade-offs at the edge.


* **Section 6: Discussion & System Recommendations**
* Provide the final consortium recommendation table mapping network constraints to feature configurations.



---

## PART 2: Comprehensive Simulation and Experimental Plan

This set of experiments is designed to run systematically on your existing traditional ML framework (XGBoost and Random Forest) using standard 3GPP UMa and UMi scenarios.

### Phase 1: Data Hygiene & Standardizing the Splitting Methodology

* **Objective:** Eliminate temporal path leakage to ensure the models are genuinely learning localized spatial gradients rather than memorizing a specific chronological walk.
* **Experiment 1.1: Sequence Segment Shuffling (The Leakage Fix)**
* *Setup:* Instead of splitting the "one very long walk" strictly chronologically ($80/20$), slice the continuous trajectory walk into independent, overlapping segments of length $N$ (e.g., $N=5$). Randomly shuffle these segments into Train and Test sets.
* *Goal:* Verify that the transition history captures *local spatial gradients* rather than simply memorizing the global path.


* **Experiment 1.2: Standardized MAE Evaluation**
* *Setup:* Convert all results to a single evaluation metric: **Euclidean distance error (MAE) in meters** for both classification and regression.
* *Goal:* Produce a single master plot showing RF vs. XGBoost side-by-side across both environments (UMa and UMi) and across grid resolutions (e.g., $15\times15$ vs $25\times25$).



---

### Phase 2: Resolving the "Absolute vs. Delta" Paradox

* **Objective:** Provide physical and engineering intuition for why absolute CSI values outperform coordinate differences in 3GPP channels.
* **Experiment 2.1: Feature Engineering Breakdown**
* *Setup:* Run three distinct configurations:
1. **Absolute Features Only:** $[m(t), m(t-1), m(t-2)]$.
2. **Delta Features Only:** $[\Delta m(t), \Delta m(t-1)]$ where $\Delta m(t) = m(t) - m(t-1)$.
3. **Hybrid Feature Set:** Absolute snapshot $m(t)$ combined with difference lags $[\Delta m(t), \Delta m(t-1)]$.


* *Goal:* Demonstrate that absolute CSI acts as a "landmark anchor" (tying the user to the local multipath scenario), while delta features act as "velocity/direction vectors." We expect the **Hybrid Feature Set** to resolve the performance gap, giving the consortium a highly robust feature template.



---

### Phase 3: Physical Geometry & Hardware Stress-Testing

* **Objective:** Prove that history acts as a crucial physical buffer when spatial angular hardware parameters scale down.
* **Experiment 3.1: The Base Station Field-of-View Sweep**
* *Setup:* Compare Center BS (broad $360^\circ$ angular coverage) against NE Corner BS (restricted $52^\circ$ angular coverage) in the UMa environment.
* *Goal:* Formally plot how localization performance decays as the BS moves to the edge. Show that the **History Gain** ($h=0 \rightarrow h=3$) expands to recover almost all of the lost spatial accuracy when the BS angle is restricted.


* **Experiment 3.2: Dynamic AoA Jitter and Legacy Device Degradation**
* *Setup:* Sweep estimation noise standard deviation $\sigma_{AoA}$ from $0^\circ$ (clean) to $20^\circ$ (extremely noisy) and evaluate models with $h=0$ vs. $h=3$. Additionally, test on User 3 (single-antenna legacy device simulation, zero AoA availability).
* *Goal:* Show that history provides a critical safety net: as spatial hardware measurements (AoA) degrade, reliance shifts naturally to temporal trends.



---

### Phase 4: Scaling & Device Heterogeneity

* **Objective:** Assess how well the history-based models generalize across diverse user populations.
* **Experiment 4.1: User Diversity Scaling**
* *Setup:* Run tests under varying training sets:
* *Scenario A:* Train on 2 users (high data per user), test on remaining users.
* *Scenario B:* Train on all 5 users.


* *Goal:* Prove that history-boosted models maintain generalization and resist overfitting when tested on device configurations they have never encountered before.



---

## PART 3: Immediate Next Steps

Before launching the full suite of simulation sweeps, you should execute these three high-priority baseline tasks to secure the project’s data pipeline.

### Step 1: Implement Sequence Segment Shuffling (Eliminate Leakage)

To ensure the paper is scientifically rigorous, we must prevent the models from memorizing the "long walk."

* **Task:** Write a Python function to slice the continuous channel trajectory arrays into small, rolling blocks of $N = 5$ consecutive steps.
* **Task:** Randomly partition these block IDs into Train ($80\%$) and Test ($20\%$). This ensures consecutive steps within a test block are never seen during training, preventing chronological leakage.

### Step 2: Establish the Standardized Evaluation Utility

* **Task:** Ensure the evaluation script converts classification predictions (classes/grid coordinates) directly into absolute Euclidean distance error in meters.
* **Task:** Align the regression outputs to output Cartesian $(x, y)$ coordinates directly, computing the Euclidean distance error in meters:

$$\text{MAE} = \frac{1}{M} \sum_{i=1}^{M} \sqrt{(x_{\text{pred},i} - x_{\text{true},i})^2 + (y_{\text{pred},i} - y_{\text{true},i})^2}$$



### Step 3: Run the First Diagnostic Baseline (The Core "No-AoA" Sweep)

Run a single, focused diagnostic sweep to validate the updated pipeline:

* **Setup:** * **Environment:** UMi (Urban Micro) single-BS setup.
* **Features:** RSS and SINR (strip out AoA entirely).
* **Sweep:** History levels $h \in [0, 1, 3]$.
* **Models:** XGBoost vs. Random Forest (with default/current tuned parameters).


* **Expected Output:** Confirm that even with sequence segment shuffling and zero AoA data, the transition history ($h=3$) still yields a substantial accuracy lift over the static ($h=0$) baseline. This confirms that the thesis holds true under strict data hygiene.