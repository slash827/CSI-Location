# Project Workflow Visualization

## 📊 Complete Project Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         YOUR ML LOCATION PROJECT                         │
│                    From Simulation to Prediction                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: UNDERSTAND THE SCRIPTS (Week 1-2)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
        ┌──────────────────┐  ┌─────────────┐  ┌──────────────────┐
        │ simple_full_csi  │  │ csi_matrix_ │  │ simulate_ue_     │
        │ _matrix.m        │  │ of_one_user │  │ movement_v2.m    │
        │                  │  │ .m          │  │                  │
        │ Basic Setup      │  │ CSI + CQI   │  │ Moving UE        │
        │ 1 BS + 1 UE      │  │ Frequency   │  │ Time series      │
        │ Static           │  │ Analysis    │  │ Metrics tracking │
        └──────────────────┘  └─────────────┘  └──────────────────┘
                    │              │              │
                    └──────────────┼──────────────┘
                                   │
                                   ▼
                        ┌────────────────────┐
                        │  CSIMetrics.m      │
                        │  (Helper Class)    │
                        │  RSS, SINR, CQI    │
                        └────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: GENERATE TRAINING DATA (Week 3-4)                              │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────┐
    │  my_ue_movement_experiment.m (YOUR SCRIPT)               │
    │  ├─ Define trajectory (linear, circular, random)         │
    │  ├─ Set scenario (LOS, NLOS, Indoor)                     │
    │  ├─ Run QuaDRiGa simulation                              │
    │  └─ Output: CSI + Position data                          │
    └──────────────────────────────────────────────────────────┘
                               │
                               │ Run Multiple Times
                               │ (Different trajectories)
                               ▼
    ┌──────────────────────────────────────────────────────────┐
    │  DATASET COLLECTION                                      │
    │  ├─ Trajectory 1: Linear movement, LOS                   │
    │  ├─ Trajectory 2: Circular path, NLOS                    │
    │  ├─ Trajectory 3: Random walk, LOS                       │
    │  ├─ ...                                                   │
    │  └─ Trajectory N: (50-100 trajectories)                  │
    └──────────────────────────────────────────────────────────┘
                               │
                               ▼
    ┌──────────────────────────────────────────────────────────┐
    │  RAW DATA                                                │
    │  ├─ CSI_magnitude: [Nsc × T]                            │
    │  ├─ CSI_phase: [Nsc × T]                                │
    │  ├─ RSS, SINR, CQI: [T × 1]                             │
    │  └─ Positions (x,y,z): [3 × T]                          │
    └──────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: FEATURE ENGINEERING (Week 5-6)                                 │
└─────────────────────────────────────────────────────────────────────────┘

    Raw CSI/CQI Data
           │
           ▼
    ┌────────────────────────────────────────┐
    │  extract_features() function           │
    │                                        │
    │  ┌──────────────────────────────────┐ │
    │  │ Temporal Features:               │ │
    │  │  • CQI mean, std, trend          │ │
    │  │  • SINR mean, std, min, max      │ │
    │  │  • RSS mean, std, rate_of_change │ │
    │  └──────────────────────────────────┘ │
    │                                        │
    │  ┌──────────────────────────────────┐ │
    │  │ Frequency Features:              │ │
    │  │  • CSI spectral statistics       │ │
    │  │  • Coherence bandwidth           │ │
    │  │  • Frequency selectivity         │ │
    │  │  • Number of fades               │ │
    │  └──────────────────────────────────┘ │
    │                                        │
    │  ┌──────────────────────────────────┐ │
    │  │ Derived Features:                │ │
    │  │  • Estimated distance            │ │
    │  │  • Doppler indicators            │ │
    │  │  • Multi-BS differences          │ │
    │  └──────────────────────────────────┘ │
    └────────────────────────────────────────┘
           │
           ▼
    Feature Matrix: [N_samples × N_features]
    Labels: [N_samples × 2]  (x, y positions)

┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: MACHINE LEARNING (Week 7-10)                                   │
└─────────────────────────────────────────────────────────────────────────┘

    Dataset Split:
    ├─ Train (70%)
    ├─ Validation (15%)
    └─ Test (15%)
           │
           ▼
    ┌─────────────────────────────────────────────────┐
    │  MODEL SELECTION                                │
    │                                                 │
    │  Option A: Random Forest (MATLAB)              │
    │  ├─ Fast training                              │
    │  ├─ Feature importance                         │
    │  └─ Good baseline                              │
    │                                                 │
    │  Option B: Neural Network (MATLAB)             │
    │  ├─ Feedforward network                        │
    │  ├─ 3-4 hidden layers                          │
    │  └─ Better accuracy                            │
    │                                                 │
    │  Option C: Deep Learning (Python/PyTorch)      │
    │  ├─ Flexible architectures                     │
    │  ├─ Advanced optimization                      │
    │  └─ Best performance                           │
    │                                                 │
    │  Option D: LSTM (Python/PyTorch)               │
    │  ├─ Temporal sequence modeling                 │
    │  ├─ Captures motion patterns                   │
    │  └─ State-of-the-art for trajectories          │
    └─────────────────────────────────────────────────┘
           │
           ▼
    Trained Model
           │
           ▼
    ┌─────────────────────────────────────────────────┐
    │  PREDICTION                                     │
    │  Input: Features from new CSI/CQI               │
    │  Output: Predicted (x, y) position              │
    └─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: EVALUATION & ANALYSIS (Week 11-12)                             │
└─────────────────────────────────────────────────────────────────────────┘

    Test Set Predictions
           │
           ▼
    ┌──────────────────────────────────────┐
    │  ERROR METRICS                       │
    │  ├─ Euclidean distance error         │
    │  ├─ Mean error                       │
    │  ├─ Median error                     │
    │  ├─ 90th percentile error            │
    │  └─ CDF of errors                    │
    └──────────────────────────────────────┘
           │
           ├──────────────────────────────┐
           │                              │
           ▼                              ▼
    ┌─────────────────┐         ┌──────────────────┐
    │  VISUALIZATION  │         │ FEATURE ANALYSIS │
    │  • Scatter plot │         │ • Importance     │
    │  • CDF curve    │         │ • Correlation    │
    │  • Error heatmap│         │ • Selection      │
    └─────────────────┘         └──────────────────┘
           │                              │
           └──────────────┬───────────────┘
                          ▼
                ┌──────────────────┐
                │ INSIGHTS         │
                │ • Best features  │
                │ • Failure cases  │
                │ • Improvements   │
                └──────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 6: ADVANCED & THESIS (Week 13-14)                                 │
└─────────────────────────────────────────────────────────────────────────┘

    Advanced Techniques (Choose ≥1):
    ├─ Multi-BS triangulation
    ├─ LSTM temporal modeling
    ├─ Real-time tracking (Kalman filter)
    ├─ Transfer learning (sim → real)
    └─ Hybrid ML + geometric methods
           │
           ▼
    Final Evaluation
           │
           ▼
    Thesis/Paper Writing
    ├─ Introduction & Related Work
    ├─ Methodology (QuaDRiGa + ML)
    ├─ Experimental Setup
    ├─ Results & Analysis
    └─ Conclusion & Future Work
```

---

## 🔄 Iterative Development Cycle

```
     ┌─────────────────────────────────────────┐
     │                                         │
     ▼                                         │
┌─────────┐      ┌──────────┐      ┌─────────┴──┐
│ Generate│ ───► │ Extract  │ ───► │   Train    │
│  Data   │      │ Features │      │   Model    │
└─────────┘      └──────────┘      └─────────┬──┘
                                               │
                                               ▼
                                          ┌─────────┐
                        ┌─────────────────│ Evaluate│
                        │                 └─────────┘
                        │                      │
                        │    ┌─────────────────┘
                        │    │
                        ▼    ▼
                   ┌────────────┐
                   │  Analyze   │
                   │  • Error   │
                   │  • Features│
                   └──────┬─────┘
                          │
            ┌─────────────┼─────────────┐
            │             │             │
            ▼             ▼             ▼
     Improve Data   Improve Features  Improve Model
     (more diverse) (better extraction)(architecture)
            │             │             │
            └─────────────┴─────────────┘
                          │
                          ▼
                     (Repeat until
                      satisfied)
```

---

## 🎯 Decision Tree: Which Script to Use?

```
                    START
                      │
                      ▼
        ┌─────────────────────────────┐
        │ What do you want to do?     │
        └─────────────┬───────────────┘
                      │
         ┏━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━━━━━━━┓
         ▼                                       ▼
    Learn Basics?                         Generate Data?
         │                                       │
         ▼                                       ▼
    ┌─────────────┐                    ┌──────────────────┐
    │ START WITH: │                    │ Multiple         │
    │             │                    │ Trajectories?    │
    │ simple_full │                    └────────┬─────────┘
    │ _csi_matrix │                             │
    └─────────────┘                    ┏━━━━━━━━┻━━━━━━━━━┓
         │                             ▼                  ▼
         ▼                        Just 1?            Many (ML)?
    ┌─────────────┐                   │                  │
    │ THEN:       │                   ▼                  ▼
    │             │       ┌───────────────────┐  ┌──────────────┐
    │ csi_matrix_ │       │ my_ue_movement_   │  │ Batch script │
    │ of_one_user │       │ experiment.m      │  │ with loop    │
    └─────────────┘       └───────────────────┘  └──────────────┘
         │
         ▼
    ┌─────────────┐
    │ THEN:       │
    │             │
    │ simulate_ue_│
    │ movement_v2 │
    └─────────────┘
         │
         ▼
    Ready for ML!
```

---

## 📈 Performance Progression

```
Expected Localization Error Over Project Timeline:

Error (meters)
  │
50│                                          Your Project Goal
  │                                          ═══════════════
  │                                          Get below this line!
40│
  │
30│  ●
  │   ╲                                     
20│    ●                                    ╔══════════════════════════╗
  │     ╲                                   ║ Excellent: < 5m          ║
15│      ●                                  ║ Good:      5-10m         ║
  │       ╲━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ║ Acceptable: 10-15m       ║
10│        ●━━━━━━━●                        ╚══════════════════════════╝
  │                 ╲       ●
 5│                  ●━━━━━━●━━━━━━━━━●    ← Target
  │
 0└────────────────────────────────────────►
   W1  W2   W4   W6   W8   W10  W12  W14    Weeks

   ●: Baseline (random)
   ●: Random Forest baseline
   ●: More data
   ●: Better features
   ●: Neural Network
   ●: LSTM + optimization
   ●: Final model
```

---

## 🔧 Tool Selection Guide

```
┌─────────────────────────────────────────────────────────┐
│ TASK                    │ TOOL                          │
├─────────────────────────┼───────────────────────────────┤
│ Channel Simulation      │ QuaDRiGa (MATLAB)             │
│ CSI Analysis           │ MATLAB (built-in functions)   │
│ Feature Extraction     │ MATLAB (custom functions)     │
│ Basic ML               │ MATLAB (TreeBagger, NN)       │
│ Advanced ML            │ Python (PyTorch, TensorFlow)  │
│ Visualization          │ MATLAB (plotting)             │
│ Data Management        │ MAT files + CSV               │
│ Version Control        │ Git                           │
│ Documentation          │ Markdown + MATLAB comments    │
└─────────────────────────┴───────────────────────────────┘
```

---

## 🎓 Learning Resources Map

```
                    ┌──────────────────────┐
                    │ SCRIPTS_EXPLAINED.md │
                    │ (Foundation)         │
                    └──────────┬───────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ Scripts  │   │   CSI    │   │ QuaDRiGa │
        │ Overview │   │ Concepts │   │  Usage   │
        └──────────┘   └──────────┘   └──────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ QUICK_REFERENCE.md   │
                    │ (Day-to-day)         │
                    └──────────┬───────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │Commands  │   │Troublesh.│   │Workflows │
        └──────────┘   └──────────┘   └──────────┘
                               │
                               ▼
                    ┌──────────────────────────┐
                    │ ML_LOCATION_PREDICTION   │
                    │ _GUIDE.md (Project Plan) │
                    └──────────┬───────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │              │               │              │
        ▼              ▼               ▼              ▼
   ┌────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ Data   │   │ Features │   │    ML    │   │Advanced  │
   │ Gen    │   │ Extract  │   │ Pipeline │   │Techniques│
   └────────┘   └──────────┘   └──────────┘   └──────────┘
```

---

## 📊 Data Flow Diagram

```
┌───────────────┐
│   QuaDRiGa    │
│  Simulation   │
└───────┬───────┘
        │ Generates
        ▼
┌────────────────────────────────┐
│  Channel Taps & Delays         │
│  • H_taps: [Nrx×Ntx×Ntaps×T]  │
│  • taus: [1×Ntaps×T]           │
└───────┬────────────────────────┘
        │ FFT Transform
        ▼
┌────────────────────────────────┐
│  Frequency-Domain CSI          │
│  • H_sc: [Nrx×Ntx×Nsc×T]      │
│  • Complex values              │
└───────┬────────────────────────┘
        │ CSIMetrics.compute()
        ▼
┌────────────────────────────────┐
│  Wireless Metrics              │
│  • RSS_dBm_wb: [T×1]           │
│  • SINR_dB_wb: [T×1]           │
│  • CQI_wb: [T×1]               │
└───────┬────────────────────────┘
        │ extract_features()
        ▼
┌────────────────────────────────┐
│  Feature Matrix                │
│  • X: [N_samples × N_features] │
│  • Normalized, cleaned         │
└───────┬────────────────────────┘
        │ + Position Labels
        ▼
┌────────────────────────────────┐
│  ML Dataset                    │
│  • X: Features                 │
│  • y: [x, y] positions         │
│  • Split: train/val/test       │
└───────┬────────────────────────┘
        │ Model.train()
        ▼
┌────────────────────────────────┐
│  Trained ML Model              │
│  • Can predict location        │
│  • From CSI/CQI input          │
└───────┬────────────────────────┘
        │ Model.predict()
        ▼
┌────────────────────────────────┐
│  Location Prediction           │
│  • Estimated (x, y)            │
│  • Confidence (optional)       │
└────────────────────────────────┘
```

---

This visualization guide helps you understand:
1. **Complete project workflow** from start to finish
2. **Which script to use** for each task
3. **How data flows** through the pipeline
4. **Expected progress** over 14 weeks
5. **Decision points** in your implementation

Keep this handy as a **mental model** of your project!
