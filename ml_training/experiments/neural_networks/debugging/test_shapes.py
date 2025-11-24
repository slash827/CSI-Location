"""Quick test to verify data shape compatibility with ResNet."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import torch
from train_optimized import CSIDataset
from models import ResNetLocalization
import numpy as np

# Test data (similar to actual data)
print("Testing CSIDataset and ResNet Compatibility")
print("=" * 60)

# Create fake data with exp11 dimensions
n_samples = 100
n_features = 12291  # 3 wideband + 3*4*1024 per-subcarrier
X_test = np.random.randn(n_samples, n_features).astype(np.float32)
y_test = np.random.randn(n_samples, 2).astype(np.float32)

print(f"\nOriginal data shape:")
print(f"  X: {X_test.shape}")
print(f"  y: {y_test.shape}")

# Create dataset for ResNet
dataset = CSIDataset(X_test, y_test, model_type='resnet')

print(f"\nAfter CSIDataset reshaping:")
print(f"  Dataset length: {len(dataset)}")

# Get one sample
X_sample, y_sample = dataset[0]
print(f"  Single sample X shape: {X_sample.shape}")
print(f"  Single sample y shape: {y_sample.shape}")

# Create batch
batch_size = 32
batch_X = torch.stack([dataset[i][0] for i in range(batch_size)])
batch_y = torch.stack([dataset[i][1] for i in range(batch_size)])

print(f"\nBatch shapes:")
print(f"  Batch X: {batch_X.shape}")
print(f"  Batch y: {batch_y.shape}")

# Calculate n_subcarriers
n_wideband = 3
n_subcarrier_features = n_features - n_wideband
n_subcarriers = n_subcarrier_features // 3
print(f"\nCalculated n_subcarriers: {n_subcarriers}")
print(f"  (from {n_subcarrier_features} subcarrier features / 3 channels)")

# Create ResNet model
print(f"\nCreating ResNet with n_subcarriers={n_subcarriers}...")
model = ResNetLocalization(n_subcarriers=n_subcarriers)

n_params = sum(p.numel() for p in model.parameters())
print(f"  Model parameters: {n_params:,}")

# Test forward pass
print(f"\nTesting forward pass...")
try:
    model.eval()
    with torch.no_grad():
        output = model(batch_X)
    print(f"  ✓ Forward pass successful!")
    print(f"  Output shape: {output.shape}")
    print(f"  Expected shape: ({batch_size}, 2)")
    
    if output.shape == (batch_size, 2):
        print(f"\n✓ ALL TESTS PASSED!")
        print(f"  Data reshaping and model are compatible.")
    else:
        print(f"\n✗ Shape mismatch!")
except Exception as e:
    print(f"  ✗ Forward pass failed!")
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
