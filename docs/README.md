# CSI Location Project - Documentation

This folder contains comprehensive documentation for your CSI-based UE location prediction project using QuaDRiGa simulations and machine learning.

---

## 📄 Documentation Files

### 1. [SCRIPTS_EXPLAINED.md](SCRIPTS_EXPLAINED.md) - **START HERE**
**Complete guide to understanding the QuaDRiGa scripts**

**What's inside:**
- Detailed explanation of each MATLAB script in the CSI_location folder
- How the scripts connect to each other
- Step-by-step tutorial for creating your own UE movement simulation
- Different movement patterns (linear, circular, random walk)
- Troubleshooting common issues
- Key concepts: CSI, CQI, frequency-selective fading

**Read this first to**:
- Understand what each script does
- Learn how to run your first simulation
- Get the foundation for the ML project

---

### 2. [ML_LOCATION_PREDICTION_GUIDE.md](ML_LOCATION_PREDICTION_GUIDE.md) - **YOUR PROJECT ROADMAP**
**Complete machine learning pipeline for UE location prediction**

**What's inside:**
- **Phase 1**: Data generation strategy (diverse trajectories, scenarios)
- **Phase 2**: Feature engineering (25+ features from CSI/CQI)
- **Phase 3**: ML pipeline (Random Forest, Neural Networks, LSTMs)
- **Phase 4**: Evaluation metrics and performance analysis
- **Phase 5**: Next steps and advanced improvements
- **Phase 6**: 14-week implementation roadmap

**Complete code examples for**:
- Generating training datasets
- Extracting features from wireless measurements
- Training ML models in MATLAB and Python
- Evaluating localization accuracy
- Advanced techniques (LSTM, multi-BS, real-time tracking)

**Read this to**:
- Plan your ML project from start to finish
- Understand the full data → model → evaluation pipeline
- Get research directions for novel contributions
- Follow the week-by-week roadmap

---

### 3. [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - **KEEP THIS HANDY**
**Quick reference card for day-to-day work**

**What's inside:**
- Quick start commands
- Common tasks (view CSI, change scenarios, adjust parameters)
- Troubleshooting solutions
- Data analysis tips
- Typical workflows
- Key variables reference
- Checklists and pro tips

**Use this when**:
- You need to quickly look up a command
- You encounter an error (troubleshooting section)
- You want to change a specific parameter
- You need to remember file organization
- You want a quick workflow checklist

---

## 🎯 How to Use This Documentation

### Complete Beginner? Follow this path:

1. **Read**: [SCRIPTS_EXPLAINED.md](SCRIPTS_EXPLAINED.md) - Sections 1-2 (first two scripts)
2. **Do**: Run `simple_full_csi_matrix.m` in MATLAB
3. **Read**: [SCRIPTS_EXPLAINED.md](SCRIPTS_EXPLAINED.md) - Section "How to Create Your Own Simulation"
4. **Do**: Run `my_ue_movement_experiment.m` and examine the outputs
5. **Experiment**: Modify trajectory, scenario, parameters using [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
6. **Read**: [ML_LOCATION_PREDICTION_GUIDE.md](ML_LOCATION_PREDICTION_GUIDE.md) - Overview and Phase 1
7. **Plan**: Your ML project using the 14-week roadmap

### Ready for ML? Follow this path:

1. **Review**: [ML_LOCATION_PREDICTION_GUIDE.md](ML_LOCATION_PREDICTION_GUIDE.md) - Complete read
2. **Generate**: 10 test trajectories using modified experiment script
3. **Extract**: Features using code from Phase 2
4. **Train**: Baseline Random Forest model (Phase 3)
5. **Evaluate**: Performance (Phase 4)
6. **Expand**: Generate 50-100 diverse trajectories (Phase 1)
7. **Improve**: Models and features (Phase 5)
8. **Use**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for day-to-day tasks

### During Development? Use this:

- **Morning**: Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - "Typical Workflow" section
- **Coding**: Keep [QUICK_REFERENCE.md](QUICK_REFERENCE.md) open for quick lookups
- **Stuck**: Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - "Troubleshooting" first
- **Planning**: Refer to [ML_LOCATION_PREDICTION_GUIDE.md](ML_LOCATION_PREDICTION_GUIDE.md) - Phase 6 roadmap
- **Research**: Read [ML_LOCATION_PREDICTION_GUIDE.md](ML_LOCATION_PREDICTION_GUIDE.md) - Phase 5 "Research Directions"

---

## 🎓 Project Overview

**Your Goal**: Build a machine learning model that predicts User Equipment (UE) location based on observed Channel State Information (CSI) and Channel Quality Indicator (CQI) values over time.

**Approach**:
1. **Simulate**: Generate realistic wireless channels using QuaDRiGa
2. **Collect**: CSI and CQI measurements for UE at known positions
3. **Extract**: Meaningful features from wireless measurements
4. **Train**: Machine learning models (Random Forest, Neural Networks, LSTMs)
5. **Evaluate**: Localization accuracy (target: < 10 meters mean error)
6. **Analyze**: What features are most important? How does environment affect accuracy?

**Why this matters**:
- **5G/6G**: Location services without GPS (indoor, urban canyons)
- **Network optimization**: Resource allocation based on UE position
- **Research**: Novel approach combining wireless physics + machine learning
- **Real-world**: Applicable to autonomous vehicles, IoT, emergency services

---

## 📊 What You'll Learn

### Technical Skills:
- Wireless channel modeling (QuaDRiGa)
- Signal processing (time/frequency domain conversions)
- Feature engineering (extracting information from raw signals)
- Machine learning (supervised learning, deep learning)
- Model evaluation and validation
- MATLAB and Python programming

### Domain Knowledge:
- 5G NR channel characteristics
- CSI structure and interpretation
- Quality metrics (RSS, SINR, CQI)
- Multipath propagation and fading
- Location estimation techniques
- Indoor vs. outdoor propagation

### Research Skills:
- Literature review (related work)
- Experiment design (systematic evaluation)
- Performance analysis (statistical evaluation)
- Scientific writing (thesis/paper)
- Reproducible research practices

---

## 📂 Related Files in Project

Your project also includes a real-world dataset in `indoor_location/` folder:

```
indoor_location/
├── data/
│   ├── train_features_sampled.csv    ← Real indoor measurements
│   └── train_targets_sampled.csv     ← True locations
├── data_loader.py                     ← Load real data
├── train_baseline_model.py            ← ML baseline on real data
└── docs/                              ← Additional docs
```

**How it connects**:
- Your QuaDRiGa simulations: **Synthetic training data** (controllable, abundant)
- The indoor_location data: **Real measurements** (validate your approach)
- **Best strategy**: Train on synthetic, validate on real (transfer learning)

---

## ✅ Success Checklist

**Week 1-2: Foundation**
- [ ] Read SCRIPTS_EXPLAINED.md completely
- [ ] Run all 4 provided scripts successfully
- [ ] Understand CSI, CQI, RSS, SINR concepts
- [ ] Can modify trajectory and see results change
- [ ] Generated first 5 trajectories

**Week 3-4: Feature Engineering**
- [ ] Read ML guide Phase 2 (Feature Engineering)
- [ ] Implemented extract_features() function
- [ ] Extracted features from 10 trajectories
- [ ] Visualized feature distributions
- [ ] Identified promising features

**Week 5-6: Baseline Model**
- [ ] Read ML guide Phase 3 (ML Pipeline)
- [ ] Created train/val/test split
- [ ] Trained Random Forest baseline
- [ ] Achieved < 20m mean error
- [ ] Documented baseline performance

**Week 7-10: Full Dataset + Improvements**
- [ ] Generated 50+ diverse trajectories
- [ ] Multiple scenarios (LOS, NLOS)
- [ ] Re-trained with full dataset
- [ ] Tried Neural Network
- [ ] Achieved < 10m mean error

**Week 11-14: Advanced + Documentation**
- [ ] Implemented advanced technique (LSTM/multi-BS)
- [ ] Complete performance evaluation
- [ ] Feature importance analysis
- [ ] All code documented
- [ ] Results visualized
- [ ] Thesis/paper draft complete

---

## 🚀 Quick Start (First 30 Minutes)

**Right now, do these 5 things**:

1. **Open MATLAB** and navigate to `CSI_location/` folder

2. **Run first test**:
   ```matlab
   simple_full_csi_matrix
   ```
   ✅ Should see 1 plot and CSI dimensions printed

3. **Run second test**:
   ```matlab
   csi_matrix_of_one_user
   ```
   ✅ Should see 3 plots and metrics

4. **Run your experiment**:
   ```matlab
   my_ue_movement_experiment
   ```
   ✅ Should see 5 plots, 2 files created

5. **Examine output**:
   ```matlab
   load('my_experiment_data.mat')
   disp(results_table(1:10,:))
   ```
   ✅ Should see table with position, RSS, SINR, CQI

**If all worked → You're ready! Continue with SCRIPTS_EXPLAINED.md**

**If errors → Check QUICK_REFERENCE.md "Troubleshooting" section**

---

## 📚 Additional Resources

### Papers to Read:
- **Indoor Localization**: "Deep Learning Indoor Localization with Channel State Information" (foundational)
- **CSI Applications**: "CSI-based Positioning and Fingerprinting" (survey paper)
- **5G Location**: "Machine Learning for 5G Location Services" (overview)

### Online Resources:
- **QuaDRiGa**: Official documentation at Fraunhofer HHI website
- **CSI Tool**: Research tools for CSI extraction
- **3GPP Standards**: 38.901 (channel models), 38.214 (CQI definition)

### Your Own Resources:
- Real dataset in `indoor_location/` folder
- Sample code in `indoor_location/train_baseline_model.py`
- This documentation :)

---

## 💬 Questions to Ask Yourself

**Understanding (Week 1-2)**:
- ❓ What is CSI and why does it vary with location?
- ❓ How does multipath propagation create frequency-selective fading?
- ❓ Why does CQI change as UE moves?
- ❓ What's the difference between LOS and NLOS scenarios?

**Design (Week 3-6)**:
- ❓ Which features are most informative for location?
- ❓ How much training data do I need?
- ❓ What's my baseline to beat?
- ❓ How do I validate my model?

**Analysis (Week 7-12)**:
- ❓ Why does my model work better in LOS than NLOS?
- ❓ What's the theoretical lower bound on localization error?
- ❓ Which scenarios generalize well?
- ❓ What are the failure cases?

**Research (Week 11-14)**:
- ❓ What's novel about my approach?
- ❓ How does it compare to state-of-the-art?
- ❓ What are the limitations?
- ❓ What are the future work directions?

---

## 🎯 Expected Outcomes

**By End of Project**:

✅ **Deliverables**:
- Working ML model for UE localization
- Dataset of 100+ simulated trajectories
- Trained models (Random Forest, Neural Network, potentially LSTM)
- Complete evaluation (metrics, plots, analysis)
- Well-documented code
- Master's thesis or research paper

✅ **Performance Targets**:
- Mean localization error: **< 10 meters** (good) or **< 5 meters** (excellent)
- Model trained on diverse scenarios (LOS, NLOS, indoor, outdoor)
- Validated on held-out test set
- Feature importance analysis completed
- Comparison with baselines (trivial, state-of-the-art)

✅ **Skills Gained**:
- Wireless channel modeling expertise
- ML/deep learning practical experience
- Signal processing skills
- Research methodology
- Scientific writing

---

## 🏁 Final Notes

This documentation is your **complete roadmap** from zero to finished project. Everything you need is here:

- **Theory**: Explained in SCRIPTS_EXPLAINED.md
- **Practice**: Code examples in all guides
- **Reference**: QUICK_REFERENCE.md for daily use
- **Project Plan**: ML_LOCATION_PREDICTION_GUIDE.md

**Work systematically, document everything, and don't hesitate to experiment!**

**Good luck with your master's project! 🎓📡🚀**

---

*Last updated: October 31, 2025*
