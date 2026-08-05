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
    Handles both 200-user and 300-user multi-user simulation datasets.
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
        if 'ue_height' in dp.dtype.names:
            height = float(dp['ue_height'][0,0][0,0])
        else:
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
        })
        
        # Calculate instantaneous physical speed v(t) (m/s)
        dx = np.diff(x_pos, prepend=x_pos[0])
        dy = np.diff(y_pos, prepend=y_pos[0])
        dist_step = np.sqrt(dx**2 + dy**2)
        speed = dist_step / np.maximum(delta_t, 1e-3)
        speed[0] = speed[1] if len(speed) > 1 else 0.0
        df_u['speed_m_s'] = speed.astype(np.float32)
        
        dfs.append(df_u)
        
    df_all = pd.concat(dfs, ignore_index=True)
    return df_all


def make_unseen_user_split(df, train_ratio=0.8, seed=42):
    """
    Splits user_ids into train_users (80%) and unseen test_users (20%).
    """
    user_ids = sorted(df['user_id'].unique())
    rng = np.random.RandomState(seed)
    shuffled_uids = rng.permutation(user_ids)
    
    n_train = int(len(user_ids) * train_ratio)
    train_uids = set(shuffled_uids[:n_train])
    test_uids  = set(shuffled_uids[n_train:])
    
    df['split'] = df['user_id'].apply(lambda u: 'train' if u in train_uids else 'test')
    return df, train_uids, test_uids
