"""
Load metadata files to get complete information including distances
"""

import numpy as np
import h5py
from pathlib import Path

def load_metadata(metadata_path):
    """Load metadata from .mat file"""
    data = {}
    with h5py.File(metadata_path, 'r') as f:
        print(f"Keys in metadata: {list(f.keys())}")
        for key in f.keys():
            if key.startswith('#') or key.startswith('__'):
                continue
            try:
                dataset = f[key]
                if isinstance(dataset, h5py.Dataset):
                    arr = dataset[()]
                    if arr.ndim == 2 and arr.shape[0] < arr.shape[1]:
                        arr = arr.T
                    data[key] = arr
                    print(f"  {key}: shape={arr.shape}, dtype={arr.dtype}")
            except Exception as e:
                print(f"  Could not load {key}: {e}")
    return data

def analyze_metadata(dataset_path, dataset_name):
    """Analyze metadata file"""
    print(f"\n{'='*70}")
    print(f"{dataset_name} - METADATA ANALYSIS")
    print(f"{'='*70}\n")
    
    metadata_path = Path(dataset_path) / "metadata.mat"
    
    if not metadata_path.exists():
        print(f"⚠️  No metadata file found")
        return
    
    print(f"📂 Loading: {metadata_path}")
    metadata = load_metadata(metadata_path)
    
    # Check for BS information
    if 'n_bs' in metadata:
        n_bs = int(metadata['n_bs'].ravel()[0])
        print(f"\n🗼 Number of Base Stations: {n_bs}")
    
    # Check for BS positions
    if 'bs_positions' in metadata:
        bs_pos = metadata['bs_positions']
        print(f"\n📍 Base Station Positions:")
        if bs_pos.ndim == 2:
            for i in range(bs_pos.shape[0]):
                print(f"   BS{i+1}: ({bs_pos[i, 0]:.1f}, {bs_pos[i, 1]:.1f}) m")
        else:
            print(f"   Single BS: ({bs_pos[0]:.1f}, {bs_pos[1]:.1f}) m")
    
    # Check for scenario type
    if 'scenario' in metadata:
        scenario = metadata['scenario']
        print(f"\n📋 Scenario: {scenario}")
    
    # Check for NLOS info
    if 'nlos_enabled' in metadata:
        nlos = bool(metadata['nlos_enabled'].ravel()[0])
        print(f"\n🚧 NLOS Enabled: {nlos}")
    
    return metadata

if __name__ == "__main__":
    # Dataset paths
    datasets = {
        'exp09': r"..\results\exp09_2025-11-04_21-41-43\dataset",
        'exp10': r"..\results\exp10_2025-11-07_12-40-00\dataset",
        'exp11': r"..\results\exp11_2025-11-15_14-07-52\dataset",
    }
    
    for name, path in datasets.items():
        if Path(path).exists():
            analyze_metadata(path, name.upper())
        else:
            print(f"\n⚠️  {name} not found: {path}")
    
    print(f"\n{'='*70}\n")
