#!/usr/bin/env python3
"""
AoA Noise Formula Sweep and Sensitivity Analysis

Loads clean simulation data (without noise) from the Center BS dataset,
applies various candidate SINR-dependent AoA noise models, and evaluates 
their impact on localization accuracy and Mean Absolute Error (MAE) 
using XGBoost models.
"""

import sys
import copy
import time
from pathlib import Path
import numpy as np
import pandas as pd

# Add the src/python directory to python path for importing multi_user_pipeline
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import multi_user_pipeline functions
import multi_user_pipeline as mup

# Ensure N_JOBS is set for speed
mup.N_JOBS = 4

def load_clean_users_data(data_dir: Path) -> list[dict]:
    """Load per-user simulation files without applying noise yet."""
    candidates = sorted(data_dir.glob('user1_*.mat'))
    if not candidates:
        raise FileNotFoundError(
            f"No user1_*.mat files found in {data_dir}\n"
            f"  Contents: {[p.name for p in data_dir.iterdir() if p.suffix == '.mat']}"
        )
    stem = candidates[0].stem[len('user1_'):]
    n_users = sum(1 for u in range(1, 20) if (data_dir / f'user{u}_{stem}.mat').exists())
    
    users_data = []
    for u in range(1, n_users + 1):
        mat_file = data_dir / f'user{u}_{stem}.mat'
        print(f"  Loading clean user {u}: {mat_file.name}")
        ud = mup.load_user_file(mat_file)
        users_data.append(ud)
    return users_data

def apply_custom_aoa_noise(ud: dict, noise_std_fn) -> dict:
    """Apply custom noise standard deviation function and quantization to AoA."""
    uid = ud['user_id']
    n_ant = ud['device']['n_antennas']
    
    # User 3 (budget device with 1 antenna) does not have AoA capability
    if n_ant <= 1:
        ud['aoa_az'] = None
        ud['aoa_el'] = None
        return ud
        
    if ud['aoa_az'] is not None or ud['aoa_el'] is not None:
        sinr_db = ud['sinr']
        # Compute noise std dynamically per snapshot
        noise_std = noise_std_fn(sinr_db)
        
    if ud['aoa_az'] is not None:
        rng = np.random.RandomState(42 + uid * 1000)
        noise = noise_std * rng.randn(len(ud['aoa_az']))
        ud['aoa_az'] = np.round(
            (ud['aoa_az'] + noise)
            / mup.AOA_QUANT_STEP_DEG) * mup.AOA_QUANT_STEP_DEG
            
    if ud['aoa_el'] is not None:
        rng = np.random.RandomState(43 + uid * 1000)
        noise = noise_std * rng.randn(len(ud['aoa_el']))
        ud['aoa_el'] = np.round(
            (ud['aoa_el'] + noise)
            / mup.AOA_QUANT_STEP_DEG) * mup.AOA_QUANT_STEP_DEG
            
    return ud

def prepare_dataset(clean_users: list, noise_std_fn, subsample_frac: float = 0.2) -> pd.DataFrame:
    """Create a DataFrame with noise applied, split into train/test, and subsampled."""
    users_copied = copy.deepcopy(clean_users)
    frames = []
    for ud in users_copied:
        ud_noisy = apply_custom_aoa_noise(ud, noise_std_fn)
        udf = mup._ud_to_dataframe(ud_noisy)
        frames.append(udf)
    df = pd.concat(frames, ignore_index=True)
    
    # Chronological train/test split (80/20)
    df = mup.make_split(df, test_ratio=0.2)
    
    # Subsample training data to speed up evaluation
    if subsample_frac < 1.0:
        train_mask = df['split'] == 'train'
        test_mask = df['split'] == 'test'
        train_df = df[train_mask]
        test_df = df[test_mask]
        
        # Chronological subsample per user to maintain path sequence coherence
        sub_trains = []
        for uid in sorted(train_df['user_id'].unique()):
            u_train = train_df[train_df['user_id'] == uid].sort_values('step_index')
            n_keep = max(1, int(len(u_train) * subsample_frac))
            sub_trains.append(u_train.iloc[:n_keep])
            
        df = pd.concat(sub_trains + [test_df], ignore_index=True)
        
    return df

def run_evaluation(df: pd.DataFrame, formula_name: str) -> dict:
    """Evaluate BASE_A and BASE_A_H3 with XGBoost for the given dataset."""
    grid_lookup = mup.build_grid_lookup(df)
    
    # 1. BASE_A (h=0, absolute)
    feat_df_a = mup.build_history_features(df, h=0, include_aoa=True)
    feat_cols_a = mup.get_feature_cols(h=0, include_aoa=True)
    res_a = mup.run_one_experiment(
        feat_df_a, feat_cols_a, grid_lookup, 
        model_name='xgboost', exp_label=f'{formula_name} | BASE_A'
    )
    
    # 2. BASE_A_H3 (h=3, absolute)
    feat_df_h3 = mup.build_history_features(df, h=3, include_aoa=True)
    feat_cols_h3 = mup.get_feature_cols(h=3, include_aoa=True)
    res_h3 = mup.run_one_experiment(
        feat_df_h3, feat_cols_h3, grid_lookup, 
        model_name='xgboost', exp_label=f'{formula_name} | BASE_A_H3'
    )
    
    return {
        'BASE_A_acc': res_a['overall']['accuracy'],
        'BASE_A_mae': res_a['overall']['mae'],
        'BASE_A_H3_acc': res_h3['overall']['accuracy'],
        'BASE_A_H3_mae': res_h3['overall']['mae'],
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sweep AoA noise formulas")
    parser.add_argument('--data-dir', required=True, help="Directory containing Center BS mat files")
    parser.add_argument('--subsample', type=float, default=0.20, help="Fraction of training data to use (default: 0.20)")
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Error: path not found {data_dir}")
        sys.exit(1)
        
    print("\n=== Loading clean user simulation data ===")
    clean_users = load_clean_users_data(data_dir)
    print(f"Loaded {len(clean_users)} users successfully.")
    
    # Define candidates
    formulas = {
        # 1. Baseline
        "Fixed Baseline (4.0°)": lambda sinr: np.full_like(sinr, 4.0),
        
        # 2. Exponential (Physical) Models
        "Physical (ref=2.0°, k=15)": lambda sinr: np.clip(2.0 * (10.0 ** (-(sinr - 10.0) / 15.0)), 1.0, 20.0),
        "Physical (ref=4.0°, k=20)": lambda sinr: np.clip(4.0 * (10.0 ** (-(sinr - 10.0) / 20.0)), 1.0, 20.0), # Current default
        "Physical (ref=6.0°, k=25)": lambda sinr: np.clip(6.0 * (10.0 ** (-(sinr - 10.0) / 25.0)), 1.0, 20.0),
        
        # 3. Log-linear Models
        "Log-Linear (ref=6.0°, b=0.2)": lambda sinr: np.clip(6.0 - 0.2 * sinr, 1.0, 20.0),
        "Log-Linear (ref=8.0°, b=0.3)": lambda sinr: np.clip(8.0 - 0.3 * sinr, 1.0, 20.0),
        
        # 4. Step-wise Model
        "Step-wise": lambda sinr: np.select([sinr >= 10.0, (sinr >= 0.0) & (sinr < 10.0)], [2.0, 6.0], default=15.0)
    }
    
    results = []
    
    print(f"\n=== Running Sweep (subsample={args.subsample:.0%}) ===")
    for name, fn in formulas.items():
        t0 = time.time()
        print(f"\nEvaluating formula: {name}...")
        df = prepare_dataset(clean_users, fn, subsample_frac=args.subsample)
        metrics = run_evaluation(df, name)
        metrics['Formula'] = name
        metrics['time_s'] = time.time() - t0
        results.append(metrics)
        
    results_df = pd.DataFrame(results)
    # Order columns
    cols = ['Formula', 'BASE_A_acc', 'BASE_A_mae', 'BASE_A_H3_acc', 'BASE_A_H3_mae', 'time_s']
    results_df = results_df[cols]
    
    print("\n" + "=" * 80)
    print("SWEEP RESULTS SUMMARY (XGBoost)")
    print("=" * 80)
    print(results_df.to_string(index=False, formatters={
        'BASE_A_acc': '{:,.2f}%'.format,
        'BASE_A_mae': '{:,.3f}m'.format,
        'BASE_A_H3_acc': '{:,.2f}%'.format,
        'BASE_A_H3_mae': '{:,.3f}m'.format,
        'time_s': '{:.1f}s'.format
    }))
    print("=" * 80)
    
    # Save results to a CSV in the results root
    out_csv = Path("results/grid_localization/aoa_noise_sweep_results.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(out_csv, index=False)
    print(f"Results saved to: {out_csv.resolve()}")

if __name__ == '__main__':
    main()
