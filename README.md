# CSI-Based UE Location Prediction Project

## 📁 Project Structure

```
CSI_location/
├── experiments/           # All experimental scripts organized by complexity
│   ├── 01_basics/        # Start here - Basic QuaDRiGa usage
│   ├── 02_single_ue_analysis/  # CSI analysis and metrics
│   ├── 03_ue_movement/   # UE trajectory simulations
│   ├── 04_data_generation/  # Generate ML training datasets
│   └── 05_ml_training/   # Machine learning models
├── utils/                # Reusable functions and classes
│   └── CSIMetrics.m      # CSI to RSS/SINR/CQI conversion
├── results/              # Output files, plots, datasets
├── docs/                 # Documentation
└── README.md             # This file
```

---

## 🚀 Getting Started

### Prerequisites
1. **MATLAB** installed
2. **QuaDRiGa** installed and in MATLAB path

### Setup QuaDRiGa Path
```matlab
addpath(genpath('D:\programs\QuaDRiGa'));  % Adjust to your installation
savepath;
```

### Add Project Utils to Path
```matlab
addpath('utils');  % Makes CSIMetrics.m available everywhere
```

---

## 📚 Learning Path

Follow experiments in order:

### **Level 1: Basics** (experiments/01_basics/)
Learn QuaDRiGa fundamentals and CSI structure

### **Level 2: Single UE Analysis** (experiments/02_single_ue_analysis/)
Deep dive into CSI metrics, frequency analysis, CQI calculation

### **Level 3: UE Movement** (experiments/03_ue_movement/)
Simulate moving UE, track CSI changes over time

### **Level 4: Data Generation** (experiments/04_data_generation/)
Generate diverse datasets for ML training

### **Level 5: ML Training** (experiments/05_ml_training/)
Train models to predict UE location from CSI/CQI

---

## 🎯 Project Goal

Build a machine learning model that predicts User Equipment (UE) location based on observed Channel State Information (CSI) and Channel Quality Indicator (CQI) values.

**Target Performance**: < 10 meters mean localization error

---

## 📖 Documentation

See `docs/` folder for comprehensive guides:
- **SCRIPTS_EXPLAINED.md** - Complete explanation of all scripts
- **ML_LOCATION_PREDICTION_GUIDE.md** - Full ML project roadmap
- **QUICK_REFERENCE.md** - Quick commands and troubleshooting
- **WORKFLOW_VISUALIZATION.md** - Visual project flow

---

## 🏃 Quick Start

1. **Navigate to basics:**
   ```matlab
   cd experiments/01_basics
   ```

2. **Run first experiment:**
   ```matlab
   exp01_minimal_setup
   ```

3. **Progress through experiments** in order

4. **Check results** in `results/` folder

---

## 💡 Tips

- Always run from experiment folder (uses relative paths)
- Check console output for explanations
- Save figures to `../../results/` for later reference
- Read comments in each script for details
- Experiment with parameters!

---

*Last updated: October 31, 2025*
