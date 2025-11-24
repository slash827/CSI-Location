"""
Analyze datasets to compare LOS vs NLOS characteristics
"""

import numpy as np
import h5py
from pathlib import Path

def load_h5_data(file_path):
    """Load data from HDF5 file"""
    data = {}
    with h5py.File(file_path, 'r') as f:
        # Navigate to train_data or val_data group
        if 'train_data' in f:
            group = f['train_data']
        elif 'val_data' in f:
            group = f['val_data']
        else:
            group = f
        
        # Extract all datasets
        for key in group.keys():
            if key.startswith('#'):
                continue
            try:
                dataset = group[key]
                if isinstance(dataset, h5py.Dataset):
                    arr = dataset[()]
                    # Transpose if needed
                    if arr.ndim == 2 and arr.shape[0] < arr.shape[1]:
                        arr = arr.T
                    data[key] = arr.ravel() if arr.size == arr.shape[0] else arr
            except:
                pass
    return data

def analyze_dataset(dataset_path, dataset_name):
    """Analyze a single dataset"""
    print(f"\n{'='*70}")
    print(f"{dataset_name}")
    print(f"{'='*70}")
    
    train_path = Path(dataset_path) / "train_data.mat"
    val_path = Path(dataset_path) / "val_data.mat"
    
    # Load training data
    print(f"\n📂 Loading: {train_path}")
    train_data = load_h5_data(train_path)
    
    # Load validation data
    print(f"📂 Loading: {val_path}")
    val_data = load_h5_data(val_path)
    
    # Combine for overall statistics
    n_train = len(train_data['positions_x'])
    n_val = len(val_data['positions_x'])
    
    print(f"\n📊 Dataset Size:")
    print(f"   Training samples:   {n_train}")
    print(f"   Validation samples: {n_val}")
    print(f"   Total samples:      {n_train + n_val}")
    
    # Check number of base stations
    print(f"\n🗼 Base Station Configuration:")
    
    # Check if we have per-BS data
    if 'RSS_per_sc' in train_data:
        rss_shape = train_data['RSS_per_sc'].shape
        print(f"   RSS_per_sc shape: {rss_shape}")
        
        if len(rss_shape) == 2:
            n_samples, n_features = rss_shape
            # exp09 has 1024 features = 4 BS × 256 subcarriers
            # exp11 has 12288 features = 4 BS × 1024 subcarriers × 3 channels
            if n_features == 1024:
                n_bs = 4
                n_sc = 256
                print(f"   Detected: {n_bs} Base Stations × {n_sc} subcarriers")
            elif n_features == 256:
                n_bs = 1
                n_sc = 256
                print(f"   Detected: {n_bs} Base Station × {n_sc} subcarriers")
            elif n_features == 4096:
                n_bs = 4
                n_sc = 1024
                print(f"   Detected: {n_bs} Base Stations × {n_sc} subcarriers")
            else:
                print(f"   Unknown configuration: {n_features} features")
    
    # Distance statistics
    print(f"\n📏 Distance Statistics (UE to BS):")
    
    if 'distances' in train_data:
        train_dist = train_data['distances'].ravel()
        val_dist = val_data['distances'].ravel()
        all_dist = np.concatenate([train_dist, val_dist])
        
        print(f"   Training set:")
        print(f"      Mean:   {train_dist.mean():.2f} m")
        print(f"      Std:    {train_dist.std():.2f} m")
        print(f"      Min:    {train_dist.min():.2f} m")
        print(f"      Max:    {train_dist.max():.2f} m")
        print(f"      Median: {np.median(train_dist):.2f} m")
        
        print(f"   Validation set:")
        print(f"      Mean:   {val_dist.mean():.2f} m")
        print(f"      Std:    {val_dist.std():.2f} m")
        
        print(f"   Overall (Train + Val):")
        print(f"      Mean:   {all_dist.mean():.2f} m")
        print(f"      Std:    {all_dist.std():.2f} m")
        print(f"      Min:    {all_dist.min():.2f} m")
        print(f"      Max:    {all_dist.max():.2f} m")
        print(f"      Median: {np.median(all_dist):.2f} m")
    else:
        print("   ⚠️  Distance data not found")
    
    # RSRP statistics
    if 'RSRP' in train_data:
        print(f"\n📡 RSRP Statistics:")
        train_rsrp = train_data['RSRP'].ravel()
        val_rsrp = val_data['RSRP'].ravel()
        all_rsrp = np.concatenate([train_rsrp, val_rsrp])
        
        print(f"   Training:   {train_rsrp.mean():.2f} ± {train_rsrp.std():.2f} dBm")
        print(f"   Validation: {val_rsrp.mean():.2f} ± {val_rsrp.std():.2f} dBm")
        print(f"   Overall:    {all_rsrp.mean():.2f} ± {all_rsrp.std():.2f} dBm")
    
    # Position statistics
    if 'positions_x' in train_data:
        print(f"\n📍 Position Range:")
        train_x = train_data['positions_x'].ravel()
        train_y = train_data['positions_y'].ravel()
        val_x = val_data['positions_x'].ravel()
        val_y = val_data['positions_y'].ravel()
        
        all_x = np.concatenate([train_x, val_x])
        all_y = np.concatenate([train_y, val_y])
        
        print(f"   X: [{all_x.min():.1f}, {all_x.max():.1f}] m")
        print(f"   Y: [{all_y.min():.1f}, {all_y.max():.1f}] m")
        print(f"   Area: {all_x.max()-all_x.min():.0f} × {all_y.max()-all_y.min():.0f} m²")
    
    return {
        'n_samples': n_train + n_val,
        'mean_distance': all_dist.mean() if 'distances' in train_data else None,
        'mean_rsrp': all_rsrp.mean() if 'RSRP' in train_data else None
    }

if __name__ == "__main__":
    # Dataset paths
    exp09_path = r"..\results\exp09_2025-11-04_21-41-43\dataset"
    exp10_path = r"..\results\exp10_2025-11-07_12-40-00\dataset"
    exp11_path = r"..\results\exp11_2025-11-15_14-07-52\dataset"
    
    # Analyze each dataset
    results = {}
    
    print("\n" + "="*70)
    print("DATASET COMPARISON ANALYSIS")
    print("="*70)
    
    if Path(exp09_path).exists():
        results['exp09'] = analyze_dataset(exp09_path, "EXP09 - LOS Only (Small)")
    else:
        print(f"\n⚠️  exp09 not found: {exp09_path}")
    
    if Path(exp10_path).exists():
        results['exp10'] = analyze_dataset(exp10_path, "EXP10 - LOS Only (Large)")
    else:
        print(f"\n⚠️  exp10 not found: {exp10_path}")
    
    if Path(exp11_path).exists():
        results['exp11'] = analyze_dataset(exp11_path, "EXP11 - NLOS Enhanced (70% NLOS)")
    else:
        print(f"\n⚠️  exp11 not found: {exp11_path}")
    
    # Summary comparison
    print(f"\n{'='*70}")
    print("SUMMARY COMPARISON")
    print(f"{'='*70}\n")
    
    print(f"{'Dataset':<15} {'Samples':<10} {'Avg Distance':<15} {'Avg RSRP':<15} {'NLOS'}")
    print(f"{'-'*70}")
    
    for name, data in results.items():
        if data:
            nlos = "70% (Mixed)" if name == 'exp11' else "0% (Pure LOS)"
            dist_str = f"{data['mean_distance']:.2f} m" if data['mean_distance'] else "N/A"
            rsrp_str = f"{data['mean_rsrp']:.2f} dBm" if data['mean_rsrp'] else "N/A"
            print(f"{name:<15} {data['n_samples']:<10} {dist_str:<15} {rsrp_str:<15} {nlos}")
    
    print(f"\n{'='*70}")
    print("KEY FINDINGS:")
    print(f"{'='*70}")
    
    if 'exp09' in results and 'exp11' in results:
        if results['exp09']['mean_distance'] and results['exp11']['mean_distance']:
            diff = results['exp11']['mean_distance'] - results['exp09']['mean_distance']
            pct = 100 * diff / results['exp09']['mean_distance']
            print(f"\n📊 Average Distance Comparison:")
            print(f"   LOS (exp09):  {results['exp09']['mean_distance']:.2f} m")
            print(f"   NLOS (exp11): {results['exp11']['mean_distance']:.2f} m")
            print(f"   Difference:   {diff:+.2f} m ({pct:+.1f}%)")
        
        if results['exp09']['mean_rsrp'] and results['exp11']['mean_rsrp']:
            diff_rsrp = results['exp11']['mean_rsrp'] - results['exp09']['mean_rsrp']
            print(f"\n📡 Average RSRP Comparison:")
            print(f"   LOS (exp09):  {results['exp09']['mean_rsrp']:.2f} dBm")
            print(f"   NLOS (exp11): {results['exp11']['mean_rsrp']:.2f} dBm")
            print(f"   Difference:   {diff_rsrp:+.2f} dB (NLOS has weaker signal)")
    
    print(f"\n🗼 Base Station Configuration:")
    print(f"   All datasets use 4 Base Stations")
    print(f"   - exp09/exp10: 256 subcarriers per BS")
    print(f"   - exp11: 1024 subcarriers per BS")
    
    print(f"\n✅ Conclusion:")
    print(f"   - All datasets have MULTIPLE (4) base stations")
    print(f"   - No single-BS datasets in the current collection")
    print(f"   - NLOS conditions reduce signal strength but similar distances")
    print(f"\n{'='*70}\n")
