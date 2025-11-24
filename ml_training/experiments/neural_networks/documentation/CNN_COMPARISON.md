# CNN Architecture Comparison

## Models Tested

### 1. Simple CNN (Baseline) ✅
**Architecture:**
- Conv1: 3 → 16 channels, kernel=5, MaxPool(4)
- Conv2: 16 → 32 channels, kernel=5, MaxPool(4)
- FC1: 8192 → 128
- FC2: 128 → 2 (output)

**Parameters:** 1,051,810

**Performance on exp11:**
- Best MAE: **14.48m** (epoch 11)
- Best R²: **0.785**
- Training: 26 epochs (early stopped)

**Key Features:**
- No batch normalization
- No dropout
- Simple and fast
- Proven to work (unlike ResNet!)

---

### 2. Improved CNN (Enhanced) 🚀
**Architecture:**
- Conv1: 3 → 32 channels, kernel=7, BN, MaxPool(4)
- Conv2: 32 → 64 channels, kernel=5, BN, MaxPool(4)
- Conv3: 64 → 128 channels, kernel=3, BN, MaxPool(4)
- FC1: 8192 → 256, Dropout(0.3)
- FC2: 256 → 128, Dropout(0.3)
- FC3: 128 → 2 (output)

**Parameters:** ~2.4M (estimated)

**Improvements over Simple CNN:**
1. **Deeper network**: 3 conv layers instead of 2
2. **Batch Normalization**: After each conv layer for training stability
3. **More channels**: 32→64→128 instead of 16→32
4. **Larger FC layers**: 256→128 instead of just 128
5. **Dropout**: 0.3 for better regularization
6. **Larger kernels**: 7-5-3 for better receptive field

**Expected Benefits:**
- Better feature extraction (3 layers)
- More stable training (BatchNorm)
- Better generalization (Dropout)
- Higher capacity (more parameters)

**Potential MAE:** 13-14m (target: beat 14.48m)

---

### 3. ResNet (Failed) ❌
**Why it failed:**
- Validation loss exploded (5113 at epoch 5)
- R² went to -6.67 (catastrophic)
- BatchNorm + skip connections overfit to training distribution
- Too complex for dataset with distribution variance

---

## Training Enhancements Added

### Epoch Timing ⏱️
```python
# Per epoch
Time=1m 23s  # Human-readable format

# Summary
Total training time: 45m 12s
Average epoch time: 1m 44s
Data loading time: 2m 15s
```

### Better Logging
```
Epoch   1/80: Train=185.46, Val=194.46, MAE=17.27m, R²=0.706, LR=1.0e-03, Time=1.4s
  ✓ New best MAE: 17.27m
```

### Model Saving
- Saves best model state
- Includes metadata (MAE, epoch, parameters)
- Path: `saved_models/{model}_cnn_best.pth`

---

## Performance Target

| Metric | Simple CNN (Baseline) | Improved CNN (Target) |
|--------|----------------------|----------------------|
| MAE | 14.48m | **< 14m** |
| R² | 0.785 | **> 0.79** |
| Params | 1.05M | ~2.4M |
| Epochs | 26 | TBD |

---

## Why Simple CNN Works (vs ResNet)

1. **No BatchNorm issues**: BN learns mean/std from training, struggles when val has different distribution
2. **No skip connections**: Skip connections can amplify distribution mismatch
3. **Right complexity**: Deep enough to learn, not so deep it memorizes
4. **Robust architecture**: Standard conv→pool→fc works for CSI data

---

## Next Steps

1. ⏳ Wait for Improved CNN training to complete
2. 📊 Compare Simple vs Improved performance
3. 🎯 If Improved CNN beats 14.48m → use it
4. 📈 If not, stick with Simple CNN (14.48m is already great!)
5. 📝 Document final results in presentation

---

## Key Insight from Debugging Session

**The problem was never just normalization** - it was:
1. Distribution variance mismatch (val had 6.6% higher RSRP std)
2. **Wrong model architecture** (ResNet catastrophically failed)

**Solution:**
- Independent normalization (fixed variance issue)
- Simple CNN architecture (avoids overfitting)
- Result: R²=0.785, MAE=14.48m ✅

The "simpler is better" principle proved correct!
