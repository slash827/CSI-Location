"""
Extended history depth, a 1D-CNN and a GRU on the 15x15 controlled grid, plus window-mean tree variants
(xgboost_wm, rf_wm: only the current report and the window mean are given, to test whether trees plateau because
they cannot form an average of the lags themselves).

Two questions the controlled-grid study has not answered:
  1. Where does the history gain stop growing (h = 0, 1, 3, 5, 7, 10, 15)?
  2. Does a neural family (1D-CNN) gain from history on the grid, as the seven
     families do on the macro cell?

Same data, split (chronological 80/20 per user), SINR-dependent AoA noise and metric
as multi_user_pipeline.py. Trees use the pipeline's own models and feature builder.
The CNN classifies the 225 cells from a sequence of per-report channels, oldest to
newest, and is evaluated with the same accuracy / MAE code. Early stopping uses the
last 10 % of each user's training rows, never the test rows.

Usage (from the repository root):
    .venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/grid_history_extended.py \
        --data-dir results/grid_localization/grid_15x15/sim_data_multi_user_<ts> \
        --out-dir results/history_extended/centre_rmalos --n-jobs 6
    ... --models cnn --depths 0 3 10 --cnn-seeds 3        # CNN only
    ... --subsample 0.1 --depths 0 3 --models xgboost cnn   # quick smoke test
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'src' / 'python'))

import pipelines.multi_user_pipeline as mu  # noqa: E402

EXPERIMENTS = {'BASE': False, 'BASE_A': True}   # name -> include AoA
EPOCHS, BATCH, LR, WD, PATIENCE, DROPOUT = 40, 512, 1e-3, 1e-4, 5, 0.1


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


# ── sequence tensor for the CNN ───────────────────────────────────────────────
def sequence_tensor(feat_df, h, aoa, stats):
    """[n, C, h+1] channels oldest -> newest. rss, sinr (+ sin/cos az, el, validity mask)."""
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


def make_cnn(in_ch, n_classes):
    import torch.nn as nn
    return nn.Sequential(
        nn.Conv1d(in_ch, 32, 3, padding=1), nn.BatchNorm1d(32), nn.LeakyReLU(0.1), nn.Dropout(DROPOUT),
        nn.Conv1d(32, 64, 3, padding=1), nn.BatchNorm1d(64), nn.LeakyReLU(0.1), nn.Dropout(DROPOUT),
        nn.Conv1d(64, 128, 3, padding=1), nn.BatchNorm1d(128), nn.LeakyReLU(0.1),
        nn.AdaptiveAvgPool1d(1), nn.Flatten(),
        nn.Linear(128, 256), nn.LeakyReLU(0.1), nn.BatchNorm1d(256), nn.Dropout(DROPOUT),
        nn.Linear(256, n_classes))


def make_gru(in_ch, n_classes):
    import torch.nn as nn

    class GRUNet(nn.Module):
        """2-layer GRU over the report sequence (oldest to newest); the last hidden state feeds the classifier."""

        def __init__(self):
            super().__init__()
            self.gru = nn.GRU(in_ch, 64, num_layers=2, batch_first=True, dropout=0.2)
            self.head = nn.Sequential(nn.Linear(64, 128), nn.LeakyReLU(0.1), nn.Dropout(DROPOUT),
                                      nn.Linear(128, n_classes))

        def forward(self, x):                      # x: [B, C, T]
            out, _ = self.gru(x.permute(0, 2, 1))
            return self.head(out[:, -1])

    return GRUNet()


def make_lstm(in_ch, n_classes):
    import torch.nn as nn

    class LSTMNet(nn.Module):
        """2-layer LSTM with the same width and head as GRUNet, for a like-for-like comparison."""

        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(in_ch, 64, num_layers=2, batch_first=True, dropout=0.2)
            self.head = nn.Sequential(nn.Linear(64, 128), nn.LeakyReLU(0.1), nn.Dropout(DROPOUT),
                                      nn.Linear(128, n_classes))

        def forward(self, x):                      # x: [B, C, T]
            out, _ = self.lstm(x.permute(0, 2, 1))
            return self.head(out[:, -1])

    return LSTMNet()


def make_gru_attn(in_ch, n_classes):
    """GRUNet with attention pooling: a learned score per time step weights all hidden states (softmax over time);
    the weighted context is concatenated with the last hidden state before the classifier."""
    import torch
    import torch.nn as nn

    class GRUAttnNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.gru = nn.GRU(in_ch, 64, num_layers=2, batch_first=True, dropout=0.2)
            self.score = nn.Linear(64, 1)
            self.head = nn.Sequential(nn.Linear(128, 128), nn.LeakyReLU(0.1), nn.Dropout(DROPOUT),
                                      nn.Linear(128, n_classes))
            self.last_attn = None

        def forward(self, x):                      # x: [B, C, T]
            out, _ = self.gru(x.permute(0, 2, 1))  # [B, T, 64]
            w = torch.softmax(self.score(out).squeeze(-1), dim=1)
            self.last_attn = w.detach()
            ctx = (w.unsqueeze(-1) * out).sum(1)
            return self.head(torch.cat([ctx, out[:, -1]], dim=1))

    return GRUAttnNet()


def make_cnn_attn(in_ch, n_classes):
    """The 1D-CNN with attention pooling over time in place of global average pooling."""
    import torch
    import torch.nn as nn

    class CNNAttnNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv = nn.Sequential(
                nn.Conv1d(in_ch, 32, 3, padding=1), nn.BatchNorm1d(32), nn.LeakyReLU(0.1), nn.Dropout(DROPOUT),
                nn.Conv1d(32, 64, 3, padding=1), nn.BatchNorm1d(64), nn.LeakyReLU(0.1), nn.Dropout(DROPOUT),
                nn.Conv1d(64, 128, 3, padding=1), nn.BatchNorm1d(128), nn.LeakyReLU(0.1))
            self.score = nn.Conv1d(128, 1, 1)
            self.head = nn.Sequential(nn.Linear(128, 256), nn.LeakyReLU(0.1), nn.BatchNorm1d(256), nn.Dropout(DROPOUT),
                                      nn.Linear(256, n_classes))
            self.last_attn = None

        def forward(self, x):                      # x: [B, C, T]
            f = self.conv(x)                       # [B, 128, T]
            w = torch.softmax(self.score(f).squeeze(1), dim=1)
            self.last_attn = w.detach()
            return self.head((f * w.unsqueeze(1)).sum(2))

    return CNNAttnNet()


def window_mean_features(feat_df, h, aoa):
    """[current value, window mean] per channel; azimuth is averaged as a unit vector. Isolates the averaging
    operator that a tree cannot build from raw lags: no individual old reports are given to the model."""
    lags = range(h + 1)
    cols = []
    for ch in ('rss', 'sinr'):
        v = np.stack([feat_df[f'{ch}_lag{l}'].values for l in lags], axis=1)
        cols += [v[:, 0], v.mean(axis=1)]
    if aoa:
        az = np.deg2rad(np.stack([feat_df[f'aoa_az_lag{l}'].values for l in lags], axis=1))
        el = np.stack([feat_df[f'aoa_el_lag{l}'].values for l in lags], axis=1)
        az_mean = np.rad2deg(np.arctan2(np.sin(az).mean(axis=1), np.cos(az).mean(axis=1)))
        cols += [np.rad2deg(az[:, 0]), az_mean, el[:, 0], el.mean(axis=1)]
    return np.stack(cols, axis=1).astype(np.float32)


def train_cnn(Xtr, ytr, Xva, yva, Xte, n_classes, seed, device, kind='cnn', return_proba=False):
    import torch
    import torch.nn as nn
    torch.manual_seed(seed)
    np.random.seed(seed)
    net = {'gru': make_gru, 'lstm': make_lstm, 'gru_attn': make_gru_attn, 'cnn_attn': make_cnn_attn}.get(kind, make_cnn)(
        Xtr.shape[1], n_classes).to(device)
    opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=WD)
    lossf = nn.CrossEntropyLoss()
    Xtr_t, ytr_t = torch.from_numpy(Xtr).to(device), torch.from_numpy(ytr).to(device)
    Xva_t, yva_t = torch.from_numpy(Xva).to(device), torch.from_numpy(yva).to(device)
    best, best_state, bad = -1.0, None, 0
    n = len(Xtr_t)
    for ep in range(EPOCHS):
        net.train()
        perm = torch.randperm(n, device=device)
        for i in range(0, n, BATCH):
            idx = perm[i:i + BATCH]
            opt.zero_grad()
            lossf(net(Xtr_t[idx]), ytr_t[idx]).backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            acc = float((net(Xva_t).argmax(1) == yva_t).float().mean())
        if acc > best:
            best, bad = acc, 0
            best_state = {k: v.detach().clone() for k, v in net.state_dict().items()}
        else:
            bad += 1
            if bad >= PATIENCE:
                break
    net.load_state_dict(best_state)
    net.eval()
    with torch.no_grad():
        logits = torch.cat([net(torch.from_numpy(Xte[i:i + 8192]).to(device)).cpu()
                            for i in range(0, len(Xte), 8192)])
    if return_proba:
        return torch.softmax(logits, dim=1).numpy(), ep + 1, best
    return logits.argmax(1).numpy(), ep + 1, best


def main():
    ap = argparse.ArgumentParser(
        description='Extended history depth and 1D-CNN on the 15x15 controlled grid.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split('Usage')[1] if 'Usage' in __doc__ else '')
    ap.add_argument('--data-dir', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--depths', type=int, nargs='+', default=[0, 1, 3, 5, 7, 10, 15])
    ap.add_argument('--models', nargs='+', choices=['xgboost', 'rf', 'cnn', 'gru', 'xgboost_wm', 'rf_wm', 'cnn_shuf', 'gru_shuf', 'cnn_shufold', 'gru_shufold', 'lstm'],
                    default=['xgboost', 'rf', 'cnn'])
    ap.add_argument('--experiments', nargs='+', choices=list(EXPERIMENTS), default=list(EXPERIMENTS))
    ap.add_argument('--cnn-seeds', type=int, default=3)
    ap.add_argument('--n-jobs', type=int, default=6)
    ap.add_argument('--subsample', type=float, default=1.0, help='fraction of rows per user (smoke tests)')
    args = ap.parse_args()

    mu.N_JOBS = args.n_jobs
    data_dir, out_dir = Path(args.data_dir), Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt = out_dir / 'checkpoint'
    ckpt.mkdir(exist_ok=True)

    df = mu.load_all_users(data_dir, sinr_dependent_aoa=True)
    if args.subsample < 1.0:
        df = df.groupby('user_id', group_keys=False).apply(
            lambda g: g.iloc[:int(len(g) * args.subsample)]).reset_index(drop=True)
    df = mu.make_split(df)
    grid_lookup = mu.build_grid_lookup(df)
    spacing = mu.get_grid_spacing(data_dir)
    labels = sorted(df['grid_point_id'].unique())
    l2i = {l: i for i, l in enumerate(labels)}
    i2l = np.array(labels)
    log(f'{len(df):,} rows, {len(labels)} cells, spacing {spacing} m, data {data_dir.name}')

    device = None
    if any(m in args.models for m in ('cnn', 'gru', 'lstm', 'cnn_shuf', 'gru_shuf', 'cnn_shufold', 'gru_shufold')):
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        log(f'CNN device: {device}')

    rows = []
    for exp in args.experiments:
        aoa = EXPERIMENTS[exp]
        for h in args.depths:
            feat = mu.build_history_features(df, h, include_aoa=aoa)
            cols = mu.get_feature_cols(h, include_aoa=aoa)
            tr = feat['split'] == 'train'
            te = feat['split'] == 'test'
            y_te_lab = feat.loc[te, 'grid_point_id'].values
            for model in args.models:
                tag = f'{model}_{exp}_h{h}'
                f = ckpt / f'{tag}.json'
                if f.exists():
                    rows.extend(json.loads(f.read_text()))
                    log(f'{tag}: loaded checkpoint')
                    continue
                t0 = time.time()
                out = []
                if model in ('xgboost', 'rf', 'xgboost_wm', 'rf_wm'):
                    base = model.split('_')[0]
                    if model.endswith('_wm'):
                        Xall_wm = window_mean_features(feat, h, aoa)
                        Xtr, Xte = Xall_wm[tr.values], Xall_wm[te.values]
                    else:
                        Xtr = feat.loc[tr, cols].values.astype(np.float32)
                        Xte = feat.loc[te, cols].values.astype(np.float32)
                    if base == 'rf':   # as in the pipeline: RF gets zeros, XGBoost keeps NaN natively
                        Xtr, Xte = np.nan_to_num(Xtr), np.nan_to_num(Xte)
                    ytr = feat.loc[tr, 'grid_point_id'].map(l2i).values
                    clf = mu.get_model(base, len(labels))
                    clf.fit(Xtr, ytr)
                    pred = i2l[clf.predict(Xte)]
                    r = mu.evaluate_split(y_te_lab, pred, grid_lookup, spacing=spacing)
                    out.append(dict(model=model, experiment=exp, h=h, seed=0, accuracy=r['accuracy'],
                                    mae=r['mae'], epochs=None, secs=round(time.time() - t0, 1)))
                else:
                    trf = feat[tr]
                    # validation = last 10 % of each user's training rows
                    val_mask = np.zeros(len(trf), bool)
                    for uid, g in trf.groupby('user_id'):
                        k = int(len(g) * 0.1)
                        val_mask[trf.index.get_indexer(g.sort_values('step_index').index[-k:])] = True
                    rs = trf[['rss_lag0', 'sinr_lag0']]
                    stats = {'rss': (rs['rss_lag0'].mean(), rs['rss_lag0'].std() + 1e-6),
                             'sinr': (rs['sinr_lag0'].mean(), rs['sinr_lag0'].std() + 1e-6)}
                    Xall = sequence_tensor(trf, h, aoa, stats)
                    yall = trf['grid_point_id'].map(l2i).values.astype(np.int64)
                    Xte = sequence_tensor(feat[te], h, aoa, stats)
                    if '_shuf' in model:
                        # order test: permute the reports inside every window (all channels of a report move together),
                        # in training and in test, so the model can use the set of reports but not their order.
                        # _shuf permutes the whole window (this also hides which report is the current one);
                        # _shufold keeps the current report in the last position and permutes only the older ones.
                        rs_ = np.random.RandomState(123)
                        n_perm = Xall.shape[2] - (1 if model.endswith('_shufold') else 0)
                        for arr_name in ('Xall', 'Xte'):
                            arr = Xall if arr_name == 'Xall' else Xte
                            idx = rs_.random_sample((arr.shape[0], n_perm)).argsort(axis=1)
                            idx = np.concatenate([idx, np.tile(np.arange(n_perm, arr.shape[2]), (arr.shape[0], 1))], axis=1)
                            arr = np.take_along_axis(arr, idx[:, None, :], axis=2)
                            if arr_name == 'Xall':
                                Xall = arr
                            else:
                                Xte = arr
                    for seed in range(args.cnn_seeds):
                        pred_i, ep, best = train_cnn(Xall[~val_mask], yall[~val_mask], Xall[val_mask],
                                                     yall[val_mask], Xte, len(labels), seed, device,
                                                     kind=model.split('_')[0])
                        r = mu.evaluate_split(y_te_lab, i2l[pred_i], grid_lookup, spacing=spacing)
                        out.append(dict(model=model, experiment=exp, h=h, seed=seed, accuracy=r['accuracy'],
                                        mae=r['mae'], epochs=ep, secs=round(time.time() - t0, 1)))
                f.write_text(json.dumps(out))
                rows.extend(out)
                log(f'{tag}: ' + ', '.join(f"{o['accuracy']:.1f}%/{o['mae']:.2f}m" for o in out)
                    + f'  ({time.time() - t0:.0f}s)')

    res = pd.DataFrame(rows)
    res.to_csv(out_dir / 'history_extended.csv', index=False)
    summ = res.groupby(['model', 'experiment', 'h'])[['accuracy', 'mae']].agg(['mean', 'std']).round(3)
    summ.to_csv(out_dir / 'history_extended_summary.csv')
    (out_dir / 'config.json').write_text(json.dumps(
        dict(data_dir=str(data_dir), depths=args.depths, models=args.models, cnn_seeds=args.cnn_seeds,
             subsample=args.subsample, epochs=EPOCHS, batch=BATCH, lr=LR, patience=PATIENCE), indent=2))
    log('done\n' + summ.to_string())


if __name__ == '__main__':
    main()
