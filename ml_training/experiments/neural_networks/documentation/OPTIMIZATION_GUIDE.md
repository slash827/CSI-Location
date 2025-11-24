# Neural Network Optimization Guide for NLOS Dataset

**Date:** November 15, 2025  
**Dataset:** exp11_2025-11-15_14-07-52 (40,000 samples with NLOS conditions)  
**Previous Best (LOS-only):** MAE 13.83m, R² 0.8077 (exp10, 3,075 features)  
**Target:** Improve robustness with NLOS dataset (12,291 features)

---

## Executive Summary

The NLOS-enhanced dataset (exp11) has **4× more features** than the LOS-only baseline (exp10):
- **exp10:** 3,075 features (1 BS, 1024 subcarriers)
- **exp11:** 12,291 features (4 BS, 1024 subcarriers each)

This requires careful hyperparameter tuning to prevent overfitting and ensure efficient training.

---

## Key Changes from Previous Training

### 1. **Dataset Update** ✅
- **Old:** `exp10_2025-11-07_12-40-00` (40K samples, LOS-only)
- **New:** `exp11_2025-11-15_14-07-52` (40K samples, 30% LOS / 70% NLOS)
- **Action:** `config.py` already updated to point to exp11

### 2. **Early Stopping Patience** ✅
- **Old:** 15 epochs (too conservative)
- **New:** 8 epochs (as requested)
- **Rationale:** Previous training peaked at epoch 21, stopped at epoch 36 (15 epochs wasted)

### 3. **Scheduler Options** ⭐ NEW
Four scheduler types now available:
1. **ReduceLROnPlateau** (default) - Adaptive, reduces on validation plateau
2. **CosineAnnealingLR** - Smooth cosine decay
3. **OneCycleLR** - Fast convergence, aggressive learning rate schedule
4. **StepLR** - Step-wise decay at fixed intervals

---

## Recommended Training Configurations

### Configuration 1: Conservative (Recommended for First Run)
**Best for:** Stable baseline, understanding NLOS impact

```bash
python train_optimized.py \
  --model resnet \
  --epochs 80 \
  --batch_size 32 \
  --lr 0.001 \
  --weight_decay 1e-4 \
  --scheduler plateau \
  --scheduler_patience 4 \
  --early_stopping_patience 8
```

**Rationale:**
- Same batch size (32) and LR (0.001) as baseline
- Reduced scheduler patience (4 vs 5) for faster adaptation
- Early stopping at 8 epochs (reduced from 15)
- Expected runtime: ~15-20 minutes on GTX 1650

---

### Configuration 2: Aggressive (Fast Convergence)
**Best for:** Quick iteration, hyperparameter search

```bash
python train_optimized.py \
  --model resnet \
  --epochs 60 \
  --batch_size 32 \
  --lr 0.002 \
  --weight_decay 5e-5 \
  --scheduler onecycle \
  --early_stopping_patience 6
```

**Rationale:**
- Higher initial LR (0.002) with OneCycleLR scheduler
- Lower weight decay to allow more flexibility with 4× features
- Tighter early stopping (6 epochs)
- Expected runtime: ~10-15 minutes

---

### Configuration 3: Fine-tuned (After Initial Results)
**Best for:** Squeezing out last 0.5-1m of accuracy

```bash
python train_optimized.py \
  --model resnet \
  --epochs 100 \
  --batch_size 64 \
  --lr 0.0005 \
  --weight_decay 2e-4 \
  --scheduler cosine \
  --early_stopping_patience 10
```

**Rationale:**
- Larger batch size (64) for stable gradients with 4× features
- Lower LR (0.0005) for fine-tuning
- Cosine annealing for smooth convergence
- More patient early stopping (10 epochs)
- Expected runtime: ~20-25 minutes

---

## Scheduler Comparison

### **ReduceLROnPlateau** (Default)
- **Pros:** Adaptive, proven effective (used in baseline)
- **Cons:** Can be slow, requires careful patience tuning
- **Best for:** Stable training, first experiments
- **Config:** `--scheduler plateau --scheduler_patience 4`

### **CosineAnnealingLR**
- **Pros:** Smooth decay, no manual tuning, good for long training
- **Cons:** Fixed schedule, doesn't adapt to validation loss
- **Best for:** 100+ epoch training, fine-tuning
- **Config:** `--scheduler cosine`

### **OneCycleLR**
- **Pros:** Fast convergence, automatic warmup, state-of-the-art
- **Cons:** Aggressive, can overfit if not careful
- **Best for:** Quick experiments, hyperparameter search
- **Config:** `--scheduler onecycle`

### **StepLR**
- **Pros:** Simple, predictable, good for debugging
- **Cons:** Manual step size tuning, can miss optimal points
- **Best for:** Controlled experiments, comparing schedules
- **Config:** `--scheduler step --step_size 15`

---

## Understanding the Feature Space

### exp10 (LOS-only): 3,075 features
```
Wideband (3):     [RSRP, SNR, CQI]
Per-subcarrier:   3 × 1024 = 3,072
                  ↳ [RSS, SINR, H_mag] × 1024 subcarriers
Total:            3 + 3,072 = 3,075
```

### exp11 (NLOS-enhanced): 12,291 features
```
Wideband (3):     [RSRP, SNR, CQI]  (aggregated across 4 BS)
Per-subcarrier:   3 × 4 × 1024 = 12,288
                  ↳ [RSS, SINR, H_mag] × 4 BS × 1024 subcarriers
Total:            3 + 12,288 = 12,291
```

**Impact:**
- 4× more input dimensions → higher overfitting risk
- More diversity in signal characteristics → better generalization potential
- Increased computational cost per forward pass

---

## Expected Performance

### Baseline (exp10, LOS-only)
```
MAE:   13.83 m
RMSE:  ~18-20 m (estimated)
R²:    0.8077
```

### Target (exp11, NLOS-enhanced)
```
Optimistic:  MAE 12-14 m  (NLOS improves generalization)
Realistic:   MAE 14-16 m  (NLOS adds difficulty, but better robustness)
Pessimistic: MAE 16-18 m  (NLOS dominates, LOS-trained weights don't transfer)
```

**Why might MAE increase?**
- NLOS conditions inherently harder to predict
- Multipath fading, signal blockage → less deterministic location-signal mapping
- Model needs to learn 4 different propagation environments (Pure LOS, Light, Moderate, Heavy)

**Why might MAE decrease?**
- More diverse training data → better generalization
- 4 BS provide spatial diversity → triangulation effect
- Baseline may have been overfitting to LOS scenarios

---

## Training Workflow

### Step 1: Baseline Run (Recommended Configuration 1)
```bash
cd ml_training/experiments/neural_networks
python train_optimized.py --model resnet --epochs 80 --batch_size 32 --lr 0.001 --early_stopping_patience 8
```

**Expected Output:**
```
✓ Data loaded: Training: X=(32000, 12291), y=(32000, 2)
✓ Created RESNET model: Parameters: 505,858
Epoch 1/80 ... Val MAE: ~35-40 m
Epoch 10/80 ... Val MAE: ~20-25 m
Epoch 20/80 ... Val MAE: ~15-18 m
Epoch 30/80 ... Val MAE: ~14-16 m
Early stopping triggered after ~38 epochs
Best validation MAE: ~14-16 m
```

### Step 2: Analyze Results
Check key metrics:
1. **Best epoch:** Should be around epoch 20-30
2. **MAE progression:** Should show steady decrease, then plateau
3. **Learning rate schedule:** Check if reductions happened at right times
4. **Overfitting:** Compare train_loss vs val_loss (gap should be < 0.02)

### Step 3: Adjust Hyperparameters
Based on Step 1 results:

| Observation | Suggested Action |
|-------------|------------------|
| Converged quickly (< 20 epochs) | Increase LR to 0.002, use OneCycleLR |
| Slow convergence (> 40 epochs) | Decrease scheduler_patience to 3 |
| Large train/val gap | Increase weight_decay to 2e-4 |
| Poor validation metrics | Decrease LR to 0.0005, increase batch_size to 64 |
| Training unstable | Decrease LR to 0.0005, use CosineAnnealingLR |

### Step 4: Compare with Baseline
```python
# After training, compare exp10 vs exp11
import json

# Load exp10 results (previous training)
with open('../../output/results/[exp10_run]/results.json') as f:
    exp10_results = json.load(f)

# Load exp11 results (new training)
with open('../../output/results/[exp11_run]/results.json') as f:
    exp11_results = json.load(f)

print(f"exp10 MAE: {exp10_results['metrics']['mae']:.2f} m")
print(f"exp11 MAE: {exp11_results['metrics']['mae']:.2f} m")
print(f"Improvement: {exp10_results['metrics']['mae'] - exp11_results['metrics']['mae']:.2f} m")
```

---

## Advanced: Per-Condition Analysis

After training, analyze performance by NLOS condition:

```python
from data_loader import DataLoader

# Load NLOS metadata
loader = DataLoader()
val_metadata = loader.load_nlos_metadata(
    'D:/gilad/projects/Academy/CSI-Location/results/exp11_2025-11-15_14-07-52/dataset',
    split='val'
)

# Filter predictions by condition
conditions = ['Pure LOS', 'Light NLOS', 'Moderate NLOS', 'Heavy NLOS']
for cond in conditions:
    mask = val_metadata['nlos_condition'] == cond
    cond_mae = np.mean(np.abs(predictions[mask] - y_val[mask]), axis=0)
    print(f"{cond}: MAE = {np.mean(cond_mae):.2f} m")
```

**Expected Pattern:**
```
Pure LOS:       10-12 m  (easiest, strong signal)
Light NLOS:     13-15 m  (moderate difficulty)
Moderate NLOS:  15-17 m  (challenging, significant multipath)
Heavy NLOS:     18-22 m  (hardest, severe blockage)
```

---

## Troubleshooting

### Issue: "RuntimeError: CUDA out of memory"
**Solution 1:** Reduce batch size
```bash
python train_optimized.py --batch_size 16 [other args]
```

**Solution 2:** Use CPU (slower)
```bash
python train_optimized.py --device cpu [other args]
```

### Issue: Training loss decreases, validation loss increases
**Diagnosis:** Overfitting  
**Solution:** Increase weight decay, reduce model capacity
```bash
python train_optimized.py --weight_decay 5e-4 [other args]
```

### Issue: Validation MAE stuck > 20m after 20 epochs
**Diagnosis:** Learning rate too low or bad initialization  
**Solution:** Increase LR, try different scheduler
```bash
python train_optimized.py --lr 0.002 --scheduler onecycle [other args]
```

### Issue: "ValueError: Expected more than 1 value per channel"
**Diagnosis:** Batch size too small with BatchNorm layers  
**Solution:** Increase batch size or disable BatchNorm
```bash
python train_optimized.py --batch_size 32 [other args]
```

---

## Next Steps After Training

1. **Validate on Test Set** (if available)
   - Generate predictions on held-out test data
   - Compare with baseline exp10 model

2. **Visualize Predictions**
   - Plot predicted vs actual positions
   - Color-code by NLOS condition
   - Identify failure modes (e.g., heavy NLOS near walls)

3. **Error Analysis**
   - Histogram of prediction errors
   - Spatial heatmap of errors (which areas are hardest?)
   - RSRP vs error correlation

4. **Model Comparison**
   - Train MLP and CNN with same hyperparameters
   - Compare parameter efficiency (accuracy per parameter)
   - Test different ResNet depths (add more residual blocks)

5. **Ensemble Methods**
   - Train multiple models with different seeds
   - Average predictions for better robustness
   - Weighted ensemble based on NLOS condition confidence

---

## Quick Reference

### Default Command (Just Run This!)
```bash
python train_optimized.py
```
Uses all defaults: ResNet, 100 epochs, batch_size=32, lr=0.001, plateau scheduler, patience=8

### Full Custom Command
```bash
python train_optimized.py \
  --model resnet \
  --epochs 80 \
  --batch_size 32 \
  --lr 0.001 \
  --weight_decay 1e-4 \
  --scheduler plateau \
  --scheduler_patience 4 \
  --early_stopping_patience 8 \
  --device cuda
```

### Check Results
```bash
# Results saved to:
# ml_training/output/results/resnet_optimized_nlos_[timestamp]/
#   ├── resnet_model.pth     (model weights)
#   └── results.json         (metrics + history)
```

---

## Summary

**Recommended First Run:**
```bash
python train_optimized.py --model resnet --epochs 80 --batch_size 32 --lr 0.001 --early_stopping_patience 8
```

**Expected Outcome:**
- Training time: 15-20 minutes
- Best MAE: 14-16 m (realistic target)
- Model saved to: `output/results/resnet_optimized_nlos_[timestamp]/`

**Key Improvements:**
✅ Reduced early stopping patience (15 → 8)  
✅ Added 4 scheduler options (plateau, cosine, onecycle, step)  
✅ Updated to exp11 NLOS dataset automatically  
✅ Comprehensive logging and result tracking  
✅ Easy hyperparameter experimentation

**Next:** Run the training, analyze results, and iterate based on the "Training Workflow" section above!
