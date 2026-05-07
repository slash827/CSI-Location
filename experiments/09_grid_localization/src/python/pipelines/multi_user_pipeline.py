"""
Multi-User Heterogeneous Environment — Localization Pipeline

Loads 5 per-user simulation .mat files (from run_multi_user_15x15.m),
builds transition history features, and evaluates experiments using
the naming convention:

  BASE        — RSS+SINR, h=0 (static baseline)
  BASE_dp     — RSS+SINR + device params, h=0
  BASE_uid    — RSS+SINR + user_id, h=0
  BASE_H      — RSS+SINR, h=3 (absolute value stacking)
  BASE_H_dp   — BASE_H + device params
  BASE_H_uid  — BASE_H + user_id
  BASE_A      — RSS+SINR+AoA, h=0
  BASE_A_dp   — BASE_A + device params
  BASE_A_uid  — BASE_A + user_id
  BASE_A_H    — RSS+SINR+AoA, h=3
  BASE_A_H_dp — BASE_A_H + device params

  Delta variants (e.g. BASE_H_delta): same as absolute but uses
  first-differences instead of stacked raw values.

Legend:
  BASE  = RSS+SINR (single serving BS)
  A     = AoA azimuth + elevation (4° Gaussian noise + 5° quantization)
  H     = history stacking h=3
  dp    = device params: n_antennas, antenna_gain_db, ue_height
  uid   = user_id as integer feature (oracle identity)
  delta = delta representation instead of absolute stacking

Usage:
  # Full run (all experiments):
  python multi_user_pipeline.py --data-dir <path/to/sim_data_multi_user_*>

  # Run only new experiments and append to existing CSVs:
  python multi_user_pipeline.py --data-dir <path> \\
      --run-only BASE_dp BASE_uid BASE_A_dp BASE_A_uid --append-results

  # Data volume sweep (BASE_H vs BASE_H_delta):
  python multi_user_pipeline.py --data-dir <path> --data-volume-sweep

  # Environmental variability (requires 3 env-run .mat files):
  python multi_user_pipeline.py --data-dir <path> --env-dir <path/to/env_runs>
"""

import argparse
import json
import sys
import time
import warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from scipy.io import loadmat
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("Warning: XGBoost not available, skipping XGBoost models")

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: Matplotlib not available, skipping plots")

warnings.filterwarnings('ignore')

# ── Project layout ────────────────────────────────────────────────────────────
SCRIPT_DIR      = Path(__file__).resolve().parent
EXPERIMENT_ROOT = SCRIPT_DIR.parent.parent          # 09_grid_localization/
RESULTS_ROOT    = SCRIPT_DIR.parent.parent.parent.parent / 'results'

HISTORY_PRIMARY   = 3    # default h for history experiments
MAX_HISTORY_CURVE = 4    # h range for learning curve (0..4)

# AoA realistic impairments
AOA_NOISE_STD_DEG  = 4.0
AOA_QUANT_STEP_DEG = 5.0

# ── Experiment registry ───────────────────────────────────────────────────────
DEVICE_COLS = ['n_antennas', 'antenna_gain_db', 'ue_height']

# Each entry: key, h (>0 means use h_primary), extra, aoa, mode
EXPERIMENTS = [
    # Static baselines (h=0)
    {'key': 'BASE',        'h': 0, 'extra': None,        'aoa': False, 'mode': 'absolute'},
    {'key': 'BASE_dp',     'h': 0, 'extra': DEVICE_COLS, 'aoa': False, 'mode': 'absolute'},
    {'key': 'BASE_uid',    'h': 0, 'extra': ['user_id'], 'aoa': False, 'mode': 'absolute'},
    # History experiments (h=3, absolute)
    {'key': 'BASE_H',      'h': 3, 'extra': None,        'aoa': False, 'mode': 'absolute'},
    {'key': 'BASE_H_dp',   'h': 3, 'extra': DEVICE_COLS, 'aoa': False, 'mode': 'absolute'},
    {'key': 'BASE_H_uid',  'h': 3, 'extra': ['user_id'], 'aoa': False, 'mode': 'absolute'},
    # AoA static baselines (h=0)
    {'key': 'BASE_A',      'h': 0, 'extra': None,        'aoa': True,  'mode': 'absolute'},
    {'key': 'BASE_A_dp',   'h': 0, 'extra': DEVICE_COLS, 'aoa': True,  'mode': 'absolute'},
    {'key': 'BASE_A_uid',  'h': 0, 'extra': ['user_id'], 'aoa': True,  'mode': 'absolute'},
    # AoA + history (h=3, absolute)
    {'key': 'BASE_A_H',    'h': 3, 'extra': None,        'aoa': True,  'mode': 'absolute'},
    {'key': 'BASE_A_H_dp', 'h': 3, 'extra': DEVICE_COLS, 'aoa': True,  'mode': 'absolute'},
    # Delta variants
    {'key': 'BASE_H_delta',      'h': 3, 'extra': None,        'aoa': False, 'mode': 'delta'},
    {'key': 'BASE_H_dp_delta',   'h': 3, 'extra': DEVICE_COLS, 'aoa': False, 'mode': 'delta'},
    {'key': 'BASE_A_H_delta',    'h': 3, 'extra': None,        'aoa': True,  'mode': 'delta'},
    {'key': 'BASE_A_H_dp_delta', 'h': 3, 'extra': DEVICE_COLS, 'aoa': True,  'mode': 'delta'},
]

# Cross-user experiments: cu_key -> base experiment key (reuses its feat_df)
CROSS_USER_EXPERIMENTS = {
    'cross_user_BASE_H':      'BASE_H',
    'cross_user_BASE_H_dp':   'BASE_H_dp',
    'cross_user_BASE_H_uid':  'BASE_H_uid',
    'cross_user_BASE_A_H':    'BASE_A_H',
    'cross_user_BASE_A_dp':   'BASE_A_dp',
    'cross_user_BASE_A_uid':  'BASE_A_uid',
}

# Core 7 experiments shown in main bar chart and heatmap (original set, renamed)
CORE_DISPLAY_EXPERIMENTS = [
    'BASE', 'BASE_H', 'BASE_H_dp', 'BASE_H_uid',
    'BASE_A', 'BASE_A_H', 'BASE_A_H_dp',
]


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_user_file(mat_path: Path) -> dict:
    """Load a single per-user .mat file (flat format from run_multi_user_15x15.m)."""
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
        'aoa_az':         np.array(data['aoa_az'],         dtype=float).ravel()
                          if 'aoa_az' in data else None,
        'aoa_el':         np.array(data['aoa_el'],         dtype=float).ravel()
                          if 'aoa_el' in data else None,
        'x_pos':          np.array(data['x_pos'],          dtype=float).ravel(),
        'y_pos':          np.array(data['y_pos'],          dtype=float).ravel(),
        'grid_point_id':  np.array(data['grid_point_id'],  dtype=int).ravel(),
        'voronoi_cell_id':np.array(data['voronoi_cell_id'],dtype=int).ravel(),
        'step_index':     np.array(data['step_index'],     dtype=int).ravel(),
        'device':         device,
    }


def _apply_aoa_noise(ud: dict) -> dict:
    """Apply 4° Gaussian noise + 5° quantization to AoA fields in-place."""
    uid = ud['user_id']
    if ud['aoa_az'] is not None:
        rng = np.random.RandomState(42 + uid * 1000)
        ud['aoa_az'] = np.round(
            (ud['aoa_az'] + AOA_NOISE_STD_DEG * rng.randn(len(ud['aoa_az'])))
            / AOA_QUANT_STEP_DEG) * AOA_QUANT_STEP_DEG
    if ud['aoa_el'] is not None:
        rng = np.random.RandomState(43 + uid * 1000)
        ud['aoa_el'] = np.round(
            (ud['aoa_el'] + AOA_NOISE_STD_DEG * rng.randn(len(ud['aoa_el'])))
            / AOA_QUANT_STEP_DEG) * AOA_QUANT_STEP_DEG
    return ud


def _ud_to_dataframe(ud: dict) -> pd.DataFrame:
    """Convert a loaded user dict to a DataFrame row."""
    n = len(ud['rss'])
    return pd.DataFrame({
        'user_id':         ud['user_id'],
        'step_index':      ud['step_index'],
        'rss':             ud['rss'],
        'sinr':            ud['sinr'],
        'aoa_azimuth':     ud['aoa_az'] if ud['aoa_az'] is not None
                           else np.full(n, np.nan),
        'aoa_elevation':   ud['aoa_el'] if ud['aoa_el'] is not None
                           else np.full(n, np.nan),
        'x_pos':           ud['x_pos'],
        'y_pos':           ud['y_pos'],
        'grid_point_id':   ud['grid_point_id'],
        'voronoi_cell_id': ud['voronoi_cell_id'],
        'n_antennas':      ud['device']['n_antennas'],
        'antenna_gain_db': ud['device']['antenna_gain_db'],
        'ue_height':       ud['device']['ue_height_m'],
    })


def load_all_users(data_dir: Path) -> pd.DataFrame:
    """Load all per-user .mat files into a combined DataFrame.

    Auto-detects the filename stem by scanning for user1_*.mat — works for
    any experiment name (voronoi_15x15, ne_bs_voronoi_15x15, etc.).
    """
    # Detect stem from user1_<stem>.mat
    candidates = sorted(data_dir.glob('user1_*.mat'))
    if not candidates:
        raise FileNotFoundError(
            f"No user1_*.mat files found in {data_dir}\n"
            f"  Contents: {[p.name for p in data_dir.iterdir() if p.suffix == '.mat']}"
        )
    stem = candidates[0].stem[len('user1_'):]   # e.g. 'ne_bs_voronoi_15x15'

    # Count how many userN_<stem>.mat files exist
    n_users = sum(1 for u in range(1, 20) if (data_dir / f'user{u}_{stem}.mat').exists())
    if n_users == 0:
        raise FileNotFoundError(f"No user files matched pattern user*_{stem}.mat in {data_dir}")

    frames = []
    for u in range(1, n_users + 1):
        mat_file = data_dir / f'user{u}_{stem}.mat'
        if not mat_file.exists():
            raise FileNotFoundError(f"Missing: {mat_file}")
        print(f"  Loading user {u}: {mat_file.name}")
        ud = load_user_file(mat_file)
        ud = _apply_aoa_noise(ud)
        udf = _ud_to_dataframe(ud)
        frames.append(udf)
        print(f"    user_id={ud['user_id']}, n={len(udf):,}, "
              f"n_ant={ud['device']['n_antennas']}, "
              f"gain={ud['device']['antenna_gain_db']:+.1f}dB, "
              f"h={ud['device']['ue_height_m']}m")
    return pd.concat(frames, ignore_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Train / test split — strictly chronological per user
# ─────────────────────────────────────────────────────────────────────────────

def make_split(df: pd.DataFrame, test_ratio: float = 0.2) -> pd.DataFrame:
    """Add 'split' column ('train'/'test') based on per-user chronological order."""
    df = df.copy()
    df['split'] = 'train'
    for uid in df['user_id'].unique():
        mask  = df['user_id'] == uid
        steps = df.loc[mask, 'step_index'].sort_values()
        n_total = len(steps)
        n_test  = int(np.floor(n_total * test_ratio))
        test_steps = steps.iloc[n_total - n_test:].values
        df.loc[mask & df['step_index'].isin(test_steps), 'split'] = 'test'

    # Verify no leakage per user
    for uid in df['user_id'].unique():
        train_steps = set(df.loc[(df['user_id'] == uid) & (df['split'] == 'train'), 'step_index'])
        test_steps  = set(df.loc[(df['user_id'] == uid) & (df['split'] == 'test'),  'step_index'])
        overlap = train_steps & test_steps
        assert len(overlap) == 0, f"Data leakage for user {uid}: {len(overlap)} shared steps"
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Feature engineering — history stacking (absolute and delta)
# ─────────────────────────────────────────────────────────────────────────────

def build_history_features(df: pd.DataFrame, h: int,
                            extra_cols=None,
                            include_aoa: bool = False) -> pd.DataFrame:
    """
    Absolute value stacking: [rss_t, sinr_t, ..., rss_{t-h}, sinr_{t-h}].
    First h rows per user are dropped (no full history).
    Optional extra_cols (constant per user) are appended once.
    """
    result_frames = []

    for uid in sorted(df['user_id'].unique()):
        udf = df[df['user_id'] == uid].sort_values('step_index').reset_index(drop=True)
        n  = len(udf)

        rss  = udf['rss'].values
        sinr = udf['sinr'].values

        cols = {}
        for lag in range(h + 1):
            cols[f'rss_lag{lag}']  = np.concatenate([np.full(lag, np.nan), rss [:n - lag]])
            cols[f'sinr_lag{lag}'] = np.concatenate([np.full(lag, np.nan), sinr[:n - lag]])
            if include_aoa:
                aoa_az = udf['aoa_azimuth'].values
                aoa_el = udf['aoa_elevation'].values
                cols[f'aoa_az_lag{lag}'] = np.concatenate([np.full(lag, np.nan), aoa_az[:n - lag]])
                cols[f'aoa_el_lag{lag}'] = np.concatenate([np.full(lag, np.nan), aoa_el[:n - lag]])

        feat_df = pd.DataFrame(cols, index=udf.index)
        valid   = feat_df.iloc[h:].copy()
        meta    = udf.iloc[h:].copy()

        valid = valid.reset_index(drop=True)
        meta  = meta.reset_index(drop=True)
        combined = pd.concat([meta, valid], axis=1)

        if extra_cols:
            for col in extra_cols:
                combined[f'feat_{col}'] = combined[col]

        result_frames.append(combined)

    return pd.concat(result_frames, ignore_index=True)


def build_delta_features(df: pd.DataFrame, h: int,
                          extra_cols=None,
                          include_aoa: bool = False) -> pd.DataFrame:
    """
    Delta representation: current absolute values + h first-difference lags.
      - Columns 0..D-1:  current absolute values (rss_lag0, sinr_lag0, ...)
      - Columns D..2D-1: delta1 = m_t - m_{t-1}   → rss_delta1, sinr_delta1, ...
      - ...
      - Columns hD..(h+1)D-1: delta_h
    Shape: (N, D*(h+1)) — same dimensionality as absolute stacking.
    First h rows per user are dropped.
    """
    result_frames = []

    for uid in sorted(df['user_id'].unique()):
        udf = df[df['user_id'] == uid].sort_values('step_index').reset_index(drop=True)
        n   = len(udf)

        rss  = udf['rss'].values
        sinr = udf['sinr'].values
        aoa_az = udf['aoa_azimuth'].values if include_aoa else None
        aoa_el = udf['aoa_elevation'].values if include_aoa else None

        cols = {}
        # Lag 0: current absolute values
        cols['rss_lag0']  = rss.copy()
        cols['sinr_lag0'] = sinr.copy()
        if include_aoa:
            cols['aoa_az_lag0'] = aoa_az.copy()
            cols['aoa_el_lag0'] = aoa_el.copy()

        # Lags 1..h: first differences  delta_k = m_{t-k+1} - m_{t-k}
        for k in range(1, h + 1):
            rss_prev  = np.concatenate([np.full(1, np.nan), rss[:-1]])   # rss_{t-1}
            sinr_prev = np.concatenate([np.full(1, np.nan), sinr[:-1]])
            # Shift k-1 more steps to get rss_{t-k}, rss_{t-k+1}
            # delta_k[t] = rss[t-(k-1)] - rss[t-k]
            lag_a = np.concatenate([np.full(k - 1, np.nan), rss[:n - (k - 1)]])   # rss_{t-(k-1)}
            lag_b = np.concatenate([np.full(k,     np.nan), rss[:n - k]])          # rss_{t-k}
            cols[f'rss_delta{k}']  = lag_a - lag_b

            lag_a = np.concatenate([np.full(k - 1, np.nan), sinr[:n - (k - 1)]])
            lag_b = np.concatenate([np.full(k,     np.nan), sinr[:n - k]])
            cols[f'sinr_delta{k}'] = lag_a - lag_b

            if include_aoa:
                lag_a = np.concatenate([np.full(k - 1, np.nan), aoa_az[:n - (k - 1)]])
                lag_b = np.concatenate([np.full(k,     np.nan), aoa_az[:n - k]])
                cols[f'aoa_az_delta{k}'] = lag_a - lag_b

                lag_a = np.concatenate([np.full(k - 1, np.nan), aoa_el[:n - (k - 1)]])
                lag_b = np.concatenate([np.full(k,     np.nan), aoa_el[:n - k]])
                cols[f'aoa_el_delta{k}'] = lag_a - lag_b

        feat_df  = pd.DataFrame(cols, index=udf.index)
        valid    = feat_df.iloc[h:].copy()
        meta     = udf.iloc[h:].copy()

        valid    = valid.reset_index(drop=True)
        meta     = meta.reset_index(drop=True)
        combined = pd.concat([meta, valid], axis=1)

        if extra_cols:
            for col in extra_cols:
                combined[f'feat_{col}'] = combined[col]

        result_frames.append(combined)

    return pd.concat(result_frames, ignore_index=True)


def get_feature_cols(h: int, extra_cols=None, include_aoa: bool = False,
                     mode: str = 'absolute') -> list:
    """Return ordered list of feature column names for history length h."""
    cols = []
    if mode == 'absolute':
        for lag in range(h + 1):
            cols += [f'rss_lag{lag}', f'sinr_lag{lag}']
            if include_aoa:
                cols += [f'aoa_az_lag{lag}', f'aoa_el_lag{lag}']
    else:  # delta
        cols += ['rss_lag0', 'sinr_lag0']
        if include_aoa:
            cols += ['aoa_az_lag0', 'aoa_el_lag0']
        for k in range(1, h + 1):
            cols += [f'rss_delta{k}', f'sinr_delta{k}']
            if include_aoa:
                cols += [f'aoa_az_delta{k}', f'aoa_el_delta{k}']
    if extra_cols:
        cols += [f'feat_{c}' for c in extra_cols]
    return cols


# ─────────────────────────────────────────────────────────────────────────────
# 4.  Grid point → position lookup
# ─────────────────────────────────────────────────────────────────────────────

def build_grid_lookup(df: pd.DataFrame) -> dict[int, tuple[float, float]]:
    """Build {grid_point_id -> (mean_x, mean_y)} from observed positions."""
    lookup = {}
    for gp, grp in df.groupby('grid_point_id'):
        lookup[int(gp)] = (grp['x_pos'].mean(), grp['y_pos'].mean())
    return lookup


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Models
# ─────────────────────────────────────────────────────────────────────────────

def get_model(model_name: str, n_classes: int):
    """Return a sklearn-compatible classifier."""
    if model_name == 'rf':
        return RandomForestClassifier(
            n_estimators=50, max_features='sqrt', max_depth=15,
            min_samples_leaf=20, random_state=42, n_jobs=1)
    elif model_name == 'xgboost':
        if not HAS_XGBOOST:
            raise RuntimeError("XGBoost not installed")
        return XGBClassifier(
            n_estimators=50, max_depth=5, learning_rate=0.15,
            subsample=0.8, colsample_bytree=0.8,
            use_label_encoder=False, eval_metric='mlogloss',
            random_state=42, n_jobs=2, verbosity=0)
    else:
        raise ValueError(f"Unknown model: {model_name}")


# ─────────────────────────────────────────────────────────────────────────────
# 6.  Evaluation helpers
# ─────────────────────────────────────────────────────────────────────────────

def compute_mae(y_true_ids: np.ndarray, y_pred_ids: np.ndarray,
                grid_lookup: dict) -> float:
    """Mean Euclidean distance (metres) between predicted and true grid points."""
    errors = []
    for t, p in zip(y_true_ids, y_pred_ids):
        tx, ty = grid_lookup.get(int(t), (0.0, 0.0))
        px, py = grid_lookup.get(int(p), (0.0, 0.0))
        errors.append(np.sqrt((tx - px) ** 2 + (ty - py) ** 2))
    return float(np.mean(errors))


def evaluate_split(y_true, y_pred, grid_lookup, label=''):
    """Return dict with accuracy and MAE."""
    acc = accuracy_score(y_true, y_pred) * 100.0
    mae = compute_mae(np.array(y_true), np.array(y_pred), grid_lookup)
    if label:
        print(f"    {label:30s}  acc={acc:5.1f}%  MAE={mae:.3f}m")
    return {'accuracy': acc, 'mae': mae}


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Single experiment runner
# ─────────────────────────────────────────────────────────────────────────────

def run_one_experiment(feat_df: pd.DataFrame,
                       feature_cols: list,
                       grid_lookup: dict,
                       model_name: str,
                       exp_label: str,
                       exclude_user=None) -> dict:
    """
    Train on 'train' split, evaluate on 'test' split.
    If exclude_user is set, that user is removed from training (cross-user test).
    """
    label_col = 'grid_point_id'

    all_labels = sorted(feat_df[label_col].unique())
    label2idx  = {lbl: i for i, lbl in enumerate(all_labels)}
    idx2label  = {i: lbl for lbl, i in label2idx.items()}

    train_mask = feat_df['split'] == 'train'
    test_mask  = feat_df['split'] == 'test'

    if exclude_user is not None:
        train_mask = train_mask & (feat_df['user_id'] != exclude_user)

    X_train = feat_df.loc[train_mask, feature_cols].values
    y_train = feat_df.loc[train_mask, label_col].map(label2idx).values
    X_test  = feat_df.loc[test_mask,  feature_cols].values
    y_test  = feat_df.loc[test_mask,  label_col].map(label2idx).values
    y_test_orig = feat_df.loc[test_mask, label_col].values

    model = get_model(model_name, len(all_labels))
    t0    = time.time()
    model.fit(X_train, y_train)
    train_sec = time.time() - t0

    y_pred_idx  = model.predict(X_test)
    y_pred_orig = np.array([idx2label[i] for i in y_pred_idx])

    overall = evaluate_split(y_test_orig, y_pred_orig, grid_lookup, label=exp_label)
    overall['train_time_s'] = round(train_sec, 2)

    # Per-user breakdown
    per_user = {}
    for uid in sorted(feat_df['user_id'].unique()):
        um = test_mask & (feat_df['user_id'] == uid)
        if um.sum() == 0:
            continue
        yt = feat_df.loc[um, label_col].values
        yp = y_pred_orig[((feat_df.loc[test_mask, 'user_id'] == uid)
                          .reset_index(drop=True)).values]
        per_user[uid] = evaluate_split(yt, yp, grid_lookup)

    # Per-Voronoi-cell breakdown
    per_cell = {}
    for cid in sorted(feat_df['voronoi_cell_id'].unique()):
        cm = test_mask & (feat_df['voronoi_cell_id'] == cid)
        if cm.sum() == 0:
            continue
        yt = feat_df.loc[cm, label_col].values
        yp = y_pred_orig[((feat_df.loc[test_mask, 'voronoi_cell_id'] == cid)
                          .reset_index(drop=True)).values]
        per_cell[int(cid)] = evaluate_split(yt, yp, grid_lookup)

    cm_matrix = confusion_matrix(y_test_orig, y_pred_orig, labels=all_labels)

    return {
        'overall':      overall,
        'per_user':     per_user,
        'per_cell':     per_cell,
        'cm':           cm_matrix,
        'cm_labels':    all_labels,
        'model':        model,
        'feature_cols': feature_cols,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8.  Registry-driven experiment runner
# ─────────────────────────────────────────────────────────────────────────────

def run_all_experiments(df: pd.DataFrame,
                        grid_lookup: dict,
                        models: list[str],
                        h_primary: int = 3,
                        run_only: list[str] = None) -> dict:
    """
    Run experiments from EXPERIMENTS registry + CROSS_USER_EXPERIMENTS.
    If run_only is given (list of keys), only those experiments run.
    """
    # Resolve h for each experiment (h>0 means use h_primary)
    def resolve_h(h): return h_primary if h > 0 else 0

    print("\n=== Data Summary ===")
    for uid, grp in df.groupby('user_id'):
        tr = (grp['split'] == 'train').sum()
        te = (grp['split'] == 'test').sum()
        dev = grp.iloc[0]
        print(f"  User {uid}: train={tr:,}  test={te:,}  "
              f"n_ant={int(dev.n_antennas)}  "
              f"gain={dev.antenna_gain_db:+.1f}dB  "
              f"h={dev.ue_height:.2f}m")
    cells = df['voronoi_cell_id'].value_counts().sort_index()
    print(f"  Voronoi cells: {cells.to_dict()}")
    print(f"  Grid classes: {df['grid_point_id'].nunique()}")

    results = {}
    # Cache (h, include_aoa, mode, extra_key) → (feat_df, feature_cols)
    feat_cache = {}

    def _get_feat(h, extra, aoa, mode):
        extra_key = tuple(extra) if extra else None
        ck = (h, aoa, mode, extra_key)
        if ck not in feat_cache:
            print(f"    [build features h={h}, aoa={aoa}, mode={mode}, "
                  f"extra={extra_key}]")
            if mode == 'delta':
                feat_df = build_delta_features(df, h, extra_cols=extra, include_aoa=aoa)
            else:
                feat_df = build_history_features(df, h, extra_cols=extra, include_aoa=aoa)
            feat_cols = get_feature_cols(h, extra_cols=extra, include_aoa=aoa, mode=mode)
            feat_cache[ck] = (feat_df, feat_cols)
        return feat_cache[ck]

    for model_name in models:
        if model_name == 'xgboost' and not HAS_XGBOOST:
            continue
        print(f"\n{'='*60}")
        print(f"Model: {model_name}")
        print(f"{'='*60}")
        results[model_name] = {}

        # ── Core experiments ──────────────────────────────────────────────────
        for exp_def in EXPERIMENTS:
            key = exp_def['key']
            if run_only is not None and key not in run_only:
                continue
            h    = resolve_h(exp_def['h'])
            extra = exp_def['extra']
            aoa   = exp_def['aoa']
            mode  = exp_def.get('mode', 'absolute')

            feat_df, feat_cols = _get_feat(h, extra, aoa, mode)
            print(f"\n--- {key} ---")
            results[model_name][key] = run_one_experiment(
                feat_df, feat_cols, grid_lookup, model_name, f"{key} {model_name}")

        # ── Cross-user experiments ────────────────────────────────────────────
        for cu_key, base_key in CROSS_USER_EXPERIMENTS.items():
            if run_only is not None and cu_key not in run_only:
                continue
            base_def = next((e for e in EXPERIMENTS if e['key'] == base_key), None)
            if base_def is None:
                continue
            h    = resolve_h(base_def['h'])
            extra = base_def['extra']
            aoa   = base_def['aoa']
            mode  = base_def.get('mode', 'absolute')

            feat_df, feat_cols = _get_feat(h, extra, aoa, mode)
            print(f"\n--- {cu_key} (train U1–U4, test U5) ---")
            results[model_name][cu_key] = run_one_experiment(
                feat_df, feat_cols, grid_lookup, model_name,
                f"{cu_key} {model_name}", exclude_user=5)

        # ── Learning curve h=0..MAX_HISTORY_CURVE (full run only) ────────────
        if run_only is None:
            print(f"\n--- Learning curve h=0..{MAX_HISTORY_CURVE} ---")
            lc = []
            for h_val in range(MAX_HISTORY_CURVE + 1):
                fdf, fc = _get_feat(h_val, None, False, 'absolute')
                res = run_one_experiment(fdf, fc, grid_lookup, model_name,
                                         f"  h={h_val} {model_name}")
                lc.append({'h': h_val,
                           'accuracy': res['overall']['accuracy'],
                           'mae':      res['overall']['mae']})
            results[model_name]['learning_curve'] = lc

    return results


# ─────────────────────────────────────────────────────────────────────────────
# 9.  Saving results
# ─────────────────────────────────────────────────────────────────────────────

def save_results(results: dict, df: pd.DataFrame, out_dir: Path,
                 models: list[str], h_primary: int,
                 append_mode: bool = False):
    """
    Save CSV summaries and experiment config JSON.
    When append_mode=True: read existing CSVs, replace rows for the new
    experiment keys, and write back. Otherwise overwrites.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_rows, pu_rows, pc_rows = [], [], []

    for model_name in models:
        if model_name not in results:
            continue
        for exp in sorted(results[model_name].keys()):
            if exp == 'learning_curve':
                continue
            o = results[model_name][exp]['overall']
            summary_rows.append({
                'model': model_name, 'experiment': exp,
                'accuracy_%': round(o['accuracy'], 2),
                'mae_m':      round(o['mae'], 4),
                'train_time_s': o.get('train_time_s'),
            })
            if not exp.startswith('cross_user_'):
                for uid, m in results[model_name][exp]['per_user'].items():
                    pu_rows.append({
                        'model': model_name, 'experiment': exp, 'user_id': uid,
                        'accuracy_%': round(m['accuracy'], 2),
                        'mae_m':      round(m['mae'], 4),
                    })
                for cid, m in results[model_name][exp]['per_cell'].items():
                    pc_rows.append({
                        'model': model_name, 'experiment': exp,
                        'voronoi_cell_id': cid,
                        'accuracy_%': round(m['accuracy'], 2),
                        'mae_m':      round(m['mae'], 4),
                    })

    def _write_csv(fname, rows):
        new_df = pd.DataFrame(rows)
        path   = out_dir / fname
        if append_mode and path.exists() and len(rows) > 0:
            existing = pd.read_csv(path)
            new_keys = new_df['experiment'].unique()
            existing = existing[~existing['experiment'].isin(new_keys)]
            pd.concat([existing, new_df], ignore_index=True).to_csv(path, index=False)
        else:
            new_df.to_csv(path, index=False)
        print(f"  Saved: {fname}")

    _write_csv('results_summary.csv',    summary_rows)
    _write_csv('per_user_breakdown.csv', pu_rows)
    _write_csv('per_cell_breakdown.csv', pc_rows)

    # ── Experiment config JSON ────────────────────────────────────────────────
    config_out = {
        'n_users': 5,
        'h_primary': h_primary,
        'max_history_curve': MAX_HISTORY_CURVE,
        'models': models,
        'train_test_split': '80/20 chronological per user',
        'naming_convention': {
            'BASE': 'RSS+SINR, h=0',
            'BASE_H': f'RSS+SINR absolute stacking h={h_primary}',
            'BASE_H_dp': f'BASE_H + device params',
            'BASE_H_uid': f'BASE_H + user_id',
            'BASE_A': 'RSS+SINR+AoA (4°/5° noise), h=0',
            'BASE_A_H': f'BASE_A absolute stacking h={h_primary}',
            'BASE_A_H_dp': 'BASE_A_H + device params',
        },
        'device_profiles': {
            'U1': {'n_antennas': 4, 'antenna_gain_db': 0.0,  'ue_height_m': 1.5, 'seed': 100},
            'U2': {'n_antennas': 2, 'antenna_gain_db': -2.0, 'ue_height_m': 1.5, 'seed': 200},
            'U3': {'n_antennas': 1, 'antenna_gain_db': -4.0, 'ue_height_m': 1.5, 'seed': 300},
            'U4': {'n_antennas': 4, 'antenna_gain_db': 0.0,  'ue_height_m': 1.5, 'seed': 400},
            'U5': {'n_antennas': 2, 'antenna_gain_db': -1.0, 'ue_height_m': 0.9, 'seed': 500},
        },
        'n_classes': df['grid_point_id'].nunique(),
        'total_samples': len(df),
    }
    with open(out_dir / 'experiment_config.json', 'w') as f:
        json.dump(config_out, f, indent=2)
    print(f"  Saved: experiment_config.json")


# ─────────────────────────────────────────────────────────────────────────────
# 10.  Data volume sweep  (BASE_H absolute vs BASE_H_delta)
# ─────────────────────────────────────────────────────────────────────────────

def run_data_volume_sweep(df: pd.DataFrame, grid_lookup: dict,
                           models: list[str],
                           h: int = 3,
                           fractions: tuple = (0.10, 0.25, 0.50, 1.00)) -> pd.DataFrame:
    """
    Compare BASE_H (absolute) vs BASE_H_delta at varying training fractions.
    Subsamples the training set AFTER the chronological split (first X% of
    training rows per user, preserving chronological order).
    The test set is always 100%.
    """
    records = []

    for model_name in models:
        if model_name == 'xgboost' and not HAS_XGBOOST:
            continue

        for mode, exp_key in [('absolute', 'BASE_H'), ('delta', 'BASE_H_delta')]:
            if mode == 'delta':
                feat_df = build_delta_features(df, h=h)
            else:
                feat_df = build_history_features(df, h=h)
            feat_cols = get_feature_cols(h=h, mode=mode)

            for frac in fractions:
                # Subsample training rows chronologically per user
                if frac < 1.0:
                    train_keep_idx = []
                    for uid in feat_df['user_id'].unique():
                        mask = (feat_df['user_id'] == uid) & (feat_df['split'] == 'train')
                        train_rows = feat_df[mask].sort_values('step_index')
                        n_keep = max(1, int(len(train_rows) * frac))
                        train_keep_idx.extend(train_rows.index[:n_keep].tolist())
                    test_idx = feat_df[feat_df['split'] == 'test'].index.tolist()
                    run_df = feat_df.loc[train_keep_idx + test_idx].copy()
                else:
                    run_df = feat_df

                # Assert no leakage
                for uid in run_df['user_id'].unique():
                    tr_s = run_df.loc[(run_df['user_id'] == uid) & (run_df['split'] == 'train'),
                                      'step_index']
                    te_s = run_df.loc[(run_df['user_id'] == uid) & (run_df['split'] == 'test'),
                                      'step_index']
                    if len(tr_s) > 0 and len(te_s) > 0:
                        assert tr_s.max() < te_s.min(), \
                            f"Leakage at frac={frac}, user={uid}"

                print(f"  {exp_key} {model_name} frac={frac:.0%}  "
                      f"train={( run_df['split']=='train').sum():,}")
                res = run_one_experiment(run_df, feat_cols, grid_lookup, model_name,
                                         f"  {exp_key} {model_name} {frac:.0%}")
                records.append({
                    'model':         model_name,
                    'experiment':    exp_key,
                    'data_fraction': frac,
                    'accuracy_%':    round(res['overall']['accuracy'], 2),
                    'mae_m':         round(res['overall']['mae'], 4),
                })

    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# 11.  Environmental variability experiment
# ─────────────────────────────────────────────────────────────────────────────

def run_env_variability(env_dir: Path, grid_lookup: dict,
                         models: list[str], h: int = 3) -> pd.DataFrame:
    """
    Load 3 single-user env runs (run1..3_voronoi_15x15.mat) and compare:
      - cross_env split: train on run1+run2, test on run3
      - single_run split: 80/20 chronological on run1 only

    Experiments: BASE (h=0), BASE_H (h=3, absolute), BASE_H_delta (h=3, delta).
    """
    records = []

    # ── Load 3 runs ────────────────────────────────────────────────────────────
    run_dfs = []
    offset  = 0   # cumulative step_index offset to avoid interleaving when concatenated
    for i in range(1, 4):
        mat_path = env_dir / f'run{i}_voronoi_15x15.mat'
        if not mat_path.exists():
            raise FileNotFoundError(f"Missing env run file: {mat_path}")
        print(f"  Loading env run {i}: {mat_path.name}")
        ud  = load_user_file(mat_path)
        ud  = _apply_aoa_noise(ud)
        udf = _ud_to_dataframe(ud)
        udf['run_id']    = i
        # Offset step_index so run1, run2, run3 have non-overlapping indices.
        # This ensures build_history_features sorts chronologically per run
        # without interleaving samples from different runs.
        udf['step_index'] = udf['step_index'] + offset
        offset += udf['step_index'].max() + 1
        run_dfs.append(udf)

    # ── Build two splits ───────────────────────────────────────────────────────
    # Cross-env: train=run1+run2, test=run3
    train_df = pd.concat([run_dfs[0], run_dfs[1]], ignore_index=True)
    train_df['split'] = 'train'
    test_df  = run_dfs[2].copy()
    test_df['split'] = 'test'
    cross_env_df = pd.concat([train_df, test_df], ignore_index=True)

    # Single-run reference: 80/20 chronological on run1
    single_run_df = make_split(run_dfs[0], test_ratio=0.2)

    splits_map = {
        'cross_env':  cross_env_df,
        'single_run': single_run_df,
    }

    for model_name in models:
        if model_name == 'xgboost' and not HAS_XGBOOST:
            continue
        print(f"\n{'='*60}\nEnv Variability — Model: {model_name}\n{'='*60}")

        for split_type, split_df in splits_map.items():
            for exp_key, h_val, mode in [
                ('BASE',         0, 'absolute'),
                ('BASE_H',       h, 'absolute'),
                ('BASE_H_delta', h, 'delta'),
            ]:
                if mode == 'delta':
                    feat_df = build_delta_features(split_df, h=h_val)
                else:
                    feat_df = build_history_features(split_df, h=h_val)
                feat_cols = get_feature_cols(h=h_val, mode=mode)

                print(f"\n  {split_type} | {exp_key}")
                res = run_one_experiment(feat_df, feat_cols, grid_lookup, model_name,
                                         f"  {split_type}/{exp_key} {model_name}")
                records.append({
                    'model':      model_name,
                    'experiment': exp_key,
                    'split_type': split_type,
                    'accuracy_%': round(res['overall']['accuracy'], 2),
                    'mae_m':      round(res['overall']['mae'], 4),
                })

    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# 12.  Visualisations
# ─────────────────────────────────────────────────────────────────────────────

def _read_bs_geometry(data_dir: Path):
    """Return (bs_xy, ibs_xys) by reading the JSONC config for data_dir.

    Tries (in order):
      1. data_generation_config.jsonc inside data_dir (single-user experiments)
      2. config name from experiment_info.mat → configs/ directory (multi-user)
    Returns (None, None) if neither is available.
    """
    def _parse_cfg(cfg):
        bs = cfg.get('base_station', {}).get('position', [])
        bs_xy = (float(bs[0]), float(bs[1])) if len(bs) >= 2 else None
        ibs_cfg = cfg.get('base_station', {}).get('interferers', {})
        ibs_xys = None
        if ibs_cfg.get('enabled') and ibs_cfg.get('positions'):
            ibs_xys = [(float(p[0]), float(p[1])) for p in ibs_cfg['positions']]
        return bs_xy, ibs_xys

    # Option 1: config file inside data_dir
    for cfg_name in ('data_generation_config.jsonc', 'config.jsonc', 'config.json'):
        p = data_dir / cfg_name
        if p.exists():
            try:
                from utils.read_jsonc import read_jsonc as _rjsonc
                return _parse_cfg(_rjsonc(p))
            except Exception:
                pass

    # Option 2: experiment_info.mat → look up config name → configs/
    try:
        import scipy.io as _sio
        mat = _sio.loadmat(str(data_dir / 'experiment_info.mat'), squeeze_me=True)
        ei = mat.get('experiment_info')
        if ei is not None:
            config_name = str(ei['config_name'].flat[0])
            cfg_path = EXPERIMENT_ROOT / 'configs' / config_name
            if cfg_path.exists():
                from utils.read_jsonc import read_jsonc as _rjsonc
                return _parse_cfg(_rjsonc(cfg_path))
    except Exception:
        pass

    return None, None


def _adaptive_vmax(values) -> float:
    """Compute a colormap ceiling that scales with the data distribution.

    Uses max(p90, median * 4) so that:
    - High-accuracy experiments (median ~0.2 m) get a 0–~0.8 m scale
      instead of being compressed into one colour by a few outliers.
    - Low-accuracy experiments (median ~5 m) still capture the spread.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr) & (arr >= 0)]
    if len(arr) == 0:
        return 1.0
    return float(max(np.percentile(arr, 90), np.median(arr) * 4, 0.1))


def plot_accuracy_bar(results: dict, models: list[str], out_dir: Path, h_primary: int):
    """Bar chart: accuracy across core 7 experiments, grouped by model."""
    if not HAS_MATPLOTLIB:
        return
    exps   = CORE_DISPLAY_EXPERIMENTS
    labels = [
        f'BASE\n(h=0)',
        f'BASE_H\n(h={h_primary})',
        f'BASE_H_dp\n(h+dev)',
        f'BASE_H_uid\n(h+uid)',
        f'BASE_A\n(h=0+AoA)',
        f'BASE_A_H\n(h+AoA)',
        f'BASE_A_H_dp\n(h+AoA+dev)',
    ]
    x     = np.arange(len(exps))
    width = 0.35

    fig, ax = plt.subplots(figsize=(13, 5))
    colors  = ['#2196F3', '#F44336', '#4CAF50', '#FF9800']
    used_models = [m for m in models if m in results]

    for mi, model_name in enumerate(used_models):
        gap = (mi - (len(used_models) - 1) / 2) * width
        vals = []
        for exp in exps:
            v = results[model_name].get(exp, {}).get('overall', {}).get('accuracy', 0.0)
            vals.append(v)
        bars = ax.bar(x + gap, vals, width * 0.85,
                      label=model_name.upper(), color=colors[mi % len(colors)],
                      alpha=0.85)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                        f'{v:.1f}%', ha='center', va='bottom', fontsize=7)

    # Vertical divider between non-AoA and AoA experiments
    ax.axvline(x=3.5, color='gray', linestyle='--', linewidth=1, alpha=0.6)
    ax.text(3.6, 95, 'AoA added →', fontsize=8, color='gray', va='top')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel('Classification Accuracy (%)')
    ax.set_title(f'Multi-User Experiment: Accuracy Comparison (core experiments)')
    ax.legend()
    ax.set_ylim(0, 100)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    path = out_dir / 'accuracy_bar_chart.png'
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: accuracy_bar_chart.png")


def plot_per_user_heatmap(results: dict, models: list[str], out_dir: Path, h_primary: int):
    """Heatmap: per-user accuracy across core 7 experiments (for each model)."""
    if not HAS_MATPLOTLIB:
        return
    exps = [e for e in CORE_DISPLAY_EXPERIMENTS if any(
        e in results.get(m, {}) for m in models)]
    user_ids = sorted({uid for m in models if m in results
                       for exp in exps if exp in results[m]
                       for uid in results[m][exp]['per_user']})

    xlabels = [
        f'BASE\nh=0', f'BASE_H\nh={h_primary}', f'BASE_H_dp\n+dev',
        f'BASE_H_uid\n+uid', f'BASE_A\nh=0\n+AoA', f'BASE_A_H\nh+AoA',
        f'BASE_A_H_dp\nh+AoA\n+dev',
    ]

    for model_name in models:
        if model_name not in results:
            continue
        mat = np.zeros((len(user_ids), len(exps)))
        for ei, exp in enumerate(exps):
            for ui, uid in enumerate(user_ids):
                mat[ui, ei] = results[model_name].get(exp, {}) \
                                              .get('per_user', {}) \
                                              .get(uid, {}) \
                                              .get('accuracy', 0.0)

        fig, ax = plt.subplots(figsize=(12, 4))
        im = ax.imshow(mat, cmap='YlGnBu', vmin=0, vmax=100, aspect='auto')
        plt.colorbar(im, ax=ax, label='Accuracy (%)')
        ax.set_xticks(range(len(exps)))
        ax.set_xticklabels(xlabels[:len(exps)], fontsize=8)
        ax.set_yticks(range(len(user_ids)))
        ax.set_yticklabels([f'U{u}' for u in user_ids])
        for ui in range(len(user_ids)):
            for ei in range(len(exps)):
                ax.text(ei, ui, f'{mat[ui,ei]:.1f}', ha='center', va='center',
                        fontsize=8, color='black' if mat[ui,ei] < 60 else 'white')
        # Divider between non-AoA and AoA columns
        ax.axvline(x=3.5, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
        ax.set_title(f'Per-User Accuracy — {model_name.upper()}')
        fig.tight_layout()
        path = out_dir / f'per_user_heatmap_{model_name}.png'
        fig.savefig(path, dpi=150)
        plt.close(fig)
        print(f"  Saved: per_user_heatmap_{model_name}.png")


def plot_mae_bar(mae_df: pd.DataFrame, models: list[str], out_dir: Path, h_primary: int):
    """Bar chart: MAE across core experiments, grouped by model.

    mae_df must have columns: model, experiment, mae_m
    Compatible with both in-memory results and results_summary.csv.
    """
    if not HAS_MATPLOTLIB:
        return
    exps   = CORE_DISPLAY_EXPERIMENTS
    labels = [
        f'BASE\n(h=0)',
        f'BASE_H\n(h={h_primary})',
        f'BASE_H_dp\n(h+dev)',
        f'BASE_H_uid\n(h+uid)',
        f'BASE_A\n(h=0+AoA)',
        f'BASE_A_H\n(h+AoA)',
        f'BASE_A_H_dp\n(h+AoA+dev)',
    ]
    x      = np.arange(len(exps))
    width  = 0.35
    colors = ['#2196F3', '#F44336', '#4CAF50', '#FF9800']

    fig, ax = plt.subplots(figsize=(13, 5))
    used_models = [m for m in models if m in mae_df['model'].values]

    for mi, model_name in enumerate(used_models):
        gap  = (mi - (len(used_models) - 1) / 2) * width
        vals = []
        for exp in exps:
            row = mae_df[(mae_df['model'] == model_name) & (mae_df['experiment'] == exp)]
            vals.append(float(row['mae_m'].iloc[0]) if len(row) else 0.0)
        bars = ax.bar(x + gap, vals, width * 0.85,
                      label=model_name.upper(), color=colors[mi % len(colors)],
                      alpha=0.85)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                        f'{v:.2f}', ha='center', va='bottom', fontsize=7)

    ax.axvline(x=3.5, color='gray', linestyle='--', linewidth=1, alpha=0.6)
    ax.text(3.6, ax.get_ylim()[1] * 0.95 if ax.get_ylim()[1] > 0 else 1,
            'AoA added →', fontsize=8, color='gray', va='top')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel('Mean Absolute Error (m)')
    ax.set_title('Multi-User Experiment: MAE Comparison (core experiments, lower is better)')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    path = out_dir / 'mae_bar_chart.png'
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: mae_bar_chart.png")


def plot_per_user_mae_heatmap(pu_df: pd.DataFrame, models: list[str],
                               out_dir: Path, h_primary: int):
    """Heatmap: per-user MAE across core experiments (for each model).

    pu_df must have columns: model, experiment, user_id, mae_m
    Compatible with both in-memory results and per_user_breakdown.csv.
    """
    if not HAS_MATPLOTLIB:
        return
    exps = [e for e in CORE_DISPLAY_EXPERIMENTS
            if any(len(pu_df[(pu_df['model'] == m) & (pu_df['experiment'] == e)]) > 0
                   for m in models)]
    user_ids = sorted(pu_df['user_id'].unique())

    xlabels = [
        f'BASE\nh=0', f'BASE_H\nh={h_primary}', f'BASE_H_dp\n+dev',
        f'BASE_H_uid\n+uid', f'BASE_A\nh=0\n+AoA', f'BASE_A_H\nh+AoA',
        f'BASE_A_H_dp\nh+AoA\n+dev',
    ]

    for model_name in models:
        if model_name not in pu_df['model'].values:
            continue
        mdf = pu_df[pu_df['model'] == model_name]
        mat = np.zeros((len(user_ids), len(exps)))
        for ei, exp in enumerate(exps):
            for ui, uid in enumerate(user_ids):
                row = mdf[(mdf['experiment'] == exp) & (mdf['user_id'] == uid)]
                mat[ui, ei] = float(row['mae_m'].iloc[0]) if len(row) else 0.0

        vmax = np.percentile(mat[mat > 0], 95) if mat.max() > 0 else 1.0
        fig, ax = plt.subplots(figsize=(12, 4))
        im = ax.imshow(mat, cmap='RdYlGn_r', vmin=0, vmax=vmax, aspect='auto')
        plt.colorbar(im, ax=ax, label='MAE (m)')
        ax.set_xticks(range(len(exps)))
        ax.set_xticklabels(xlabels[:len(exps)], fontsize=8)
        ax.set_yticks(range(len(user_ids)))
        ax.set_yticklabels([f'U{u}' for u in user_ids])
        for ui in range(len(user_ids)):
            for ei in range(len(exps)):
                ax.text(ei, ui, f'{mat[ui,ei]:.2f}', ha='center', va='center',
                        fontsize=8, color='black')
        ax.axvline(x=3.5, color='blue', linestyle='--', linewidth=1.5, alpha=0.7)
        ax.set_title(f'Per-User MAE — {model_name.upper()} (lower is better)')
        fig.tight_layout()
        path = out_dir / f'per_user_mae_heatmap_{model_name}.png'
        fig.savefig(path, dpi=150)
        plt.close(fig)
        print(f"  Saved: per_user_mae_heatmap_{model_name}.png")


def plot_voronoi_mae_map(results: dict, df: pd.DataFrame,
                         models: list[str], out_dir: Path, h_primary: int,
                         grid_lookup: dict = None,
                         data_dir: Path = None,
                         exp_key: str = 'BASE_H',
                         out_filename: str = None):
    """Per-grid-point MAE scatter map, derived from in-memory confusion matrix.

    MAE[t] = sum_p( cm[t,p] * dist(t,p) ) / sum_p( cm[t,p] )
    Uses the same Voronoi background as plot_voronoi_accuracy_map.
    """
    if not HAS_MATPLOTLIB:
        return
    best_model = models[0] if models else None
    if best_model not in results or exp_key not in results[best_model]:
        return
    if out_filename is None:
        out_filename = f'voronoi_mae_map_{exp_key}.png'

    import matplotlib.colors as mcolors
    from scipy.spatial.distance import cdist as _cdist

    CELL_COLORS = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']

    cm_mat  = results[best_model][exp_key]['cm']
    labels  = results[best_model][exp_key]['cm_labels']

    # Build position lookup if not provided
    if grid_lookup is None:
        grid_lookup = build_grid_lookup(df)

    # Per-grid-point MAE from confusion matrix rows
    mae_per_point = {}
    for i, t in enumerate(labels):
        row   = cm_mat[i, :].astype(float)
        total = row.sum()
        if total == 0:
            continue
        tx, ty = grid_lookup.get(int(t), (0.0, 0.0))
        weighted = sum(
            row[j] * np.sqrt((tx - grid_lookup.get(int(labels[j]), (0.0, 0.0))[0]) ** 2 +
                             (ty - grid_lookup.get(int(labels[j]), (0.0, 0.0))[1]) ** 2)
            for j in range(len(labels))
        )
        mae_per_point[t] = weighted / total

    gp_df = df.groupby('grid_point_id').agg(
        x_pos=('x_pos', 'mean'),
        y_pos=('y_pos', 'mean'),
        voronoi_cell_id=('voronoi_cell_id', lambda s: int(s.mode()[0]))
    ).reset_index()

    pos_lookup     = {int(r.grid_point_id): (r.x_pos, r.y_pos) for r in gp_df.itertuples()}
    voronoi_lookup = {int(r.grid_point_id): r.voronoi_cell_id  for r in gp_df.itertuples()}
    cell_ids = sorted(gp_df['voronoi_cell_id'].unique())
    n_cells  = len(cell_ids)

    voronoi_centers = None
    if data_dir is not None:
        try:
            import scipy.io as _sio
            user1_candidates = sorted(data_dir.glob('user1_*.mat'))
            if user1_candidates:
                mat1 = _sio.loadmat(str(user1_candidates[0]),
                                    squeeze_me=True, struct_as_record=False)
                if 'voronoi_centers' in mat1:
                    vc = np.array(mat1['voronoi_centers'], dtype=float)
                    voronoi_centers = vc.reshape(-1, 2) if vc.ndim == 1 else vc
        except Exception:
            pass
    if voronoi_centers is None or len(voronoi_centers) != n_cells:
        voronoi_centers = np.array([
            [gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'x_pos'].mean(),
             gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'y_pos'].mean()]
            for cid in cell_ids
        ])

    pad  = 1.5
    x_min = gp_df['x_pos'].min() - pad;  x_max = gp_df['x_pos'].max() + pad
    y_min = gp_df['y_pos'].min() - pad;  y_max = gp_df['y_pos'].max() + pad
    xx, yy = np.meshgrid(np.linspace(x_min, x_max, 400),
                         np.linspace(y_min, y_max, 400))
    mesh_pts      = np.column_stack([xx.ravel(), yy.ravel()])
    mesh_cell_idx = np.argmin(_cdist(mesh_pts, voronoi_centers),
                              axis=1).reshape(xx.shape)
    cell_cmap = mcolors.ListedColormap(CELL_COLORS[:n_cells])

    xs, ys, cs = [], [], []
    for gp, (x, y) in pos_lookup.items():
        xs.append(x); ys.append(y)
        cs.append(mae_per_point.get(gp, 0.0))

    vmax = _adaptive_vmax(cs) if cs else 1.0
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pcolormesh(xx, yy, mesh_cell_idx, cmap=cell_cmap, alpha=0.15,
                  vmin=-0.5, vmax=n_cells - 0.5, shading='auto', zorder=0)
    ax.contour(xx, yy, mesh_cell_idx, levels=np.arange(0.5, n_cells),
               colors='#555555', linewidths=1.5, zorder=1, alpha=0.8)
    sc = ax.scatter(xs, ys, c=cs, cmap='RdYlGn_r', vmin=0, vmax=vmax,
                    s=60, alpha=0.9, edgecolors='none', zorder=3)
    plt.colorbar(sc, ax=ax, label='Per-grid-point MAE (m)')

    cell_centroids = [
        np.array([gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'x_pos'].mean(),
                  gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'y_pos'].mean()])
        for cid in cell_ids
    ]
    for i, cid in enumerate(cell_ids):
        cx, cy = cell_centroids[i]
        ax.text(cx, cy, f'C{cid}', ha='center', va='center',
                fontsize=9, fontweight='bold', color=CELL_COLORS[i % len(CELL_COLORS)],
                zorder=8, alpha=0.6)

    bs_xy, ibs_xys = _read_bs_geometry(data_dir) if data_dir else (None, None)
    if bs_xy is not None:
        ax.scatter([bs_xy[0]], [bs_xy[1]], marker='^', s=300, c='blue', zorder=6,
                   edgecolors='white', linewidths=1.5, label='Serving BS')
    if ibs_xys:
        ax.scatter([p[0] for p in ibs_xys], [p[1] for p in ibs_xys],
                   marker='x', s=150, c='red', zorder=6, linewidths=2,
                   label='Interferers')

    overall_mae = float(np.mean(cs)) if cs else 0.0
    ax.set_title(f'MAE per grid point — {exp_key} ({best_model})\nOverall MAE = {overall_mae:.3f} m',
                 fontsize=11)
    ax.set_xlabel('X (m)');  ax.set_ylabel('Y (m)')
    ax.set_aspect('equal')
    if bs_xy is not None or ibs_xys:
        ax.legend(fontsize=9)
    fig.tight_layout()
    path = out_dir / out_filename
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_filename}")


def plot_learning_curve(results: dict, models: list[str], out_dir: Path):
    """Accuracy vs history length h=0..MAX_HISTORY_CURVE."""
    if not HAS_MATPLOTLIB:
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    colors  = ['#2196F3', '#F44336']
    markers = ['o', 's']

    for mi, model_name in enumerate(models):
        if model_name not in results or 'learning_curve' not in results[model_name]:
            continue
        lc  = results[model_name]['learning_curve']
        hs  = [entry['h'] for entry in lc]
        acc = [entry['accuracy'] for entry in lc]
        ax.plot(hs, acc, marker=markers[mi % 2], color=colors[mi % 2],
                label=model_name.upper(), linewidth=2, markersize=6)
        for h_val, a in zip(hs, acc):
            ax.annotate(f'{a:.1f}%', xy=(h_val, a), xytext=(0, 6),
                        textcoords='offset points', ha='center', fontsize=8)

    ax.set_xlabel('History length h')
    ax.set_ylabel('Classification Accuracy (%)')
    ax.set_title('Multi-User: Accuracy vs. Transition History Length')
    ax.set_xticks(range(MAX_HISTORY_CURVE + 1))
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    path = out_dir / 'learning_curve.png'
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: learning_curve.png")


def plot_confusion_matrix(results: dict, models: list[str], out_dir: Path, n_classes: int):
    """Confusion matrix for BASE_H of the first model."""
    if not HAS_MATPLOTLIB:
        return
    best_model = models[0] if models else None
    if best_model not in results or 'BASE_H' not in results[best_model]:
        return

    cm     = results[best_model]['BASE_H']['cm']
    labels = results[best_model]['BASE_H']['cm_labels']

    cm_norm = cm.astype(float)
    row_sums = cm_norm.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    cm_norm = cm_norm / row_sums * 100.0

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(cm_norm, cmap='Blues', vmin=0, vmax=100, aspect='auto')
    plt.colorbar(im, ax=ax, label='Recall (%)')
    ax.set_title(f'Confusion Matrix — {best_model.upper()} BASE_H\n'
                 f'(row-normalised, {n_classes} classes)')
    ax.set_xlabel('Predicted grid point')
    ax.set_ylabel('True grid point')
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    path = out_dir / 'confusion_matrix_BASE_H.png'
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: confusion_matrix_BASE_H.png")


def plot_voronoi_accuracy_map(results: dict, df: pd.DataFrame,
                               models: list[str], out_dir: Path, h_primary: int,
                               data_dir: Path = None,
                               voronoi_names: list = None,
                               voronoi_centers_override: np.ndarray = None,
                               exp_key: str = 'BASE_H',
                               out_filename: str = 'voronoi_accuracy_map.png'):
    """Per-grid-point accuracy with Voronoi cell segmentation and labels."""
    if not HAS_MATPLOTLIB:
        return
    best_model = models[0] if models else None
    exp = exp_key
    if best_model not in results or exp not in results[best_model]:
        return

    import matplotlib.colors as mcolors
    from scipy.spatial.distance import cdist as _cdist

    CELL_COLORS = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']

    gp_df = df.groupby('grid_point_id').agg(
        x_pos=('x_pos', 'mean'),
        y_pos=('y_pos', 'mean'),
        voronoi_cell_id=('voronoi_cell_id', lambda s: int(s.mode()[0]))
    ).reset_index()

    pos_lookup     = {int(r.grid_point_id): (r.x_pos, r.y_pos)
                      for r in gp_df.itertuples()}
    voronoi_lookup = {int(r.grid_point_id): r.voronoi_cell_id
                      for r in gp_df.itertuples()}

    cell_ids = sorted(gp_df['voronoi_cell_id'].unique())
    n_cells  = len(cell_ids)

    voronoi_centers = voronoi_centers_override
    _voronoi_names  = voronoi_names
    if (voronoi_centers is None or _voronoi_names is None) and data_dir is not None:
        try:
            import scipy.io as _sio
            user1_candidates = sorted(data_dir.glob('user1_*.mat'))
            if user1_candidates:
                mat1 = _sio.loadmat(str(user1_candidates[0]),
                                    squeeze_me=True, struct_as_record=False)
                if 'voronoi_centers' in mat1 and voronoi_centers is None:
                    vc = np.array(mat1['voronoi_centers'], dtype=float)
                    voronoi_centers = vc.reshape(-1, 2) if vc.ndim == 1 else vc
                if 'voronoi_names' in mat1 and _voronoi_names is None:
                    vn = mat1['voronoi_names']
                    _voronoi_names = [str(v) for v in vn] if hasattr(vn, '__len__') else None
        except Exception:
            pass

    if voronoi_centers is None or len(voronoi_centers) != n_cells:
        voronoi_centers = np.array([
            [gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'x_pos'].mean(),
             gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'y_pos'].mean()]
            for cid in cell_ids
        ])
    if _voronoi_names is None or len(_voronoi_names) != n_cells:
        _voronoi_names = [f'C{cid}' for cid in cell_ids]

    cell_centroids = [
        np.array([gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'x_pos'].mean(),
                  gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'y_pos'].mean()])
        for cid in cell_ids
    ]

    pad = 1.5
    x_min, x_max = gp_df['x_pos'].min() - pad, gp_df['x_pos'].max() + pad
    y_min, y_max = gp_df['y_pos'].min() - pad, gp_df['y_pos'].max() + pad
    xx, yy = np.meshgrid(np.linspace(x_min, x_max, 400),
                         np.linspace(y_min, y_max, 400))
    mesh_pts = np.column_stack([xx.ravel(), yy.ravel()])
    mesh_cell_idx = np.argmin(_cdist(mesh_pts, voronoi_centers),
                              axis=1).reshape(xx.shape)
    cell_cmap = mcolors.ListedColormap(CELL_COLORS[:n_cells])

    cm_mat   = results[best_model][exp]['cm']
    labels   = results[best_model][exp]['cm_labels']
    cm_diag  = np.diag(cm_mat).astype(float)
    row_total = cm_mat.sum(axis=1).astype(float)
    row_total[row_total == 0] = 1
    grid_acc = {lbl: (cm_diag[i] / row_total[i]) * 100
                for i, lbl in enumerate(labels)}

    xs, ys, cs = [], [], []
    for gp, (x, y) in pos_lookup.items():
        xs.append(x); ys.append(y)
        cs.append(grid_acc.get(gp, 0.0))

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pcolormesh(xx, yy, mesh_cell_idx, cmap=cell_cmap, alpha=0.15,
                  vmin=-0.5, vmax=n_cells - 0.5, shading='auto', zorder=0)
    ax.contour(xx, yy, mesh_cell_idx, levels=np.arange(0.5, n_cells),
               colors='#555555', linewidths=1.5, zorder=1, alpha=0.8)
    sc = ax.scatter(xs, ys, c=cs, cmap='RdYlGn', vmin=0, vmax=100,
                    s=60, alpha=0.9, edgecolors='none', zorder=3)
    plt.colorbar(sc, ax=ax, label='Per-grid-point accuracy (%)')

    for i, cid in enumerate(cell_ids):
        color = CELL_COLORS[i % len(CELL_COLORS)]
        name  = _voronoi_names[i]
        cx, cy = cell_centroids[i]
        ax.text(cx, cy, name, ha='center', va='center',
                fontsize=9, fontweight='bold', color=color, zorder=8,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                          alpha=0.65, edgecolor=color, linewidth=1.2))

    bs_xy, ibs_xys = _read_bs_geometry(data_dir) if data_dir else (None, None)
    if bs_xy is not None:
        ax.scatter([bs_xy[0]], [bs_xy[1]], marker='^', s=300, c='blue', zorder=6,
                   edgecolors='white', linewidths=1.5, label='Serving BS')
    if ibs_xys:
        ax.scatter([p[0] for p in ibs_xys], [p[1] for p in ibs_xys],
                   marker='x', s=150, c='red', zorder=6, linewidths=2,
                   label='Interferers')

    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.set_title(f'Per-Grid-Point Accuracy ({best_model.upper()} {exp})\n'
                 f'Multi-user 15×15 Voronoi — Voronoi cell segmentation')
    ax.set_aspect('equal')
    ax.legend(fontsize=9)
    ax.grid(alpha=0.15)
    fig.tight_layout()
    path = out_dir / out_filename
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_filename}")


# ─────────────────────────────────────────────────────────────────────────────
# 13.  Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Multi-user heterogeneous localization pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Full run:
  python multi_user_pipeline.py --data-dir <path>

  # Add only new baselines, append to existing CSVs:
  python multi_user_pipeline.py --data-dir <path> \\
      --run-only BASE_dp BASE_uid BASE_A_dp BASE_A_uid --append-results

  # Data volume sweep:
  python multi_user_pipeline.py --data-dir <path> --data-volume-sweep

  # Env variability:
  python multi_user_pipeline.py --data-dir <path> --env-dir <path>
""")
    parser.add_argument('--data-dir', required=True,
                        help='Directory containing user1..user5_voronoi_15x15.mat')
    parser.add_argument('--models', nargs='+', default=['xgboost', 'rf'],
                        choices=['xgboost', 'rf'],
                        help='Models to run (default: xgboost rf)')
    parser.add_argument('--history', type=int, default=HISTORY_PRIMARY,
                        help=f'Primary history length (default: {HISTORY_PRIMARY})')
    parser.add_argument('--out-dir', default=None,
                        help='Output directory (default: results/multi_user_voronoi_15x15/)')
    parser.add_argument('--run-only', nargs='+', default=None,
                        help='Run only these experiment keys (e.g. BASE_dp BASE_uid)')
    parser.add_argument('--append-results', action='store_true',
                        help='Append new rows to existing CSVs instead of overwriting')
    parser.add_argument('--data-volume-sweep', action='store_true',
                        help='Run BASE_H vs BASE_H_delta data volume sweep')
    parser.add_argument('--env-dir', default=None,
                        help='Path to env variability .mat files (run1..3_voronoi_15x15.mat)')
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Error: data directory not found: {data_dir}")
        sys.exit(1)

    out_dir = Path(args.out_dir) if args.out_dir else \
              RESULTS_ROOT / 'multi_user_voronoi_15x15'
    csv_dir = out_dir / 'csvs'
    acc_dir = out_dir / 'images' / 'accuracy'
    mae_dir = out_dir / 'images' / 'mae'
    oth_dir = out_dir / 'images' / 'other'
    for d in (out_dir, csv_dir, acc_dir, mae_dir, oth_dir):
        d.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {out_dir}")

    # ── Load data ─────────────────────────────────────────────────────────────
    print("\n=== Loading user data ===")
    df = load_all_users(data_dir)
    print(f"Loaded {len(df):,} total samples, "
          f"{df['user_id'].nunique()} users, "
          f"{df['grid_point_id'].nunique()} grid classes")

    df = make_split(df, test_ratio=0.2)
    print(f"Split: train={( df['split']=='train').sum():,}  "
          f"test={( df['split']=='test').sum():,}")

    grid_lookup = build_grid_lookup(df)

    # ── Data volume sweep (separate mode) ─────────────────────────────────────
    if args.data_volume_sweep:
        print("\n=== Data Volume Sweep: BASE_H vs BASE_H_delta ===")
        sweep_df = run_data_volume_sweep(df, grid_lookup, args.models,
                                          h=args.history)
        sweep_path = csv_dir / 'data_volume_sweep.csv'
        sweep_df.to_csv(sweep_path, index=False)
        print(f"\nSaved: {sweep_path}")
        print(sweep_df.to_string(index=False))
        return

    # ── Environmental variability (separate mode) ─────────────────────────────
    if args.env_dir:
        env_dir = Path(args.env_dir)
        if not env_dir.exists():
            print(f"Error: env-dir not found: {env_dir}")
            sys.exit(1)
        print("\n=== Environmental Variability Experiment ===")
        env_df = run_env_variability(env_dir, grid_lookup, args.models, h=args.history)
        env_path = csv_dir / 'env_variability_results.csv'
        env_df.to_csv(env_path, index=False)
        print(f"\nSaved: {env_path}")
        print(env_df.to_string(index=False))
        return

    # ── Run experiments ────────────────────────────────────────────────────────
    results = run_all_experiments(df, grid_lookup,
                                  models=args.models,
                                  h_primary=args.history,
                                  run_only=args.run_only)

    # ── Print summary table ────────────────────────────────────────────────────
    if results:
        print("\n" + "=" * 70)
        print("RESULTS SUMMARY")
        print("=" * 70)
        print(f"{'Model':<10} {'Experiment':<20} {'Accuracy':>10} {'MAE (m)':>10}")
        print("-" * 70)
        for model_name in args.models:
            if model_name not in results:
                continue
            for exp in sorted(results[model_name].keys()):
                if exp == 'learning_curve':
                    continue
                o = results[model_name][exp]['overall']
                print(f"{model_name:<10} {exp:<20} {o['accuracy']:>9.1f}%  {o['mae']:>9.3f}m")
        print("=" * 70)

    # ── Save CSVs ─────────────────────────────────────────────────────────────
    print(f"\nSaving results to {out_dir}")
    save_results(results, df, csv_dir, args.models, args.history,
                 append_mode=args.append_results)

    # ── Plots (full run only, not in --run-only mode) ─────────────────────────
    if HAS_MATPLOTLIB and args.run_only is None:
        print("\nGenerating plots...")

        # Accuracy plots → images/accuracy/
        plot_accuracy_bar(results, args.models, acc_dir, args.history)
        plot_per_user_heatmap(results, args.models, acc_dir, args.history)
        plot_voronoi_accuracy_map(results, df, args.models, acc_dir, args.history,
                                   data_dir=data_dir, exp_key='BASE_H',
                                   out_filename='voronoi_accuracy_map_BASE_H.png')
        plot_voronoi_accuracy_map(results, df, args.models, acc_dir, args.history,
                                   data_dir=data_dir, exp_key='BASE_A',
                                   out_filename='voronoi_accuracy_map_BASE_A.png')

        # MAE plots → images/mae/
        summary_rows, pu_rows = [], []
        for m in args.models:
            if m not in results:
                continue
            for exp, r in results[m].items():
                if exp == 'learning_curve':
                    continue
                summary_rows.append({'model': m, 'experiment': exp,
                                     'mae_m': r['overall']['mae']})
                for uid, ur in r.get('per_user', {}).items():
                    pu_rows.append({'model': m, 'experiment': exp,
                                    'user_id': uid, 'mae_m': ur['mae']})
        if summary_rows:
            plot_mae_bar(pd.DataFrame(summary_rows), args.models, mae_dir, args.history)
        if pu_rows:
            plot_per_user_mae_heatmap(pd.DataFrame(pu_rows), args.models,
                                      mae_dir, args.history)
        plot_voronoi_mae_map(results, df, args.models, mae_dir, args.history,
                             grid_lookup=grid_lookup, data_dir=data_dir,
                             exp_key='BASE_H',
                             out_filename='voronoi_mae_map_BASE_H.png')
        plot_voronoi_mae_map(results, df, args.models, mae_dir, args.history,
                             grid_lookup=grid_lookup, data_dir=data_dir,
                             exp_key='BASE_A',
                             out_filename='voronoi_mae_map_BASE_A.png')

        # Other plots → images/other/
        plot_learning_curve(results, args.models, oth_dir)
        plot_confusion_matrix(results, args.models, oth_dir,
                              df['grid_point_id'].nunique())

    print("\n=== Multi-user pipeline complete ===")


if __name__ == '__main__':
    main()
