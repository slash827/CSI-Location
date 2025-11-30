# ML Training Folder Reorganization Guide

**Date:** November 18, 2025  
**Status:** Complete

## 📁 New Folder Structure

The `ml_training` folder has been reorganized for better clarity and maintainability.

### Core Modules (`core/`)

**Purpose:** Essential functionality used across the project

```
core/
├── config.py                    # Project configuration and paths
├── loaders/
│   └── data_loader.py          # CSI dataset loading and parsing
├── preprocessing/
│   └── preprocessing.py        # Data preprocessing and normalization
└── utils/
    └── utils.py                # Utility functions
```

**Usage:**
```python
from core.config import DEFAULT_DATASET_PATH
from core.loaders.data_loader import CSIDataLoader
from core.preprocessing.preprocessing import Preprocessor
```

### Analysis Tools (`analysis/`)

**Purpose:** Data exploration, visualization, and comparison

```
analysis/
├── exploratory/
│   ├── eda.py                  # Exploratory Data Analysis
│   ├── analyze_datasets.py     # Dataset comparison and statistics
│   ├── analyze_metadata.py     # Metadata extraction and analysis
│   └── inspect_mat.py          # MATLAB file inspection
└── comparison/
    ├── compare_feature_selection.py  # Feature selection comparison
    └── compare_cnn_results.py        # CNN model comparison
```

**Usage:**
```bash
python analysis/exploratory/eda.py
python analysis/comparison/compare_cnn_results.py
```

### Scripts (`scripts/`)

**Purpose:** Standalone executable scripts

```
scripts/
├── quickstart.py               # Quick start guide script
├── data_generation/
│   └── generate_and_filter_data.py  # Data generation utilities
└── visualization/
    └── plot_results.py         # Result visualization
```

**Usage:**
```bash
python scripts/quickstart.py
python scripts/data_generation/generate_and_filter_data.py
```

### Documentation (`docs/`)

**Purpose:** Project documentation and guides

```
docs/
├── README.md                           # Main project README
├── QUICKSTART.md                       # Quick start guide
├── OVERVIEW.md                         # Project overview
├── QUICK_REFERENCE.md                  # Quick reference
├── ACHIEVEMENT_SUMMARY.md              # Project achievements
├── BASELINE_FIXED.md                   # Baseline fixes
├── DATASET_COMPARISON.md               # Dataset comparison
├── EARLY_STOPPING_INFO.md              # Early stopping guide
├── FEATURE_ANALYSIS_RESULTS.md         # Feature analysis
├── FEATURE_SELECTION_FAILURE_ANALYSIS.md
├── ISSUE_RESOLVED.md                   # Resolved issues
├── LOGGING_SYSTEM_SUMMARY.md           # Logging system
├── NEURAL_NETWORK_PLAN.md              # NN architecture plan
├── OPTIMIZATION_STRATEGY.md            # Optimization strategies
├── REORGANIZATION_COMPLETE.md          # Previous reorganization
├── REORGANIZATION_PLAN.md              # Previous plans
├── SETUP_COMPLETE.md                   # Setup documentation
└── TROUBLESHOOTING.md                  # Troubleshooting guide
```

### Experiments (`experiments/`)

**Purpose:** Experimental code and model training

```
experiments/
├── compare_runs.py                     # Compare experiment runs
├── run_baseline.py                     # Run baseline models
├── run_optimized_models.py             # Run optimized models
├── feature_engineering/                # Feature engineering experiments
├── los_only/                           # LOS-only experiments
├── nlos_conditions/                    # NLOS experiments
└── neural_networks/                    # Neural network experiments
    └── (see Neural Networks section below)
```

### Data Folders (unchanged)

```
data/                  # Training data
models/                # Saved models
output/                # Output files
results/               # Experiment results
runs/                  # TensorBoard runs
```

---

## 🧠 Neural Networks Reorganization (`experiments/neural_networks/`)

### Training Scripts (`training_scripts/`)

**Purpose:** Main training scripts for different model architectures

```
training_scripts/
├── train.py                    # Basic CNN training
├── train_advanced.py           # Advanced training with techniques
├── train_improved_cnn.py       # Improved CNN (11.47m MAE winner!)
├── train_independent_norm.py   # Independent normalization training
└── train_optimized.py          # Optimized training configuration
```

**Usage:**
```bash
cd experiments/neural_networks/training_scripts
python train_improved_cnn.py --epochs 80 --lr 0.001
python train_independent_norm.py --epochs 50 --patience 10
```

### Debugging Tools (`debugging/`)

**Purpose:** Debugging, testing, and diagnostic scripts

```
debugging/
├── debug_simple_cnn.py         # CNN debugging
├── test_shapes.py              # Shape compatibility tests
├── test_predictions.py         # Prediction testing
├── check_consistency.py        # Consistency validation
├── check_nlos_dist.py          # NLOS distribution check
└── diagnose_exp11.py           # exp11 diagnostics
```

**Usage:**
```bash
cd experiments/neural_networks/debugging
python test_shapes.py
python diagnose_exp11.py
```

### Analysis Tools (`analysis/`)

**Purpose:** Model comparison, visualization, and analysis

```
analysis/
├── compare_models.py           # Compare different models
├── compare_cnn_results.py      # Compare CNN architectures
├── visualize_lr_schedules.py   # Learning rate visualization
├── understand_normalization.py # Normalization analysis
└── verify_normalization_fix.py # Verify normalization fix
```

**Usage:**
```bash
cd experiments/neural_networks/analysis
python compare_models.py
python visualize_lr_schedules.py
```

### Documentation (`documentation/`)

**Purpose:** Neural network documentation and results

```
documentation/
├── README.md                       # Neural networks overview
├── ADVANCED_TRAINING_GUIDE.md      # Advanced training guide
├── CNN_COMPARISON.md               # CNN architecture comparison
├── OPTIMIZATION_GUIDE.md           # Optimization guide
├── OPTIMIZATION_STRATEGIES.md      # Strategy details
├── RESULTS.md                      # Training results
├── ROOT_CAUSE_ANALYSIS.md          # Problem analysis
├── TRAINING_SESSION_SUMMARY.md     # Session summaries
└── cnn_comparison.png              # Comparison visualization
```

### Archived Experiments (`archived_experiments/`)

**Purpose:** Old experiments and deprecated code

```
archived_experiments/
├── run_advanced_experiments.py  # Old advanced experiments
├── run_all.py                   # Old batch runner
└── (previous archived files)
```

### Saved Models (`saved_models/`)

**Purpose:** Trained model checkpoints (unchanged)

```
saved_models/
├── improved_cnn_best.pth        # Best Improved CNN (11.47m MAE)
├── simple_cnn_best.pth          # Simple CNN checkpoint
└── ...
```

### Shared Modules (root level)

```
experiments/neural_networks/
├── models.py                    # Model architecture definitions
├── __init__.py                  # Package initialization
└── __pycache__/                 # Python cache
```

---

## 🔄 Migration Guide

### Updating Import Paths

**Old imports:**
```python
# Old way (before reorganization)
from config import DEFAULT_DATASET_PATH
from data_loader import CSIDataLoader
from preprocessing import Preprocessor
```

**New imports:**
```python
# New way (after reorganization)
from core.config import DEFAULT_DATASET_PATH
from core.loaders.data_loader import CSIDataLoader
from core.preprocessing.preprocessing import Preprocessor
```

### Running Scripts

**Before:**
```bash
cd ml_training
python quickstart.py
python eda.py
python train.py  # (in experiments/neural_networks)
```

**After:**
```bash
cd ml_training
python scripts/quickstart.py
python analysis/exploratory/eda.py

cd experiments/neural_networks/training_scripts
python train.py
```

### Finding Documentation

**All `.md` files are now in:**
- `ml_training/docs/` - General documentation
- `experiments/neural_networks/documentation/` - Neural network specific docs

---

## 📋 Quick Reference

### I want to...

**Load data:**
```python
from core.loaders.data_loader import CSIDataLoader
loader = CSIDataLoader('path/to/dataset')
```

**Train a model:**
```bash
cd experiments/neural_networks/training_scripts
python train_improved_cnn.py --epochs 80
```

**Compare models:**
```bash
cd experiments/neural_networks/analysis
python compare_models.py
```

**Analyze datasets:**
```bash
cd analysis/exploratory
python analyze_datasets.py
```

**Debug shape issues:**
```bash
cd experiments/neural_networks/debugging
python test_shapes.py
```

**Read documentation:**
```bash
# General docs
cat docs/QUICKSTART.md
cat docs/OVERVIEW.md

# Neural network docs
cat experiments/neural_networks/documentation/README.md
cat experiments/neural_networks/documentation/RESULTS.md
```

---

## 🎯 Benefits of New Structure

### ✅ Improved Organization
- **Logical grouping** by functionality
- **Clear separation** of concerns
- **Easier navigation** for new contributors

### ✅ Better Maintainability
- **Core modules** isolated and reusable
- **Scripts** clearly separated from libraries
- **Documentation** centralized and organized

### ✅ Scalability
- **Easy to add** new experiments
- **Clear structure** for new model architectures
- **Organized** archived code

### ✅ Professional Structure
- **Industry-standard** folder layout
- **Package-like** organization
- **Clear entry points** for users

---

## 📚 Related Documentation

- **Main Project README:** `../../README.md`
- **Project Presentation:** `../../PROJECT_PRESENTATION.md`
- **Technical FAQ:** `../../docs/TECHNICAL_FAQ.md`
- **ML Training Docs:** `docs/`
- **Neural Network Docs:** `experiments/neural_networks/documentation/`

---

## 🔧 Troubleshooting

### Import Errors After Reorganization

**Problem:** `ModuleNotFoundError: No module named 'config'`

**Solution:**
```python
# Update imports to use new paths
from core.config import DEFAULT_DATASET_PATH  # Not: from config import ...
```

### Scripts Not Found

**Problem:** `python eda.py` gives "file not found"

**Solution:**
```bash
# Use new paths
python analysis/exploratory/eda.py
```

### Need Old File Location

**Check this guide** - all file moves are documented above, or search the repository:
```bash
# Find a specific file
Get-ChildItem -Recurse -Filter "filename.py"
```

---

**Last Updated:** November 18, 2025  
**Maintained by:** Project Team  
**Questions?** Check the documentation folders or see `TROUBLESHOOTING.md`
