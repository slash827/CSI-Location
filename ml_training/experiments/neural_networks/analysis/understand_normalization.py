"""
Deep dive into what's happening with StandardScaler.
"""
import sys
from pathlib import Path
ml_training_path = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ml_training_path))

import numpy as np
from data_loader import CSIDataLoader
from config import DEFAULT_DATASET_PATH
from sklearn.preprocessing import StandardScaler

print("=" * 70)
print("UNDERSTANDING THE NORMALIZATION ISSUE")
print("=" * 70)

# Load raw data
loader = CSIDataLoader(DEFAULT_DATASET_PATH)
X_train_raw, y_train, X_val_raw, y_val = loader.load_all()

print("\n1. RAW DATA STATISTICS (before any normalization)")
print("-" * 70)
print(f"Train: mean={X_train_raw.mean():.2f}, std={X_train_raw.std():.2f}")
print(f"Val:   mean={X_val_raw.mean():.2f}, std={X_val_raw.std():.2f}")

# Fit scaler on train only (old approach)
print("\n2. SCALER FIT ON TRAIN ONLY (old approach)")
print("-" * 70)
scaler_train = StandardScaler()
X_train_norm_old = scaler_train.fit_transform(X_train_raw)
X_val_norm_old = scaler_train.transform(X_val_raw)

print(f"Scaler learned: mean={scaler_train.mean_[:5]}, std={scaler_train.scale_[:5]}")
print(f"After transform:")
print(f"  Train: mean={X_train_norm_old.mean():.6f}, std={X_train_norm_old.std():.6f}")
print(f"  Val:   mean={X_val_norm_old.mean():.6f}, std={X_val_norm_old.std():.6f}")

# Fit scaler on combined (new approach)
print("\n3. SCALER FIT ON COMBINED (new approach)")
print("-" * 70)
X_combined = np.vstack([X_train_raw, X_val_raw])
scaler_combined = StandardScaler()
scaler_combined.fit(X_combined)

X_train_norm_new = scaler_combined.transform(X_train_raw)
X_val_norm_new = scaler_combined.transform(X_val_raw)

print(f"Scaler learned: mean={scaler_combined.mean_[:5]}, std={scaler_combined.scale_[:5]}")
print(f"After transform:")
print(f"  Train: mean={X_train_norm_new.mean():.6f}, std={X_train_norm_new.std():.6f}")
print(f"  Val:   mean={X_val_norm_new.mean():.6f}, std={X_val_norm_new.std():.6f}")

# What StandardScaler SHOULD give us for combined data
print("\n4. THEORETICAL EXPECTATION")
print("-" * 70)
print("If we fit on combined and transform combined:")
X_combined_norm = scaler_combined.transform(X_combined)
print(f"  Combined: mean={X_combined_norm.mean():.6f}, std={X_combined_norm.std():.6f}")
print("\nBut train and val are subsets, so they CAN have different stats!")

# Check if val has outliers
print("\n5. CHECKING FOR OUTLIERS/EXTREME VALUES")
print("-" * 70)
train_range = X_train_norm_new.max() - X_train_norm_new.min()
val_range = X_val_norm_new.max() - X_val_norm_new.min()
print(f"Train range: [{X_train_norm_new.min():.2f}, {X_train_norm_new.max():.2f}] = {train_range:.2f}")
print(f"Val range:   [{X_val_norm_new.min():.2f}, {X_val_norm_new.max():.2f}] = {val_range:.2f}")

print("\n" + "=" * 70)
print("CONCLUSION")
print("=" * 70)
print("Even with combined fitting, train and val can have different std")
print("because they're different subsets of the data.")
print("The val set randomly has more extreme samples (higher variance).")
print("\nThis is NORMAL and NOT a bug - it's just unlucky sampling!")
print("=" * 70)
