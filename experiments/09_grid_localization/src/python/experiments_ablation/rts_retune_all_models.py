"""
Experiment 4: Kalman/RTS process-noise re-tune across every model family.

Background: the master benchmark reports RTS smoothing degrading every model by
28-48%, using process_noise_std=0.5 and R_std=15.0. Experiment 2 showed that on
k-NN h=5 predictions the smoother is simply mis-tuned: raising Q turns -20% into
+11.35%. Separately, the July XGB/RF sweeps recorded RTS *helping* slightly, so
there are three inconsistent pictures on record.

This resolves it by, for each model family:
  1. training at h=5 under the Campaign B protocol,
  2. collecting raw test-set predictions,
  3. sweeping (process_noise_std x R_std) for both the forward Kalman filter and
     the RTS smoother,
  4. reporting the notebook default alongside the best setting found.

Models: k-NN, Random Forest, XGBoost, 1D-CNN, GRU, 1D-CNN + temporal attention.
Architectures are transcribed from notebooks 04, 06 and 07.
"""
import sys, json, time, datetime, copy
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path('d:/gilad/projects/Academy/CSI-Location')
sys.path.insert(0, str(PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'src' / 'python'))

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from pipelines.multi_user_pipeline_regression import _read_bs_position_3d
from pipelines.multi_user_200_pipeline import make_unseen_user_split
from utils.csi_dataset import DerivedCSI1DDataset, load_and_prepare_data
from utils.training_utils import EarlyStopping, apply_kalman_smoother

from sklearn.neighbors import KNeighborsRegressor
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

SEED = 42
H = 5
SEQ_LEN = H + 1
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

Q_GRID = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0]
R_GRID = [2.0, 5.0, 10.0, 15.0, 25.0, 40.0]

RUN_TS = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
OUT_DIR = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
           / f'rts_retune_all_models_{RUN_TS}')
OUT_DIR.mkdir(parents=True, exist_ok=True)

torch.manual_seed(SEED); np.random.seed(SEED)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


# ── architectures (transcribed from NB04 / NB06 / NB07) ───────────────────────
class DerivedCSI1DCNNNet(nn.Module):
    def __init__(self, in_channels=13, static_dim=3, dropout=DROPOUT):
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
    def __init__(self, d_model=128, n_heads=4, ffn_dim=256, attn_dropout=0.1, seq_len=SEQ_LEN):
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
    def __init__(self, in_channels=13, static_dim=3, dropout=DROPOUT):
        super().__init__()
        self.conv_block = nn.Sequential(
            nn.Conv1d(in_channels, 32, 3, padding=1), nn.BatchNorm1d(32), nn.LeakyReLU(0.1), nn.Dropout(dropout),
            nn.Conv1d(32, 64, 3, padding=1), nn.BatchNorm1d(64), nn.LeakyReLU(0.1), nn.Dropout(dropout),
            nn.Conv1d(64, 128, 3, padding=1), nn.BatchNorm1d(128), nn.LeakyReLU(0.1))
        self.temporal_attn = TemporalAttentionBlock()
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
    def __init__(self, input_dim=13, static_dim=3, hidden_dim=128, num_layers=2, dropout=0.30):
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


# ── data ──────────────────────────────────────────────────────────────────────
log('loading Campaign B dataset...')
data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
DATA_DIR = sorted(data_base.glob('sim_data_300users_*'))[-1]
bs_pos = np.array(_read_bs_position_3d(DATA_DIR))
df_filt, _, _ = load_and_prepare_data(DATA_DIR, bs_pos, seed=SEED, single_ant_ratio=SINGLE_ANT_RATIO)
df_filt, train_uids, test_uids = make_unseen_user_split(df_filt, TRAIN_RATIO, SEED)
df_tr = df_filt[df_filt.split == 'train']
df_te = df_filt[df_filt.split == 'test']

tr_ds = DerivedCSI1DDataset(df_tr, h=H)
te_ds = DerivedCSI1DDataset(df_te, h=H,
                            sig_mean=tr_ds.sig_mean, sig_std=tr_ds.sig_std,
                            stat_mean=tr_ds.stat_mean, stat_std=tr_ds.stat_std,
                            targ_mean=tr_ds.targ_mean, targ_std=tr_ds.targ_std,
                            speed_mean=tr_ds.speed_mean, speed_std=tr_ds.speed_std)
TS, TM = tr_ds.targ_std, tr_ds.targ_mean
log(f'{len(tr_ds):,} train / {len(te_ds):,} test windows | device={device}')


def flat(ds):
    n = len(ds)
    d = ds.samples[0]['seq'].size + ds.samples[0]['static'].size
    X = np.empty((n, d), dtype=np.float32); Y = np.empty((n, 2), dtype=np.float32)
    uid = np.empty(n, dtype=np.int64); dt = np.empty(n, dtype=np.float64)
    ant = np.empty(n, dtype=np.int64)
    for i, s in enumerate(ds.samples):
        X[i] = np.concatenate([s['seq'].ravel(), s['static'].ravel()])
        Y[i] = s['target']; uid[i] = s['user_id']; dt[i] = s['delta_t']; ant[i] = s['n_antennas']
    return X, Y, uid, dt, ant


Xtr, Ytr, _, _, _ = flat(tr_ds)
Xte, Yte, UID, DT, ANT = flat(te_ds)
Y_m = Yte * TS + TM
TEST_USERS = np.unique(UID)


def train_torch(model, name):
    tl = DataLoader(tr_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    vl = DataLoader(te_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    model = model.to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    es = EarlyStopping(patience=ES_PATIENCE, min_delta=ES_MIN_DELTA, verbose=False)
    huber = nn.HuberLoss()
    for ep in range(EPOCHS):
        model.train()
        for b in tl:
            seq = b['seq'].to(device); st = b['static'].to(device)
            tg = b['target'].to(device); sp = b['speed'].to(device)
            p, s, u = model(seq, st)
            loss = (LAMBDA_POS * huber(p, tg) + LAMBDA_SPEED * huber(s, sp)
                    + LAMBDA_UNC * u.mean())
            opt.zero_grad(); loss.backward(); opt.step()
        model.eval(); errs = []
        with torch.no_grad():
            for b in vl:
                p, _, _ = model(b['seq'].to(device), b['static'].to(device))
                pm = p.cpu().numpy() * TS + TM
                tm_ = b['target'].numpy() * TS + TM
                errs.append(np.linalg.norm(pm - tm_, axis=1))
        vmae = float(np.concatenate(errs).mean())
        log(f'    {name} epoch {ep+1:02d} | val MAE {vmae:.3f} m')
        if es(vmae, model, ep):
            break
    es.restore_best(model)
    model.eval(); preds = []
    with torch.no_grad():
        for b in vl:
            p, _, _ = model(b['seq'].to(device), b['static'].to(device))
            preds.append(p.cpu().numpy())
    return np.concatenate(preds) * TS + TM


def sweep_rts(P_m, name, results):
    raw = float(np.linalg.norm(P_m - Y_m, axis=1).mean())
    grid, best, default = [], None, None
    for q in Q_GRID:
        for r in R_GRID:
            kf, rts = apply_kalman_smoother(P_m, Y_m, UID, DT, TEST_USERS,
                                            process_noise_std=q, R_std=r)
            kf_mae = float(np.linalg.norm(kf - Y_m, axis=1).mean())
            rts_mae = float(np.linalg.norm(rts - Y_m, axis=1).mean())
            rec = dict(Q=q, R=r, kf_mae=round(kf_mae, 4), rts_mae=round(rts_mae, 4),
                       kf_gain_pct=round(100 * (raw - kf_mae) / raw, 2),
                       rts_gain_pct=round(100 * (raw - rts_mae) / raw, 2))
            grid.append(rec)
            if q == 0.5 and r == 15.0:
                default = rec
            if best is None or rts_mae < best['rts_mae']:
                best = rec
    results[name] = dict(raw_mae=round(raw, 4), notebook_default=default, best=best, grid=grid)
    log(f'  {name}: raw {raw:.3f} | default(Q=0.5,R=15) {default["rts_mae"]:.3f} '
        f'({default["rts_gain_pct"]:+.2f}%) | best Q={best["Q"]},R={best["R"]} '
        f'{best["rts_mae"]:.3f} ({best["rts_gain_pct"]:+.2f}%)')
    return results


results = {'meta': dict(dataset=str(DATA_DIR), h=H, seed=SEED,
                        q_grid=Q_GRID, r_grid=R_GRID,
                        n_test_windows=int(len(te_ds)),
                        n_test_users=int(len(TEST_USERS)))}
models = {}

log('=' * 70)
log('classical models')
log('=' * 70)
t = time.time(); knn = KNeighborsRegressor(n_neighbors=5, n_jobs=-1).fit(Xtr, Ytr)
models['knn_h5'] = knn.predict(Xte) * TS + TM
log(f'  k-NN fitted+predicted in {time.time()-t:.1f}s')

t = time.time()
rf = RandomForestRegressor(n_estimators=150, max_features='sqrt', max_depth=16,
                           min_samples_leaf=5, random_state=SEED, n_jobs=-1).fit(Xtr, Ytr)
models['random_forest_h5'] = rf.predict(Xte) * TS + TM
log(f'  Random Forest trained in {time.time()-t:.1f}s')

t = time.time()
xgb = XGBRegressor(n_estimators=50, max_depth=5, learning_rate=0.15, subsample=0.8,
                   colsample_bytree=0.8, random_state=SEED, n_jobs=-1,
                   tree_method='hist', multi_strategy='one_output_per_tree').fit(Xtr, Ytr)
models['xgboost_h5'] = xgb.predict(Xte) * TS + TM
log(f'  XGBoost trained in {time.time()-t:.1f}s')

log('=' * 70)
log('deep models')
log('=' * 70)
for name, net in (('cnn_h5', DerivedCSI1DCNNNet()),
                  ('gru_h5', MultiTaskGRU2DNet()),
                  ('cnn_attn_h5', CNNAttnNet())):
    t = time.time()
    log(f'  training {name}...')
    models[name] = train_torch(net, name)
    log(f'  {name} trained in {time.time()-t:.1f}s')

log('=' * 70)
log('RTS / Kalman sweep')
log('=' * 70)
rts = {}
for name, P in models.items():
    sweep_rts(P, name, rts)
results['models'] = rts

n_rec = sum(1 for v in rts.values() if v['best']['rts_gain_pct'] > 0)
results['verdict'] = dict(
    n_models=len(rts), n_recoverable=n_rec,
    all_recoverable=bool(n_rec == len(rts)),
    default_hurts_all=bool(all(v['notebook_default']['rts_gain_pct'] < 0 for v in rts.values())))
log(f'recoverable with re-tuned Q/R: {n_rec}/{len(rts)} models')

out = OUT_DIR / 'rts_retune_all_models_summary.json'
out.write_text(json.dumps(results, indent=1), encoding='utf-8')
log(f'saved -> {out}')

# markdown summary
lines = ['# Kalman/RTS Re-tune Across Model Families', '',
         f'- Dataset: `{DATA_DIR.name}`', f'- History depth: h={H}, seed={SEED}',
         f'- Test: {len(te_ds):,} windows over {len(TEST_USERS)} unseen users', '',
         '| Model | Raw MAE | RTS @ notebook default (Q=0.5, R=15) | Best RTS | Best (Q, R) |',
         '| :--- | ---: | ---: | ---: | :---: |']
for name, v in rts.items():
    d, b = v['notebook_default'], v['best']
    lines.append(f'| {name} | {v["raw_mae"]:.3f} m | {d["rts_mae"]:.3f} m ({d["rts_gain_pct"]:+.2f}%) '
                 f'| {b["rts_mae"]:.3f} m ({b["rts_gain_pct"]:+.2f}%) | Q={b["Q"]}, R={b["R"]} |')
(OUT_DIR / 'rts_retune_report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
log('DONE')
