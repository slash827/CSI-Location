# Neural Networks for CSI-Based Localization

This folder contains neural network implementations for CSI-based indoor localization.

## 📁 Structure

```
neural_networks/
├── models.py          # Model architectures (MLP, CNN, ResNet)
├── train.py           # Training script
├── __init__.py        # Module initialization
└── README.md          # This file
```

## 🏗️ Models

### 1. MLP (Multi-Layer Perceptron)
- **Architecture**: Simple feedforward network
- **Layers**: 3075 → 1024 → 512 → 256 → 128 → 2
- **Parameters**: ~4.5M
- **Expected MAE**: 16-20m
- **Training time**: ~5-10 min (CPU)

### 2. CNN (Convolutional Neural Network)
- **Architecture**: 1D convolutions on frequency domain
- **Input**: [batch, 3 channels, 1024 subcarriers]
- **Channels**: RSS, SINR, H_mag
- **Parameters**: ~300K
- **Expected MAE**: 14-18m
- **Training time**: ~10-20 min (CPU)

### 3. ResNet (Residual Network)
- **Architecture**: Deep network with skip connections
- **Blocks**: 3 residual blocks
- **Parameters**: ~500K
- **Expected MAE**: 12-16m
- **Training time**: ~20-30 min (CPU)

## 🚀 Quick Start

### Install PyTorch

```bash
pip install torch torchvision torchaudio
```

### Test Models

```bash
cd ml_training/experiments/neural_networks
python models.py
```

Expected output:
```
Testing Neural Network Models
======================================================================

1. MLP Localization
----------------------------------------------------------------------
Input shape: torch.Size([32, 3075])
Output shape: torch.Size([32, 2])
Parameters: 4,562,946

2. CNN Localization
----------------------------------------------------------------------
Input shape: torch.Size([32, 3, 1024])
Output shape: torch.Size([32, 2])
Parameters: 314,626

3. ResNet Localization
----------------------------------------------------------------------
Input shape: torch.Size([32, 3, 1024])
Output shape: torch.Size([32, 2])
Parameters: 542,210

======================================================================
All models working correctly!
```

### Train MLP

```bash
cd ml_training
python experiments/neural_networks/train.py --model mlp --epochs 100
```

### Train CNN

```bash
python experiments/neural_networks/train.py --model cnn --epochs 100
```

### Train ResNet

```bash
python experiments/neural_networks/train.py --model resnet --epochs 100
```

## ⚙️ Configuration Options

```bash
python experiments/neural_networks/train.py \
    --model mlp \              # Model type: mlp, cnn, resnet
    --epochs 100 \             # Number of epochs
    --batch_size 256 \         # Batch size
    --lr 0.001 \               # Learning rate
    --weight_decay 1e-4 \      # L2 regularization
    --early_stopping_patience 15 \  # Early stopping patience
    --device auto              # Device: auto, cuda, cpu
```

## 📊 Expected Results

### Comparison with Baseline

| Model | Val MAE | Training Time | Parameters | Improvement |
|-------|---------|---------------|------------|-------------|
| **Random Forest (baseline)** | 20.10 m | 39s | N/A | - |
| **MLP** | 16-20 m | 5-10 min | 4.5M | 0-20% |
| **CNN** | 14-18 m | 10-20 min | 300K | 10-30% |
| **ResNet** | 12-16 m | 20-30 min | 500K | 20-40% |

### Training Progress Example

```
Epoch 1/100 (12.3s)
  Train Loss: 245.6789
  Val Loss: 198.2345
  Val MAE: 24.56 m
  Val R²: 0.4523
  LR: 0.001000

Epoch 10/100 (12.1s)
  Train Loss: 156.7890
  Val Loss: 145.6789
  Val MAE: 18.34 m
  Val R²: 0.5678
  LR: 0.001000

...

Epoch 45/100 (11.9s)
  Train Loss: 89.1234
  Val Loss: 112.3456
  Val MAE: 14.67 m
  Val R²: 0.6890
  LR: 0.000125
  ✓ New best model! (MAE: 14.67 m)
```

## 📁 Output Structure

After training, results are saved to:

```
ml_training/output/results/neural_net_{model}_{timestamp}/
├── {model}_model.pth      # Best model weights
└── results.json           # Training history and metrics
```

Example `results.json`:
```json
{
  "model_type": "cnn",
  "config": {
    "epochs": 100,
    "batch_size": 256,
    "lr": 0.001,
    "weight_decay": 0.0001
  },
  "final_metrics": {
    "position_mae": 15.23,
    "position_rmse": 18.45,
    "r2": 0.6745
  },
  "history": {
    "train_loss": [...],
    "val_loss": [...],
    "val_mae": [...],
    "val_r2": [...]
  }
}
```

## 🎯 Tips for Best Results

### 1. Start with MLP
- Simplest to train
- Fast convergence
- Good baseline

### 2. Try CNN for Better Accuracy
- Exploits frequency structure
- Fewer parameters than MLP
- Usually better generalization

### 3. Use ResNet if You Need Best Performance
- Most complex
- Requires more tuning
- Potential for best accuracy

### 4. Monitor Training
- Watch for overfitting (train/val gap)
- Use early stopping
- Reduce LR on plateau

### 5. Hyperparameter Tuning
- Learning rate: [0.0001, 0.0005, 0.001, 0.005]
- Batch size: [64, 128, 256, 512]
- Weight decay: [1e-5, 1e-4, 1e-3]

## 🐛 Troubleshooting

### Out of Memory
```bash
# Reduce batch size
python train.py --batch_size 128
```

### Training Too Slow
```bash
# Use GPU if available
python train.py --device cuda

# Or reduce epochs
python train.py --epochs 50
```

### Overfitting
```bash
# Increase weight decay
python train.py --weight_decay 1e-3

# Or reduce model size (use CNN instead of MLP)
python train.py --model cnn
```

### Poor Performance
- Make sure data is preprocessed correctly
- Check for NaN/Inf values
- Try different learning rates
- Increase epochs

## 📚 Next Steps

1. **Train all 3 models**
2. **Compare results** with baseline
3. **Ensemble predictions** for best accuracy
4. **Fine-tune hyperparameters**
5. **Implement attention mechanisms** (advanced)

## 🏆 Current Best Results

*Will be updated as experiments complete*

- **MLP**: TBD
- **CNN**: TBD
- **ResNet**: TBD

---

**Status**: ✅ Ready to train!
