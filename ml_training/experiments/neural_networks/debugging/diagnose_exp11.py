"""Diagnose exp11 dataset issues - check position scaling and data quality."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import numpy as np
import h5py
from data_loader import CSIDataLoader

print("="*70)
print("DIAGNOSING EXP11 DATASET")
print("="*70)

dataset_path = Path("D:/gilad/projects/Academy/CSI-Location/results/exp11_2025-11-15_14-07-52/dataset")

# Load data
loader = CSIDataLoader(dataset_path)
X_train, y_train, X_val, y_val = loader.load_all()

print(f"\n1. DATA SHAPES")
print(f"   Train: X={X_train.shape}, y={y_train.shape}")
print(f"   Val:   X={X_val.shape}, y={y_val.shape}")

print(f"\n2. POSITION STATISTICS (TRAIN)")
print(f"   X coordinate:")
print(f"     Min:  {y_train[:, 0].min():.2f}")
print(f"     Max:  {y_train[:, 0].max():.2f}")
print(f"     Mean: {y_train[:, 0].mean():.2f}")
print(f"     Std:  {y_train[:, 0].std():.2f}")
print(f"   Y coordinate:")
print(f"     Min:  {y_train[:, 1].min():.2f}")
print(f"     Max:  {y_train[:, 1].max():.2f}")
print(f"     Mean: {y_train[:, 1].mean():.2f}")
print(f"     Std:  {y_train[:, 1].std():.2f}")

print(f"\n3. POSITION STATISTICS (VAL)")
print(f"   X coordinate:")
print(f"     Min:  {y_val[:, 0].min():.2f}")
print(f"     Max:  {y_val[:, 0].max():.2f}")
print(f"     Mean: {y_val[:, 0].mean():.2f}")
print(f"     Std:  {y_val[:, 0].std():.2f}")
print(f"   Y coordinate:")
print(f"     Min:  {y_val[:, 1].min():.2f}")
print(f"     Max:  {y_val[:, 1].max():.2f}")
print(f"     Mean: {y_val[:, 1].mean():.2f}")
print(f"     Std:  {y_val[:, 1].std():.2f}")

print(f"\n4. FEATURE STATISTICS (TRAIN - first 10 features)")
for i in range(min(10, X_train.shape[1])):
    print(f"   Feature {i}: min={X_train[:, i].min():.2e}, max={X_train[:, i].max():.2e}, "
          f"mean={X_train[:, i].mean():.2e}, std={X_train[:, i].std():.2e}")

print(f"\n5. CHECK FOR NaN/Inf")
print(f"   Train X: NaN={np.isnan(X_train).sum()}, Inf={np.isinf(X_train).sum()}")
print(f"   Train y: NaN={np.isnan(y_train).sum()}, Inf={np.isinf(y_train).sum()}")
print(f"   Val X:   NaN={np.isnan(X_val).sum()}, Inf={np.isinf(X_val).sum()}")
print(f"   Val y:   NaN={np.isnan(y_val).sum()}, Inf={np.isinf(y_val).sum()}")

# Check raw MATLAB file
print(f"\n6. CHECKING RAW MATLAB FILE")
train_file = dataset_path / "train_data.mat"
with h5py.File(train_file, 'r') as f:
    print(f"   Keys in file: {list(f.keys())}")
    if 'positions_x' in f:
        pos_x_raw = f['positions_x'][:]
        pos_y_raw = f['positions_y'][:]
        print(f"   Raw positions_x shape: {pos_x_raw.shape}")
        print(f"   Raw positions_y shape: {pos_y_raw.shape}")
        print(f"   Raw X range: [{pos_x_raw.min():.2f}, {pos_x_raw.max():.2f}]")
        print(f"   Raw Y range: [{pos_y_raw.min():.2f}, {pos_y_raw.max():.2f}]")

# Compare with exp10
print(f"\n7. COMPARING WITH EXP10")
exp10_path = Path("D:/gilad/projects/Academy/CSI-Location/results/exp10_2025-11-07_12-40-00/dataset")
if exp10_path.exists():
    loader_exp10 = CSIDataLoader(exp10_path)
    X_train_10, y_train_10 = loader_exp10.load_train_data()
    print(f"   exp10 train: X={X_train_10.shape}, y={y_train_10.shape}")
    print(f"   exp10 position X range: [{y_train_10[:, 0].min():.2f}, {y_train_10[:, 0].max():.2f}]")
    print(f"   exp10 position Y range: [{y_train_10[:, 1].min():.2f}, {y_train_10[:, 1].max():.2f}]")
    print(f"   exp10 features: {X_train_10.shape[1]}")
else:
    print(f"   exp10 not found at {exp10_path}")

print("="*70)
