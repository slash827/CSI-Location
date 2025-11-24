import h5py
import numpy as np
from pathlib import Path

file_path = Path(__file__).parent.parent / 'results' / 'exp09_2025-11-04_21-41-43' / 'dataset' / 'train_data.mat'

with h5py.File(file_path, 'r') as f:
    print("=" * 60)
    print("MATLAB FILE STRUCTURE")
    print("=" * 60)
    print(f"\nTop-level keys: {list(f.keys())}\n")
    
    for key in f.keys():
        if key.startswith('#'):
            continue
        
        item = f[key]
        print(f"\nKey: '{key}'")
        print(f"  Type: {type(item)}")
        
        if isinstance(item, h5py.Dataset):
            print(f"  Shape: {item.shape}")
            print(f"  Dtype: {item.dtype}")
            if item.size < 10:
                print(f"  Value: {item[()]}")
        
        elif isinstance(item, h5py.Group):
            print(f"  Contents: {list(item.keys())}")
            for subkey in list(item.keys())[:5]:  # Show first 5
                subitem = item[subkey]
                if isinstance(subitem, h5py.Dataset):
                    print(f"    {subkey}: shape={subitem.shape}, dtype={subitem.dtype}")
