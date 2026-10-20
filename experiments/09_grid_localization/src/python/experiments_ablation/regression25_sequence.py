"""
GRU and 1D-CNN on the 25x25 regression data (five pooled device profiles, NE BS), same split as the tree runs.

Question: the tree models plateau at about three steps of history. On the 15x15 grid (classification) a GRU and a
1D-CNN keep improving up to 15 steps (grid_history_extended.py). Do they also lower the absolute position error
of the 25x25 regression, where the trees stay close to the constant guess?

Protocol identical to multi_user_pipeline_regression.py: fixed 4 degree AoA noise, chronological 80/20 split per
user, first 30 % of each user's training split, targets are the BS-relative Cartesian coordinates, metric is the
mean 3D position error in metres. The network is trained on standardized targets (MSE); a validation block (the
last 10 % of each user's training rows) selects the epoch. Reports are saved after every run.

Usage (from the repository root):
    .venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/regression25_sequence.py \
        --data-dir results/grid_localization/grid_25x25/sim_data_ne_bs_2026-10-16_14-57-54 \
        --out-dir results/regression_25x25_2026_10/mixed_30_sequence --models gru cnn --history 0 3 7 15 --seeds 2
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'src' / 'python'))

import pipelines.multi_user_pipeline_regression as reg  # noqa: E402

EXPERIMENTS = {'BASE': False, 'BASE_A': True}   # name -> include AoA
EPOCHS, BATCH, LR, WD, PATIENCE, DROPOUT = 40, 1024, 1e-3, 1e-4, 5, 0.1


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def sequence_tensor(feat_df, h, aoa, stats):
    """[n, C, h+1] channels oldest -> newest: rss, sinr (+ sin/cos azimuth, elevation, validity mask)."""
    lags = range(h, -1, -1)
    rss = np.stack([feat_df[f'rss_lag{l}'].values for l in lags], axis=1)
    sinr = np.stack([feat_df[f'sinr_lag{l}'].values for l in lags], axis=1)
    chans = [(rss - stats['rss'][0]) / stats['rss'][1], (sinr - stats['sinr'][0]) / stats['sinr'][1]]
    if aoa:
        az = np.stack([feat_df[f'aoa_az_lag{l}'].values for l in lags], axis=1)
        el = np.stack([feat_df[f'aoa_el_lag{l}'].values for l in lags], axis=1)
        valid = np.isfinite(az) & np.isfinite(el)
        azr = np.deg2rad(np.where(valid, az, 0.0))
        chans += [np.sin(azr), np.cos(azr), np.where(valid, el, 0.0) / 90.0, valid.astype(np.float32)]
    return np.stack(chans, axis=1).astype(np.float32)


def make_cnn(in_ch, n_out):
    import torch.nn as nn
    return nn.Sequential(
        nn.Conv1d(in_ch, 32, 3, padding=1), nn.BatchNorm1d(32), nn.LeakyReLU(0.1), nn.Dropout(DROPOUT),
        nn.Conv1d(32, 64, 3, padding=1), nn.BatchNorm1d(64), nn.LeakyReLU(0.1), nn.Dropout(DROPOUT),
        nn.Conv1d(64, 128, 3, padding=1), nn.BatchNorm1d(128), nn.LeakyReLU(0.1),
        nn.AdaptiveAvgPool1d(1), nn.Flatten(),
        nn.Linear(128, 256), nn.LeakyReLU(0.1), nn.BatchNorm1d(256), nn.Dropout(DROPOUT),
        nn.Linear(256, n_out))


def make_gru(in_ch, n_out):
    import torch.nn as nn

    class GRUNet(nn.Module):
        """2-layer GRU over the report sequence (oldest to newest); the last hidden state feeds the regression head."""

        def __init__(self):
            super().__init__()
            self.gru = nn.GRU(in_ch, 64, num_layers=2, batch_first=True, dropout=0.2)
            self.head = nn.Sequential(nn.Linear(64, 128), nn.LeakyReLU(0.1), nn.Dropout(DROPOUT),
                                      nn.Linear(128, n_out))

        def forward(self, x):                      # x: [B, C, T]
            out, _ = self.gru(x.permute(0, 2, 1))
            return self.head(out[:, -1])

    return GRUNet()


def train_net(Xtr, ytr, Xva, yva, Xte, y_sd, seed, device, kind):
    """Standardized-target MSE; epoch chosen by validation mean error in metres. Returns test predictions (standardized)."""
    import torch
    import torch.nn as nn
    torch.manual_seed(seed)
    np.random.seed(seed)
    net = (make_gru if kind == 'gru' else make_cnn)(Xtr.shape[1], ytr.shape[1]).to(device)
    opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=WD)
    lossf = nn.MSELoss()
    Xtr_t, ytr_t = torch.from_numpy(Xtr).to(device), torch.from_numpy(ytr).to(device)
    Xva_t, yva_t = torch.from_numpy(Xva).to(device), torch.from_numpy(yva).to(device)
    sd = torch.from_numpy(y_sd).to(device)
    best, best_state, bad = np.inf, None, 0
    n = len(Xtr_t)
    for ep in range(EPOCHS):
        net.train()
        perm = torch.randperm(n, device=device)
        for i in range(0, n, BATCH):
            idx = perm[i:i + BATCH]
            if len(idx) < 2:
                continue
            opt.zero_grad()
            lossf(net(Xtr_t[idx]), ytr_t[idx]).backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            val = float(((net(Xva_t) - yva_t) * sd).norm(dim=1).mean())
        if val < best:
            best, bad = val, 0
            best_state = {k: v.detach().clone() for k, v in net.state_dict().items()}
        else:
            bad += 1
            if bad >= PATIENCE:
                break
    net.load_state_dict(best_state)
    net.eval()
    with torch.no_grad():
        pred = torch.cat([net(torch.from_numpy(Xte[i:i + 8192]).to(device)).cpu()
                          for i in range(0, len(Xte), 8192)]).numpy()
    return pred, ep + 1, best


def main():
    ap = argparse.ArgumentParser(
        description='GRU and 1D-CNN on the 25x25 regression data.',
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('Usage')[1])
    ap.add_argument('--data-dir', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--models', nargs='+', default=['gru'], choices=['gru', 'cnn'])
    ap.add_argument('--history', nargs='+', type=int, default=[0, 3, 7, 15])
    ap.add_argument('--experiments', nargs='+', default=['BASE', 'BASE_A'], choices=list(EXPERIMENTS))
    ap.add_argument('--seeds', type=int, default=2)
    ap.add_argument('--first-seed', type=int, default=0, help='seeds run are first-seed .. first-seed + seeds - 1')
    ap.add_argument('--subsample', type=float, default=0.3)
    ap.add_argument('--epochs', type=int, default=40, help='maximum epochs (early stopping on the validation error)')
    ap.add_argument('--patience', type=int, default=5)
    args = ap.parse_args()
    global EPOCHS, PATIENCE
    EPOCHS, PATIENCE = args.epochs, args.patience

    import torch
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    data_dir, out = Path(args.data_dir), Path(args.out_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f'Simulation data not found: {data_dir}')
    out.mkdir(parents=True, exist_ok=True)

    df = reg.load_all_users(data_dir, sinr_dependent_aoa=False)
    bs_pos = np.array(reg._read_bs_position_3d(data_dir))
    delta = np.column_stack([df['x_pos'], df['y_pos'], df['ue_height']]) - bs_pos
    df['target_x'], df['target_y'], df['target_z'] = delta[:, 0], delta[:, 1], delta[:, 2]
    df = reg.make_split(df, test_ratio=0.2)
    keep = []
    for uid in df['user_id'].unique():
        tr = df[(df['user_id'] == uid) & (df['split'] == 'train')].sort_values('step_index')
        keep.append(tr.index[:int(len(tr) * args.subsample)])
    df = df.loc[np.concatenate(keep + [df[df['split'] == 'test'].index])].reset_index(drop=True)
    log(f'device {device}; rows {len(df):,}')

    rows, csv_path = [], out / 'results_sequence.csv'
    targets = ['target_x', 'target_y', 'target_z']
    for h in args.history:
        for exp in args.experiments:
            aoa = EXPERIMENTS[exp]
            feat = reg.build_history_features(df, h, include_aoa=aoa)
            feat = feat.sort_values(['user_id', 'step_index'])
            is_test = (feat['split'] == 'test').values
            tr_all = feat[~is_test]
            # validation block: last 10 % of each user's training rows
            val_idx = np.concatenate([g.index[int(len(g) * 0.9):] for _, g in tr_all.groupby('user_id')])
            is_val = feat.index.isin(val_idx)
            is_train = ~is_test & ~is_val
            stats = {c: (float(np.nanmean(feat.loc[is_train, f'{c}_lag0'])), float(np.nanstd(feat.loc[is_train, f'{c}_lag0']) + 1e-6))
                     for c in ('rss', 'sinr')}
            X = sequence_tensor(feat, h, aoa, stats)
            Y = feat[targets].values.astype(np.float32)
            y_mu, y_sd = Y[is_train].mean(0), Y[is_train].std(0) + 1e-6
            Ys = (Y - y_mu) / y_sd
            err_true = Y[is_test]
            for kind in args.models:
                for seed in range(args.first_seed, args.first_seed + args.seeds):
                    t0 = time.time()
                    pred, epochs, val = train_net(X[is_train], Ys[is_train], X[is_val], Ys[is_val], X[is_test],
                                                  y_sd.astype(np.float32), seed, device, kind)
                    err = np.linalg.norm(pred * y_sd + y_mu - err_true, axis=1)
                    rows.append({'model': kind, 'experiment': exp, 'h': h, 'seed': seed, 'mae_m': round(float(err.mean()), 4),
                                 'median_m': round(float(np.median(err)), 4), 'val_mae_m': round(val, 4), 'epochs': epochs,
                                 'n_test': int(is_test.sum()), 'seconds': round(time.time() - t0, 1)})
                    log(f'{kind} {exp} h={h} seed={seed}: MAE {err.mean():.3f} m (val {val:.3f}, {epochs} epochs, {time.time() - t0:.0f}s)')
                    pd.DataFrame(rows).to_csv(csv_path, index=False)
    log(f'[OK] Results saved to: {csv_path}')


if __name__ == '__main__':
    main()
