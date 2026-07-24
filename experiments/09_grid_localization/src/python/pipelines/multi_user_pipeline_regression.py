"""
Multi-User Heterogeneous Environment — 3D Regression Pipeline

Instead of classifying UEs to discrete grid points (which causes OOM on large grids like 25x25),
this pipeline predicts continuous 3D coordinates in spherical space:
  - Distance from serving BS (meters)
  - AoA Azimuth angle (degrees)
  - AoA Elevation angle (degrees)

It then converts predictions back to 3D Cartesian coordinates to calculate physical distance error in meters.

Usage:
  python multi_user_pipeline_regression.py --data-dir <path/to/sim_data> --out-dir results/ne_bs_voronoi_25x25_regression
"""

import argparse
import gc
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat
from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

# Add src/python to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.read_jsonc import read_jsonc

try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("Warning: XGBoost not available, skipping XGBoost models")

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False

TUNED_PARAMS: dict = {}
N_JOBS: int = -1

def _fmt_s(seconds: float) -> str:
    """Format seconds as '1h 2m 3s', '2m 3s', or '3s'."""
    s = max(0, int(seconds))
    if s >= 3600:
        return f'{s // 3600}h {(s % 3600) // 60}m {s % 60}s'
    if s >= 60:
        return f'{s // 60}m {s % 60}s'
    return f'{s}s'

# Constants
AOA_NOISE_STD_DEG = 4.0
AOA_QUANT_STEP_DEG = 5.0

def custom_euclidean_obj_sklearn(y_true, y_pred):
    """Custom objective function for XGBoost to optimize 3D Euclidean distance.
    y_true: Ground truth Cartesian coordinates, shape (N * 3,) or (N, 3).
    y_pred: Predicted Cartesian coordinates, shape (N, 3).
    """
    if y_true.ndim == 1:
        y_true = y_true.reshape(y_pred.shape)
        
    delta = y_pred - y_true
    dist = np.linalg.norm(delta, axis=1, keepdims=True)
    dist = np.maximum(dist, 1e-6)  # clip to avoid division by zero
    
    # Gradient: d L_i / d preds_ij = delta_ij / dist
    grad = delta / dist
    
    # Hessian (second derivative):
    # d^2 L_i / d preds_ij^2 = (1 - (delta_ij / dist)^2) / dist
    hess = (1.0 - (delta / dist)**2) / dist
    hess = np.maximum(hess, 1e-4)  # clip to positive value to keep tree growth stable
    
    return grad, hess

# ─────────────────────────────────────────────────────────────────────────────
# 1. Configuration & Data Loader
# ─────────────────────────────────────────────────────────────────────────────

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # experiments/09_grid_localization

EXPERIMENTS = [
    {'key': 'BASE',         'h': 0, 'aoa': False, 'extra': None,       'desc': 'Static RSS+SINR (no AoA)'},
    {'key': 'BASE_H3',      'h': 3, 'aoa': False, 'extra': None,       'desc': 'RSS+SINR history h=3'},
    {'key': 'BASE_H3_dp',   'h': 3, 'aoa': False, 'extra': ['device'], 'desc': 'RSS+SINR history h=3 + device params'},
    {'key': 'BASE_A',       'h': 0, 'aoa': True,  'extra': None,       'desc': 'Static RSS+SINR+AoA'},
    {'key': 'BASE_A_H3',    'h': 3, 'aoa': True,  'extra': None,       'desc': 'RSS+SINR+AoA history h=3'},
    {'key': 'BASE_A_H3_dp', 'h': 3, 'aoa': True,  'extra': ['device'], 'desc': 'RSS+SINR+AoA history h=3 + device params'},
    # A/B testing variants (Phase 3 Python enhancements)
    {'key': 'BASE_A_H3_dp_INT',    'h': 3, 'aoa': True,  'extra': ['device'], 'include_interference': True, 'desc': 'Baseline + Interference Fingerprint'},
    {'key': 'BASE_A_H3_dp_SCALE',  'h': 3, 'aoa': True,  'extra': ['device'], 'scale_targets': True,         'desc': 'Baseline + Target Standard Scaling'},
    {'key': 'BASE_A_H3_dp_NATIVE', 'h': 3, 'aoa': True,  'extra': ['device'], 'use_native_xgb': True,        'desc': 'Baseline + Native XGBoost Multi-Output'},
    {'key': 'BASE_A_H3_dp_ALL',    'h': 3, 'aoa': True,  'extra': ['device'], 'include_interference': True, 'scale_targets': True, 'use_native_xgb': True, 'desc': 'All Enhancements Combined'},
    # Absolute vs Delta feature modes (Phase 2 guidelines)
    {'key': 'BASE_A_H3_dp_DELTA',      'h': 3, 'aoa': True,  'extra': ['device'], 'feature_mode': 'delta',       'desc': 'Baseline + Delta Features Only'},
    {'key': 'BASE_A_H3_dp_HYBRID',     'h': 3, 'aoa': True,  'extra': ['device'], 'feature_mode': 'hybrid',      'desc': 'Baseline + Hybrid Feature Set'},
    {'key': 'BASE_A_H3_dp_PATH_DELTA', 'h': 3, 'aoa': True,  'extra': ['device'], 'feature_mode': 'path_delta',  'desc': 'Baseline + Path Delta (Reconstructible)'},
    # Hybrid history depth sweep (feature count tradeoff)
    {'key': 'BASE_A_H1_dp_HYBRID',     'h': 1, 'aoa': True,  'extra': ['device'], 'feature_mode': 'hybrid',      'desc': 'Hybrid Feature Set h=1 (abs now + 1 delta)'},
    {'key': 'BASE_A_H2_dp_HYBRID',     'h': 2, 'aoa': True,  'extra': ['device'], 'feature_mode': 'hybrid',      'desc': 'Hybrid Feature Set h=2 (abs now + 2 deltas)'},
]

def load_user_file(mat_path: Path) -> dict:
    """Load a single per-user .mat file (flat format)."""
    data = loadmat(str(mat_path), squeeze_me=True, struct_as_record=False)

    dp = data['device_profile']
    device = {
        'n_antennas':      int(np.atleast_1d(dp.n_antennas)[0]),
        'antenna_gain_db': float(np.atleast_1d(dp.antenna_gain_db)[0]),
        'ue_height_m':     float(np.atleast_1d(dp.ue_height_m)[0]),
    }

    return {
        'user_id':        int(np.atleast_1d(data['user_id_val'])[0]),
        'rss':            np.array(data['rss'],            dtype=float).ravel(),
        'sinr':           np.array(data['sinr'],           dtype=float).ravel(),
        'aoa_az':         np.array(data['aoa_az'],         dtype=float).ravel() if 'aoa_az' in data else None,
        'aoa_el':         np.array(data['aoa_el'],         dtype=float).ravel() if 'aoa_el' in data else None,
        'x_pos':          np.array(data['x_pos'],          dtype=float).ravel(),
        'y_pos':          np.array(data['y_pos'],          dtype=float).ravel(),
        'grid_point_id':  np.array(data['grid_point_id'],  dtype=int).ravel(),
        'voronoi_cell_id':np.array(data['voronoi_cell_id'],dtype=int).ravel(),
        'step_index':     np.array(data['step_index'],     dtype=int).ravel(),
        'device':         device,
    }

def _apply_aoa_noise(ud: dict, sinr_dependent: bool = False) -> dict:
    """Apply noise + 5° quantization to AoA fields in-place.
    
    If the device has only 1 antenna, the BS cannot calculate its AoA,
    so we set the AoA fields to None (will be treated as NaN).
    """
    uid = ud['user_id']
    n_ant = ud['device']['n_antennas']
    
    if n_ant <= 1:
        ud['aoa_az'] = None
        ud['aoa_el'] = None
        return ud
        
    if ud['aoa_az'] is not None or ud['aoa_el'] is not None:
        if sinr_dependent:
            sinr_db = ud['sinr']
            noise_std = 2.0 * (10.0 ** (-(sinr_db - 10.0) / 15.0))
            noise_std = np.clip(noise_std, 1.0, 20.0)
        else:
            noise_std = np.full(len(ud['rss']), AOA_NOISE_STD_DEG)

    if ud['aoa_az'] is not None:
        rng = np.random.RandomState(42 + uid * 1000)
        noise = noise_std * rng.randn(len(ud['aoa_az']))
        ud['aoa_az'] = np.round((ud['aoa_az'] + noise) / AOA_QUANT_STEP_DEG) * AOA_QUANT_STEP_DEG
            
    if ud['aoa_el'] is not None:
        rng = np.random.RandomState(43 + uid * 1000)
        noise = noise_std * rng.randn(len(ud['aoa_el']))
        ud['aoa_el'] = np.round((ud['aoa_el'] + noise) / AOA_QUANT_STEP_DEG) * AOA_QUANT_STEP_DEG
            
    return ud

def _ud_to_dataframe(ud: dict) -> pd.DataFrame:
    """Convert a loaded user dict to a DataFrame."""
    n = len(ud['rss'])
    return pd.DataFrame({
        'user_id':         ud['user_id'],
        'step_index':      ud['step_index'],
        'rss':             ud['rss'],
        'sinr':            ud['sinr'],
        'aoa_azimuth':     ud['aoa_az'] if ud['aoa_az'] is not None else np.full(n, np.nan),
        'aoa_elevation':   ud['aoa_el'] if ud['aoa_el'] is not None else np.full(n, np.nan),
        'x_pos':           ud['x_pos'],
        'y_pos':           ud['y_pos'],
        'grid_point_id':   ud['grid_point_id'],
        'voronoi_cell_id': ud['voronoi_cell_id'],
        'n_antennas':      ud['device']['n_antennas'],
        'antenna_gain_db': ud['device']['antenna_gain_db'],
        'ue_height':       ud['device']['ue_height_m'],
    })

def load_all_users(data_dir: Path, sinr_dependent_aoa: bool = False) -> pd.DataFrame:
    """Load all per-user .mat files into a combined DataFrame."""
    candidates = sorted(data_dir.glob('user1_*.mat'))
    if not candidates:
        raise FileNotFoundError(f"No user1_*.mat files found in {data_dir}")
    stem = candidates[0].stem[len('user1_'):]

    n_users = sum(1 for u in range(1, 20) if (data_dir / f'user{u}_{stem}.mat').exists())
    if n_users == 0:
        raise FileNotFoundError(f"No user files matched pattern user*_{stem}.mat in {data_dir}")

    frames = []
    for u in range(1, n_users + 1):
        mat_file = data_dir / f'user{u}_{stem}.mat'
        print(f"  Loading user {u}: {mat_file.name}")
        ud = load_user_file(mat_file)
        ud = _apply_aoa_noise(ud, sinr_dependent=sinr_dependent_aoa)
        udf = _ud_to_dataframe(ud)
        frames.append(udf)
        print(f"    user_id={ud['user_id']}, n={len(udf):,}, "
              f"n_ant={ud['device']['n_antennas']}, "
              f"gain={ud['device']['antenna_gain_db']:+.1f}dB, "
              f"h={ud['device']['ue_height_m']}m")
    return pd.concat(frames, ignore_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Train / Test Split
# ─────────────────────────────────────────────────────────────────────────────

def make_split(df: pd.DataFrame, test_ratio: float = 0.2) -> pd.DataFrame:
    """Split train/test chronologically per user."""
    df = df.copy()
    df['split'] = 'train'
    for uid in df['user_id'].unique():
        mask  = df['user_id'] == uid
        steps = df.loc[mask, 'step_index'].sort_values()
        n_total = len(steps)
        n_test  = int(np.floor(n_total * test_ratio))
        test_steps = steps.iloc[n_total - n_test:].values
        df.loc[mask & df['step_index'].isin(test_steps), 'split'] = 'test'
    return df

def make_segment_split(df: pd.DataFrame, N: int = 5, test_ratio: float = 0.2, random_state: int = 42) -> pd.DataFrame:
    """Slice trajectory into non-overlapping segments of length N,
    and randomly assign segments to train/test per user.
    """
    df = df.copy()
    df['split'] = 'train'
    
    # Store global numpy random state to restore it later
    state = np.random.get_state()
    np.random.seed(random_state)
    
    for uid in df['user_id'].unique():
        user_mask = df['user_id'] == uid
        user_df = df[user_mask].sort_values('step_index')
        indices = user_df.index.values
        n_samples = len(indices)
        
        n_segments = int(np.ceil(n_samples / N))
        segment_ids = np.arange(n_segments)
        
        n_test_segments = int(np.floor(n_segments * test_ratio))
        test_segments = np.random.choice(segment_ids, size=n_test_segments, replace=False)
        test_segments_set = set(test_segments)
        
        test_indices = []
        for seg_id in range(n_segments):
            if seg_id in test_segments_set:
                start_idx = seg_id * N
                end_idx = min(start_idx + N, n_samples)
                test_indices.extend(indices[start_idx:end_idx])
                
        df.loc[test_indices, 'split'] = 'test'
        
    np.random.set_state(state)
    return df

# ─────────────────────────────────────────────────────────────────────────────
# 3. Feature & Target Engineering
# ─────────────────────────────────────────────────────────────────────────────

def build_history_features(df: pd.DataFrame, h: int, extra_cols=None, include_aoa: bool = False, include_interference: bool = False, feature_mode: str = 'absolute') -> pd.DataFrame:
    """Stack h previous samples with current sample."""
    result_frames = []
    for uid in sorted(df['user_id'].unique()):
        udf = df[df['user_id'] == uid].sort_values('step_index').reset_index(drop=True)
        n  = len(udf)

        rss  = udf['rss'].values
        sinr = udf['sinr'].values
        delta_rss = np.concatenate([[np.nan], rss[1:] - rss[:-1]])
        delta_sinr = np.concatenate([[np.nan], sinr[1:] - sinr[:-1]])

        if include_interference:
            interf = udf['interference'].values
            delta_interf = np.concatenate([[np.nan], interf[1:] - interf[:-1]])

        if include_aoa:
            aoa_az = udf['aoa_azimuth'].values
            aoa_el = udf['aoa_elevation'].values
            delta_az = np.concatenate([[np.nan], aoa_az[1:] - aoa_az[:-1]])
            delta_el = np.concatenate([[np.nan], aoa_el[1:] - aoa_el[:-1]])

        cols = {}
        if feature_mode == 'absolute':
            for lag in range(h + 1):
                cols[f'rss_lag{lag}']  = np.concatenate([np.full(lag, np.nan), rss [:n - lag]])
                cols[f'sinr_lag{lag}'] = np.concatenate([np.full(lag, np.nan), sinr[:n - lag]])
                if include_interference:
                    cols[f'interference_lag{lag}'] = np.concatenate([np.full(lag, np.nan), interf[:n - lag]])
                if include_aoa:
                    cols[f'aoa_az_lag{lag}'] = np.concatenate([np.full(lag, np.nan), aoa_az[:n - lag]])
                    cols[f'aoa_el_lag{lag}'] = np.concatenate([np.full(lag, np.nan), aoa_el[:n - lag]])
        elif feature_mode == 'delta':
            for lag in range(h):
                cols[f'rss_delta_lag{lag}']  = np.concatenate([np.full(lag, np.nan), delta_rss[:n - lag]])
                cols[f'sinr_delta_lag{lag}'] = np.concatenate([np.full(lag, np.nan), delta_sinr[:n - lag]])
                if include_interference:
                    cols[f'interference_delta_lag{lag}'] = np.concatenate([np.full(lag, np.nan), delta_interf[:n - lag]])
                if include_aoa:
                    cols[f'aoa_az_delta_lag{lag}'] = np.concatenate([np.full(lag, np.nan), delta_az[:n - lag]])
                    cols[f'aoa_el_delta_lag{lag}'] = np.concatenate([np.full(lag, np.nan), delta_el[:n - lag]])
        elif feature_mode == 'hybrid':
            cols['rss_lag0'] = rss
            cols['sinr_lag0'] = sinr
            if include_interference:
                cols['interference_lag0'] = interf
            if include_aoa:
                cols['aoa_az_lag0'] = aoa_az
                cols['aoa_el_lag0'] = aoa_el

            for lag in range(h):
                cols[f'rss_delta_lag{lag}']  = np.concatenate([np.full(lag, np.nan), delta_rss[:n - lag]])
                cols[f'sinr_delta_lag{lag}'] = np.concatenate([np.full(lag, np.nan), delta_sinr[:n - lag]])
                if include_interference:
                    cols[f'interference_delta_lag{lag}'] = np.concatenate([np.full(lag, np.nan), delta_interf[:n - lag]])
                if include_aoa:
                    cols[f'aoa_az_delta_lag{lag}'] = np.concatenate([np.full(lag, np.nan), delta_az[:n - lag]])
                    cols[f'aoa_el_delta_lag{lag}'] = np.concatenate([np.full(lag, np.nan), delta_el[:n - lag]])
        elif feature_mode == 'path_delta':
            # Earliest absolute lag (at lag h)
            cols[f'rss_lag{h}']  = np.concatenate([np.full(h, np.nan), rss [:n - h]])
            cols[f'sinr_lag{h}'] = np.concatenate([np.full(h, np.nan), sinr[:n - h]])
            if include_interference:
                cols[f'interference_lag{h}'] = np.concatenate([np.full(h, np.nan), interf[:n - h]])
            if include_aoa:
                cols[f'aoa_az_lag{h}'] = np.concatenate([np.full(h, np.nan), aoa_az[:n - h]])
                cols[f'aoa_el_lag{h}'] = np.concatenate([np.full(h, np.nan), aoa_el[:n - h]])
                
            # Path deltas walking forward from h-1 down to 0
            for lag in range(h):
                cols[f'rss_delta_lag{lag}']  = np.concatenate([np.full(lag, np.nan), delta_rss[:n - lag]])
                cols[f'sinr_delta_lag{lag}'] = np.concatenate([np.full(lag, np.nan), delta_sinr[:n - lag]])
                if include_interference:
                    cols[f'interference_delta_lag{lag}'] = np.concatenate([np.full(lag, np.nan), delta_interf[:n - lag]])
                if include_aoa:
                    cols[f'aoa_az_delta_lag{lag}'] = np.concatenate([np.full(lag, np.nan), delta_az[:n - lag]])
                    cols[f'aoa_el_delta_lag{lag}'] = np.concatenate([np.full(lag, np.nan), delta_el[:n - lag]])

        feat_df = pd.DataFrame(cols, index=udf.index)
        valid   = feat_df.iloc[h:].copy()
        meta    = udf.iloc[h:].copy()

        valid = valid.reset_index(drop=True)
        meta  = meta.reset_index(drop=True)
        combined = pd.concat([meta, valid], axis=1)

        if extra_cols:
            for col in extra_cols:
                if col == 'device':
                    combined['feat_n_antennas'] = combined['n_antennas']
                    combined['feat_antenna_gain_db'] = combined['antenna_gain_db']
                    combined['feat_ue_height'] = combined['ue_height']
                else:
                    combined[f'feat_{col}'] = combined[col]

        result_frames.append(combined)

    return pd.concat(result_frames, ignore_index=True)

def get_feature_cols(h: int, extra_cols=None, include_aoa: bool = False, include_interference: bool = False, feature_mode: str = 'absolute') -> list:
    """Generate list of feature column names."""
    cols = []
    if feature_mode == 'absolute':
        for lag in range(h + 1):
            cols.extend([f'rss_lag{lag}', f'sinr_lag{lag}'])
            if include_interference:
                cols.append(f'interference_lag{lag}')
            if include_aoa:
                cols.extend([f'aoa_az_lag{lag}', f'aoa_el_lag{lag}'])
    elif feature_mode == 'delta':
        for lag in range(h):
            cols.extend([f'rss_delta_lag{lag}', f'sinr_delta_lag{lag}'])
            if include_interference:
                cols.append(f'interference_delta_lag{lag}')
            if include_aoa:
                cols.extend([f'aoa_az_delta_lag{lag}', f'aoa_el_delta_lag{lag}'])
    elif feature_mode == 'hybrid':
        cols.extend(['rss_lag0', 'sinr_lag0'])
        if include_interference:
            cols.append('interference_lag0')
        if include_aoa:
            cols.extend(['aoa_az_lag0', 'aoa_el_lag0'])

        for lag in range(h):
            cols.extend([f'rss_delta_lag{lag}', f'sinr_delta_lag{lag}'])
            if include_interference:
                cols.append(f'interference_delta_lag{lag}')
            if include_aoa:
                cols.extend([f'aoa_az_delta_lag{lag}', f'aoa_el_delta_lag{lag}'])
    elif feature_mode == 'path_delta':
        cols.extend([f'rss_lag{h}', f'sinr_lag{h}'])
        if include_interference:
            cols.append(f'interference_lag{h}')
        if include_aoa:
            cols.extend([f'aoa_az_lag{h}', f'aoa_el_lag{h}'])

        for lag in range(h):
            cols.extend([f'rss_delta_lag{lag}', f'sinr_delta_lag{lag}'])
            if include_interference:
                cols.append(f'interference_delta_lag{lag}')
            if include_aoa:
                cols.extend([f'aoa_az_delta_lag{lag}', f'aoa_el_delta_lag{lag}'])

    if extra_cols:
        for col in extra_cols:
            if col == 'device':
                cols.extend(['feat_n_antennas', 'feat_antenna_gain_db', 'feat_ue_height'])
            else:
                cols.append(f'feat_{col}')
    return cols

def _read_bs_position_3d(data_dir: Path) -> list:
    """Read config file or mat file metadata to find BS 3D position."""
    # Option 1: config file inside data_dir
    for cfg_name in ('data_generation_config.jsonc', 'config.jsonc', 'config.json'):
        p = data_dir / cfg_name
        if p.exists():
            try:
                cfg = read_jsonc(p)
                bs = cfg.get('base_station', {}).get('position', [])
                if len(bs) >= 3:
                    return [float(x) for x in bs]
            except Exception:
                pass

    # Option 2: experiment_info.mat
    try:
        mat = loadmat(str(data_dir / 'experiment_info.mat'), squeeze_me=True)
        ei = mat.get('experiment_info')
        if ei is not None:
            config_name = str(ei['config_name'].flat[0]) if hasattr(ei['config_name'], 'flat') else str(ei['config_name'])
            cfg_path = EXPERIMENT_ROOT / 'configs' / config_name
            if cfg_path.exists():
                cfg = read_jsonc(cfg_path)
                bs = cfg.get('base_station', {}).get('position', [])
                if len(bs) >= 3:
                    return [float(x) for x in bs]
    except Exception:
        pass

    # Fallback to NE BS default
    print("Warning: BS position not found, falling back to default [116.0, 116.0, 10.0]")
    return [116.0, 116.0, 10.0]

def get_grid_spacing(data_dir: Path) -> float:
    """Read configuration file to determine grid spacing (meters)."""
    for cfg_name in ('data_generation_config.jsonc', 'config.jsonc', 'config.json'):
        p = data_dir / cfg_name
        if p.exists():
            try:
                cfg = read_jsonc(p)
                return float(cfg.get('grid', {}).get('spacing', 4.0))
            except Exception:
                pass
    return 4.0

def spherical_to_cartesian(distance: np.ndarray, azimuth_deg: np.ndarray, elevation_deg: np.ndarray, bs_pos: np.ndarray) -> np.ndarray:
    """Convert spherical coordinates back to Cartesian [x, y, z] relative to BS."""
    azimuth_rad = np.radians(azimuth_deg)
    elevation_rad = np.radians(elevation_deg)
    
    horizontal_dist = distance * np.cos(elevation_rad)
    dx = horizontal_dist * np.sin(azimuth_rad)
    dy = horizontal_dist * np.cos(azimuth_rad)
    dz = -distance * np.sin(elevation_rad)
    
    return bs_pos + np.column_stack([dx, dy, dz])

# ─────────────────────────────────────────────────────────────────────────────
# 4. Pipeline Execution
# ─────────────────────────────────────────────────────────────────────────────

def get_model(model_name: str):
    """Return a sklearn-compatible regressor.
    If tune_hyperparams() has been called, TUNED_PARAMS overrides the defaults.
    """
    if model_name == 'rf':
        params = dict(n_estimators=50, max_depth=15, min_samples_leaf=20, random_state=42, n_jobs=N_JOBS)
        params.update(TUNED_PARAMS.get('rf', {}))
        params['n_jobs'] = N_JOBS
        return RandomForestRegressor(**params)
    elif model_name == 'xgboost':
        if not HAS_XGBOOST:
            raise RuntimeError("XGBoost is not installed")
        params = dict(n_estimators=50, max_depth=6, learning_rate=0.1, random_state=42, n_jobs=N_JOBS)
        params.update(TUNED_PARAMS.get('xgboost', {}))
        params['n_jobs'] = N_JOBS
        return MultiOutputRegressor(XGBRegressor(**params))
    elif model_name == 'xgboost_custom':
        if not HAS_XGBOOST:
            raise RuntimeError("XGBoost is not installed")
        params = dict(n_estimators=50, max_depth=6, learning_rate=0.1, random_state=42, n_jobs=N_JOBS)
        params.update(TUNED_PARAMS.get('xgboost_custom', {}))
        params['n_jobs'] = N_JOBS
        params['objective'] = custom_euclidean_obj_sklearn
        return XGBRegressor(**params)
    else:
        raise ValueError(f"Unknown model: {model_name}")

def tune_hyperparams(df: pd.DataFrame,
                     models: list,
                     bs_pos: np.ndarray,
                     n_trials: int = 50,
                     sample_frac: float = 0.30,
                     out_dir: Path = None) -> None:
    """
    Run an Optuna TPE study for each model and store the best params in
    the global TUNED_PARAMS dict so that subsequent get_model() calls use them.

    Progress is persisted to a SQLite database in out_dir/tuning/
    so an interrupted run can be resumed by re-running with the same command.
    When all n_trials are done, best params are saved to tuned_params.json.
    """
    if not HAS_OPTUNA:
        print("[tune] Optuna not installed — skipping hyperparameter tuning.")
        print("       Install with: pip install optuna")
        return

    print(f"\n=== Hyperparameter Tuning (Optuna | {n_trials} trials | "
          f"{sample_frac:.0%} of training data) ===")

    # Build BASE_A_H3_dp features (full features including history + device + AoA)
    # This represents our primary architectural target.
    print("Building full BASE_A_H3_dp features for tuning...")
    feat_df = build_history_features(df, h=3, extra_cols=['device'], include_aoa=True)
    feat_cols = get_feature_cols(h=3, extra_cols=['device'], include_aoa=True)

    # Subsample training rows chronologically per user
    train_rows = feat_df[feat_df['split'] == 'train'].copy()
    kept = []
    for uid in sorted(train_rows['user_id'].unique()):
        u_rows = train_rows[train_rows['user_id'] == uid].sort_values('step_index')
        n_keep = max(1, int(len(u_rows) * sample_frac))
        kept.append(u_rows.iloc[:n_keep])
    sub_train = pd.concat(kept, ignore_index=True)

    # Inner 80/20 chronological split within the subsample
    sub_train = sub_train.copy()
    sub_train['inner_split'] = 'inner_train'
    for uid in sorted(sub_train['user_id'].unique()):
        mask = sub_train['user_id'] == uid
        rows = sub_train.loc[mask].sort_values('step_index')
        n_val = max(1, int(len(rows) * 0.2))
        sub_train.loc[rows.index[-n_val:], 'inner_split'] = 'inner_val'

    targets = ['target_x', 'target_y', 'target_z']
    X_tr  = sub_train.loc[sub_train['inner_split'] == 'inner_train', feat_cols].values.astype(np.float32)
    y_tr  = sub_train.loc[sub_train['inner_split'] == 'inner_train', targets].values.astype(np.float32)
    X_val = sub_train.loc[sub_train['inner_split'] == 'inner_val',   feat_cols].values.astype(np.float32)
    y_val = sub_train.loc[sub_train['inner_split'] == 'inner_val',   targets].values.astype(np.float32)

    ue_val_true = np.column_stack([
        sub_train.loc[sub_train['inner_split'] == 'inner_val', 'x_pos'].values,
        sub_train.loc[sub_train['inner_split'] == 'inner_val', 'y_pos'].values,
        sub_train.loc[sub_train['inner_split'] == 'inner_val', 'ue_height'].values
    ])

    # Free large DataFrames
    del feat_df, kept, sub_train
    gc.collect()

    print(f"  Tuning data: {len(X_tr):,} inner-train  /  {len(X_val):,} inner-val")

    tune_dir = (out_dir / 'tuning') if out_dir else Path('tuning')
    tune_dir.mkdir(parents=True, exist_ok=True)
    params_path = tune_dir / 'tuned_params.json'
    print(f"  Persistence: {tune_dir}")

    for model_name in models:
        if model_name == 'xgboost' and not HAS_XGBOOST:
            print(f"  Skipping {model_name} (not installed)")
            continue

        print(f"  Tuning {model_name} ({n_trials} trials)...")

        # ── Persistent SQLite study — survives interruptions ──────────────────
        db_path    = tune_dir / f'study_{model_name}.db'
        storage    = f'sqlite:///{db_path}'
        study_name = f'hparam_search_{model_name}'

        study = optuna.create_study(
            study_name=study_name,
            storage=storage,
            direction='minimize',  # minimize MAE
            sampler=optuna.samplers.TPESampler(seed=42),
            load_if_exists=True,
        )

        already_done = len([t for t in study.trials
                            if t.state == optuna.trial.TrialState.COMPLETE])
        remaining    = max(0, n_trials - already_done)
        if already_done:
            print(f"    Resuming: {already_done} trials already saved, "
                  f"{remaining} remaining.")
        if remaining == 0:
            print(f"    All {n_trials} trials already completed — loading saved result.")
            TUNED_PARAMS[model_name] = study.best_params
            print(f"    Best inner-val MAE: {study.best_value:.4f} m")
            print(f"    Best params: {study.best_params}")
            continue

        _tune_wall0  = time.time()
        _trial_times = []

        def _trial_callback(study, trial, _mn=model_name):
            if trial.state != optuna.trial.TrialState.COMPLETE:
                return
            _trial_times.append(time.time())
            done    = already_done + len(_trial_times)
            elapsed = _trial_times[-1] - _tune_wall0
            avg_s   = elapsed / len(_trial_times)
            eta_s   = avg_s * (n_trials - done)
            best    = study.best_value
            cur     = trial.value if trial.value is not None else float('nan')
            filled  = int(20 * done / n_trials)
            bar     = '#' * filled + '-' * (20 - filled)
            print(f'    trial {done:>3}/{n_trials}  '
                  f'MAE={cur:.4f}m  best={best:.4f}m  '
                  f'[{bar}]  ETA ~ {_fmt_s(eta_s)}', flush=True)

        def objective(trial, _mn=model_name):
            if _mn == 'rf':
                # Impute NaNs for Random Forest
                X_tr_imp = np.nan_to_num(X_tr, nan=0.0)
                X_val_imp = np.nan_to_num(X_val, nan=0.0)
                reg = RandomForestRegressor(
                    n_estimators=trial.suggest_int('n_estimators', 50, 200, step=50),
                    max_depth=trial.suggest_int('max_depth', 8, 20),
                    min_samples_leaf=trial.suggest_int('min_samples_leaf', 5, 30),
                    random_state=42, n_jobs=N_JOBS
                )
                reg.fit(X_tr_imp, y_tr)
                y_pred = reg.predict(X_val_imp)
            elif _mn == 'xgboost_custom':
                reg = XGBRegressor(
                    n_estimators=trial.suggest_int('n_estimators', 50, 250, step=50),
                    max_depth=trial.suggest_int('max_depth', 3, 9),
                    learning_rate=trial.suggest_float('learning_rate', 0.02, 0.30, log=True),
                    subsample=trial.suggest_float('subsample', 0.6, 1.0),
                    colsample_bytree=trial.suggest_float('colsample_bytree', 0.5, 1.0),
                    random_state=42, n_jobs=N_JOBS, verbosity=0,
                    objective=custom_euclidean_obj_sklearn
                )
                reg.fit(X_tr, y_tr)
                y_pred = reg.predict(X_val)
            else:  # xgboost
                reg = MultiOutputRegressor(XGBRegressor(
                    n_estimators=trial.suggest_int('n_estimators', 50, 250, step=50),
                    max_depth=trial.suggest_int('max_depth', 3, 9),
                    learning_rate=trial.suggest_float('learning_rate', 0.02, 0.30, log=True),
                    subsample=trial.suggest_float('subsample', 0.6, 1.0),
                    colsample_bytree=trial.suggest_float('colsample_bytree', 0.5, 1.0),
                    random_state=42, n_jobs=N_JOBS, verbosity=0
                ))
                reg.fit(X_tr, y_tr)
                y_pred = reg.predict(X_val)

            ue_pred = bs_pos + y_pred
            mae = np.mean(np.linalg.norm(ue_val_true - ue_pred, axis=1))
            return float(mae)

        study.optimize(objective, n_trials=remaining, callbacks=[_trial_callback])

        TUNED_PARAMS[model_name] = study.best_params
        print(f"    Best inner-val MAE: {study.best_value:.4f} m")
        print(f"    Best params: {study.best_params}")

    # Persist tuned params
    with open(params_path, 'w') as f:
        json.dump(TUNED_PARAMS, f, indent=2)
    print(f"  [OK] Tuned params saved to: {params_path}")

def run_one_experiment(feat_df: pd.DataFrame, feature_cols: list, bs_pos: np.ndarray, 
                       model_name: str, exp_label: str, spacing: float = 4.0,
                       scale_targets: bool = False, use_native_xgb: bool = False) -> dict:
    """Train on train split, evaluate on test split, and compute spatial 3D metrics."""
    train_mask = feat_df['split'] == 'train'
    test_mask  = feat_df['split'] == 'test'

    # Prepare features
    X_train = feat_df.loc[train_mask, feature_cols].values.astype(np.float32)
    X_test  = feat_df.loc[test_mask,  feature_cols].values.astype(np.float32)

    # Impute NaNs for Random Forest
    if model_name == 'rf':
        X_train = np.nan_to_num(X_train, nan=0.0)
        X_test  = np.nan_to_num(X_test, nan=0.0)

    # Prepare 3D targets (X, Y, Z relative to BS)
    targets = ['target_x', 'target_y', 'target_z']
    y_train = feat_df.loc[train_mask, targets].values.astype(np.float32)
    y_test  = feat_df.loc[test_mask,  targets].values.astype(np.float32)

    # Scale targets if requested
    if scale_targets:
        scaler = StandardScaler()
        y_train_fit = scaler.fit_transform(y_train)
    else:
        y_train_fit = y_train

    # True Cartesian UE coordinates
    ue_true = np.column_stack([
        feat_df.loc[test_mask, 'x_pos'].values,
        feat_df.loc[test_mask, 'y_pos'].values,
        feat_df.loc[test_mask, 'ue_height'].values
    ])

    # Instantiate Model
    if model_name == 'xgboost' and use_native_xgb:
        if not HAS_XGBOOST:
            raise RuntimeError("XGBoost is not installed")
        params = dict(n_estimators=50, max_depth=6, learning_rate=0.1, random_state=42, n_jobs=N_JOBS)
        params.update(TUNED_PARAMS.get('xgboost', {}))
        params['n_jobs'] = N_JOBS
        model = XGBRegressor(**params)
    else:
        model = get_model(model_name)

    # Train
    t0 = time.time()
    model.fit(X_train, y_train_fit)
    train_sec = time.time() - t0

    # Predict
    y_pred = model.predict(X_test)
    if scale_targets:
        y_pred = scaler.inverse_transform(y_pred)

    # Calculate Cartesian predicted coordinates
    ue_pred = bs_pos + y_pred

    # Calculate 3D Position Errors in meters
    position_errors = np.linalg.norm(ue_true - ue_pred, axis=1)
    mae = np.mean(position_errors)
    mpe = mae / spacing

    # Calculate spherical coordinates for metric validation and backwards compatibility
    pred_delta = ue_pred - bs_pos
    pred_dist = np.linalg.norm(pred_delta, axis=1)
    pred_azimuth = np.arctan2(pred_delta[:, 0], pred_delta[:, 1]) * 180.0 / np.pi
    pred_horizontal = np.sqrt(pred_delta[:, 0]**2 + pred_delta[:, 1]**2)
    pred_elevation = -np.arctan2(pred_delta[:, 2], pred_horizontal) * 180.0 / np.pi

    true_dist = feat_df.loc[test_mask, 'target_distance'].values
    true_azimuth = feat_df.loc[test_mask, 'target_azimuth'].values
    true_elevation = feat_df.loc[test_mask, 'target_elevation'].values

    # Metrics for spherical comparison
    dist_mae = mean_absolute_error(true_dist, pred_dist)
    
    # Handle wrap-around for azimuth
    az_diff = np.abs(true_azimuth - pred_azimuth)
    az_diff = np.minimum(az_diff, 360.0 - az_diff)
    az_mae = np.mean(az_diff)
    
    el_mae = mean_absolute_error(true_elevation, pred_elevation)

    overall = {
        'mae_m': round(mae, 4),
        'mpe_pts': round(mpe, 4),
        'dist_mae': round(dist_mae, 4),
        'az_mae': round(az_mae, 4),
        'el_mae': round(el_mae, 4),
        'train_time_s': round(train_sec, 2),
    }

    # Per-user breakdown
    per_user = {}
    test_user_ids = feat_df.loc[test_mask, 'user_id'].values
    test_cells = feat_df.loc[test_mask, 'voronoi_cell_id'].values

    for uid in sorted(feat_df['user_id'].unique()):
        u_mask = test_user_ids == uid
        if np.sum(u_mask) == 0:
            continue
        u_errors = position_errors[u_mask]
        u_mae = np.mean(u_errors)
        
        # Spherical errors per user
        u_true_dist = true_dist[u_mask]
        u_pred_dist = pred_dist[u_mask]
        u_true_az = true_azimuth[u_mask]
        u_pred_az = pred_azimuth[u_mask]
        u_true_el = true_elevation[u_mask]
        u_pred_el = pred_elevation[u_mask]
        
        u_dist_mae = mean_absolute_error(u_true_dist, u_pred_dist)
        
        # Handle wrap-around for azimuth per user
        u_az_diff = np.abs(u_true_az - u_pred_az)
        u_az_diff = np.minimum(u_az_diff, 360.0 - u_az_diff)
        u_az_mae = np.mean(u_az_diff)
        
        u_el_mae = mean_absolute_error(u_true_el, u_pred_el)

        per_user[uid] = {
            'mae_m': round(u_mae, 4),
            'mpe_pts': round(u_mae / spacing, 4),
            'dist_mae': round(u_dist_mae, 4),
            'az_mae': round(u_az_mae, 4),
            'el_mae': round(u_el_mae, 4),
        }

    # Per-cell breakdown
    per_cell = {}
    for cid in sorted(feat_df['voronoi_cell_id'].unique()):
        c_mask = test_cells == cid
        if np.sum(c_mask) == 0:
            continue
        c_errors = position_errors[c_mask]
        c_mae = np.mean(c_errors)
        
        per_cell[cid] = {
            'mae_m': round(c_mae, 4),
            'mpe_pts': round(c_mae / spacing, 4)
        }

    return {
        'overall': overall,
        'per_user': per_user,
        'per_cell': per_cell
    }

def main():
    parser = argparse.ArgumentParser(description="Multi-User Regression Pipeline")
    parser.add_argument('--data-dir', required=True, type=str, help="MATLAB simulation results path")
    parser.add_argument('--out-dir', required=True, type=str, help="Python results output path")
    parser.add_argument('--models', nargs='+', default=['xgboost', 'rf'], choices=['xgboost', 'rf', 'xgboost_custom'])
    parser.add_argument('--history', type=int, default=3, help="Primary history depth")
    parser.add_argument('--subsample', type=float, default=1.0, help="Train subsample fraction (0.0 to 1.0)")
    parser.add_argument('--split-method', type=str, default='chronological', choices=['chronological', 'segment_shuffle'], help="Train/test split method")
    parser.add_argument('--segment-len', type=int, default=5, help="Segment length for segment_shuffle split")
    parser.add_argument('--sinr-dependent-aoa', action='store_true', help="Apply physical noise mapping")
    parser.add_argument('--run-only', nargs='+', default=None, help="Filter experiment keys to run")
    parser.add_argument('--tune-hyperparams', action='store_true', help="Run Optuna hyperparameter search before experiments")
    parser.add_argument('--tune-trials', type=int, default=50, help="Number of Optuna trials per model")
    parser.add_argument('--tune-fraction', type=float, default=1.0, help="Subsample fraction of train data for tuning")
    parser.add_argument('--load-tuned-params', type=str, default=None, help="Path to tuned_params.json to load pre-tuned params")
    parser.add_argument('--n-jobs', type=int, default=-1, help="Number of CPU cores to use (-1 for all)")
    args = parser.parse_args()

    global N_JOBS
    N_JOBS = args.n_jobs
    print(f"[config] n_jobs={N_JOBS} (RF and XGBoost thread count)")

    global TUNED_PARAMS
    if args.load_tuned_params:
        params_file = Path(args.load_tuned_params)
        if not params_file.exists():
            print(f"Error: --load-tuned-params file not found: {params_file}")
            sys.exit(1)
        with open(params_file) as f:
            loaded = json.load(f)
        TUNED_PARAMS.update(loaded)
        print(f"[OK] Loaded tuned params from {params_file}")
        for mn, p in TUNED_PARAMS.items():
            print(f"  {mn}: {p}")

    data_dir = Path(args.data_dir)
    out_dir  = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from {data_dir}...")
    df = load_all_users(data_dir, sinr_dependent_aoa=args.sinr_dependent_aoa)
    
    spacing = get_grid_spacing(data_dir)
    bs_pos_3d = _read_bs_position_3d(data_dir)
    bs_pos = np.array(bs_pos_3d)

    print(f"\nGrid spacing:   {spacing} m")
    print(f"Serving BS:     {bs_pos_3d} m")

    # Compute target variables
    print("\nComputing continuous 3D target coordinates...")
    ue_coords = np.column_stack([df['x_pos'], df['y_pos'], df['ue_height']])
    delta = ue_coords - bs_pos
    
    df['target_x'] = delta[:, 0]
    df['target_y'] = delta[:, 1]
    df['target_z'] = delta[:, 2]
    
    df['target_distance'] = np.linalg.norm(delta, axis=1)
    df['target_azimuth'] = np.arctan2(delta[:, 0], delta[:, 1]) * 180.0 / np.pi
    
    horizontal_dist = np.sqrt(delta[:, 0]**2 + delta[:, 1]**2)
    df['target_elevation'] = -np.arctan2(delta[:, 2], horizontal_dist) * 180.0 / np.pi
    df['interference'] = df['rss'] - df['sinr']

    # Split selection
    if args.split_method == 'segment_shuffle':
        print(f"Splitting train/test via segment shuffle (block size={args.segment_len}, 80/20 per user)...")
        df = make_segment_split(df, N=args.segment_len, test_ratio=0.2)
    else:
        print("Splitting train/test chronologically (80/20 per user)...")
        df = make_split(df, test_ratio=0.2)

    # Subsampling of training set
    if args.subsample < 1.0:
        print(f"Subsampling training split chronologically by fraction {args.subsample:.2f}...")
        train_idxs = []
        for uid in df['user_id'].unique():
            user_train = df[(df['user_id'] == uid) & (df['split'] == 'train')].sort_values('step_index')
            n_sub = int(len(user_train) * args.subsample)
            train_idxs.append(user_train.index[:n_sub])
            
        test_idxs = df[df['split'] == 'test'].index
        all_kept_idxs = np.concatenate(train_idxs + [test_idxs])
        df = df.loc[all_kept_idxs].reset_index(drop=True)

    # Run hyperparameter tuning if requested
    if args.tune_hyperparams:
        tune_hyperparams(df, args.models, bs_pos, n_trials=args.tune_trials, sample_frac=args.tune_fraction, out_dir=out_dir)

    # Run experiments
    results = {}
    to_run = [e for e in EXPERIMENTS if args.run_only is None or e['key'] in args.run_only]
    n_total = len(to_run) * len(args.models)
    n_done = 0

    print(f"\nRunning {len(to_run)} regression experiments ({n_total} total runs)...", flush=True)
    t_start = time.time()
    
    for exp in to_run:
        key = exp['key']
        h = exp['h']
        aoa = exp['aoa']
        extra = exp['extra']
        include_interference = exp.get('include_interference', False)
        scale_targets = exp.get('scale_targets', False)
        use_native_xgb = exp.get('use_native_xgb', False)
        feature_mode = exp.get('feature_mode', 'absolute')
        
        print(f"\nExperiment {key} (h={h}, AoA={aoa}, extra={extra}, int={include_interference}, scale={scale_targets}, native_xgb={use_native_xgb}, mode={feature_mode})", flush=True)
        
        # Build stacked features
        feat_df = build_history_features(df, h, extra_cols=extra, include_aoa=aoa, include_interference=include_interference, feature_mode=feature_mode)
        feature_cols = get_feature_cols(h, extra_cols=extra, include_aoa=aoa, include_interference=include_interference, feature_mode=feature_mode)

        results[key] = {}
        for model in args.models:
            n_done += 1
            print(f"  Training {model}...", flush=True)
            res = run_one_experiment(feat_df, feature_cols, bs_pos, model, key, spacing=spacing,
                                     scale_targets=scale_targets, use_native_xgb=use_native_xgb)
            results[key][model] = res
            
            elapsed = time.time() - t_start
            avg_s = elapsed / n_done
            eta_s = avg_s * (n_total - n_done)
            
            print(f"    3D Position MAE: {res['overall']['mae_m']:.3f} m (MPE: {res['overall']['mpe_pts']:.3f} pts)", flush=True)
            print(f"    [Progress {n_done}/{n_total} | Elapsed: {_fmt_s(elapsed)} | ETA: {_fmt_s(eta_s)}]", flush=True)

    # Save outputs
    print("\nSaving results to CSVs...")
    summary_rows = []
    user_rows = []
    cell_rows = []

    for key, models_res in results.items():
        for model, res in models_res.items():
            # Summary
            summary_rows.append({
                'model': model,
                'experiment': key,
                '3d_mae_m': res['overall']['mae_m'],
                'mpe_pts': res['overall']['mpe_pts'],
                'dist_mae': res['overall']['dist_mae'],
                'az_mae': res['overall']['az_mae'],
                'el_mae': res['overall']['el_mae'],
                'train_time_s': res['overall']['train_time_s'],
            })

            # User breakdown
            for uid, ures in res['per_user'].items():
                user_rows.append({
                    'model': model,
                    'experiment': key,
                    'user_id': uid,
                    '3d_mae_m': ures['mae_m'],
                    'mpe_pts': ures['mpe_pts'],
                    'dist_mae': ures['dist_mae'],
                    'az_mae': ures['az_mae'],
                    'el_mae': ures['el_mae'],
                })

            # Cell breakdown
            for cid, cres in res['per_cell'].items():
                cell_rows.append({
                    'model': model,
                    'experiment': key,
                    'voronoi_cell_id': cid,
                    '3d_mae_m': cres['mae_m'],
                    'mpe_pts': cres['mpe_pts'],
                })

    csv_dir = out_dir / 'csvs'
    csv_dir.mkdir(exist_ok=True)

    pd.DataFrame(summary_rows).to_csv(csv_dir / 'results_summary.csv', index=False)
    pd.DataFrame(user_rows).to_csv(csv_dir / 'per_user_breakdown.csv', index=False)
    pd.DataFrame(cell_rows).to_csv(csv_dir / 'per_cell_breakdown.csv', index=False)

    # Generate PIPELINE_REPORT.md
    print("Generating PIPELINE_REPORT.md...")
    with open(out_dir / 'PIPELINE_REPORT.md', 'w') as f:
        f.write(f"# Multi-User 3D Regression Pipeline Report\n\n")
        f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Data directory:** `{data_dir.name}`\n")
        f.write(f"**BS position:** `{bs_pos_3d}`\n")
        f.write(f"**Grid spacing:** `{spacing}m`\n\n")
        
        f.write("## Overall Regression Results\n\n")
        f.write("| Model | Experiment | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train time (s) |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for r in summary_rows:
            f.write(f"| {r['model']} | {r['experiment']} | {r['3d_mae_m']:.3f} | {r['mpe_pts']:.3f} | {r['dist_mae']:.3f} | {r['az_mae']:.3f} | {r['el_mae']:.3f} | {r['train_time_s']} |\n")

        f.write("\n## Per-User Results\n\n")
        f.write("| Model | Experiment | User | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for r in user_rows:
            f.write(f"| {r['model']} | {r['experiment']} | U{r['user_id']} | {r['3d_mae_m']:.3f} | {r['mpe_pts']:.3f} | {r['dist_mae']:.3f} | {r['az_mae']:.3f} | {r['el_mae']:.3f} |\n")

    print(f"Pipeline complete! Outputs saved in {out_dir}")

if __name__ == '__main__':
    main()
