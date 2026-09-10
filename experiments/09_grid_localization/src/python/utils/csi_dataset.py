"""
csi_dataset.py
--------------
Shared data loading, feature engineering and PyTorch Dataset for the
Multi-User-Environment CNN notebooks (NB06, NB07 ...).

All features are 100% BS-side computable from standard CSI/SRS feedback.
No UE-internal state or GPS data is used.
"""
import numpy as np
import torch
from torch.utils.data import Dataset
from pathlib import Path

# ── Column name constants ─────────────────────────────────────────────────────
SIGNAL_COLS = [
    "rss", "sinr",
    "sin_az", "cos_az", "sin_el", "cos_el",
    "ray_x", "ray_y",
    "d_rss", "d_az", "d_ray_x", "d_ray_y",
    "delta_t"
]
STATIC_COLS = ["n_antennas", "antenna_gain_db", "ue_height"]
TARGET_COLS = ["target_x", "target_y"]


# ── Feature Engineering ───────────────────────────────────────────────────────

def build_derived_features(df):
    """
    Compute 12 additional BS-side derived features and add them to a copy of df.

    New columns added:
        sin_az, cos_az, sin_el, cos_el  -- AoA angle embeddings
        ray_x, ray_y                    -- geometric range-direction vector
        d_rss, d_az, d_ray_x, d_ray_y  -- temporal derivatives (per user)

    Args:
        df: pd.DataFrame with columns aoa_azimuth, aoa_elevation,
            rss, delta_t, user_id.

    Returns:
        pd.DataFrame (copy with new columns).
    """
    df = df.copy()

    az_rad = np.radians(df["aoa_azimuth"])
    el_rad = np.radians(df["aoa_elevation"])
    df["sin_az"] = np.sin(az_rad).astype(np.float32)
    df["cos_az"] = np.cos(az_rad).astype(np.float32)
    df["sin_el"] = np.sin(el_rad).astype(np.float32)
    df["cos_el"] = np.cos(el_rad).astype(np.float32)

    # RSS-to-range estimate via FSPL (path-loss exponent 2.8, ref -45 dBm)
    r_est = 10.0 ** ((-45.0 - df["rss"]) / (10.0 * 2.8))
    df["ray_x"] = (r_est * df["sin_az"] * df["cos_el"]).astype(np.float32)
    df["ray_y"] = (r_est * df["cos_az"] * df["cos_el"]).astype(np.float32)

    # Temporal derivatives normalised by delta_t (per-user diff)
    df["d_rss"]   = df.groupby("user_id")["rss"].diff().fillna(0.0)   / df["delta_t"]
    df["d_az"]    = df.groupby("user_id")["aoa_azimuth"].diff().fillna(0.0) / df["delta_t"]
    df["d_ray_x"] = df.groupby("user_id")["ray_x"].diff().fillna(0.0) / df["delta_t"]
    df["d_ray_y"] = df.groupby("user_id")["ray_y"].diff().fillna(0.0) / df["delta_t"]

    return df


def load_and_prepare_data(data_dir, bs_pos, seed=42, single_ant_ratio=0.15,
                          aoa_noise_std_deg=4.0, aoa_quant_step_deg=5.0):
    """
    Full data preparation pipeline:
      1. Load all user recordings from data_dir
      2. Compute 2D targets relative to serving BS
      3. Apply AoA noise model (Gaussian noise + quantisation)
      4. Set AoA=0 for single-antenna UEs (no beamforming)
      5. Downsample single-antenna users to target ratio
      6. Compute 8 derived BS-side CSI features

    Args:
        data_dir: str or Path to simulation data directory.
        bs_pos:   array-like [x, y, z] absolute BS position.
        seed:     random seed for reproducibility.
        single_ant_ratio: target fraction of single-antenna users (default 0.15).
        aoa_noise_std_deg: Gaussian std for AoA impairment (deg).
        aoa_quant_step_deg: AoA quantisation step (deg, models codebook).

    Returns:
        df_filt:     pd.DataFrame ready for DerivedCSI1DDataset.
        multi_uids:  np.ndarray of multi-antenna user IDs.
        keep_single: np.ndarray of kept single-antenna user IDs.
    """
    from pipelines.multi_user_200_pipeline import load_200_users

    bs_pos   = np.array(bs_pos, dtype=float)
    data_dir = Path(data_dir)

    df_raw = load_200_users(data_dir)

    # 2D targets: displacement from serving BS
    ue_xy = np.column_stack([df_raw["x_pos"], df_raw["y_pos"]])
    delta = ue_xy - bs_pos[:2]
    df_raw["target_x"] = delta[:, 0].astype(np.float32)
    df_raw["target_y"] = delta[:, 1].astype(np.float32)

    # AoA noise model: Gaussian + quantisation, zero for single-antenna UEs
    mask_ant  = df_raw["n_antennas"] > 1
    rng_noise = np.random.RandomState(seed)
    df_raw.loc[mask_ant, "aoa_azimuth"]   += (aoa_noise_std_deg * rng_noise.randn(mask_ant.sum())).astype(np.float32)
    df_raw.loc[mask_ant, "aoa_elevation"] += (aoa_noise_std_deg * rng_noise.randn(mask_ant.sum())).astype(np.float32)
    df_raw.loc[mask_ant, "aoa_azimuth"]   = np.round(df_raw.loc[mask_ant, "aoa_azimuth"]   / aoa_quant_step_deg) * aoa_quant_step_deg
    df_raw.loc[mask_ant, "aoa_elevation"] = np.round(df_raw.loc[mask_ant, "aoa_elevation"] / aoa_quant_step_deg) * aoa_quant_step_deg
    df_raw.loc[~mask_ant, ["aoa_azimuth", "aoa_elevation"]] = 0.0

    # Downsample single-antenna UEs to target ratio
    single_uids = df_raw[df_raw["n_antennas"] == 1]["user_id"].unique()
    multi_uids  = df_raw[df_raw["n_antennas"]  > 1]["user_id"].unique()
    target_n    = int(len(multi_uids) * single_ant_ratio / (1.0 - single_ant_ratio))
    rng_down    = np.random.RandomState(seed)
    keep_single = rng_down.choice(single_uids, size=min(target_n, len(single_uids)), replace=False)
    keep_uids   = set(multi_uids).union(set(keep_single))
    df_filt     = df_raw[df_raw["user_id"].isin(keep_uids)].reset_index(drop=True)

    # Compute derived features
    df_filt = build_derived_features(df_filt)

    return df_filt, multi_uids, keep_single


# ── PyTorch Dataset ───────────────────────────────────────────────────────────

class DerivedCSI1DDataset(Dataset):
    """
    Sequence dataset for derived BS-side CSI features.

    Each sample:
        seq        : float32 Tensor [13, h+1]  -- temporal signal channels
        static     : float32 Tensor [3]         -- static device features
        target     : float32 Tensor [2]         -- normalised (x, y) offset
        speed      : float32 Tensor [1]         -- normalised speed
        user_id    : int
        delta_t    : float
        n_antennas : int

    Pass training-set statistics (*_mean, *_std) to the test-set constructor
    to avoid data leakage.
    """

    def __init__(self, df, h=5,
                 sig_mean=None, sig_std=None,
                 stat_mean=None, stat_std=None,
                 targ_mean=None, targ_std=None,
                 speed_mean=None, speed_std=None):
        self.samples = []
        df = df.copy()
        df["raw_n_antennas"] = df["n_antennas"].values

        self.sig_mean   = sig_mean   if sig_mean   is not None else df[SIGNAL_COLS].mean().values
        self.sig_std    = sig_std    if sig_std    is not None else df[SIGNAL_COLS].std().values  + 1e-6
        self.stat_mean  = stat_mean  if stat_mean  is not None else df[STATIC_COLS].mean().values
        self.stat_std   = stat_std   if stat_std   is not None else df[STATIC_COLS].std().values  + 1e-6
        self.targ_mean  = targ_mean  if targ_mean  is not None else df[TARGET_COLS].mean().values
        self.targ_std   = targ_std   if targ_std   is not None else df[TARGET_COLS].std().values  + 1e-6
        self.speed_mean = speed_mean if speed_mean is not None else float(df["speed_m_s"].mean())
        self.speed_std  = speed_std  if speed_std  is not None else float(df["speed_m_s"].std()) + 1e-6

        # delta_t is both a model input (normalised, below) and the physical time
        # step used downstream by the Kalman/RTS smoother. Keep the seconds value
        # before SIGNAL_COLS is standardised in place, otherwise the smoother is
        # handed z-scores - which are negative for most samples and get clamped to
        # 0.01 s, destroying the state transition.
        df["_delta_t_seconds"] = df["delta_t"].astype(float).values

        df[SIGNAL_COLS]    = (df[SIGNAL_COLS]   - self.sig_mean)   / self.sig_std
        df[STATIC_COLS]    = (df[STATIC_COLS]   - self.stat_mean)  / self.stat_std
        df[TARGET_COLS]    = (df[TARGET_COLS]   - self.targ_mean)  / self.targ_std
        df["norm_speed"]   = (df["speed_m_s"]   - self.speed_mean) / self.speed_std

        L = h + 1
        for uid, udf in df.groupby("user_id"):
            udf = udf.sort_values("step_index").reset_index(drop=True)
            n_steps = len(udf)
            if n_steps < L:
                continue

            sigs     = udf[SIGNAL_COLS].values.astype(np.float32)
            stats    = udf[STATIC_COLS].values.astype(np.float32)
            targs    = udf[TARGET_COLS].values.astype(np.float32)
            speeds   = udf["norm_speed"].values.astype(np.float32)
            u_ids    = udf["user_id"].values
            dts      = udf["_delta_t_seconds"].values   # seconds, not the z-scored feature
            raw_ants = udf["raw_n_antennas"].values

            for i in range(h, n_steps):
                self.samples.append({
                    "seq":        sigs[i - h:i + 1].T,   # [13, L]
                    "static":     stats[i],
                    "target":     targs[i],
                    "speed":      np.array([speeds[i]], dtype=np.float32),
                    "user_id":    u_ids[i],
                    "delta_t":    dts[i],
                    "n_antennas": raw_ants[i]
                })

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        return {
            "seq":        torch.tensor(s["seq"],        dtype=torch.float32),
            "static":     torch.tensor(s["static"],     dtype=torch.float32),
            "target":     torch.tensor(s["target"],     dtype=torch.float32),
            "speed":      torch.tensor(s["speed"],      dtype=torch.float32),
            "user_id":    s["user_id"],
            "delta_t":    s["delta_t"],
            "n_antennas": s["n_antennas"]
        }
