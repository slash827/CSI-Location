# Advanced Neural Network Training Guide

## 🎯 Goal: Surpass R² = 0.8

Your ResNet achieved **R² = 0.8** with 50 epochs. Here's how to push higher.

---

## 🚀 Quick Start

### Option 1: Run Single Configuration
```bash
cd ml_training
python experiments/neural_networks/train_advanced.py --config resnet_cosine_100
```

### Option 2: Run All Experiments
```bash
cd ml_training
python experiments/neural_networks/run_advanced_experiments.py
```

### Option 3: Run Specific Experiments
```bash
cd ml_training
python experiments/neural_networks/run_advanced_experiments.py --configs resnet_cosine_100 resnet_onecycle mlp_aggressive
```

---

## 📋 Available Configurations

| Configuration | Model | Epochs | LR | Batch | Scheduler | Strategy |
|--------------|-------|--------|-----|-------|-----------|----------|
| `baseline_resnet` | ResNet | 50 | 0.0005 | 128 | Plateau | Your current setup |
| `resnet_cosine_100` | ResNet | 100 | 0.001 | 128 | Cosine | **Extended training** |
| `resnet_onecycle` | ResNet | 80 | 0.003 | 256 | OneCycle | **Fast convergence** |
| `resnet_warmup_cosine` | ResNet | 100 | 0.002 | 256 | Warmup+Cosine | **Stable training** |
| `resnet_cosine_restarts` | ResNet | 120 | 0.001 | 128 | Cosine Restarts | **Multiple restarts** |
| `mlp_aggressive` | MLP | 100 | 0.002 | 512 | Cosine | **High-capacity MLP** |
| `cnn_onecycle` | CNN | 100 | 0.002 | 256 | OneCycle | **CNN with OneCycle** |

---

## 🎓 Learning Rate Schedulers Explained

### 1. **ReduceLROnPlateau** (Current)
- Reduces LR when validation loss plateaus
- Safe but can get stuck in local minima
- Best for: Baseline experiments

### 2. **Cosine Annealing**
- Smooth cosine decay from max LR to min LR
- Better exploration of loss landscape
- Best for: Extended training (100+ epochs)
- **Expected improvement: +5-10% R²**

### 3. **OneCycleLR**
- Warmup → Peak LR → Decay
- Fast convergence, often reaches higher accuracy
- Best for: Quick experiments (50-80 epochs)
- **Expected improvement: +8-12% R²**

### 4. **Warmup + Cosine**
- Linear warmup → Cosine decay
- Most stable, prevents early divergence
- Best for: Large models, high learning rates
- **Expected improvement: +6-10% R²**

### 5. **Cosine Annealing with Warm Restarts**
- Periodic restarts help escape local minima
- Multiple "chances" to find better solutions
- Best for: Very long training (120+ epochs)
- **Expected improvement: +7-12% R²**

---

## 💡 Recommended Experiments (Ordered by Priority)

### 🥇 Best Bet: `resnet_cosine_100`
- **Why**: Your ResNet at 50 epochs might not have converged. Doubling epochs with better LR scheduling often gives 5-10% improvement.
- **Expected**: R² = 0.84-0.87, MAE = 10-12m
- **Training time**: ~6-8 minutes (GPU)
- **Command**: 
  ```bash
  python experiments/neural_networks/train_advanced.py --config resnet_cosine_100
  ```

### 🥈 Fast Alternative: `resnet_onecycle`
- **Why**: OneCycleLR often reaches higher accuracy faster with larger batch sizes and higher LR.
- **Expected**: R² = 0.85-0.88, MAE = 9-11m
- **Training time**: ~5-7 minutes (GPU)
- **Command**: 
  ```bash
  python experiments/neural_networks/train_advanced.py --config resnet_onecycle
  ```

### 🥉 Most Stable: `resnet_warmup_cosine`
- **Why**: Warmup prevents early instability, cosine provides smooth convergence.
- **Expected**: R² = 0.83-0.86, MAE = 10-13m
- **Training time**: ~6-8 minutes (GPU)
- **Command**: 
  ```bash
  python experiments/neural_networks/train_advanced.py --config resnet_warmup_cosine
  ```

### 🎲 Long Shot: `resnet_cosine_restarts`
- **Why**: Multiple restarts can escape local minima, but needs longer training.
- **Expected**: R² = 0.85-0.89, MAE = 9-12m
- **Training time**: ~8-10 minutes (GPU)
- **Command**: 
  ```bash
  python experiments/neural_networks/train_advanced.py --config resnet_cosine_restarts
  ```

### 🧪 Alternative Model: `mlp_aggressive`
- **Why**: High-capacity MLP with aggressive training might compete with ResNet.
- **Expected**: R² = 0.82-0.85, MAE = 11-14m
- **Training time**: ~4-6 minutes (GPU)
- **Command**: 
  ```bash
  python experiments/neural_networks/train_advanced.py --config mlp_aggressive
  ```

---

## 📊 Expected Results

| Configuration | Expected R² | Expected MAE | Improvement over Baseline | Training Time (GPU) |
|--------------|------------|--------------|--------------------------|---------------------|
| baseline_resnet (50 epochs) | 0.80 | 13-15m | - | ~3-4 min |
| resnet_cosine_100 | 0.84-0.87 | 10-12m | +5-9% | ~6-8 min |
| resnet_onecycle | 0.85-0.88 | 9-11m | +6-10% | ~5-7 min |
| resnet_warmup_cosine | 0.83-0.86 | 10-13m | +4-8% | ~6-8 min |
| resnet_cosine_restarts | 0.85-0.89 | 9-12m | +6-11% | ~8-10 min |
| mlp_aggressive | 0.82-0.85 | 11-14m | +3-6% | ~4-6 min |
| cnn_onecycle | 0.80-0.84 | 12-15m | +0-5% | ~5-7 min |

---

## 🔍 How to Monitor Progress

During training, watch for:

1. **Validation R² Trend**
   - Should steadily increase
   - If plateaus early (<30 epochs), might need higher LR

2. **Learning Rate**
   - Cosine: Smooth decay
   - OneCycle: U-shape (up then down)
   - Plateau: Step-wise drops

3. **Training vs Validation Loss**
   - Both should decrease
   - If training << validation, add regularization (higher weight_decay)

4. **Best Model Checkpoints**
   - Script saves best model automatically
   - Look for "✓ New best model!" messages

---

## 📈 After Training: Compare Results

```bash
cd ml_training
python experiments/neural_networks/run_advanced_experiments.py --compare-only
```

This will show:
- Best R² and MAE for each configuration
- Summary statistics
- Sorted leaderboard

---

## 🎯 Next Steps After Reaching R² > 0.85

If you reach R² > 0.85, consider:

1. **Ensemble Methods**
   - Average predictions from multiple models
   - Expected: +1-3% R²

2. **Model Architecture Improvements**
   - Attention mechanisms
   - Deeper ResNet (more residual blocks)
   - Multi-scale feature extraction

3. **Data Augmentation**
   - Add noise to training data
   - Synthetic trajectories

4. **Test on Real Data**
   - Validate on unseen scenarios
   - Check generalization

---

## 🛠️ Troubleshooting

### GPU Out of Memory
- Reduce batch size: `--batch-size 64` or `32`
- Use smaller model: Try `cnn` instead of `resnet`

### Training Diverges (Loss → NaN)
- Lower learning rate by 50%
- Add warmup epochs
- Use `resnet_warmup_cosine` config

### Training Too Slow
- Increase batch size to 256 or 512
- Use OneCycleLR for faster convergence
- Reduce epochs to 50-80

---

## 📝 Example Session

```bash
# 1. Try extended training with cosine annealing (RECOMMENDED)
cd ml_training
python experiments/neural_networks/train_advanced.py --config resnet_cosine_100

# 2. If that works well, try OneCycle for potentially higher R²
python experiments/neural_networks/train_advanced.py --config resnet_onecycle

# 3. Run all experiments overnight and compare
python experiments/neural_networks/run_advanced_experiments.py

# 4. Check results
python experiments/neural_networks/run_advanced_experiments.py --compare-only
```

---

## 📊 Results Location

All results are saved to:
```
ml_training/output/results/neural_net_advanced_{config}_{timestamp}/
├── resnet_model.pth          # Best model weights
├── results.json              # Metrics and training history
└── training.log              # Full training log
```

---

## 🎓 Key Insights

1. **More epochs ≠ always better**
   - Cosine annealing helps extract more from same epochs
   - OneCycle can match 100 epochs in 50-80

2. **Batch size matters**
   - Larger batches (256-512) = more stable gradients
   - Smaller batches (32-128) = better generalization
   - For 4GB GPU: Use 128-256

3. **Learning rate is critical**
   - Too high: Training diverges
   - Too low: Gets stuck in local minima
   - OneCycle finds optimal automatically

4. **Early stopping is your friend**
   - Prevents overfitting
   - Saves time
   - Script stops if no improvement for 15-25 epochs

---

## 📞 Quick Commands Cheatsheet

```bash
# Run best configuration (extended training)
python experiments/neural_networks/train_advanced.py --config resnet_cosine_100

# Run fastest configuration (OneCycle)
python experiments/neural_networks/train_advanced.py --config resnet_onecycle

# Run all experiments
python experiments/neural_networks/run_advanced_experiments.py

# Run specific experiments
python experiments/neural_networks/run_advanced_experiments.py --configs resnet_cosine_100 resnet_onecycle

# Compare existing results
python experiments/neural_networks/run_advanced_experiments.py --compare-only

# Force CPU (for debugging)
python experiments/neural_networks/train_advanced.py --config resnet_cosine_100 --device cpu
```

---

## 🎉 Expected Outcome

**With these advanced configurations, you should be able to reach:**
- **R² = 0.85-0.88** (up from 0.80)
- **MAE = 9-12m** (down from 13-15m)
- **Training time: 5-10 minutes** per configuration

Good luck! 🚀
