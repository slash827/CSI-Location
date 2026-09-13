"""
Shared definitions for the seven Campaign B model families.

Three ablation scripts previously transcribed these architectures independently
(`rts_retune_all_models.py`, `aoa_masking_across_models.py`, and the notebooks).
That is one copy too many: B2 (seed repeats) and B3 (universality figure) both
need the complete set, and a silent divergence between copies would make their
numbers incomparable with the master benchmark.

Everything here is transcribed from notebooks 04, 06 and 07 and from the master
benchmark run, and must stay in step with them. The seventh family, the
mask-aware CNN, is the same 1D-CNN trained on AoA-masked features with the extra
`has_valid_aoa` channel (report section 7.6), so it differs only in input width.

Nothing in this module runs on import beyond defining constants and classes.
"""
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'src' / 'python'))

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from sklearn.neighbors import KNeighborsRegressor
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

from utils import csi_dataset
from utils.csi_dataset import DerivedCSI1DDataset
from utils.training_utils import EarlyStopping

# ── protocol constants (must match the master benchmark) ──────────────────────
SINGLE_ANT_RATIO = 0.15
TRAIN_RATIO = 0.80
BATCH_SIZE = 512
EPOCHS = 60
LR = 3e-4
WEIGHT_DECAY = 1e-2
DROPOUT = 0.35
ES_PATIENCE = 8
ES_MIN_DELTA = 0.05
LAMBDA_POS, LAMBDA_SPEED, LAMBDA_UNC = 1.0, 0.2, 0.05

N_SIGNAL = len(csi_dataset.SIGNAL_COLS)          # 13

# AoA masking (report section 7.6) — the columns zeroed for AoA-blind devices
TRIG_COLS = ['sin_az', 'cos_az', 'sin_el', 'cos_el']
RAY_COLS = ['ray_x', 'ray_y']
DELTA_COLS = ['d_az', 'd_ray_x', 'd_ray_y']

CLASSICAL = ('knn', 'random_forest', 'xgboost')
DEEP = ('cnn', 'gru', 'cnn_attn', 'mask_aware_cnn')
ALL_MODELS = CLASSICAL + DEEP

DISPLAY_NAME = {
    'knn': 'k-NN',
    'random_forest': 'Random Forest',
    'xgboost': 'XGBoost',
    'cnn': '1D-CNN',
    'gru': 'GRU',
    'cnn_attn': 'CNN + attention',
    'mask_aware_cnn': 'Mask-aware CNN',
}

# which paradigm each family belongs to — used by the B3 figure
PARADIGM = {
    'knn': 'instance-based',
    'random_forest': 'bagged trees',
    'xgboost': 'boosted trees',
    'cnn': 'convolutional',
    'gru': 'recurrent',
    'cnn_attn': 'attention',
    'mask_aware_cnn': 'convolutional',
}


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


# ── architectures ─────────────────────────────────────────────────────────────
class DerivedCSI1DCNNNet(nn.Module):
    """NB06. Also serves as the mask-aware CNN with in_channels = N_SIGNAL + 1."""

    def __init__(self, in_channels=N_SIGNAL, static_dim=3, dropout=DROPOUT):
        super().__init__()
        self.conv_block = nn.Sequential(
            nn.Conv1d(in_channels, 32, 3, padding=1), nn.BatchNorm1d(32), nn.LeakyReLU(0.1), nn.Dropout(dropout),
            nn.Conv1d(32, 64, 3, padding=1), nn.BatchNorm1d(64), nn.LeakyReLU(0.1), nn.Dropout(dropout),
            nn.Conv1d(64, 128, 3, padding=1), nn.BatchNorm1d(128), nn.LeakyReLU(0.1),
            nn.AdaptiveAvgPool1d(1))
        self.shared_trunk = nn.Sequential(
            nn.Linear(128 + static_dim, 128), nn.LeakyReLU(0.1), nn.BatchNorm1d(128), nn.Dropout(dropout))
        self.head_pos = nn.Sequential(nn.Linear(128, 64), nn.LeakyReLU(0.1), nn.Linear(64, 2))
        self.head_speed = nn.Sequential(nn.Linear(128, 32), nn.LeakyReLU(0.1), nn.Linear(32, 1))
        self.head_unc = nn.Sequential(nn.Linear(128, 32), nn.LeakyReLU(0.1), nn.Linear(32, 1), nn.Softplus())

    def forward(self, x_seq, x_static):
        f = self.conv_block(x_seq).squeeze(-1)
        feat = self.shared_trunk(torch.cat([f, x_static], dim=1))
        return self.head_pos(feat), self.head_speed(feat), self.head_unc(feat)


class TemporalAttentionBlock(nn.Module):
    def __init__(self, d_model=128, n_heads=4, ffn_dim=256, attn_dropout=0.1, seq_len=6):
        super().__init__()
        self.pos_emb = nn.Embedding(seq_len, d_model)
        self.attn = nn.MultiheadAttention(d_model, n_heads, dropout=attn_dropout, batch_first=True)
        self.norm1 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(nn.Linear(d_model, ffn_dim), nn.GELU(),
                                 nn.Dropout(attn_dropout), nn.Linear(ffn_dim, d_model))
        self.norm2 = nn.LayerNorm(d_model)

    def forward(self, x):
        x = x.permute(0, 2, 1)
        x = x + self.pos_emb(torch.arange(x.size(1), device=x.device))
        a, _ = self.attn(x, x, x)
        x = self.norm1(x + a)
        x = self.norm2(x + self.ffn(x))
        return x.mean(dim=1)


class CNNAttnNet(nn.Module):
    """NB07."""

    def __init__(self, in_channels=N_SIGNAL, static_dim=3, dropout=DROPOUT, seq_len=6):
        super().__init__()
        self.conv_block = nn.Sequential(
            nn.Conv1d(in_channels, 32, 3, padding=1), nn.BatchNorm1d(32), nn.LeakyReLU(0.1), nn.Dropout(dropout),
            nn.Conv1d(32, 64, 3, padding=1), nn.BatchNorm1d(64), nn.LeakyReLU(0.1), nn.Dropout(dropout),
            nn.Conv1d(64, 128, 3, padding=1), nn.BatchNorm1d(128), nn.LeakyReLU(0.1))
        self.temporal_attn = TemporalAttentionBlock(seq_len=seq_len)
        self.shared_trunk = nn.Sequential(
            nn.Linear(128 + static_dim, 128), nn.LeakyReLU(0.1), nn.BatchNorm1d(128), nn.Dropout(dropout))
        self.head_pos = nn.Sequential(nn.Linear(128, 64), nn.LeakyReLU(0.1), nn.Linear(64, 2))
        self.head_speed = nn.Sequential(nn.Linear(128, 32), nn.LeakyReLU(0.1), nn.Linear(32, 1))
        self.head_unc = nn.Sequential(nn.Linear(128, 32), nn.LeakyReLU(0.1), nn.Linear(32, 1), nn.Softplus())

    def forward(self, x_seq, x_static):
        f = self.temporal_attn(self.conv_block(x_seq))
        feat = self.shared_trunk(torch.cat([f, x_static], dim=1))
        return self.head_pos(feat), self.head_speed(feat), self.head_unc(feat)


class MultiTaskGRU2DNet(nn.Module):
    """NB04."""

    def __init__(self, input_dim=N_SIGNAL, static_dim=3, hidden_dim=128,
                 num_layers=2, dropout=0.30):
        super().__init__()
        self.gru = nn.GRU(input_dim, hidden_dim, num_layers, batch_first=True, dropout=dropout)
        self.shared_trunk = nn.Sequential(
            nn.Linear(hidden_dim + static_dim, 256), nn.LeakyReLU(0.1), nn.BatchNorm1d(256), nn.Dropout(dropout))
        self.head_pos = nn.Sequential(nn.Linear(256, 128), nn.LeakyReLU(0.1), nn.Linear(128, 2))
        self.head_speed = nn.Sequential(nn.Linear(256, 64), nn.LeakyReLU(0.1), nn.Linear(64, 1))
        self.head_unc = nn.Sequential(nn.Linear(256, 64), nn.LeakyReLU(0.1), nn.Linear(64, 1), nn.Softplus())

    def forward(self, x_seq, x_static):
        out, _ = self.gru(x_seq.permute(0, 2, 1))
        feat = self.shared_trunk(torch.cat([out[:, -1, :], x_static], dim=1))
        return self.head_pos(feat), self.head_speed(feat), self.head_unc(feat)


def build_net(name, h, in_channels=None):
    """Instantiate one deep family for a given history depth."""
    seq_len = h + 1
    if in_channels is None:
        in_channels = N_SIGNAL + 1 if name == 'mask_aware_cnn' else N_SIGNAL
    if name in ('cnn', 'mask_aware_cnn'):
        return DerivedCSI1DCNNNet(in_channels=in_channels)
    if name == 'gru':
        return MultiTaskGRU2DNet(input_dim=in_channels)
    if name == 'cnn_attn':
        return CNNAttnNet(in_channels=in_channels, seq_len=seq_len)
    raise ValueError(f'Unknown deep model: {name}')


def build_classical(name, seed):
    """Instantiate one classical family with the master-benchmark hyperparameters."""
    if name == 'knn':
        return KNeighborsRegressor(n_neighbors=5, n_jobs=-1)
    if name == 'random_forest':
        return RandomForestRegressor(n_estimators=150, max_features='sqrt', max_depth=16,
                                     min_samples_leaf=5, random_state=seed, n_jobs=-1)
    if name == 'xgboost':
        return XGBRegressor(n_estimators=50, max_depth=5, learning_rate=0.15, subsample=0.8,
                            colsample_bytree=0.8, random_state=seed, n_jobs=-1,
                            tree_method='hist', multi_strategy='one_output_per_tree')
    raise ValueError(f'Unknown classical model: {name}')


# ── data plumbing ─────────────────────────────────────────────────────────────
@contextmanager
def signal_cols(cols):
    """Temporarily override the module-level SIGNAL_COLS the dataset reads."""
    original = csi_dataset.SIGNAL_COLS
    try:
        csi_dataset.SIGNAL_COLS = list(cols)
        yield
    finally:
        csi_dataset.SIGNAL_COLS = original


def apply_aoa_mask(df):
    """Zero the AoA embeddings for devices that cannot measure an angle.

    sin^2 + cos^2 = 0 lies strictly off the unit circle, so "no angle" becomes
    representable and distinguishable from "angle = 0 degrees".
    """
    df = df.copy()
    blind = df['n_antennas'] <= 1
    df.loc[blind, TRIG_COLS] = 0.0
    df.loc[blind, RAY_COLS] = 0.0
    df.loc[blind, DELTA_COLS] = 0.0
    df['has_valid_aoa'] = (~blind).astype(np.float32)
    return df


def make_datasets(df_tr, df_te, h):
    """Train/test DerivedCSI1DDataset pair, test normalised by train statistics."""
    tr = DerivedCSI1DDataset(df_tr, h=h)
    te = DerivedCSI1DDataset(df_te, h=h,
                             sig_mean=tr.sig_mean, sig_std=tr.sig_std,
                             stat_mean=tr.stat_mean, stat_std=tr.stat_std,
                             targ_mean=tr.targ_mean, targ_std=tr.targ_std,
                             speed_mean=tr.speed_mean, speed_std=tr.speed_std)
    return tr, te


def flatten(ds):
    """Flatten a dataset to (X, Y, uid, delta_t_seconds, n_antennas)."""
    n = len(ds)
    d = ds.samples[0]['seq'].size + ds.samples[0]['static'].size
    X = np.empty((n, d), np.float32)
    Y = np.empty((n, 2), np.float32)
    uid = np.empty(n, np.int64)
    dt = np.empty(n, np.float64)
    ant = np.empty(n, np.int64)
    for i, s in enumerate(ds.samples):
        X[i] = np.concatenate([s['seq'].ravel(), s['static'].ravel()])
        Y[i] = s['target']
        uid[i] = s['user_id']
        dt[i] = s['delta_t']
        ant[i] = s['n_antennas']
    return X, Y, uid, dt, ant


# ── training ──────────────────────────────────────────────────────────────────
def train_deep(net, tr_ds, te_ds, targ_std, targ_mean, device,
               name='model', epochs=EPOCHS, verbose=False):
    """Train one deep family and return de-normalised test predictions (metres).

    Early stopping is on test MAE, matching the master benchmark's protocol. That
    is optimistic in absolute terms, but it is applied identically to every family
    and every depth, so the comparisons this supports remain valid.
    """
    tl = DataLoader(tr_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    vl = DataLoader(te_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    net = net.to(device)
    opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    es = EarlyStopping(patience=ES_PATIENCE, min_delta=ES_MIN_DELTA, verbose=False)
    huber = nn.HuberLoss()
    for ep in range(epochs):
        net.train()
        for b in tl:
            p, s, u = net(b['seq'].to(device), b['static'].to(device))
            loss = (LAMBDA_POS * huber(p, b['target'].to(device))
                    + LAMBDA_SPEED * huber(s, b['speed'].to(device))
                    + LAMBDA_UNC * u.mean())
            opt.zero_grad()
            loss.backward()
            opt.step()
        net.eval()
        errs = []
        with torch.no_grad():
            for b in vl:
                p, _, _ = net(b['seq'].to(device), b['static'].to(device))
                pm = p.cpu().numpy() * targ_std + targ_mean
                tm = b['target'].numpy() * targ_std + targ_mean
                errs.append(np.linalg.norm(pm - tm, axis=1))
        vmae = float(np.concatenate(errs).mean())
        if verbose:
            log(f'    {name} epoch {ep + 1:02d} | val MAE {vmae:.3f} m')
        if es(vmae, net, ep):
            break
    es.restore_best(net)
    net.eval()
    preds = []
    with torch.no_grad():
        for b in vl:
            p, _, _ = net(b['seq'].to(device), b['static'].to(device))
            preds.append(p.cpu().numpy())
    return np.concatenate(preds) * targ_std + targ_mean


def evaluate(pred_m, true_m, ant):
    """Standard metric block: overall / cohort MAE and percentiles, in metres."""
    err = np.linalg.norm(pred_m - true_m, axis=1)
    multi, single = ant > 1, ant == 1
    return {
        'mae': float(err.mean()),
        'p50': float(np.median(err)),
        'p90': float(np.percentile(err, 90)),
        'multi_mae': float(err[multi].mean()) if multi.any() else float('nan'),
        'single_mae': float(err[single].mean()) if single.any() else float('nan'),
        'n_multi': int(multi.sum()),
        'n_single': int(single.sum()),
    }


def get_device():
    return torch.device('cuda' if torch.cuda.is_available() else 'cpu')


def ci95(vals):
    v = np.asarray(vals, dtype=float)
    if len(v) < 2:
        return 0.0
    return float(1.96 * v.std(ddof=1) / np.sqrt(len(v)))
