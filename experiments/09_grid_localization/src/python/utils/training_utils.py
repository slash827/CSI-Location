"""
training_utils.py
-----------------
Shared training utilities for Multi-User-Environment CNN notebooks.

Provides:
  - EarlyStopping          : patience-based checkpoint callback
  - run_kalman_and_rts_2d  : forward Kalman filter + RTS smoother
  - collect_test_predictions: batch evaluation -> numpy arrays
  - print_per_antenna_benchmark: formatted per-antenna MAE table
  - plot_trajectories      : 5-user trajectory grid inline + save to disk
"""
import copy
import time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.linalg import inv


# ── Early Stopping ────────────────────────────────────────────────────────────

class EarlyStopping:
    """
    Monitors validation MAE and stops training when no improvement has been
    seen for `patience` epochs.

    Usage::

        es = EarlyStopping(patience=8, min_delta=0.05)
        for epoch in range(EPOCHS):
            ...
            if es(val_mae, model, save_path=OUT_DIR / "best_model.pt"):
                break
        model.load_state_dict(es.best_state)

    Attributes:
        best_val_mae (float): best validation MAE seen so far.
        best_epoch (int): epoch at which best_val_mae was achieved.
        best_state (dict): model state_dict at best_epoch.
        stopped (bool): True once patience is exhausted.
        counter (int): epochs since last improvement.
    """

    def __init__(self, patience=8, min_delta=0.05, verbose=True):
        """
        Args:
            patience (int): number of epochs with no improvement before stop.
            min_delta (float): minimum improvement in metres to reset counter.
            verbose (bool): print a message when patience counter increases.
        """
        self.patience    = patience
        self.min_delta   = min_delta
        self.verbose     = verbose
        self.best_val_mae = float("inf")
        self.best_epoch  = 0
        self.best_state  = None
        self.counter     = 0
        self.stopped     = False

    def __call__(self, val_mae, model, epoch, save_path=None):
        """
        Call once per epoch after validation.

        Args:
            val_mae (float): current epoch validation 2D MAE (metres).
            model: PyTorch model (used to deepcopy state on improvement).
            epoch (int): current epoch number (1-indexed, for logging).
            save_path (Path | None): if given, saves best checkpoint here.

        Returns:
            bool: True if training should stop (patience exhausted).
        """
        improved = (self.best_val_mae - val_mae) > self.min_delta

        if improved:
            self.best_val_mae = val_mae
            self.best_epoch   = epoch
            self.best_state   = copy.deepcopy(model.state_dict())
            self.counter      = 0
            if save_path is not None:
                import torch
                torch.save(self.best_state, save_path)
        else:
            self.counter += 1
            if self.verbose:
                print(f"  [EarlyStopping] No improvement for {self.counter}/{self.patience} epochs "
                      f"(best {self.best_val_mae:.3f}m @ epoch {self.best_epoch})")

        if self.counter >= self.patience:
            self.stopped = True
            if self.verbose:
                print(f"  [EarlyStopping] Patience exhausted. Stopping at epoch {epoch}. "
                      f"Best MAE: {self.best_val_mae:.3f}m at epoch {self.best_epoch}.")
            return True

        return False

    def restore_best(self, model):
        """Load best weights back into model."""
        if self.best_state is not None:
            model.load_state_dict(self.best_state)
        return model


# ── Kinematic Post-Processing ─────────────────────────────────────────────────

def run_kalman_and_rts_2d(y_true, y_pred, delta_t_vec,
                          process_noise_std=0.5, R_std=15.0):
    """
    2D constant-velocity Kalman Filter + RTS smoother on a single-user trajectory.

    State vector: [x, y, vx, vy]
    Observation:  [x, y]  (from neural-network position prediction)

    Args:
        y_true (np.ndarray): shape (N, 2) -- ground-truth positions (unused in KF,
                             kept for API symmetry with legacy code).
        y_pred (np.ndarray): shape (N, 2) -- raw NN position predictions (metres).
        delta_t_vec (array): shape (N,) -- inter-sample time intervals (seconds).
        process_noise_std (float): KF process-noise std (m / sqrt(s)).
        R_std (float): KF measurement-noise std (metres).

    Returns:
        kf_pos  (np.ndarray): shape (N, 2) -- Kalman-filtered positions.
        rts_pos (np.ndarray): shape (N, 2) -- RTS-smoothed positions.
    """
    N = len(y_pred)
    if N == 0:
        return y_pred, y_pred

    H = np.zeros((2, 4))
    H[0, 0], H[1, 1] = 1.0, 1.0
    R = (R_std ** 2) * np.eye(2)

    x_pred = np.zeros((N, 4)); P_pred = np.zeros((N, 4, 4))
    x_filt = np.zeros((N, 4)); P_filt = np.zeros((N, 4, 4))
    x_filt[0, :2] = y_pred[0]
    P_filt[0]     = np.eye(4) * 100.0
    x_pred[0]     = x_filt[0]
    P_pred[0]     = P_filt[0]

    # Forward pass
    for t in range(1, N):
        dt = max(0.01, float(delta_t_vec[t]))
        F  = np.eye(4); F[0, 2], F[1, 3] = dt, dt
        q  = process_noise_std ** 2
        Q  = np.diag([q * dt**2, q * dt**2, q, q])
        x_p = F @ x_filt[t - 1]
        P_p = F @ P_filt[t - 1] @ F.T + Q
        x_pred[t], P_pred[t] = x_p, P_p
        y_k = y_pred[t] - H @ x_p
        S_k = H @ P_p @ H.T + R
        K_k = P_p @ H.T @ inv(S_k)
        x_filt[t] = x_p + K_k @ y_k
        P_filt[t] = (np.eye(4) - K_k @ H) @ P_p

    # RTS backward pass
    x_smooth = np.zeros((N, 4)); P_smooth = np.zeros((N, 4, 4))
    x_smooth[-1] = x_filt[-1]
    P_smooth[-1] = P_filt[-1]
    for t in range(N - 2, -1, -1):
        dt = max(0.01, float(delta_t_vec[t + 1]))
        F  = np.eye(4); F[0, 2], F[1, 3] = dt, dt
        C_k = P_filt[t] @ F.T @ inv(P_pred[t + 1])
        x_smooth[t] = x_filt[t] + C_k @ (x_smooth[t + 1] - x_pred[t + 1])
        P_smooth[t] = P_filt[t] + C_k @ (P_smooth[t + 1] - P_pred[t + 1]) @ C_k.T

    return x_filt[:, :2], x_smooth[:, :2]


def apply_kalman_smoother(preds_raw, targs, uids, dts, test_users,
                          process_noise_std=0.5, R_std=15.0):
    """
    Apply run_kalman_and_rts_2d to every test user and return full arrays.

    Returns:
        kf_preds  (np.ndarray): shape (N, 2)
        rts_preds (np.ndarray): shape (N, 2)
    """
    kf_preds  = np.zeros_like(preds_raw)
    rts_preds = np.zeros_like(preds_raw)
    for uid in test_users:
        u_mask = (uids == uid)
        if not np.any(u_mask):
            continue
        x_kf, x_rts = run_kalman_and_rts_2d(
            targs[u_mask], preds_raw[u_mask], dts[u_mask],
            process_noise_std=process_noise_std, R_std=R_std
        )
        kf_preds[u_mask]  = x_kf
        rts_preds[u_mask] = x_rts
    return kf_preds, rts_preds


# ── Evaluation Helpers ────────────────────────────────────────────────────────

def collect_test_predictions(model, loader, device, train_ds):
    """
    Run model on test_loader and collect all predictions / targets / metadata.

    Returns dict with keys:
        preds_raw, targs, preds_speed, targs_speed, preds_unc,
        uids, dts, n_ants  -- all np.ndarray
    """
    import torch
    model.eval()
    preds_pos_list, preds_spd_list, preds_unc_list = [], [], []
    targs_pos_list, targs_spd_list = [], []
    uids_list, dts_list, n_ants_list = [], [], []

    with torch.no_grad():
        for batch in loader:
            seq   = batch["seq"].to(device)
            stat  = batch["static"].to(device)
            t_pos = batch["target"].to(device)
            t_spd = batch["speed"].to(device)
            p_pos, p_spd, p_unc = model(seq, stat)

            pred_pos_m   = p_pos.cpu().numpy() * train_ds.targ_std  + train_ds.targ_mean
            targ_pos_m   = t_pos.cpu().numpy() * train_ds.targ_std  + train_ds.targ_mean
            pred_speed_m = p_spd.cpu().numpy() * train_ds.speed_std + train_ds.speed_mean
            targ_speed_m = t_spd.cpu().numpy() * train_ds.speed_std + train_ds.speed_mean
            pred_unc_m   = p_unc.cpu().numpy() * float(np.mean(train_ds.targ_std))

            preds_pos_list.append(pred_pos_m)
            targs_pos_list.append(targ_pos_m)
            preds_spd_list.append(pred_speed_m)
            targs_spd_list.append(targ_speed_m)
            preds_unc_list.append(pred_unc_m)
            uids_list.extend(batch["user_id"].numpy())
            dts_list.extend(batch["delta_t"].numpy())
            n_ants_list.extend(batch["n_antennas"].numpy())

    return {
        "preds_raw":   np.vstack(preds_pos_list),
        "targs":       np.vstack(targs_pos_list),
        "preds_speed": np.vstack(preds_spd_list),
        "targs_speed": np.vstack(targs_spd_list),
        "preds_unc":   np.vstack(preds_unc_list),
        "uids":        np.array(uids_list),
        "dts":         np.array(dts_list),
        "n_ants":      np.array(n_ants_list)
    }


def print_per_antenna_benchmark(errs_2d, n_ants, uids, model_name, h_target,
                                best_epoch, nb06_mae=None):
    """
    Print a formatted per-antenna error breakdown to stdout.

    Args:
        errs_2d (np.ndarray): per-sample 2D Euclidean errors (metres).
        n_ants (np.ndarray): per-sample antenna count.
        uids (np.ndarray): per-sample user IDs.
        model_name (str): e.g. "1D-CNN" or "CNN+Attention".
        h_target (int): history depth used.
        best_epoch (int): epoch from which best model was restored.
        nb06_mae (float | None): if given, prints a comparison line.
    """
    mae_overall = np.mean(errs_2d)
    p50_overall = np.percentile(errs_2d, 50)
    p90_overall = np.percentile(errs_2d, 90)

    print(f"=== {model_name} BENCHMARK (h={h_target}, EPOCH {best_epoch}) ===")
    print(f"Overall 2D MAE: {mae_overall:.3f}m  (P50: {p50_overall:.3f}m | P90: {p90_overall:.3f}m)")
    if nb06_mae is not None:
        delta = mae_overall - nb06_mae
        sign  = "+" if delta >= 0 else ""
        print(f"--- NB06 baseline: {nb06_mae:.3f}m | Delta: {sign}{delta:.3f}m ({sign}{100*delta/nb06_mae:.1f}%)")
    print("-" * 85)
    print("PER-ANTENNA BREAKDOWN:")
    for nant in [4, 2, 1]:
        mask = (n_ants == nant)
        if not np.any(mask):
            continue
        e_sub = errs_2d[mask]
        n_u   = len(np.unique(uids[mask]))
        lbl   = "AoA Beamforming Capable" if nant > 1 else "RSS Distance Only (No AoA)"
        print(f"  [{nant}-Antenna UEs] ({n_u:2d} Users | {mask.sum():5,} samples) - {lbl}:")
        print(f"    |-- 2D MAE:    {np.mean(e_sub):6.3f}m")
        print(f"    |-- Median P50:{np.percentile(e_sub, 50):6.3f}m")
        print(f"    +-- P90 Error: {np.percentile(e_sub, 90):6.3f}m")
    print("-" * 85)
    return mae_overall, p50_overall, p90_overall


# ── Trajectory Plotting ───────────────────────────────────────────────────────

def plot_trajectories(targs, preds_raw, rts_preds, uids, n_ants, test_users,
                      plot_dir, scatter_color="dodgerblue", model_label="Model",
                      n_users=5):
    """
    Generate and save per-user trajectory plots.  Shows the first `n_users`
    test users; each plot appears inline in Jupyter and is also saved to disk.

    Args:
        targs (np.ndarray): shape (N, 2) -- ground truth positions.
        preds_raw (np.ndarray): shape (N, 2) -- raw NN predictions.
        rts_preds (np.ndarray): shape (N, 2) -- RTS-smoothed predictions.
        uids (np.ndarray): per-sample user ID.
        n_ants (np.ndarray): per-sample antenna count.
        test_users (iterable): iterable of test user IDs.
        plot_dir (Path): directory where PNG files are saved.
        scatter_color (str): matplotlib colour for raw predictions scatter.
        model_label (str): label used in plot legend.
        n_users (int): how many users to plot (default 5).
    """
    plot_dir = Path(plot_dir)
    plot_dir.mkdir(parents=True, exist_ok=True)
    sample_uids = sorted(list(test_users))[:n_users]
    print(f"Saving {n_users} trajectory plots to: {plot_dir}")

    for u_idx, uid in enumerate(sample_uids, 1):
        u_mask = (uids == uid)
        if not np.any(u_mask):
            continue

        gt_s    = targs[u_mask]
        raw_s   = preds_raw[u_mask]
        rts_s   = rts_preds[u_mask]
        n_ant_u = int(n_ants[u_mask][0])
        mae_raw = np.mean(np.linalg.norm(raw_s - gt_s, axis=1))
        mae_rts = np.mean(np.linalg.norm(rts_s - gt_s, axis=1))

        fig, ax = plt.subplots(figsize=(10, 7.5))
        ax.plot(gt_s[:, 0], gt_s[:, 1], "k-", lw=3.0,
                label=f"Ground Truth (User {uid}, Ant={n_ant_u})")
        ax.scatter(raw_s[:, 0], raw_s[:, 1], color=scatter_color, alpha=0.55,
                   s=22, label=f"{model_label} (MAE: {mae_raw:.2f}m)")
        ax.plot(rts_s[:, 0], rts_s[:, 1], "g-", lw=2.2,
                label=f"RTS Smoother (MAE: {mae_rts:.2f}m)")
        ax.set_xlabel("X Relative to Serving BS (metres)", fontsize=11)
        ax.set_ylabel("Y Relative to Serving BS (metres)", fontsize=11)
        ax.set_title(
            f"User {uid} | {model_label} h=5 | Ant={n_ant_u} | "
            f"Raw MAE: {mae_raw:.2f}m | RTS MAE: {mae_rts:.2f}m",
            fontsize=12, fontweight="bold"
        )
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        plot_path = plot_dir / f"trajectory_user_{uid}.png"
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.show()  # renders inline in Jupyter
        print(f"  [{u_idx}/{n_users}] User {uid} | Ant={n_ant_u} | "
              f"Raw MAE: {mae_raw:.2f}m | RTS MAE: {mae_rts:.2f}m | Saved: {plot_path.name}")
