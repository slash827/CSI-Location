# Neural Network Approaches for CSI-Based Localization

**Status**: 📋 Planning Phase  
**Priority**: Medium (after hyperparameter tuning results)  
**Dataset**: exp10 (32,000 train, 8,000 val, 3,075 features)

---

## 🎯 Why Neural Networks?

### Advantages Over Tree-Based Models

1. **Non-linear Feature Interactions**
   - Tree models split features independently
   - Neural networks can learn complex combinations
   - Important for CSI where phase + magnitude patterns interact

2. **Spatial Pattern Recognition**
   - Can learn 2D spatial embeddings
   - Better for geographic coordinates prediction
   - Can capture distance-based patterns

3. **Scalability**
   - Fast inference once trained
   - Can handle more data efficiently
   - GPU acceleration available

4. **Potential for Better Accuracy**
   - Current best: 20.10m MAE (Random Forest)
   - Target: 12-15m MAE (25-40% improvement)

---

## 🏗️ Proposed Architectures

### 1. Multi-Layer Perceptron (MLP) ⭐ (Start Here!)

**Architecture:**
```
Input (3,075) 
  → Dense(1024, ReLU) + Dropout(0.3)
  → Dense(512, ReLU) + Dropout(0.3)
  → Dense(256, ReLU) + Dropout(0.2)
  → Dense(128, ReLU) + Dropout(0.2)
  → Dense(2, Linear)  # (x, y) coordinates
```

**Why This Works:**
- Simple to implement and train
- Progressive dimensionality reduction (3075 → 1024 → 512 → 256 → 128 → 2)
- Dropout prevents overfitting
- ReLU for non-linearity

**Training Configuration:**
- Optimizer: Adam (lr=0.001)
- Loss: MSE (Mean Squared Error)
- Batch size: 256
- Epochs: 50-100 (with early stopping)
- L2 regularization: 1e-4

**Expected Performance:**
- Training time: ~5-10 minutes (CPU) or ~1-2 min (GPU)
- Val MAE: 15-18m (optimistic), 18-22m (realistic)

**Advantages:**
✅ Simple to implement
✅ Fast training
✅ Good baseline for neural networks
✅ Works well with tabular data

**Disadvantages:**
❌ Doesn't exploit frequency structure
❌ Treats all features equally
❌ May not capture spatial patterns optimally

---

### 2. CNN-Based Architecture ⭐⭐ (Better!)

**Idea:** Treat per-subcarrier features as 1D signals (frequency domain)

**Architecture:**
```
Input reshape: (3,075) → (3, 1024, 1)  # [RSS, SINR, H_mag] × 1024 subcarriers
  → Conv1D(64, kernel=7, stride=2) + ReLU + BatchNorm
  → MaxPool1D(2)
  → Conv1D(128, kernel=5, stride=2) + ReLU + BatchNorm
  → MaxPool1D(2)
  → Conv1D(256, kernel=3, stride=1) + ReLU + BatchNorm
  → GlobalAveragePooling1D()
  → Dense(256, ReLU) + Dropout(0.3)
  → Dense(128, ReLU) + Dropout(0.2)
  → Dense(2, Linear)  # (x, y) coordinates
```

**Why This Works:**
- Convolutional layers exploit frequency continuity
- Different subcarriers nearby are correlated
- Learns frequency patterns (multipath structure)
- Pooling reduces dimensionality naturally

**Training Configuration:**
- Optimizer: Adam (lr=0.0005)
- Loss: MSE
- Batch size: 128
- Epochs: 50-100
- Data augmentation: Add Gaussian noise to inputs

**Expected Performance:**
- Training time: ~10-20 minutes (CPU) or ~2-5 min (GPU)
- Val MAE: 14-17m (optimistic), 16-20m (realistic)

**Advantages:**
✅ Exploits frequency structure
✅ Fewer parameters than MLP
✅ More interpretable (can visualize filters)
✅ Robust to noise

---

### 3. ResNet-style Architecture ⭐⭐⭐ (Best - If Time Permits)

**Idea:** Deep network with skip connections for better gradient flow

**Architecture:**
```
Input reshape: (3,075) → (3, 1024, 1)
  → Initial Conv1D(64, kernel=7, stride=2) + BN + ReLU
  → ResBlock1 (Conv → BN → ReLU → Conv → BN) + Skip
  → ResBlock2 (Conv → BN → ReLU → Conv → BN) + Skip
  → ResBlock3 (Conv → BN → ReLU → Conv → BN) + Skip
  → GlobalAveragePooling1D()
  → Dense(256, ReLU) + Dropout(0.3)
  → Dense(2, Linear)
```

**Why This Works:**
- Skip connections enable deeper networks
- Better gradient flow during training
- Can learn hierarchical features (low-level → high-level)
- State-of-the-art in many domains

**Expected Performance:**
- Training time: ~20-30 minutes (CPU) or ~5-10 min (GPU)
- Val MAE: 12-16m (optimistic), 15-18m (realistic)

**Advantages:**
✅ Can go deeper without vanishing gradients
✅ Better feature extraction
✅ Potential for best accuracy

**Disadvantages:**
❌ More complex to implement
❌ Longer training time
❌ More hyperparameters to tune

---

## 📊 Implementation Plan

### Phase 1: MLP Baseline (Week 1)

**Step 1**: Create `models/neural_networks.py` with MLP class
```python
import torch
import torch.nn as nn

class MLPLocalization(nn.Module):
    def __init__(self, input_dim=3075):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 1024),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 2)
        )
    
    def forward(self, x):
        return self.network(x)
```

**Step 2**: Create `experiments/train_neural_net.py` for training
- Load data with PyTorch DataLoader
- Training loop with early stopping
- Learning rate scheduling
- Model checkpointing

**Step 3**: Run experiments
```bash
python experiments/train_neural_net.py --model mlp --epochs 100 --lr 0.001
```

**Expected Timeline**: 2-3 days

---

### Phase 2: CNN Architecture (Week 2)

**Step 1**: Implement CNN in `models/neural_networks.py`

**Step 2**: Reshape data in data_loader
```python
# Reshape for CNN: (N, 3075) → (N, 3, 1024, 1)
# 3 channels: RSS, SINR, H_mag
# 1024: subcarriers
X_reshaped = X[:, :3].reshape(-1, 3, 1, 1).concatenate(
    X[:, 3:3+1024].reshape(-1, 1, 1024, 1),
    X[:, 3+1024:3+2048].reshape(-1, 1, 1024, 1),
    X[:, 3+2048:].reshape(-1, 1, 1024, 1)
)
```

**Step 3**: Train and compare with MLP

**Expected Timeline**: 3-4 days

---

### Phase 3: Hyperparameter Tuning (Week 3)

**Tune:**
- Learning rate: [0.0001, 0.0005, 0.001, 0.005]
- Dropout: [0.1, 0.2, 0.3, 0.4]
- Batch size: [64, 128, 256, 512]
- Hidden dimensions: [512, 1024, 2048]

**Tool**: Optuna for automatic hyperparameter search (but limit trials to save time)

---

## 🛠️ Technical Requirements

### Libraries Needed

```bash
pip install torch torchvision  # PyTorch
pip install tensorboard        # For visualization
pip install optuna             # For hyperparameter tuning (optional)
```

**Alternative: TensorFlow/Keras** (easier for beginners)
```bash
pip install tensorflow
```

### Hardware Considerations

**CPU Training:**
- MLP: ~5-10 min per epoch
- CNN: ~10-20 min per epoch
- Total: 1-3 hours

**GPU Training (if available):**
- MLP: ~30 sec per epoch
- CNN: ~1-2 min per epoch
- Total: 10-30 minutes

**Recommendation**: Start with CPU, optimize later with GPU if needed

---

## 📈 Expected Results Comparison

| Model | Val MAE | Training Time | Complexity |
|-------|---------|---------------|------------|
| **Current Best (RF)** | 20.10 m | 39s | Low |
| Linear | 23.31 m | 28s | Very Low |
| XGBoost (expected) | 18-20 m | 60-120s | Medium |
| **MLP** | 16-20 m | 5-30 min | Medium |
| **CNN** | 14-18 m | 10-60 min | Medium-High |
| **ResNet** | 12-16 m | 20-90 min | High |

---

## 🎯 Success Criteria

### Minimum Viable Product (MVP)
- ✅ MLP implementation working
- ✅ Training completes without errors
- ✅ Val MAE < 22m (better than Linear)

### Good Performance
- ✅ Val MAE < 18m (better than Random Forest)
- ✅ Training time < 30 minutes
- ✅ Stable convergence (no overfitting)

### Excellent Performance
- ✅ Val MAE < 15m (25% better than RF)
- ✅ Ensemble with RF achieves < 14m MAE
- ✅ Production-ready model with inference < 1ms

---

## 🚀 Quick Start Commands (When Ready)

### Step 1: Install PyTorch
```bash
pip install torch torchvision torchaudio
```

### Step 2: Create neural network module
```bash
# Will create: ml_training/models/neural_networks.py
```

### Step 3: Create training script
```bash
# Will create: ml_training/experiments/train_neural_net.py
```

### Step 4: Train MLP
```bash
cd ml_training
python experiments/train_neural_net.py --model mlp
```

### Step 5: Train CNN
```bash
python experiments/train_neural_net.py --model cnn
```

### Step 6: Compare results
```bash
python experiments/compare_runs.py
```

---

## 🔬 Advanced Techniques (Future)

### 1. Ensemble Models
Combine Random Forest + XGBoost + Neural Network:
```python
final_prediction = 0.4 * rf_pred + 0.3 * xgb_pred + 0.3 * nn_pred
```
Expected: 12-14m MAE

### 2. Transfer Learning
Pre-train on exp09 dataset, fine-tune on exp10:
```python
model.load_pretrained('exp09_best.pth')
model.fine_tune(exp10_data, epochs=20)
```

### 3. Multi-Task Learning
Predict both position AND uncertainty:
```python
# Output: (x, y, uncertainty_x, uncertainty_y)
loss = mse_loss(pred_pos, true_pos) + nll_loss(pred_unc, errors)
```

### 4. Attention Mechanisms
Learn which subcarriers are most important:
```python
attention_weights = softmax(Q @ K.T / sqrt(d_k))
weighted_features = attention_weights @ V
```

---

## 📝 Notes

- **Start simple**: Begin with MLP, add complexity only if needed
- **Monitor overfitting**: Use validation loss, not just training loss
- **Early stopping**: Stop training when val loss stops improving (patience=10-15 epochs)
- **Learning rate scheduling**: Reduce LR when plateau (factor=0.5, patience=5)
- **Regularization**: Use dropout + L2 to prevent overfitting
- **Batch normalization**: Helps training stability in deeper networks

---

**Status**: ⏸️ Waiting for optimized RF/XGBoost results before starting neural networks

**Next Action**: Review results from `run_optimized_models.py`, then decide whether to proceed with neural networks or further tune tree-based models.
