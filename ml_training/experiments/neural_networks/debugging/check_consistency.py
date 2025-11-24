"""Check if train and val data are consistent and properly structured."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import numpy as np
import torch
from data_loader import CSIDataLoader
from preprocessing import preprocess_dataset
from train_optimized import CSIDataset
from sklearn.preprocessing import StandardScaler

print("="*70)
print("CHECKING DATA CONSISTENCY")
print("="*70)

dataset_path = Path("D:/gilad/projects/Academy/CSI-Location/results/exp11_2025-11-15_14-07-52/dataset")

# Load with preprocessing (as in training)
X_train, y_train, X_val, y_val, preprocessor = preprocess_dataset(dataset_path)

print(f"\n1. AFTER PREPROCESSING")
print(f"   Train: X={X_train.shape}, y={y_train.shape}")
print(f"   Val:   X={X_val.shape}, y={y_val.shape}")

# Check feature statistics
print(f"\n2. FEATURE STATISTICS")
print(f"   Train X: mean={X_train.mean():.4f}, std={X_train.std():.4f}")
print(f"   Val X:   mean={X_val.mean():.4f}, std={X_val.std():.4f}")
print(f"   Train y: mean={y_train.mean():.2f}, std={y_train.std():.2f}")
print(f"   Val y:   mean={y_val.mean():.2f}, std={y_val.std():.2f}")

# Normalize targets
target_scaler = StandardScaler()
y_train_scaled = target_scaler.fit_transform(y_train)
y_val_scaled = target_scaler.transform(y_val)

print(f"\n3. AFTER TARGET NORMALIZATION")
print(f"   Train y scaled: mean={y_train_scaled.mean():.4f}, std={y_train_scaled.std():.4f}")
print(f"   Val y scaled:   mean={y_val_scaled.mean():.4f}, std={y_val_scaled.std():.4f}")

# Create datasets and check reshaping
train_dataset = CSIDataset(X_train[:100], y_train_scaled[:100], model_type='resnet')
val_dataset = CSIDataset(X_val[:100], y_val_scaled[:100], model_type='resnet')

print(f"\n4. AFTER CSIDataset RESHAPING")
X_sample_train, y_sample_train = train_dataset[0]
X_sample_val, y_sample_val = val_dataset[0]

print(f"   Train sample: X shape={X_sample_train.shape}, y shape={y_sample_train.shape}")
print(f"   Val sample:   X shape={X_sample_val.shape}, y shape={y_sample_val.shape}")
print(f"   Train y value: {y_sample_train.numpy()}")
print(f"   Val y value:   {y_sample_val.numpy()}")

# Check if features look similar
print(f"\n5. FEATURE SIMILARITY CHECK")
print(f"   Train X sample stats: min={X_sample_train.min():.2f}, max={X_sample_train.max():.2f}, mean={X_sample_train.mean():.2f}")
print(f"   Val X sample stats:   min={X_sample_val.min():.2f}, max={X_sample_val.max():.2f}, mean={X_sample_val.mean():.2f}")

# Check if NLOS distribution differs between train and val
from data_loader import CSIDataLoader
loader = CSIDataLoader(dataset_path)

try:
    train_meta = loader.load_nlos_metadata(dataset_path, split='train')
    val_meta = loader.load_nlos_metadata(dataset_path, split='val')
    
    print(f"\n6. NLOS DISTRIBUTION")
    print(f"   Train NLOS conditions:")
    train_conds, train_counts = np.unique(train_meta['nlos_condition'], return_counts=True)
    for cond, count in zip(train_conds, train_counts):
        print(f"     {cond}: {count} ({count/len(train_meta['nlos_condition'])*100:.1f}%)")
    
    print(f"   Val NLOS conditions:")
    val_conds, val_counts = np.unique(val_meta['nlos_condition'], return_counts=True)
    for cond, count in zip(val_conds, val_counts):
        print(f"     {cond}: {count} ({count/len(val_meta['nlos_condition'])*100:.1f}%)")
except Exception as e:
    print(f"\n6. NLOS DISTRIBUTION: Could not load metadata - {e}")

print("="*70)
