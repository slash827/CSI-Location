"""
Multi-User Heterogeneous Environment — Localization Pipeline

Loads 5 per-user simulation .mat files (from run_multi_user_15x15.m),
builds transition history features, and evaluates 4 experiments:

  E1 — Static baseline:          [rss, sinr]                          (h=0 only)
  E2 — Transitions only:         [rss_t, sinr_t, ..., rss_{t-h}, sinr_{t-h}]  (h=3)
  E3 — Transitions + device params: E2 + [n_antennas, antenna_gain_db, ue_height]
  E4 — Transitions + user_id:    E2 + [user_id as integer]

Research hypothesis:
  Transition-based features (h>0) are robust to device heterogeneity,
  while static features (h=0) degrade — because transitions capture
  relative changes that are device-independent.

Usage:
  python multi_user_pipeline.py --data-dir <path/to/sim_data_multi_user_*>
"""

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

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
SCRIPT_DIR   = Path(__file__).resolve().parent
EXPERIMENT_ROOT = SCRIPT_DIR.parent.parent          # 09_grid_localization/
RESULTS_ROOT = SCRIPT_DIR.parent.parent.parent.parent / 'results'

HISTORY_PRIMARY   = 3    # h used for E2/E3/E4
MAX_HISTORY_CURVE = 4    # h range for learning curve (0..4)

# AoA realistic impairments — applied in Python post-simulation (no re-simulation needed).
# Clean AoA is saved in .mat files; noise injected here, matching localization_pipeline.py.
# 4° Gaussian noise: typical direction estimation error for practical antenna arrays at 2.6 GHz.
# 5° quantization: typical beam-grid resolution for codebook-based beamforming.
AOA_NOISE_STD_DEG  = 4.0   # Gaussian noise std (degrees)
AOA_QUANT_STEP_DEG = 5.0   # Quantization step (degrees)


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


def load_all_users(data_dir: Path) -> pd.DataFrame:
    """Load all 5 per-user .mat files into a combined DataFrame."""
    frames = []
    for u in range(1, 6):
        mat_file = data_dir / f'user{u}_voronoi_15x15.mat'
        if not mat_file.exists():
            raise FileNotFoundError(f"Missing: {mat_file}")
        print(f"  Loading user {u}: {mat_file.name}")
        ud = load_user_file(mat_file)

        # Apply realistic AoA impairments: Gaussian noise + quantization.
        # Clean values are saved in .mat; noise is injected here (no re-simulation needed).
        # Each user gets an independent noise realization (seed keyed on user_id).
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

        udf = pd.DataFrame({
            'user_id':         ud['user_id'],
            'step_index':      ud['step_index'],
            'rss':             ud['rss'],
            'sinr':            ud['sinr'],
            'aoa_azimuth':     ud['aoa_az'] if ud['aoa_az'] is not None
                               else np.full(len(ud['rss']), np.nan),
            'aoa_elevation':   ud['aoa_el'] if ud['aoa_el'] is not None
                               else np.full(len(ud['rss']), np.nan),
            'x_pos':           ud['x_pos'],
            'y_pos':           ud['y_pos'],
            'grid_point_id':   ud['grid_point_id'],
            'voronoi_cell_id': ud['voronoi_cell_id'],
            'n_antennas':      ud['device']['n_antennas'],
            'antenna_gain_db': ud['device']['antenna_gain_db'],
            'ue_height':       ud['device']['ue_height_m'],
        })
        frames.append(udf)
        n = len(udf)
        print(f"    user_id={ud['user_id']}, n={n:,}, "
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
# 3.  Feature engineering — history stacking
# ─────────────────────────────────────────────────────────────────────────────

def build_history_features(df: pd.DataFrame, h: int,
                            extra_cols=None,
                            include_aoa: bool = False) -> pd.DataFrame:
    """
    For each sample t (within one user), stack [rss_t, sinr_t, ..., rss_{t-h}, sinr_{t-h}].
    When include_aoa=True, also stacks [aoa_az_t, aoa_el_t, ..., aoa_az_{t-h}, aoa_el_{t-h}].
    The first h rows per user are dropped (no history available).
    Optional extra_cols (constant per user, e.g. n_antennas) are appended once.

    Returns a new DataFrame with only valid rows and feature columns added.
    """
    result_frames = []

    for uid in sorted(df['user_id'].unique()):
        udf = df[df['user_id'] == uid].sort_values('step_index').reset_index(drop=True)
        n  = len(udf)

        # Core raw measurements
        rss  = udf['rss'].values
        sinr = udf['sinr'].values

        # Stack [rss_t, sinr_t, rss_{t-1}, sinr_{t-1}, ..., rss_{t-h}, sinr_{t-h}]
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

        # Drop first h rows (no full history yet)
        valid = feat_df.iloc[h:].copy()
        meta  = udf.iloc[h:].copy()

        valid = valid.reset_index(drop=True)
        meta  = meta.reset_index(drop=True)
        combined = pd.concat([meta, valid], axis=1)

        # Append constant device / user info columns
        if extra_cols:
            for col in extra_cols:
                combined[f'feat_{col}'] = combined[col]

        result_frames.append(combined)

    return pd.concat(result_frames, ignore_index=True)


def get_feature_cols(h: int, extra_cols=None, include_aoa: bool = False) -> list:
    """Return ordered list of feature column names for history length h."""
    cols = []
    for lag in range(h + 1):
        cols += [f'rss_lag{lag}', f'sinr_lag{lag}']
        if include_aoa:
            cols += [f'aoa_az_lag{lag}', f'aoa_el_lag{lag}']
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
    If exclude_user is set, that user is removed from TRAINING (cross-user test).
    """
    label_col = 'grid_point_id'

    # Encode labels as 0-based integers (sklearn requirement)
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

    # Overall metrics
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

    # Confusion matrix (sampled to keep memory manageable)
    cm = confusion_matrix(y_test_orig, y_pred_orig,
                          labels=all_labels)

    return {
        'overall':    overall,
        'per_user':   per_user,
        'per_cell':   per_cell,
        'cm':         cm,
        'cm_labels':  all_labels,
        'model':      model,
        'feature_cols': feature_cols,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8.  All experiments
# ─────────────────────────────────────────────────────────────────────────────

def run_all_experiments(df: pd.DataFrame,
                        grid_lookup: dict,
                        models: list[str],
                        h_primary: int = 3) -> dict:
    """Run E1–E4 for each model, return nested results dict."""
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

    for model_name in models:
        if model_name == 'xgboost' and not HAS_XGBOOST:
            continue
        print(f"\n{'='*60}")
        print(f"Model: {model_name}")
        print(f"{'='*60}")
        results[model_name] = {}

        # ── E1: static baseline h=0 ──────────────────────────────────
        print("\n--- E1: Static baseline (h=0) ---")
        feat_df_e1 = build_history_features(df, h=0, extra_cols=None)
        fcols_e1   = get_feature_cols(h=0, extra_cols=None)
        results[model_name]['E1'] = run_one_experiment(
            feat_df_e1, fcols_e1, grid_lookup, model_name,
            f"E1 h=0 {model_name}")

        # ── E2: transitions only h=3 ──────────────────────────────────
        print(f"\n--- E2: Transitions h={h_primary} ---")
        feat_df_e2 = build_history_features(df, h=h_primary, extra_cols=None)
        fcols_e2   = get_feature_cols(h=h_primary, extra_cols=None)
        results[model_name]['E2'] = run_one_experiment(
            feat_df_e2, fcols_e2, grid_lookup, model_name,
            f"E2 h={h_primary} {model_name}")

        # ── E3: transitions + device params (continuous) ──────────────
        print(f"\n--- E3: Transitions h={h_primary} + device params ---")
        device_cols = ['n_antennas', 'antenna_gain_db', 'ue_height']
        feat_df_e3 = build_history_features(df, h=h_primary, extra_cols=device_cols)
        fcols_e3   = get_feature_cols(h=h_primary, extra_cols=device_cols)
        results[model_name]['E3'] = run_one_experiment(
            feat_df_e3, fcols_e3, grid_lookup, model_name,
            f"E3 h={h_primary}+device {model_name}")

        # ── E4: transitions + user_id (categorical) ───────────────────
        print(f"\n--- E4: Transitions h={h_primary} + user_id ---")
        feat_df_e4 = build_history_features(df, h=h_primary, extra_cols=['user_id'])
        fcols_e4   = get_feature_cols(h=h_primary, extra_cols=['user_id'])
        results[model_name]['E4'] = run_one_experiment(
            feat_df_e4, fcols_e4, grid_lookup, model_name,
            f"E4 h={h_primary}+uid {model_name}")

        # ── E5: static + AoA (h=0) ────────────────────────────────────
        print(f"\n--- E5: Static + AoA (h=0) ---")
        feat_df_e5 = build_history_features(df, h=0, include_aoa=True)
        fcols_e5   = get_feature_cols(h=0, include_aoa=True)
        results[model_name]['E5'] = run_one_experiment(
            feat_df_e5, fcols_e5, grid_lookup, model_name,
            f"E5 h=0+AoA {model_name}")

        # ── E6: transitions + AoA (h=3, no device params) ─────────────
        print(f"\n--- E6: Transitions h={h_primary} + AoA ---")
        feat_df_e6 = build_history_features(df, h=h_primary, include_aoa=True)
        fcols_e6   = get_feature_cols(h=h_primary, include_aoa=True)
        results[model_name]['E6'] = run_one_experiment(
            feat_df_e6, fcols_e6, grid_lookup, model_name,
            f"E6 h={h_primary}+AoA {model_name}")

        # ── E7: transitions + AoA + device params ─────────────────────
        print(f"\n--- E7: Transitions h={h_primary} + AoA + device params ---")
        feat_df_e7 = build_history_features(df, h=h_primary, extra_cols=device_cols,
                                            include_aoa=True)
        fcols_e7   = get_feature_cols(h=h_primary, extra_cols=device_cols, include_aoa=True)
        results[model_name]['E7'] = run_one_experiment(
            feat_df_e7, fcols_e7, grid_lookup, model_name,
            f"E7 h={h_primary}+AoA+dev {model_name}")

        # ── Cross-user: train U1-U4, test U5 ──────────────────────────
        print(f"\n--- Cross-user: train on U1–U4, test on U5 ---")
        results[model_name]['cross_user_E2'] = run_one_experiment(
            feat_df_e2, fcols_e2, grid_lookup, model_name,
            f"Cross-user E2 {model_name}", exclude_user=5)
        results[model_name]['cross_user_E6'] = run_one_experiment(
            feat_df_e6, fcols_e6, grid_lookup, model_name,
            f"Cross-user E6 (AoA) {model_name}", exclude_user=5)

        # ── Learning curve h=0..MAX_HISTORY_CURVE ─────────────────────
        print(f"\n--- Learning curve h=0..{MAX_HISTORY_CURVE} ---")
        lc = []
        for h_val in range(MAX_HISTORY_CURVE + 1):
            fdf = build_history_features(df, h=h_val, extra_cols=None)
            fc  = get_feature_cols(h=h_val, extra_cols=None)
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
                 models: list[str], h_primary: int):
    """Save CSV summaries and experiment config JSON."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Summary CSV ───────────────────────────────────────────────────────────
    summary_rows = []
    for model_name in models:
        if model_name not in results:
            continue
        for exp in ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7']:
            if exp not in results[model_name]:
                continue
            o = results[model_name][exp]['overall']
            summary_rows.append({
                'model': model_name, 'experiment': exp,
                'accuracy_%': round(o['accuracy'], 2),
                'mae_m':      round(o['mae'], 4),
                'train_time_s': o.get('train_time_s', None),
            })
        # Cross-user variants
        for cu_key in ['cross_user_E2', 'cross_user_E6']:
            if cu_key in results[model_name]:
                cu = results[model_name][cu_key]['overall']
                summary_rows.append({
                    'model': model_name, 'experiment': cu_key,
                    'accuracy_%': round(cu['accuracy'], 2),
                    'mae_m':      round(cu['mae'], 4),
                    'train_time_s': cu.get('train_time_s', None),
                })
    pd.DataFrame(summary_rows).to_csv(out_dir / 'results_summary.csv', index=False)
    print(f"  Saved: results_summary.csv")

    # ── Per-user breakdown CSV ────────────────────────────────────────────────
    pu_rows = []
    for model_name in models:
        if model_name not in results:
            continue
        for exp in ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7']:
            if exp not in results[model_name]:
                continue
            for uid, m in results[model_name][exp]['per_user'].items():
                pu_rows.append({
                    'model': model_name, 'experiment': exp, 'user_id': uid,
                    'accuracy_%': round(m['accuracy'], 2),
                    'mae_m':      round(m['mae'], 4),
                })
    pd.DataFrame(pu_rows).to_csv(out_dir / 'per_user_breakdown.csv', index=False)
    print(f"  Saved: per_user_breakdown.csv")

    # ── Per-cell breakdown CSV ────────────────────────────────────────────────
    pc_rows = []
    for model_name in models:
        if model_name not in results:
            continue
        for exp in ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7']:
            if exp not in results[model_name]:
                continue
            for cid, m in results[model_name][exp]['per_cell'].items():
                pc_rows.append({
                    'model': model_name, 'experiment': exp, 'voronoi_cell_id': cid,
                    'accuracy_%': round(m['accuracy'], 2),
                    'mae_m':      round(m['mae'], 4),
                })
    pd.DataFrame(pc_rows).to_csv(out_dir / 'per_cell_breakdown.csv', index=False)
    print(f"  Saved: per_cell_breakdown.csv")

    # ── Experiment config JSON ────────────────────────────────────────────────
    config_out = {
        'n_users': 5,
        'h_primary': h_primary,
        'max_history_curve': MAX_HISTORY_CURVE,
        'models': models,
        'train_test_split': '80/20 chronological per user',
        'feature_sets': {
            'F1_E1': 'rss, sinr  (h=0)',
            'F2_E2': f'rss, sinr stacked x {h_primary+1}  (h={h_primary})',
            'F3_E3': f'F2 + n_antennas, antenna_gain_db, ue_height  (h={h_primary})',
            'F4_E4': f'F2 + user_id  (h={h_primary})',
            'F5_E5': 'rss, sinr, aoa_az, aoa_el  (h=0)',
            'F6_E6': f'rss, sinr, aoa_az, aoa_el stacked x {h_primary+1}  (h={h_primary})',
            'F7_E7': f'F6 + n_antennas, antenna_gain_db, ue_height  (h={h_primary})',
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
# 10.  Visualisations
# ─────────────────────────────────────────────────────────────────────────────

def plot_accuracy_bar(results: dict, models: list[str], out_dir: Path, h_primary: int):
    """Bar chart: accuracy across E1–E7, grouped by model."""
    if not HAS_MATPLOTLIB:
        return
    exps   = ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7']
    labels = [
        f'E1\n(h=0)',
        f'E2\n(h={h_primary})',
        f'E3\n(h+dev)',
        f'E4\n(h+uid)',
        f'E5\n(h=0+AoA)',
        f'E6\n(h+AoA)',
        f'E7\n(h+AoA+dev)',
    ]
    x     = np.arange(len(exps))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 5))
    colors = ['#2196F3', '#F44336', '#4CAF50', '#FF9800']
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
    ax.set_xticklabels(labels)
    ax.set_ylabel('Classification Accuracy (%)')
    ax.set_title('Multi-User Experiment: E1–E7 Accuracy Comparison')
    ax.legend()
    ax.set_ylim(0, 100)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    path = out_dir / 'accuracy_bar_chart.png'
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: accuracy_bar_chart.png")


def plot_per_user_heatmap(results: dict, models: list[str], out_dir: Path, h_primary: int):
    """Heatmap: per-user accuracy across E1–E7 (for each model)."""
    if not HAS_MATPLOTLIB:
        return
    exps = ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7']
    # Filter to experiments that actually exist
    exps = [e for e in exps if any(
        e in results.get(m, {}) for m in models)]
    user_ids = sorted({uid for m in models if m in results
                       for exp in exps if exp in results[m]
                       for uid in results[m][exp]['per_user']})

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

        fig, ax = plt.subplots(figsize=(11, 4))
        im = ax.imshow(mat, cmap='YlGnBu', vmin=0, vmax=100, aspect='auto')
        plt.colorbar(im, ax=ax, label='Accuracy (%)')
        ax.set_xticks(range(len(exps)))
        xlabels = [f'E1\nh=0', f'E2\nh={h_primary}', f'E3\n+dev', f'E4\n+uid',
                   f'E5\nh=0\n+AoA', f'E6\nh+AoA', f'E7\nh+AoA\n+dev']
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
    """Confusion matrix for the best experiment (E2) of the best model."""
    if not HAS_MATPLOTLIB:
        return
    best_model = models[0] if models else None
    if best_model not in results or 'E2' not in results[best_model]:
        return

    cm     = results[best_model]['E2']['cm']
    labels = results[best_model]['E2']['cm_labels']

    # Normalise to percentage
    cm_norm = cm.astype(float)
    row_sums = cm_norm.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    cm_norm = cm_norm / row_sums * 100.0

    # Only plot if manageable (<= 50 classes shown); otherwise aggregate
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(cm_norm, cmap='Blues', vmin=0, vmax=100, aspect='auto')
    plt.colorbar(im, ax=ax, label='Recall (%)')
    ax.set_title(f'Confusion Matrix — {best_model.upper()} E2\n'
                 f'(row-normalised, {n_classes} classes)')
    ax.set_xlabel('Predicted grid point')
    ax.set_ylabel('True grid point')
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    path = out_dir / 'confusion_matrix_E2.png'
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: confusion_matrix_E2.png")


def plot_voronoi_accuracy_map(results: dict, df: pd.DataFrame,
                               models: list[str], out_dir: Path, h_primary: int,
                               data_dir: Path = None,
                               voronoi_names: list = None,
                               voronoi_centers_override: np.ndarray = None,
                               exp_key: str = 'E2',
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

    # ── Unique grid-point positions and cell membership ───────────────────────
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

    # ── Voronoi cell centers: caller override → mat file → mean-position fallback ─
    voronoi_centers = voronoi_centers_override   # may be None
    _voronoi_names  = voronoi_names              # may be None
    if (voronoi_centers is None or _voronoi_names is None) and data_dir is not None:
        try:
            import scipy.io as _sio
            mat1 = _sio.loadmat(str(data_dir / 'user1_voronoi_15x15.mat'),
                                squeeze_me=True, struct_as_record=False)
            if 'voronoi_centers' in mat1 and voronoi_centers is None:
                vc = np.array(mat1['voronoi_centers'], dtype=float)
                voronoi_centers = vc.reshape(-1, 2) if vc.ndim == 1 else vc
            if 'voronoi_names' in mat1 and _voronoi_names is None:
                vn = mat1['voronoi_names']
                _voronoi_names = [str(v) for v in vn] if hasattr(vn, '__len__') else None
        except Exception:
            pass

    # Fallback: derive centers as mean position of grid points per cell
    if voronoi_centers is None or len(voronoi_centers) != n_cells:
        voronoi_centers = np.array([
            [gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'x_pos'].mean(),
             gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'y_pos'].mean()]
            for cid in cell_ids
        ])
    if _voronoi_names is None or len(_voronoi_names) != n_cells:
        _voronoi_names = [f'C{cid}' for cid in cell_ids]

    # Label positions: centroid of grid points in each cell
    cell_centroids = [
        np.array([gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'x_pos'].mean(),
                  gp_df.loc[gp_df['voronoi_cell_id'] == cid, 'y_pos'].mean()])
        for cid in cell_ids
    ]

    # ── Build nearest-centre background mesh for segmentation ─────────────────
    pad = 1.5
    x_min, x_max = gp_df['x_pos'].min() - pad, gp_df['x_pos'].max() + pad
    y_min, y_max = gp_df['y_pos'].min() - pad, gp_df['y_pos'].max() + pad
    xx, yy = np.meshgrid(np.linspace(x_min, x_max, 400),
                         np.linspace(y_min, y_max, 400))
    mesh_pts = np.column_stack([xx.ravel(), yy.ravel()])
    mesh_cell_idx = np.argmin(_cdist(mesh_pts, voronoi_centers),
                              axis=1).reshape(xx.shape)
    cell_cmap = mcolors.ListedColormap(CELL_COLORS[:n_cells])

    # ── Per-grid-point accuracy from confusion matrix ─────────────────────────
    cm     = results[best_model][exp]['cm']
    labels = results[best_model][exp]['cm_labels']
    cm_diag   = np.diag(cm).astype(float)
    row_total = cm.sum(axis=1).astype(float)
    row_total[row_total == 0] = 1
    grid_acc = {lbl: (cm_diag[i] / row_total[i]) * 100
                for i, lbl in enumerate(labels)}

    xs, ys, cs = [], [], []
    for gp, (x, y) in pos_lookup.items():
        xs.append(x); ys.append(y)
        cs.append(grid_acc.get(gp, 0.0))

    # ── Plot ──────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 8))

    # Voronoi cell segmentation: filled regions + boundary lines
    ax.pcolormesh(xx, yy, mesh_cell_idx, cmap=cell_cmap, alpha=0.15,
                  vmin=-0.5, vmax=n_cells - 0.5, shading='auto', zorder=0)
    ax.contour(xx, yy, mesh_cell_idx, levels=np.arange(0.5, n_cells),
               colors='#555555', linewidths=1.5, zorder=1, alpha=0.8)

    # Per-grid-point accuracy scatter
    sc = ax.scatter(xs, ys, c=cs, cmap='RdYlGn', vmin=0, vmax=100,
                    s=60, alpha=0.9, edgecolors='none', zorder=3)
    plt.colorbar(sc, ax=ax, label='Per-grid-point accuracy (%)')

    # Cell labels centred inside each Voronoi region
    for i, cid in enumerate(cell_ids):
        color = CELL_COLORS[i % len(CELL_COLORS)]
        name  = _voronoi_names[i]
        cx, cy = cell_centroids[i]
        ax.text(cx, cy, name, ha='center', va='center',
                fontsize=9, fontweight='bold', color=color, zorder=8,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                          alpha=0.65, edgecolor=color, linewidth=1.2))

    # BS markers
    ax.scatter([19], [19], marker='^', s=300, c='blue', zorder=6,
               edgecolors='white', linewidths=1.5, label='Serving BS')
    ax.scatter([-11, 19], [19, -11], marker='x', s=150, c='red',
               zorder=6, linewidths=2, label='Interferers')

    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.set_title(f'Per-Grid-Point Accuracy ({best_model.upper()} {exp}, h={h_primary})\n'
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
# 11.  Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Multi-user heterogeneous localization pipeline')
    parser.add_argument('--data-dir', required=True,
                        help='Directory containing user1_voronoi_15x15.mat .. user5_voronoi_15x15.mat')
    parser.add_argument('--models', nargs='+', default=['xgboost', 'rf'],
                        choices=['xgboost', 'rf'],
                        help='Models to run (default: xgboost rf)')
    parser.add_argument('--history', type=int, default=HISTORY_PRIMARY,
                        help=f'Primary history length for E2/E3/E4 (default: {HISTORY_PRIMARY})')
    parser.add_argument('--out-dir', default=None,
                        help='Output directory (default: results/multi_user_voronoi_15x15/)')
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Error: data directory not found: {data_dir}")
        sys.exit(1)

    out_dir = Path(args.out_dir) if args.out_dir else \
              RESULTS_ROOT / 'multi_user_voronoi_15x15'
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {out_dir}")

    # ── Load data ─────────────────────────────────────────────────────────────
    print("\n=== Loading user data ===")
    df = load_all_users(data_dir)
    print(f"Loaded {len(df):,} total samples, "
          f"{df['user_id'].nunique()} users, "
          f"{df['grid_point_id'].nunique()} grid classes")

    # ── Split ─────────────────────────────────────────────────────────────────
    df = make_split(df, test_ratio=0.2)
    print(f"Split: train={( df['split']=='train').sum():,}  "
          f"test={( df['split']=='test').sum():,}")

    # ── Grid position lookup ──────────────────────────────────────────────────
    grid_lookup = build_grid_lookup(df)

    # ── Run experiments ───────────────────────────────────────────────────────
    results = run_all_experiments(df, grid_lookup,
                                  models=args.models,
                                  h_primary=args.history)

    # ── Print summary table ───────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("RESULTS SUMMARY")
    print("=" * 65)
    header = f"{'Model':<10} {'Exp':<8} {'Accuracy':>10} {'MAE (m)':>10}"
    print(header)
    print("-" * 65)
    for model_name in args.models:
        if model_name not in results:
            continue
        for exp in ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7']:
            if exp not in results[model_name]:
                continue
            o = results[model_name][exp]['overall']
            print(f"{model_name:<10} {exp:<8} {o['accuracy']:>9.1f}%  {o['mae']:>9.3f}m")
        # cross-user variants
        for cu_key, label in [('cross_user_E2', 'CU-E2'), ('cross_user_E6', 'CU-E6')]:
            if cu_key in results[model_name]:
                cu = results[model_name][cu_key]['overall']
                print(f"{model_name:<10} {label:<8} {cu['accuracy']:>9.1f}%  {cu['mae']:>9.3f}m")
    print("=" * 65)

    # ── Save CSVs ─────────────────────────────────────────────────────────────
    print(f"\nSaving results to {out_dir}")
    save_results(results, df, out_dir, args.models, args.history)

    # ── Plots ─────────────────────────────────────────────────────────────────
    if HAS_MATPLOTLIB:
        print("\nGenerating plots...")
        plot_accuracy_bar(results, args.models, out_dir, args.history)
        plot_per_user_heatmap(results, args.models, out_dir, args.history)
        plot_learning_curve(results, args.models, out_dir)
        plot_confusion_matrix(results, args.models, out_dir,
                              df['grid_point_id'].nunique())
        plot_voronoi_accuracy_map(results, df, args.models, out_dir, args.history,
                                   data_dir=data_dir)

    print("\n=== Multi-user pipeline complete ===")


if __name__ == '__main__':
    main()
