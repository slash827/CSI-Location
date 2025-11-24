"""Check NLOS distribution in train vs val splits."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import numpy as np
import h5py

print("="*70)
print("CHECKING NLOS DISTRIBUTION IN TRAIN VS VAL")
print("="*70)

dataset_path = Path("D:/gilad/projects/Academy/CSI-Location/results/exp11_2025-11-15_14-07-52/dataset")

# Load NLOS metadata
metadata_file = dataset_path / "nlos_metadata.mat"

with h5py.File(metadata_file, 'r') as f:
    print(f"\nKeys in metadata file: {list(f.keys())}")
    
    # Load train and val NLOS conditions
    train_cond = f['train_conditions'][:]
    val_cond = f['val_conditions'][:]
    
# Load RSRP from main data files  
train_file = dataset_path / "train_data.mat"
val_file = dataset_path / "val_data.mat"

with h5py.File(train_file, 'r') as f:
    train_rsrp = f['RSRP'][:]
    
with h5py.File(val_file, 'r') as f:
    val_rsrp = f['RSRP'][:]
    
print(f"\nTrain samples: {len(train_cond)}")
print(f"Val samples: {len(val_cond)}")

# Decode NLOS conditions (stored as uint8)
condition_map = {1: 'Pure LOS', 2: 'Light NLOS', 3: 'Moderate NLOS', 4: 'Heavy NLOS'}

print(f"\n--- TRAIN NLOS DISTRIBUTION ---")
train_unique, train_counts = np.unique(train_cond, return_counts=True)
for cond_id, count in zip(train_unique, train_counts):
    cond_name = condition_map.get(cond_id, f'Unknown_{cond_id}')
    print(f"  {cond_name}: {count} ({count/len(train_cond)*100:.1f}%)")

print(f"\n--- VAL NLOS DISTRIBUTION ---")
val_unique, val_counts = np.unique(val_cond, return_counts=True)
for cond_id, count in zip(val_unique, val_counts):
    cond_name = condition_map.get(cond_id, f'Unknown_{cond_id}')
    print(f"  {cond_name}: {count} ({count/len(val_cond)*100:.1f}%)")

# Check RSRP statistics
print(f"\n--- RSRP STATISTICS ---")
print(f"Train RSRP: mean={train_rsrp.mean():.2f} dBm, std={train_rsrp.std():.2f} dBm")
print(f"Val RSRP:   mean={val_rsrp.mean():.2f} dBm, std={val_rsrp.std():.2f} dBm")

# Check per-condition RSRP
print(f"\n--- RSRP BY CONDITION (TRAIN) ---")
for cond_id in train_unique:
    mask = train_cond == cond_id
    cond_name = condition_map.get(cond_id, f'Unknown_{cond_id}')
    print(f"  {cond_name}: {train_rsrp[mask].mean():.2f} ± {train_rsrp[mask].std():.2f} dBm")

print(f"\n--- RSRP BY CONDITION (VAL) ---")
for cond_id in val_unique:
    mask = val_cond == cond_id
    cond_name = condition_map.get(cond_id, f'Unknown_{cond_id}')
    print(f"  {cond_name}: {val_rsrp[mask].mean():.2f} ± {val_rsrp[mask].std():.2f} dBm")

print("="*70)
