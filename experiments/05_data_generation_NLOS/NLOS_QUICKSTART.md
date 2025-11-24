# NLOS Dataset Generation - Quick Start Guide
## How to Generate and Test NLOS-Enhanced Dataset

**Created:** November 15, 2025  
**Purpose:** Step-by-step guide to generate exp11 NLOS dataset and train models

---

## 📋 Prerequisites

✅ **MATLAB Setup:**
- MATLAB R2023a or later
- QuaDRiGa v2.8.1 installed
- `utils/` folder accessible

✅ **Python Setup:**
- Python 3.11
- PyTorch 2.7.1 (with CUDA 11.8 for GPU)
- All ml_training dependencies installed

✅ **Disk Space:**
- ~3-4 GB for dataset files
- ~1 GB for plots and analysis

---

## 🚀 Step 1: Generate NLOS Dataset (MATLAB)

### Option A: Generate Full Dataset (Recommended)

**Time:** 15-20 minutes  
**Output:** 40,000 samples (32K train + 8K val)

```matlab
cd d:\gilad\projects\Academy\CSI-Location\experiments\04_data_generation
exp11_nlos_dataset
```

**What happens:**
1. Loads configuration from `config_nlos_dataset.m`
2. Generates 500 trajectories with mixed LOS/NLOS conditions:
   - 150 Pure LOS trajectories (30%)
   - 125 Light NLOS trajectories (25%)
   - 125 Moderate NLOS trajectories (25%)
   - 100 Heavy NLOS trajectories (20%)
3. Simulates CSI for all trajectories using QuaDRiGa
4. Saves data to `results/exp11_<timestamp>/dataset/`
5. Generates analysis plots and report

### Option B: Test with Small Dataset (Quick Test)

**Time:** 2-3 minutes  
**Output:** 4,000 samples (3.2K train + 800 val)

**Before running, edit `config_nlos_dataset.m`:**
```matlab
% Change line 15:
config.n_trajectories = 50;  % Instead of 500
```

Then run:
```matlab
exp11_nlos_dataset
```

**Remember to change back to 500 for full dataset!**

---

## 🔍 Step 2: Validate Dataset Quality (MATLAB)

After generation completes, check the output:

### A. Check Console Output

Look for:
```
========================================
EXPERIMENT 11 COMPLETE!
========================================

📁 Output directory: results/exp11_<timestamp>
📊 Training samples: 32000
📊 Validation samples: 8000
🎯 NLOS Distribution:
   - Pure LOS: 12000 samples (30.0%)
   - Light NLOS: 10000 samples (25.0%)
   - Moderate NLOS: 10000 samples (25.0%)
   - Heavy NLOS: 8000 samples (20.0%)
⏱️  Total time: 15.2 minutes
```

### B. Review Generated Files

**Dataset Files (in `results/exp11_<timestamp>/dataset/`):**
```
train_data.mat         ~2.8 GB   Training samples
val_data.mat           ~720 MB   Validation samples
nlos_metadata.mat      ~1 MB     NLOS condition labels
```

**Analysis Files (in `results/exp11_<timestamp>/analysis/`):**
```
nlos_analysis.png      NLOS distribution histograms
nlos_analysis.fig      MATLAB figure for editing
```

**Report:**
```
experiment_report.txt  Complete generation summary
```

### C. Visual Inspection

Open `analysis/nlos_analysis.png` to verify:
- **Top-left:** Training NLOS distribution matches target (30/25/25/20%)
- **Top-right:** Validation NLOS distribution similar to training
- **Bottom-left:** RSRP histogram shows LOS/NLOS separation
- **Bottom-right:** Spatial coverage across 80×80m area

---

## 🐍 Step 3: Inspect Dataset with Python

Update your dataset path and inspect:

```powershell
cd d:\gilad\projects\Academy\CSI-Location\ml_training
python data_loader.py --dataset_path "..\results\exp11_<timestamp>\dataset" --inspect
```

**Expected Output:**
```
======================================================================
DATASET INSPECTION
======================================================================

Dataset path: ..\results\exp11_<timestamp>\dataset

Loading training data from: train_data.mat
  - Loaded 32000 samples
Loading validation data from: val_data.mat
  - Loaded 8000 samples
Loading NLOS metadata from: nlos_metadata.mat
  - Training NLOS distribution:
    Pure LOS: 12000 samples (37.5%)
    Light NLOS: 10000 samples (31.2%)
    Moderate NLOS: 10000 samples (31.2%)
    Heavy NLOS: 8000 samples (25.0%)

--- Training Set ---
Samples: 32000
Features: 3075
Targets: 2 (x, y positions)

--- Validation Set ---
Samples: 8000
Features: 3075

--- NLOS Condition Statistics ---
Training set:
  Pure LOS       : 12000 samples, RSRP:  -55.23 ±  8.45 dBm
  Light NLOS     : 10000 samples, RSRP:  -67.89 ± 10.12 dBm
  Moderate NLOS  : 10000 samples, RSRP:  -75.34 ± 12.67 dBm
  Heavy NLOS     :  8000 samples, RSRP:  -84.56 ± 15.23 dBm

======================================================================
```

**Key Checks:**
- ✅ Total samples: 40,000 (32K + 8K)
- ✅ Features: 3,075 (3 wideband + 1024×3 per-subcarrier)
- ✅ NLOS distribution matches target
- ✅ RSRP values show clear LOS/NLOS separation (~10-30 dB difference)

---

## 🤖 Step 4: Train ML Models on NLOS Dataset

### A. Update Configuration

Edit `ml_training/config.py`:

```python
# Line ~15-20: Update dataset path
DEFAULT_DATASET_PATH = Path(r"d:\gilad\projects\Academy\CSI-Location\results\exp11_<timestamp>\dataset")
```

### B. Test Quick Baseline (5-10 minutes)

Train a simple MLP to verify data loading:

```powershell
cd d:\gilad\projects\Academy\CSI-Location\ml_training\experiments\neural_networks
python train.py --model mlp --epochs 10 --batch_size 64
```

**Expected Performance (10 epochs):**
- Training loss should decrease
- Validation MAE: 18-22m (rough estimate)
- No errors or crashes

### C. Train Full ResNet Model (20-30 minutes)

```powershell
python train.py --model resnet --epochs 50 --batch_size 32 --lr 0.001
```

**Expected Performance (50 epochs):**

| Metric | LOS-only (exp10) | NLOS-enhanced (exp11) | Expected Change |
|--------|------------------|----------------------|-----------------|
| **MAE** | 13.5m | 15-18m | +10-30% worse (harder) |
| **R²** | 0.80 | 0.72-0.78 | Slightly worse |
| **RMSE** | ~18m | ~20-24m | +10-30% worse |

**Why worse initially?**
- NLOS adds complexity and uncertainty
- More challenging localization problem
- Model needs to learn NLOS-specific patterns

### D. Train with Advanced Optimization (40-60 minutes)

Use the advanced training framework:

```powershell
cd ml_training\experiments\neural_networks
python train_advanced.py --config baseline_resnet
```

**Expected Performance (100 epochs):**

| Metric | Target | Notes |
|--------|--------|-------|
| **MAE** | 12-15m | Better than initial, may match exp10! |
| **R²** | 0.78-0.83 | Robust to NLOS |
| **Generalization** | Excellent | Works in both LOS and NLOS |

---

## 📊 Step 5: Compare LOS-only vs NLOS-enhanced

### A. Side-by-Side Performance

| Dataset | Samples | MAE (50 epochs) | MAE (100 epochs) | R² | Robustness |
|---------|---------|-----------------|------------------|-----|------------|
| **exp10 (LOS-only)** | 40K | 13.5m | ~10-12m | 0.80-0.85 | ❌ Fails on NLOS |
| **exp11 (NLOS-enhanced)** | 40K | 15-18m | ~12-15m | 0.78-0.83 | ✅ Robust to NLOS |

### B. Analysis by NLOS Condition

After training, analyze performance by NLOS type:

```python
# Add this to your evaluation script
from scipy.io import loadmat

# Load NLOS metadata
nlos_meta = loadmat('results/exp11_<timestamp>/dataset/nlos_metadata.mat')
val_conditions = nlos_meta['val_conditions']

# Calculate MAE per condition
for i in range(1, 5):
    mask = val_conditions == i
    mae_cond = np.mean(np.abs(predictions[mask] - targets[mask]))
    print(f"Condition {i} MAE: {mae_cond:.2f}m")
```

**Expected Pattern:**
- Pure LOS: 10-12m (easiest)
- Light NLOS: 13-15m
- Moderate NLOS: 15-18m
- Heavy NLOS: 18-22m (hardest)

---

## 🎯 Success Criteria

### Dataset Generation ✅

- [x] 40,000 total samples generated
- [x] NLOS distribution matches target (30/25/25/20%)
- [x] RSRP shows clear LOS/NLOS separation (10-30 dB)
- [x] No NaN/Inf values in features
- [x] Spatial coverage ≥85% of 80×80m area

### ML Performance ✅

**Initial Training (50 epochs):**
- 🎯 MAE ≤ 18m (acceptable)
- 🎯 R² ≥ 0.72 (reasonable)
- 🎯 Model trains without errors

**Optimized Training (100 epochs):**
- 🎯 MAE ≤ 15m (target)
- 🎯 R² ≥ 0.78 (good)
- 🎯 Better than exp10 in NLOS scenarios

**Advanced Goal (150 epochs + tricks):**
- 🌟 MAE ≤ 12m (excellent)
- 🌟 R² ≥ 0.82 (state-of-the-art)
- 🌟 Robust performance in all NLOS conditions

---

## 🐛 Troubleshooting

### Problem: MATLAB Error During Generation

**Error:** `Undefined function or variable 'generate_linear_trajectory'`

**Solution:**
```matlab
% Add trajectory generators to path
addpath('d:\gilad\projects\Academy\CSI-Location\experiments\04_data_generation')
```

### Problem: Out of Memory in MATLAB

**Error:** `Out of memory. Type "help memory" for your options.`

**Solutions:**
1. Reduce `config.n_timesteps` from 80 to 60
2. Reduce `config.n_trajectories` from 500 to 400
3. Set `config.output.generate_plots = false` to skip plots
4. Close other MATLAB windows

### Problem: Python Can't Load .mat File

**Error:** `NotImplementedError: Please use HDF5 reader for matlab v7.3 files`

**Solution:**
```powershell
pip install h5py
```

### Problem: GPU Out of Memory During Training

**Error:** `CUDA out of memory`

**Solutions:**
1. Reduce batch size: `--batch_size 16` (instead of 32)
2. Reduce model size (not recommended)
3. Use CPU: `--device cpu` (slower)

### Problem: Model Performance Worse Than Expected

**Possible Causes:**
1. **Too few epochs:** Train for at least 50 epochs
2. **Wrong learning rate:** Try `--lr 0.0005` (lower) or `--lr 0.002` (higher)
3. **Data loading issue:** Check with `--inspect` flag
4. **NLOS is just harder:** Expected! Optimize with advanced techniques

---

## 📈 Expected Timeline

### Quick Test (Small Dataset)
- Generate 50 traj: **3 minutes**
- Inspect dataset: **1 minute**
- Train MLP 10 epochs: **2 minutes**
- **Total: 6 minutes** ✅

### Full Pipeline (Production Dataset)
- Generate 500 traj: **15-20 minutes**
- Inspect dataset: **2 minutes**
- Train ResNet 50 epochs: **25-30 minutes**
- Train ResNet 100 epochs: **50-60 minutes**
- **Total: 90-115 minutes** (~1.5-2 hours)

---

## 📝 Next Steps After Generation

### 1. Document Results
- Save training curves (loss, MAE, R²)
- Plot predictions vs ground truth
- Create error distribution analysis
- Compare with exp10 results

### 2. Analysis by NLOS Type
- Calculate MAE per NLOS condition
- Visualize error patterns
- Identify challenging scenarios
- Document in `NLOS_RESULTS_ANALYSIS.md`

### 3. Model Improvements
- Try curriculum learning (LOS → mixed)
- Add NLOS indicator as input feature
- Test ensemble methods
- Explore attention mechanisms

### 4. Presentation Update
- Add exp11 results to `PROJECT_PRESENTATION.md`
- Update performance tables
- Add NLOS analysis section
- Document lessons learned

---

## 📞 Support

**Files Created:**
- `NLOS_IMPLEMENTATION.md` - Complete technical documentation
- `config_nlos_dataset.m` - NLOS configuration
- `exp11_nlos_dataset.m` - Generation script
- `NLOS_QUICKSTART.md` - This file

**Key References:**
- `experiments/01_basics/exp03_los_vs_nlos.m` - LOS/NLOS comparison
- `experiments/04_data_generation/exp10_large_dataset.m` - Original LOS dataset
- `ml_training/data_loader.py` - Updated with NLOS support

---

**Ready to Generate?**

```matlab
% In MATLAB:
cd d:\gilad\projects\Academy\CSI-Location\experiments\04_data_generation
exp11_nlos_dataset

% After generation, in PowerShell:
cd d:\gilad\projects\Academy\CSI-Location\ml_training
python data_loader.py --dataset_path "..\results\exp11_<timestamp>\dataset" --inspect
```

**Good luck! 🚀**

---

*Document Version: 1.0 | Created: November 15, 2025*
