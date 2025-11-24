# Neural Networks - Training Scripts

This folder contains the main training scripts for different CNN architectures and training strategies.

## 🎯 Quick Start

### Best Performance (Use This!)

**Improved CNN with Independent Normalization** - Achieved **11.47m MAE** on exp11 (NLOS):

```bash
python train_improved_cnn.py --epochs 80 --lr 0.001 --patience 15
```

### Training Scripts

| Script | Architecture | Best For | MAE | Notes |
|--------|-------------|----------|-----|-------|
| `train_improved_cnn.py` | **Improved CNN** | **NLOS** | **11.47m** | ⭐ Best overall |
| `train_independent_norm.py` | Simple CNN | NLOS | 14.48m | Independent norm |
| `train.py` | ResNet | LOS | 13.5m | Good for LOS only |
| `train_advanced.py` | ResNet + techniques | LOS | ~13m | Advanced features |
| `train_optimized.py` | Optimized CNN | General | ~12-14m | Balanced approach |

## 📊 Training Examples

### 1. Improved CNN (Recommended for NLOS)

```bash
# Full training with best settings
python train_improved_cnn.py \
    --epochs 80 \
    --lr 0.001 \
    --patience 15 \
    --batch_size 32

# Quick test run
python train_improved_cnn.py --epochs 10
```

**Why this works:**
- ✅ No skip connections (better for NLOS)
- ✅ Independent normalization per dataset
- ✅ Proper regularization
- ✅ Optimized architecture

### 2. Independent Normalization

```bash
# Standard training
python train_independent_norm.py \
    --epochs 50 \
    --patience 10 \
    --lr 0.001

# With custom batch size
python train_independent_norm.py \
    --epochs 80 \
    --batch_size 64 \
    --lr 0.0005
```

**Key feature:** Fits separate StandardScalers for train and validation sets.

### 3. Basic CNN Training

```bash
# Simple training
python train.py --model cnn

# ResNet training (for LOS datasets)
python train.py --model resnet
```

### 4. Advanced Training

```bash
# With advanced techniques
python train_advanced.py \
    --lr 0.001 \
    --weight_decay 1e-4 \
    --dropout 0.3
```

### 5. Optimized Training

```bash
# Optimized configuration
python train_optimized.py \
    --epochs 100 \
    --early_stopping
```

## 🔧 Common Arguments

All training scripts support these common arguments:

```
--epochs INT          Number of training epochs (default: 50-80)
--batch_size INT      Batch size (default: 32)
--lr FLOAT            Learning rate (default: 0.001)
--patience INT        Early stopping patience (default: 10-15)
--dataset_path PATH   Path to dataset folder
```

## 📈 Expected Results

### On exp11 (NLOS Dataset - 40K samples, 70% NLOS):

| Model | MAE | R² | Training Time |
|-------|-----|-----|---------------|
| Improved CNN | 11.47m | 0.858 | ~60 min |
| Simple CNN | 14.48m | 0.75 | ~45 min |
| ResNet | Failed | -6.67 | N/A |

### On exp10 (LOS Dataset - 40K samples, pure LOS):

| Model | MAE | R² | Training Time |
|-------|-----|-----|---------------|
| ResNet | 13.5m | 0.80 | ~50 min |
| Simple CNN | ~15m | ~0.75 | ~40 min |

## 💡 Training Tips

### 1. Choose the Right Script

- **NLOS data (exp11):** Use `train_improved_cnn.py` (no skip connections)
- **LOS data (exp10):** Use `train.py` with ResNet
- **Experimenting:** Start with `train_independent_norm.py`

### 2. Monitor Training

All scripts output training metrics:
```
Epoch 1/80: train_loss=2500.5, val_loss=2100.3, val_MAE=45.2m, val_R²=0.123
Epoch 2/80: train_loss=1800.2, val_loss=1650.4, val_MAE=38.5m, val_R²=0.334
...
Epoch 42/80: train_loss=650.1, val_loss=580.2, val_MAE=11.47m, val_R²=0.858 ⭐
```

### 3. Early Stopping

All scripts use early stopping to prevent overfitting:
- Monitors validation MAE
- Stops if no improvement for `patience` epochs
- Restores best weights automatically

### 4. Saving Models

Models are automatically saved to `../saved_models/`:
```
saved_models/
├── improved_cnn_best.pth       # Best Improved CNN
├── simple_cnn_best.pth         # Best Simple CNN
└── resnet_best.pth             # Best ResNet
```

## 🚀 Advanced Usage

### Custom Dataset Path

```bash
python train_improved_cnn.py \
    --dataset_path "../../results/exp11_2025-11-15_14-07-52/dataset"
```

### GPU Training

Scripts automatically use GPU if available:
```python
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Using device: {device}")
```

### Resume Training

Most scripts save checkpoints that can be loaded:
```python
# In your script
checkpoint = torch.load('saved_models/improved_cnn_best.pth')
model.load_state_dict(checkpoint)
```

## 📊 Comparing Results

After training multiple models:

```bash
cd ../analysis
python compare_models.py
```

This generates comparison plots and statistics.

## 🐛 Debugging

If training fails:

1. **Check shapes:**
   ```bash
   cd ../debugging
   python test_shapes.py
   ```

2. **Verify data:**
   ```bash
   python check_nlos_dist.py
   ```

3. **Diagnose issues:**
   ```bash
   python diagnose_exp11.py
   ```

## 📚 Related Documentation

- **Model Architectures:** `../models.py`
- **Training Results:** `../documentation/RESULTS.md`
- **Optimization Guide:** `../documentation/OPTIMIZATION_GUIDE.md`
- **Advanced Training:** `../documentation/ADVANCED_TRAINING_GUIDE.md`

## 🎓 Key Learnings

### What Works for NLOS:
✅ **Simple CNN** (no skip connections)  
✅ **Independent normalization**  
✅ **Moderate regularization**  
✅ **Patient early stopping**  

### What Doesn't Work for NLOS:
❌ **ResNet** (skip connections fail)  
❌ **Shared normalization** (distribution mismatch)  
❌ **Heavy regularization** (underfitting)  
❌ **Too aggressive early stopping**  

---

**Last Updated:** November 18, 2025  
**Best Result:** 11.47m MAE with Improved CNN on exp11 NLOS
