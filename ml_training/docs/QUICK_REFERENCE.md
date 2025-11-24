# ML Training - Quick Reference

**Last Updated:** November 15, 2025  
**Status:** ✅ NLOS experiments complete, folder organized

---

## 🎯 Quick Links

### 📊 Results & Documentation
- **[Main Results](experiments/neural_networks/RESULTS.md)** - Comprehensive exp11 results (11.47m MAE) ⭐
- **[CNN Comparison](experiments/neural_networks/CNN_COMPARISON.md)** - Architecture analysis
- **[Root Cause Analysis](experiments/neural_networks/ROOT_CAUSE_ANALYSIS.md)** - Debugging journey
- **[Reorganization Plan](REORGANIZATION_PLAN.md)** - Folder structure guide

### 🚀 Training Scripts
- **Best:** `train_improved_cnn.py` - Enhanced CNN (11.47m MAE) ✨
- **Baseline:** `train_independent_norm.py` - Simple CNN (14.48m MAE)
- **Debug:** `debug_simple_cnn.py` - Fast testing on 10% data

### 📈 Visualization
- **Compare Models:** `compare_cnn_results.py` - Generate comparison charts
- **Latest Plot:** `experiments/neural_networks/cnn_comparison.png`

---

## 🏆 Best Results (exp11 NLOS Dataset)

| Model | MAE | R² | Parameters | Epochs | File |
|-------|-----|-----|------------|--------|------|
| **Improved CNN** 🥇 | **11.47m** | **0.858** | 2.17M | 61 | `saved_models/improved_cnn_best.pth` |
| Simple CNN | 14.48m | 0.785 | 1.05M | 26 | `saved_models/simple_cnn_best.pth` |
| ResNet | ❌ Failed | -6.67 | 505K | - | *Do not use* |

**Achievement:** 21% better MAE than baseline! 🎉

---

## 📂 Folder Organization

```
ml_training/
├── experiments/
│   ├── los_only/              # Future: LOS-only experiments
│   ├── nlos_conditions/       # Future: NLOS-specific scripts
│   ├── feature_engineering/   # Future: Feature analysis
│   └── neural_networks/       # ✅ Documentation & archived scripts
│
├── data/                      # Datasets (exp09, exp10, exp11)
├── saved_models/              # Best models for production
├── results/                   # Training logs & plots
│
└── Training Scripts (root):
    ├── train_improved_cnn.py  # Main training script ⭐
    ├── train_independent_norm.py
    ├── debug_simple_cnn.py
    └── compare_cnn_results.py
```

---

## ⚡ Quick Start

### Train the Best Model (Improved CNN):
```bash
cd ml_training
python train_improved_cnn.py
```
**Expected:** MAE ~11-12m, training ~13 minutes on GTX 1650

### Test on 10% Data (Fast Debugging):
```bash
python debug_simple_cnn.py
```
**Expected:** Completes in ~2 minutes

### Generate Comparison Plot:
```bash
python compare_cnn_results.py
```
**Output:** `experiments/neural_networks/cnn_comparison.png`

---

## 📊 Dataset Information

### exp11 (NLOS-Enhanced) - **Current Best**
- **Size:** 40,000 samples (32K train, 8K val)
- **NLOS Distribution:** Perfect balance
  - 30% Pure LOS
  - 25% Light NLOS
  - 25% Moderate NLOS  
  - 20% Heavy NLOS
- **Features:** 12,291 (3 wideband + 3×4096 per-subcarrier)
- **Best MAE:** 11.47m (Improved CNN)

### exp09 (LOS-Only)
- **Size:** 50,000 samples
- **NLOS:** 0% (pure LOS)
- **Status:** Ready for training
- **Expected MAE:** 8-10m

### exp10 (LOS-Only)
- **Size:** 100,000 samples
- **NLOS:** 0% (pure LOS)
- **Status:** Ready for training
- **Expected MAE:** 8-10m (better with more data)

---

## 🔧 Key Technical Details

### Preprocessing:
- **Normalization:** Independent StandardScaler for train/val
- **Why:** Val has 6.6% higher RSRP variance
- **Result:** Both sets have mean=0, std=1 ✅

### Model Architecture (Improved CNN):
```
3 Conv blocks: [3→32→64→128] with BatchNorm + MaxPool
2 FC layers: [256→128] with Dropout(0.3)
Output: 2 neurons (x, y coordinates)
```

### Training Setup:
- **Optimizer:** Adam (lr=1e-3)
- **Scheduler:** ReduceLROnPlateau (factor=0.5, patience=5)
- **Loss:** MSELoss
- **Early Stopping:** patience=15
- **Batch Size:** 32
- **Hardware:** GTX 1650 (4GB VRAM)

---

## 💡 Lessons Learned

### What Works ✅
1. **Simple CNN architecture** - No skip connections, clean gradient flow
2. **Independent normalization** - Handles distribution variance
3. **Batch Normalization** - Stabilizes training (without skip connections)
4. **Dropout (0.3)** - Prevents overfitting
5. **Proper initialization** - Output bias = 50m (room center)

### What Doesn't Work ❌
1. **ResNet architecture** - Skip connections amplify distribution issues
2. **Combined normalization** - Fit on train, fails on different val distribution
3. **Too complex models** - Overfitting on limited NLOS data
4. **No regularization** - Poor generalization

---

## 🎯 Performance Targets

| Environment | Target MAE | Current Best | Status |
|-------------|-----------|--------------|--------|
| **NLOS (70%)** | **<12m** | **11.47m** | ✅ **Achieved!** |
| LOS-Only | <10m | TBD | ⏳ TODO |
| Mixed (50% NLOS) | <11m | TBD | ⏳ TODO |

---

## 📈 Next Steps

### Short-term:
1. ✅ ~~Document exp11 results~~
2. ✅ ~~Organize folder structure~~
3. ⏳ Train models on exp09 (LOS-only 50K)
4. ⏳ Train models on exp10 (LOS-only 100K)
5. ⏳ Compare LOS vs NLOS performance

### Medium-term:
1. Ensemble methods (Simple + Improved CNN)
2. Attention mechanisms for subcarrier selection
3. Multi-task learning (position + NLOS type)
4. Transfer learning from LOS to NLOS

### Long-term:
1. Real-world validation
2. Multi-floor localization
3. Moving UE trajectory prediction
4. Edge deployment optimization

---

## 🚨 Common Issues & Solutions

### Negative R² during training:
- **Cause:** Distribution mismatch or wrong architecture
- **Solution:** Use independent normalization + Simple/Improved CNN
- **Reference:** See `ROOT_CAUSE_ANALYSIS.md`

### Validation loss much higher than training:
- **Cause:** Model too complex or distribution variance
- **Solution:** Add Dropout, use independent normalization
- **Expected:** Val loss ~4-5× train loss is acceptable

### Training too slow:
- **Quick test:** Use `debug_simple_cnn.py` with 10% data
- **Optimization:** Reduce batch size, fewer epochs
- **Hardware:** Use GPU (CUDA) if available

### Out of memory:
- **Solution:** Reduce batch size (try 16 or 8)
- **Feature reduction:** Use feature selection tools
- **Model size:** Try Simple CNN instead of Improved

---

## 📝 File Naming Conventions

### Models:
- `{architecture}_{variant}_best.pth` (e.g., `improved_cnn_best.pth`)
- Saved in `saved_models/` folder

### Results:
- `RESULTS_exp##.md` or `RESULTS_{description}.md`
- Saved in `experiments/neural_networks/`

### Plots:
- `{experiment}_{metric}.png` (e.g., `cnn_comparison.png`)
- Saved in `results/` or `experiments/neural_networks/`

---

## 📚 Documentation Index

1. **[RESULTS.md](experiments/neural_networks/RESULTS.md)** - Main results (START HERE)
2. **[CNN_COMPARISON.md](experiments/neural_networks/CNN_COMPARISON.md)** - Architecture details
3. **[ROOT_CAUSE_ANALYSIS.md](experiments/neural_networks/ROOT_CAUSE_ANALYSIS.md)** - Debugging story
4. **[REORGANIZATION_PLAN.md](REORGANIZATION_PLAN.md)** - Folder structure
5. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - This document

---

## 🎓 References

### Project Documents:
- **Root README:** `../README.md`
- **Executive Summary:** `../EXECUTIVE_SUMMARY.md`
- **Presentation:** `../PROJECT_PRESENTATION.md`

### Related Folders:
- **Experiments (MATLAB):** `../experiments/`
- **Data Generation:** `../experiments/04_data_generation/`
- **Documentation:** `../docs/`

---

**Status:** ✅ Production-ready NLOS localization model (11.47m MAE)  
**Contact:** Gilad  
**Date:** November 15, 2025

---

## 🏃 TL;DR

```bash
# Train best model
cd ml_training
python train_improved_cnn.py

# View results
cat experiments/neural_networks/RESULTS.md

# Generate comparison plot
python compare_cnn_results.py
```

**Result:** 11.47m MAE on NLOS-heavy dataset 🎉
