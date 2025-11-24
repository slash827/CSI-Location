"""Quick test to see what the model is actually predicting."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import torch
import numpy as np
from train_optimized import CSIDataset
from models import ResNetLocalization
from data_loader import CSIDataLoader

print("="*70)
print("TESTING MODEL PREDICTIONS ON EXP11")
print("="*70)

# Load data
dataset_path = Path("D:/gilad/projects/Academy/CSI-Location/results/exp11_2025-11-15_14-07-52/dataset")
loader = CSIDataLoader(dataset_path)
X_train, y_train, X_val, y_val = loader.load_all()

print(f"\nData loaded:")
print(f"  Train: X={X_train.shape}, y={y_train.shape}")
print(f"  Val:   X={X_val.shape}, y={y_val.shape}")

print(f"\nTarget (y) statistics:")
print(f"  Train y min: {y_train.min():.2f}, max: {y_train.max():.2f}")
print(f"  Train y mean: {y_train.mean():.2f}, std: {y_train.std():.2f}")
print(f"  Val y min: {y_val.min():.2f}, max: {y_val.max():.2f}")
print(f"  Val y mean: {y_val.mean():.2f}, std: {y_val.std():.2f}")

# Create dataset
print(f"\nCreating CSIDataset...")
train_dataset = CSIDataset(X_train[:100], y_train[:100], model_type='resnet')

# Check shapes after reshaping
X_sample, y_sample = train_dataset[0]
print(f"  Sample X shape: {X_sample.shape}")
print(f"  Sample y shape: {y_sample.shape}")
print(f"  Sample y value: {y_sample.numpy()}")

# Create model
n_wideband = 3
n_subcarriers = (X_train.shape[1] - n_wideband) // 3
print(f"\nCreating ResNet with n_subcarriers={n_subcarriers}...")
model = ResNetLocalization(n_subcarriers=n_subcarriers)

# Random initialization predictions
print(f"\nTesting predictions with random initialization...")
model.eval()
with torch.no_grad():
    batch_X = torch.stack([train_dataset[i][0] for i in range(10)])
    batch_y = torch.stack([train_dataset[i][1] for i in range(10)])
    
    print(f"  Batch X shape: {batch_X.shape}")
    print(f"  Batch y shape: {batch_y.shape}")
    print(f"  Batch y (true):")
    print(f"    {batch_y.numpy()[:3]}")
    
    predictions = model(batch_X)
    print(f"  Predictions shape: {predictions.shape}")
    print(f"  Predictions (random init):")
    print(f"    {predictions.numpy()[:3]}")
    
    # Compute loss
    loss = torch.nn.functional.mse_loss(predictions, batch_y)
    print(f"\n  MSE Loss: {loss.item():.4f}")
    
    # Compute MAE
    mae = torch.abs(predictions - batch_y).mean()
    print(f"  MAE: {mae.item():.2f} m")
    
    # Check if predictions are in reasonable range
    pred_mean = predictions.mean().item()
    pred_std = predictions.std().item()
    print(f"\n  Prediction statistics:")
    print(f"    Mean: {pred_mean:.2f}")
    print(f"    Std:  {pred_std:.2f}")
    print(f"    Min:  {predictions.min().item():.2f}")
    print(f"    Max:  {predictions.max().item():.2f}")

print("="*70)
