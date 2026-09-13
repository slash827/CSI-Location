"""
B1: Is the h=5 optimum about SIX SAMPLES or about TWO AND A HALF SECONDS?

This is the largest unexamined confound in the study. Step duration is
spacing / speed, and the Campaign B population spans 0.17 to 20 m/s, so per-user
delta_t ranges 0.27 s to 32.5 s. A fixed history depth therefore covers a window
of anywhere from 1.3 s to 162 s depending on who the user is, and every history
result published so far is averaged over that spread.

Until the two are separated, "h=5 is optimal" can only mean "six samples", and any
physical reading in terms of coherence time or heading decorrelation is
unsupported.

PRE-REGISTERED SUCCESS CRITERION, fixed before running:

  * If per-class optima coincide in SAMPLES (every class peaking at the same h
    regardless of its very different window durations), the effect is
    architectural - a property of how many lags the estimator can use.

  * If per-class optima coincide in SECONDS (classes peaking at different h such
    that h * delta_t is similar), the effect is physical - a property of channel
    or motion coherence.

  * If neither, the optimum is driven by something else again, and the report must
    say so.

Either outcome is publishable. The current pooled result is not interpretable.

Two models are swept: the 1D-CNN, which turns at h=10 and therefore has a genuine
optimum to locate, and XGBoost, which saturates instead - if the effect is
physical it should show in both, and if it is architectural the two should differ.

Usage:
    python history_by_speed_class.py
    python history_by_speed_class.py --depths 0 1 3 5 10 --models cnn xgboost
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'src' / 'python'))

from pipelines.multi_user_pipeline_regression import _read_bs_position_3d
from pipelines.multi_user_200_pipeline import make_unseen_user_split
from utils.csi_dataset import DerivedCSI1DDataset, load_and_prepare_data
from utils.training_utils import EarlyStopping
from xgboost import XGBRegressor

# speed classes chosen to match the generator's own strata
# (run_multi_user_300_25x25.m: static, pedestrian, jogger, vehicle)
SPEED_CLASSES = [(0.0, 0.8, 'static'), (0.8, 2.0, 'pedestrian'),
                 (2.0, 6.0, 'jogger'), (6.0, 999.0, 'vehicle')]

DROPOUT = 0.35
BATCH_SIZE = 512
EPOCHS = 60
LR = 3e-4
WEIGHT_DECAY = 1e-2
ES_PATIENCE = 8
ES_MIN_DELTA = 0.05
LAMBDA_POS, LAMBDA_SPEED, LAMBDA_UNC = 1.0, 0.2, 0.05

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


class DerivedCSI1DCNNNet(nn.Module):
    """Transcribed from notebook 06."""

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


def flatten(ds):
    n = len(ds)
    d = ds.samples[0]['seq'].size + ds.samples[0]['static'].size
    X = np.empty((n, d), np.float32)
    Y = np.empty((n, 2), np.float32)
    uid = np.empty(n, np.int64)
    dt = np.empty(n, np.float64)
    for i, s in enumerate(ds.samples):
        X[i] = np.concatenate([s['seq'].ravel(), s['static'].ravel()])
        Y[i] = s['target']
        uid[i] = s['user_id']
        dt[i] = s['delta_t']
    return X, Y, uid, dt


def train_cnn(tr_ds, te_ds, ts, tm, seed):
    torch.manual_seed(seed)
    tl = DataLoader(tr_ds, batch_size=BATCH_SIZE, shuffle=True)
    vl = DataLoader(te_ds, batch_size=BATCH_SIZE, shuffle=False)
    model = DerivedCSI1DCNNNet().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    es = EarlyStopping(patience=ES_PATIENCE, min_delta=ES_MIN_DELTA, verbose=False)
    huber = nn.HuberLoss()
    for ep in range(EPOCHS):
        model.train()
        for b in tl:
            p, s, u = model(b['seq'].to(device), b['static'].to(device))
            loss = (LAMBDA_POS * huber(p, b['target'].to(device))
                    + LAMBDA_SPEED * huber(s, b['speed'].to(device))
                    + LAMBDA_UNC * u.mean())
            opt.zero_grad(); loss.backward(); opt.step()
        model.eval(); errs = []
        with torch.no_grad():
            for b in vl:
                p, _, _ = model(b['seq'].to(device), b['static'].to(device))
                errs.append(np.linalg.norm(p.cpu().numpy() * ts + tm
                                           - (b['target'].numpy() * ts + tm), axis=1))
        if es(float(np.concatenate(errs).mean()), model, ep):
            break
    es.restore_best(model)
    model.eval(); preds = []
    with torch.no_grad():
        for b in vl:
            p, _, _ = model(b['seq'].to(device), b['static'].to(device))
            preds.append(p.cpu().numpy())
    return np.concatenate(preds) * ts + tm


def main():
    ap = argparse.ArgumentParser(
        description='Separate history depth from elapsed time (B1).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python history_by_speed_class.py
  python history_by_speed_class.py --models xgboost --depths 0 1 3 5 10 15
""")
    ap.add_argument('--depths', type=int, nargs='+', default=[0, 1, 3, 5, 10])
    ap.add_argument('--models', nargs='+', default=['xgboost', 'cnn'],
                    choices=['xgboost', 'cnn'])
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--single-ant-ratio', type=float, default=0.15)
    args = ap.parse_args()

    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'history_by_speed_class_{run_ts}')
    out_dir.mkdir(parents=True, exist_ok=True)

    log(f'device={device} | models={args.models} | depths={args.depths}')
    data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
    data_dir = sorted(data_base.glob('sim_data_300users_*'))[-1]
    bs_pos = np.array(_read_bs_position_3d(data_dir))
    df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=args.seed,
                                     single_ant_ratio=args.single_ant_ratio)
    df, _, _ = make_unseen_user_split(df, 0.8, args.seed)
    df_tr, df_te = df[df.split == 'train'], df[df.split == 'test']

    user_speed = df_te.groupby('user_id').speed_m_s.first()

    def class_of(uid_arr):
        sp = user_speed.reindex(uid_arr).values
        out = np.full(len(uid_arr), -1, dtype=int)
        for i, (lo, hi, _) in enumerate(SPEED_CLASSES):
            out[(sp >= lo) & (sp < hi)] = i
        return out

    results = {'meta': {'dataset': str(data_dir), 'seed': args.seed,
                        'depths': args.depths, 'models': args.models,
                        'speed_classes': [{'lo': lo, 'hi': hi, 'name': n}
                                          for lo, hi, n in SPEED_CLASSES],
                        'criterion': 'optima aligned in samples => architectural; '
                                     'aligned in seconds => physical'},
               'by_model': {}}

    for mname in args.models:
        log('=' * 84)
        log(f'MODEL: {mname}')
        log('=' * 84)
        per_depth = {}
        for h in args.depths:
            t0 = time.time()
            tr = DerivedCSI1DDataset(df_tr, h=h)
            te = DerivedCSI1DDataset(df_te, h=h,
                                     sig_mean=tr.sig_mean, sig_std=tr.sig_std,
                                     stat_mean=tr.stat_mean, stat_std=tr.stat_std,
                                     targ_mean=tr.targ_mean, targ_std=tr.targ_std,
                                     speed_mean=tr.speed_mean, speed_std=tr.speed_std)
            ts, tm = tr.targ_std, tr.targ_mean
            X_tr, Y_tr, _, _ = flatten(tr)
            X_te, Y_te, uid_te, dt_te = flatten(te)
            true = Y_te * ts + tm

            if mname == 'xgboost':
                model = XGBRegressor(n_estimators=50, max_depth=5, learning_rate=0.15,
                                     subsample=0.8, colsample_bytree=0.8,
                                     random_state=args.seed, n_jobs=-1,
                                     tree_method='hist',
                                     multi_strategy='one_output_per_tree')
                model.fit(X_tr, Y_tr)
                pred = model.predict(X_te) * ts + tm
            else:
                pred = train_cnn(tr, te, ts, tm, args.seed)

            err = np.linalg.norm(pred - true, axis=1)
            cls = class_of(uid_te)
            rec = {'overall_mae': float(err.mean()),
                   'elapsed_sec': round(time.time() - t0, 1), 'classes': {}}
            for i, (_, _, cname) in enumerate(SPEED_CLASSES):
                m = cls == i
                if not m.any():
                    continue
                median_dt = float(np.median(dt_te[m]))
                rec['classes'][cname] = {
                    'mae': float(err[m].mean()), 'n': int(m.sum()),
                    'median_dt_s': median_dt,
                    'window_sec': round(h * median_dt, 2)}
            per_depth[h] = rec
            log(f'  h={h:<2d} overall {rec["overall_mae"]:6.3f} | '
                + ' '.join(f'{c}={rec["classes"][c]["mae"]:6.3f}'
                           for c in rec['classes'])
                + f' | {rec["elapsed_sec"]:.0f}s')

        # per class: locate the optimum in samples and in seconds
        log('-' * 84)
        log(f'{"class":<12}{"n":>7}{"dt":>7}' +
            ''.join(f'{"h="+str(h):>9}' for h in args.depths) +
            f'{"best h":>8}{"window s":>10}{"gain":>8}')
        log('-' * 84)
        summary = {}
        for _, _, cname in SPEED_CLASSES:
            if cname not in per_depth[args.depths[0]]['classes']:
                continue
            maes = [per_depth[h]['classes'][cname]['mae'] for h in args.depths]
            best_i = int(np.argmin(maes))
            best_h = args.depths[best_i]
            info = per_depth[best_h]['classes'][cname]
            gain = 100.0 * (maes[0] - maes[best_i]) / maes[0]
            summary[cname] = {
                'maes': dict(zip([f'h={h}' for h in args.depths],
                                 [round(m, 4) for m in maes])),
                'best_h': best_h,
                'best_window_sec': info['window_sec'],
                'median_dt_s': round(info['median_dt_s'], 3),
                'gain_pct': round(gain, 2),
                'n': info['n']}
            log(f'{cname:<12}{info["n"]:>7}{info["median_dt_s"]:>7.2f}'
                + ''.join(f'{m:>9.3f}' for m in maes)
                + f'{best_h:>8}{info["window_sec"]:>10.1f}{gain:>7.2f}%')

        best_hs = [v['best_h'] for v in summary.values()]
        best_secs = [v['best_window_sec'] for v in summary.values()]
        aligned_samples = len(set(best_hs)) == 1
        # "aligned in seconds" = spread of optimal windows small relative to their mean
        sec_spread = (max(best_secs) - min(best_secs)) / max(np.mean(best_secs), 1e-9)
        aligned_seconds = sec_spread < 0.5
        results['by_model'][mname] = {
            'per_depth': {f'h={h}': per_depth[h] for h in args.depths},
            'per_class': summary,
            'best_h_per_class': dict(zip(summary.keys(), best_hs)),
            'best_window_sec_per_class': dict(zip(summary.keys(), best_secs)),
            'aligned_in_samples': bool(aligned_samples),
            'aligned_in_seconds': bool(aligned_seconds),
            'window_sec_relative_spread': round(float(sec_spread), 3),
        }
        log('-' * 84)
        log(f'  optimal h per class : {dict(zip(summary.keys(), best_hs))}')
        log(f'  optimal window (s)  : {dict(zip(summary.keys(), best_secs))}')
        log(f'  aligned in SAMPLES  : {aligned_samples}')
        log(f'  aligned in SECONDS  : {aligned_seconds} '
            f'(relative spread {sec_spread:.2f})')
        if aligned_samples and not aligned_seconds:
            log('  => ARCHITECTURAL: the optimum tracks lag count, not elapsed time')
        elif aligned_seconds and not aligned_samples:
            log('  => PHYSICAL: the optimum tracks elapsed time, not lag count')
        else:
            log('  => INCONCLUSIVE on this criterion - see per-class curves')

    out = out_dir / 'history_by_speed_class_summary.json'
    out.write_text(json.dumps(results, indent=1), encoding='utf-8')
    log(f'saved -> {out}')


if __name__ == '__main__':
    sys.exit(main())
