"""
Verify that the new preprocessing approach gives consistent train/val statistics.
"""
import sys
from pathlib import Path

# Add ml_training to path
ml_training_path = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ml_training_path))

import numpy as np
from preprocessing import preprocess_dataset
from config import DEFAULT_DATASET_PATH

print("=" * 70)
print("VERIFYING NORMALIZATION FIX")
print("=" * 70)

# Load and preprocess
X_train, y_train, X_val, y_val, preprocessor = preprocess_dataset(
    DEFAULT_DATASET_PATH, 
    remove_outliers=False,  # Disable to keep all data
    save_processed=False
)

print("\n" + "=" * 70)
print("NORMALIZATION STATISTICS CHECK")
print("=" * 70)

print("\nTrain features:")
print(f"  Mean: {X_train.mean():.6f}")
print(f"  Std:  {X_train.std():.6f}")
print(f"  Min:  {X_train.min():.2f}")
print(f"  Max:  {X_train.max():.2f}")

print("\nVal features:")
print(f"  Mean: {X_val.mean():.6f}")
print(f"  Std:  {X_val.std():.6f}")
print(f"  Min:  {X_val.min():.2f}")
print(f"  Max:  {X_val.max():.2f}")

# Check if they're close
mean_diff = abs(X_train.mean() - X_val.mean())
std_diff = abs(X_train.std() - X_val.std())

print("\n" + "=" * 70)
print("DISTRIBUTION MATCH CHECK")
print("=" * 70)
print(f"\nMean difference: {mean_diff:.6f}")
print(f"Std difference:  {std_diff:.6f}")

if mean_diff < 0.01 and std_diff < 0.05:
    print("\n✅ SUCCESS! Train and val have consistent normalization")
    print("   Both sets should now have similar learning dynamics")
else:
    print("\n⚠️  WARNING! Train and val still have different statistics")
    print("   Mean diff should be < 0.01, Std diff should be < 0.05")

print("=" * 70)
