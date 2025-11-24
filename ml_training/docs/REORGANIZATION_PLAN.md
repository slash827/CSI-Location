# ML Training Folder Reorganization Plan

**Status:** ✅ **Updated with Task-Based Organization (Nov 15, 2025)**

---

## 📁 New Organization: Task-Based Structure

### Implemented Structure:

```
ml_training/
├── experiments/
│   ├── los_only/              # ✅ LOS-only experiments (exp09, exp10)
│   ├── nlos_conditions/       # ✅ NLOS experiments (exp11+)
│   ├── feature_engineering/   # ✅ Feature selection/analysis
│   └── neural_networks/       # ✅ Deep learning experiments
│       ├── RESULTS.md         # Main results (11.47m MAE achieved!)
│       ├── CNN_COMPARISON.md  # Architecture comparison
│       ├── ROOT_CAUSE_ANALYSIS.md  # Debugging docs
│       └── archived/          # Old/deprecated scripts
│
├── data/                      # Generated datasets (exp09, exp10, exp11)
├── models/                    # Training checkpoints
├── saved_models/              # Best models for production
│   ├── simple_cnn_best.pth    # 14.48m MAE baseline
│   └── improved_cnn_best.pth  # 11.47m MAE champion ✨
├── results/                   # Training outputs, plots, logs
├── output/                    # Temporary outputs
├── runs/                      # TensorBoard logs
│
├── config.py                  # Global configuration
├── data_loader.py             # Data loading utilities
├── preprocessing.py           # Preprocessing pipeline
├── utils.py                   # Helper functions
├── models.py                  # Model definitions
│
└── Core Training Scripts (root level):
    ├── train_improved_cnn.py  # Current best: 11.47m MAE
    ├── train_independent_norm.py  # Simple CNN baseline
    ├── debug_simple_cnn.py    # 10% data testing
    ├── compare_models.py      # Model comparison tools
    └── check_nlos_dist.py     # NLOS analysis
```

---

## 🎯 Organization by Task

### 1. **experiments/los_only/**
- **Purpose:** Baseline LOS-only experiments
- **Datasets:** exp09 (50K), exp10 (100K)
- **Status:** Folders created, training TBD
- **Expected:** 8-12m MAE

### 2. **experiments/nlos_conditions/**
- **Purpose:** NLOS-enhanced localization
- **Datasets:** exp11 (40K, 70% NLOS)
- **Status:** ✅ **Successfully trained!**
- **Best Result:** **11.47m MAE, R²=0.858** (Improved CNN)
- **Scripts:** All NLOS training scripts in root (for now)

### 3. **experiments/feature_engineering/**
- **Purpose:** Feature selection & analysis
- **Status:** Folder created, scripts to move
- **Future:** PCA, mutual information, correlation studies

### 4. **experiments/neural_networks/**
- **Purpose:** Deep learning architecture experiments
- **Status:** ✅ Documentation complete
- **Contents:**
  - `RESULTS.md` - Comprehensive results document
  - `CNN_COMPARISON.md` - Architecture analysis
  - `ROOT_CAUSE_ANALYSIS.md` - Debugging journey
  - `archived/` - Deprecated scripts

---

## 📊 Current Best Results

| Task | Dataset | Model | MAE | R² | Status |
|------|---------|-------|-----|-----|--------|
| **NLOS Localization** | **exp11** | **Improved CNN** | **11.47m** | **0.858** | ✅ **Complete** |
| LOS Baseline | exp09 | TBD | TBD | TBD | ⏳ TODO |
| LOS Large-scale | exp10 | TBD | TBD | TBD | ⏳ TODO |

---

## ✅ What's Been Fixed

### Previous Issues:
1. ❌ Too many files in root directory
2. ❌ No clear separation by task type
3. ❌ Negative R² in training (catastrophic failure)
4. ❌ ResNet architecture overfitting

### Current Solutions:
1. ✅ **Task-based folder structure** created
2. ✅ **Clear separation:** LOS vs NLOS vs feature engineering
3. ✅ **Training fixed:** 11.47m MAE achieved (was getting R²=-1.5)
4. ✅ **Architecture solved:** Improved CNN works, ResNet documented as failed
5. ✅ **Comprehensive documentation** in neural_networks/

---

## 🔄 File Organization Status

### ✅ Completed:
- Task-based folders created
- Documentation organized in `neural_networks/`
- Best models saved with clear naming

### ⏳ To Do:
1. **Move feature engineering scripts:**
   - `compare_feature_selection.py` → `experiments/feature_engineering/`
   - `FEATURE_ANALYSIS_RESULTS.md` → `experiments/feature_engineering/`
   - `FEATURE_SELECTION_FAILURE_ANALYSIS.md` → `experiments/feature_engineering/`

2. **Archive old/failed scripts:**
   - Failed ResNet attempts → `experiments/neural_networks/archived/`
   - Deprecated normalization experiments → `experiments/neural_networks/archived/`

3. **Create LOS training scripts:**
   - New scripts for exp09/exp10 → `experiments/los_only/`

4. **Update imports:**
   - If scripts move to subfolders, update relative imports
   - Test all scripts after moving

---

## 📚 Key Documentation

1. **[RESULTS.md](experiments/neural_networks/RESULTS.md)**
   - Comprehensive exp11 results
   - 11.47m MAE achievement
   - Training details, model comparison, performance analysis

2. **[CNN_COMPARISON.md](experiments/neural_networks/CNN_COMPARISON.md)**
   - Simple CNN vs Improved CNN
   - Why ResNet failed
   - Architecture recommendations

3. **[ROOT_CAUSE_ANALYSIS.md](experiments/neural_networks/ROOT_CAUSE_ANALYSIS.md)**
   - Complete debugging timeline
   - Distribution mismatch investigation
   - Independent normalization solution

4. **[REORGANIZATION_PLAN.md](REORGANIZATION_PLAN.md)** (this file)
   - Current folder structure
   - Organization strategy
   - Migration guide

---

## 🚀 Quick Start by Task

### Training NLOS Models (Current):
```bash
cd ml_training
python train_improved_cnn.py  # Best: 11.47m MAE
```

### Training LOS-Only Models (Future):
```bash
cd ml_training/experiments/los_only
# TODO: Create training scripts
```

### Feature Analysis:
```bash
cd ml_training/experiments/feature_engineering
# TODO: Move existing scripts here
```

### View Results:
```bash
# Main results document
cat ml_training/experiments/neural_networks/RESULTS.md

# Architecture comparison
cat ml_training/experiments/neural_networks/CNN_COMPARISON.md
```

---

## 🎯 Next Steps

### Immediate (File Organization):
1. ✅ Create task-based folders
2. ✅ Create comprehensive RESULTS.md
3. ⏳ Move feature engineering scripts
4. ⏳ Archive deprecated scripts

### Short-term (New Experiments):
1. Train models on exp09 (LOS-only, 50K samples)
2. Train models on exp10 (LOS-only, 100K samples)
3. Compare LOS vs NLOS performance
4. Feature importance analysis

### Long-term (Advanced Work):
1. Ensemble methods (combine Simple + Improved CNN)
2. Attention mechanisms
3. Multi-task learning (position + NLOS type)
4. Real-world validation

---

## 📝 Migration Guide

### If you need to move scripts:

1. **Identify task type:**
   - LOS-only? → `experiments/los_only/`
   - NLOS? → Keep in root (current NLOS scripts)
   - Feature? → `experiments/feature_engineering/`
   - Architecture? → `experiments/neural_networks/`

2. **Move file:**
   ```powershell
   Move-Item script.py experiments/{category}/
   ```

3. **Update imports:**
   ```python
   # If moving to subfolder, update paths:
   # Old: from data_loader import load_data
   # New: from ...data_loader import load_data
   
   # Old: data_dir = 'data/'
   # New: data_dir = '../../../data/'
   ```

4. **Test:** Run script to verify it works

---

## 🏆 Achievement Summary

- ✅ **11.47m MAE** on NLOS-heavy dataset (70% NLOS)
- ✅ **21% improvement** over Simple CNN baseline
- ✅ **Task-based organization** for better project structure
- ✅ **Comprehensive documentation** for reproducibility
- ✅ **Production-ready models** saved and versioned

---

**Last Updated:** November 15, 2025  
**Status:** Task-based structure created, NLOS experiments complete  
**Next:** LOS-only experiments & further organization
