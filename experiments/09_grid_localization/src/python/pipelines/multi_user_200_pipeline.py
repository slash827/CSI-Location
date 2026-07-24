import os
import sys
import time
import glob
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.io import loadmat

def load_200_users(data_dir):
    """
    Loads per-user MAT files from data_dir into a single DataFrame.
    Computes instantaneous physical speed v(t) (m/s) per user trajectory.
    """
    mat_files = sorted(glob.glob(os.path.join(data_dir, 'user*.mat')))
    if not mat_files:
        mat_files = sorted(glob.glob(os.path.join(data_dir, 'mat_files', 'user*.mat')))
    if not mat_files:
        raise FileNotFoundError(f"No user*.mat files found in {data_dir} or {os.path.join(data_dir, 'mat_files')}")
        
    dfs = []
    for f in mat_files:
        mat = loadmat(f)
        u_id = int(mat['user_id_val'][0, 0])
        rss = mat['rss'].flatten().astype(np.float32)
        sinr = mat['sinr'].flatten().astype(np.float32)
        aoa_az = mat['aoa_az'].flatten().astype(np.float32)
        aoa_el = mat['aoa_el'].flatten().astype(np.float32)
        x_pos = mat['x_pos'].flatten().astype(np.float32)
        y_pos = mat['y_pos'].flatten().astype(np.float32)
        step_idx = mat['step_index'].flatten().astype(np.int32)
        
        # Load delta_t and timestamp if present
        if 'delta_t' in mat:
            delta_t = mat['delta_t'].flatten().astype(np.float32)
        else:
            delta_t = np.ones(len(rss), dtype=np.float32) * 1.333
            
        if 'timestamp_sec' in mat:
            timestamp_sec = mat['timestamp_sec'].flatten().astype(np.float32)
        else:
            timestamp_sec = (step_idx - 1) * 1.333
            
        # Device profile
        dp = mat['device_profile']
        n_ant = float(dp['n_antennas'][0,0][0,0])
        gain = float(dp['antenna_gain_db'][0,0][0,0])
        height = float(dp['ue_height_m'][0,0][0,0])
        
        df_u = pd.DataFrame({
            'user_id': u_id,
            'step_index': step_idx,
            'rss': rss,
            'sinr': sinr,
            'aoa_azimuth': aoa_az,
            'aoa_elevation': aoa_el,
            'x_pos': x_pos,
            'y_pos': y_pos,
            'delta_t': delta_t,
            'timestamp_sec': timestamp_sec,
            'n_antennas': n_ant,
            'antenna_gain_db': gain,
            'ue_height': height
        }).sort_values('step_index').reset_index(drop=True)
        
        # Compute ground truth physical speed v(t) = sqrt(dx^2 + dy^2) / dt
        dx = np.diff(df_u['x_pos'].values, prepend=df_u['x_pos'].values[0])
        dy = np.diff(df_u['y_pos'].values, prepend=df_u['y_pos'].values[0])
        dt = np.maximum(0.01, df_u['delta_t'].values)
        df_u['speed_m_s'] = np.sqrt(dx**2 + dy**2) / dt
        
        dfs.append(df_u)
        
    df_all = pd.concat(dfs, ignore_index=True)
    return df_all

def make_unseen_user_split(df, train_ratio=0.8, seed=42):
    """
    Performs an 80/20 User-Level Split:
    160 Training Users vs. 40 Completely Unseen Test Users.
    """
    user_ids = sorted(df['user_id'].unique())
    np.random.seed(seed)
    shuffled_users = np.random.permutation(user_ids)
    
    n_train = int(len(user_ids) * train_ratio)
    train_users = set(shuffled_users[:n_train])
    test_users  = set(shuffled_users[n_train:])
    
    df['split'] = df['user_id'].apply(lambda u: 'train' if u in train_users else 'test')
    return df, train_users, test_users

def build_multitask_sequences(df, h, signal_cols=['rss', 'sinr', 'aoa_azimuth', 'aoa_elevation', 'delta_t'],
                               static_cols=['n_antennas', 'antenna_gain_db', 'ue_height'],
                               target_cols=['target_x', 'target_y', 'target_z']):
    """
    Constructs sequence datasets for multi-task training:
      - X_seq: [N, h+1, 5] (including delta_t channel)
      - X_static: [N, 3]
      - y_coords: [N, 3] (3D location)
      - y_speed:  [N, 1] (instantaneous speed)
    """
    all_seq, all_static, all_coords, all_speeds = [], [], [], []
    
    for uid in sorted(df['user_id'].unique()):
        udf = df[df['user_id']==uid].sort_values('step_index').reset_index(drop=True)
        sigs = udf[signal_cols].values.astype(np.float32)
        statics = udf[static_cols].values.astype(np.float32)
        coords = udf[target_cols].values.astype(np.float32)
        speeds = udf['speed_m_s'].values.astype(np.float32).reshape(-1, 1)
        
        for i in range(h, len(udf)):
            all_seq.append(sigs[i-h : i+1])  # [h+1, n_channels]
            all_static.append(statics[i])
            all_coords.append(coords[i])
            all_speeds.append(speeds[i])
            
    return np.stack(all_seq), np.stack(all_static), np.stack(all_coords), np.stack(all_speeds)
