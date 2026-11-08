"""
Absolute values against differences, and generalization to unseen devices (macro cell).

Question (Dudi, 2026-11-01): does a model that sees the *changes* between consecutive
reports generalize better to devices it has not seen than a model that sees the absolute
values, especially as the devices differ more?

Data: the 300-user mixed-propagation macro cell (Campaign B), with the same loading, AoA
noise model and single-antenna share (15 %) as the macro results of record, and the
disjoint-user split (test users are never seen in training). Unlike the macro results of
record, the static device features (antenna count, antenna gain, height) are NOT given to
the models: the point is to see what each representation does without being told the device.

Representations of the RSS/SINR window (h reports back plus the current one):
  snap    absolute at lag 0 only (h = 0), the single-report reference
  abs     absolute RSS and SINR at lags 0..h
  diff    only the differences between consecutive reports (h of them per metric)
  both    absolute at lags 0..h and the differences
  wnorm   absolute minus the mean of the window (removes any constant per-device offset;
          the competing "per-device normalization" baseline)
With --aoa the AoA embeddings (sin/cos of azimuth and elevation, absolute, all lags) are
added to every representation; the angle is measured at the BS, not by the device.

Device heterogeneity, applied to the TEST users only (the training devices are the known
ones; the test devices are new and differ from them):
  offset   a constant per-device RSS offset drawn from N(0, sigma^2) dB (antenna gain,
           calibration); differences cancel it exactly, so this is the easy case
  drift    the same offset plus a slow per-device random walk (0.1 dB per report,
           calibration drift); differences do not cancel this fully
  quant    the same offset plus a coarser RSS report (2 dB steps)
SINR is left unchanged (a receive-gain error scales signal and interference alike). The
simulation already varies the antenna gain by -4 to +2 dB and the height by 0.8 to 1.8 m
between users, so sigma = 0 is not a homogeneous fleet.

--class-split: train only on 4-antenna devices; test on unseen 4-antenna (in class),
2-antenna and 1-antenna devices (out of class).

Usage (from the repository root):
    .venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/device_generalization.py \
        --out-dir results/device_generalization/macro_mixed
    ... --aoa --out-dir results/device_generalization/macro_mixed_aoa
    ... --class-split --out-dir results/device_generalization/macro_mixed_class
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_zoo as Z  # noqa: E402  (also puts src/python on the path)
from model_zoo import PROJECT_ROOT, log  # noqa: E402

from pipelines.multi_user_pipeline_regression import _read_bs_position_3d  # noqa: E402
from pipelines.multi_user_200_pipeline import make_unseen_user_split  # noqa: E402
from utils.csi_dataset import load_and_prepare_data  # noqa: E402

REPS = ['snap', 'abs', 'diff', 'both', 'wnorm']
CONDITIONS = [('offset', 0.0), ('offset', 3.0), ('offset', 6.0), ('offset', 10.0), ('offset', 15.0), ('offset', 20.0),
              ('drift', 6.0), ('quant', 6.0)]
DRIFT_STEP_DB = 0.1
QUANT_STEP_DB = 2.0
TRIG = ['sin_az', 'cos_az', 'sin_el', 'cos_el']


def perturb_rss(df, kind, sigma, seed):
    """Return a copy of df with a per-device RSS impairment (one draw per user)."""
    df = df.copy()
    if sigma == 0 and kind == 'offset':
        return df
    rng = np.random.RandomState(seed)
    out = df['rss'].values.astype(float).copy()
    for uid, idx in df.groupby('user_id').indices.items():
        order = idx[np.argsort(df['step_index'].values[idx])]
        v = out[order] + rng.randn() * sigma
        if kind == 'drift':
            v = v + np.cumsum(rng.randn(len(order)) * DRIFT_STEP_DB)
        elif kind == 'quant':
            v = np.round(v / QUANT_STEP_DB) * QUANT_STEP_DB
        out[order] = v
    df['rss'] = out
    return df


def window_features(df, rep, h, aoa):
    """Build the feature matrix for one representation. Returns X, Y, n_antennas, user_id."""
    df = df.sort_values(['user_id', 'step_index']).reset_index(drop=True)
    g = df.groupby('user_id')
    hh = 0 if rep == 'snap' else h
    lag = {}
    for c in ['rss', 'sinr'] + (TRIG if aoa else []):
        for k in range(hh + 1):
            lag[(c, k)] = g[c].shift(k).values
    cols = []
    if rep in ('snap', 'abs', 'both'):
        cols += [lag[(c, k)] for c in ('rss', 'sinr') for k in range(hh + 1)]
    if rep in ('diff', 'both'):
        cols += [lag[(c, k)] - lag[(c, k + 1)] for c in ('rss', 'sinr') for k in range(hh)]
    if rep == 'wnorm':
        for c in ('rss', 'sinr'):
            m = np.mean([lag[(c, k)] for k in range(hh + 1)], axis=0)
            cols += [lag[(c, k)] - m for k in range(hh + 1)]
    if aoa:
        cols += [lag[(c, k)] for c in TRIG for k in range(hh + 1)]
    X = np.column_stack(cols).astype(np.float32)
    # rows with a full window (h earlier reports of the same user)
    valid = ~np.isnan(np.column_stack([lag[('rss', hh)]])).any(1)
    Y = df[['target_x', 'target_y']].values.astype(np.float32)
    cross = crossing_flags(df, hh)
    return X[valid], Y[valid], df['n_antennas'].values[valid], df['user_id'].values[valid], cross[valid]


def sequence_features(df, rep, h, aoa):
    """Same representations as window_features, as a sequence [N, L, C] for the GRU (oldest first).

    abs: (rss, sinr) per report; diff: (d rss, d sinr) per report, the difference to the report
    before it (so diff and both need one report more of history); both: the four together;
    wnorm: (rss, sinr) minus the window mean; snap: one report. AoA embeddings per report if aoa.
    """
    df = df.sort_values(['user_id', 'step_index']).reset_index(drop=True)
    g = df.groupby('user_id')
    hh = 0 if rep == 'snap' else h
    need = hh + 1 if rep in ('diff', 'both') else hh
    lag = {(c, k): g[c].shift(k).values for c in ['rss', 'sinr'] + (TRIG if aoa else []) for k in range(need + 1)}
    steps = []
    for k in range(hh, -1, -1):
        ch = []
        if rep in ('snap', 'abs', 'both'):
            ch += [lag[('rss', k)], lag[('sinr', k)]]
        if rep in ('diff', 'both'):
            ch += [lag[('rss', k)] - lag[('rss', k + 1)], lag[('sinr', k)] - lag[('sinr', k + 1)]]
        if rep == 'wnorm':
            for c in ('rss', 'sinr'):
                ch.append(lag[(c, k)] - np.mean([lag[(c, j)] for j in range(hh + 1)], axis=0))
        if aoa:
            ch += [lag[(c, k)] for c in TRIG]
        steps.append(np.column_stack(ch))
    X = np.stack(steps, axis=1).astype(np.float32)
    valid = ~np.isnan(lag[('rss', need)])
    Y = df[['target_x', 'target_y']].values.astype(np.float32)
    cross = crossing_flags(df, need)
    return X[valid], Y[valid], df['n_antennas'].values[valid], df['user_id'].values[valid], cross[valid]


def crossing_flags(df, span):
    """True where the reports of the window (current and `span` earlier) lie in more than one
    Voronoi zone, i.e. the window spans a change of propagation segment. In the simulation each
    segment is generated separately, so the signal can step there for a reason that is not the
    channel; these windows are where a model could read the zone boundary instead of the map.
    df must be sorted by user and step."""
    if 'zone_code' not in df.columns:
        return np.zeros(len(df), bool)
    g = df.groupby('user_id')['zone_code']
    z0 = df['zone_code'].values
    cross = np.zeros(len(df), bool)
    for k in range(1, span + 1):
        zk = g.shift(k).values
        cross |= ~np.isnan(zk) & (zk != z0)
    return cross


class GRURegressor:
    """One-layer GRU on the report sequence; early stopping on held-out TRAINING users."""

    def __init__(self, seed, device, hidden=64, epochs=40, patience=5, lr=2e-3, batch=512):
        self.seed, self.device, self.hidden = seed, device, hidden
        self.epochs, self.patience, self.lr, self.batch = epochs, patience, lr, batch

    def fit(self, X, Y, uid):
        import torch
        import torch.nn as nn
        torch.manual_seed(self.seed)
        self.xm = np.nanmean(X, axis=(0, 1)); self.xs = np.nanstd(X, axis=(0, 1)) + 1e-6
        self.ym = Y.mean(0); self.ys = Y.std(0) + 1e-6
        users = np.unique(uid)
        val_users = np.random.RandomState(self.seed).choice(users, max(1, len(users) // 10), replace=False)
        v = np.isin(uid, val_users)

        class Net(nn.Module):
            def __init__(s, c, hdim):
                super().__init__()
                s.gru = nn.GRU(c, hdim, batch_first=True)
                s.head = nn.Sequential(nn.Linear(hdim, hdim), nn.ReLU(), nn.Linear(hdim, 2))

            def forward(s, x):
                return s.head(s.gru(x)[0][:, -1])

        self.net = Net(X.shape[2], self.hidden).to(self.device)
        Xt, Yt = self._x(X), torch.tensor((Y - self.ym) / self.ys, dtype=torch.float32)
        opt = torch.optim.AdamW(self.net.parameters(), lr=self.lr, weight_decay=1e-3)
        loss_fn = nn.HuberLoss()
        tr_idx, va_idx = np.where(~v)[0], np.where(v)[0]
        best, best_state, bad = np.inf, None, 0
        for ep in range(self.epochs):
            self.net.train()
            perm = np.random.RandomState(self.seed + ep).permutation(tr_idx)
            for i in range(0, len(perm), self.batch):
                b = perm[i:i + self.batch]
                loss = loss_fn(self.net(Xt[b].to(self.device)), Yt[b].to(self.device))
                opt.zero_grad(); loss.backward(); opt.step()
            vm = np.linalg.norm((self._predict(Xt[va_idx]) - Y[va_idx]), axis=1).mean()
            if vm < best - 0.02:
                best, bad = vm, 0
                best_state = {k: t.detach().clone() for k, t in self.net.state_dict().items()}
            else:
                bad += 1
                if bad >= self.patience:
                    break
        self.net.load_state_dict(best_state)
        return self

    def _x(self, X):
        import torch
        return torch.tensor(np.nan_to_num((X - self.xm) / self.xs), dtype=torch.float32)

    def _predict(self, Xt):
        import torch
        self.net.eval()
        out = []
        with torch.no_grad():
            for i in range(0, len(Xt), 8192):
                out.append(self.net(Xt[i:i + 8192].to(self.device)).cpu().numpy())
        return np.concatenate(out) * self.ys + self.ym

    def predict(self, X):
        return self._predict(self._x(X))


def read_device_classes(data_dir):
    """user_id -> device_class for datasets that save it (run_shared_env_devices.m); {} otherwise."""
    from scipy.io import loadmat
    out = {}
    for f in sorted((Path(data_dir) / 'mat_files').glob('user*_*.mat')):
        m = loadmat(str(f), variable_names=['user_id_val', 'device_class'], squeeze_me=True)
        if 'device_class' in m:
            out[int(m['user_id_val'])] = str(m['device_class'])
    return out


def mask_aoa(df):
    """Single-antenna devices report no angle: zero their trig embeddings."""
    df = df.copy()
    df.loc[df['n_antennas'] <= 1, TRIG] = 0.0
    return df


def main():
    ap = argparse.ArgumentParser(
        description='Absolute values against differences, and transfer to unseen devices (macro cell).',
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('Usage')[1])
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--data-dir', default=None,
                    help='simulation folder (relative to the repository root); default: the latest 300-user mixed run')
    ap.add_argument('--train-classes', nargs='+', default=None,
                    help='with --class-split and a dataset that saves device_class (run_shared_env_devices.m): '
                         'train only on these classes, e.g. --train-classes flagship midtier')
    ap.add_argument('--aoa', action='store_true', help='add the (BS-side) AoA embeddings to every representation')
    ap.add_argument('--class-split', action='store_true', help='train on 4-antenna devices only')
    ap.add_argument('--drop-crossings', action='store_true',
                    help='train and test only on windows inside one Voronoi zone (boundary-artifact check)')
    ap.add_argument('--h', type=int, default=5)
    ap.add_argument('--seeds', type=int, nargs='+', default=[42, 43, 44, 45, 46])
    ap.add_argument('--models', nargs='+', default=['xgboost', 'random_forest'],
                    choices=['xgboost', 'random_forest', 'knn', 'gru'])
    args = ap.parse_args()

    out = PROJECT_ROOT / args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
    data_dir = (PROJECT_ROOT / args.data_dir) if args.data_dir else sorted(data_base.glob('sim_data_300users_*'))[-1]
    if not data_dir.exists():
        raise FileNotFoundError(f'Simulation data not found: {data_dir}')
    bs_pos = np.array(_read_bs_position_3d(data_dir))
    log(f'data={data_dir.name} aoa={args.aoa} class_split={args.class_split} h={args.h} seeds={args.seeds}')

    df0, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=42, single_ant_ratio=Z.SINGLE_ANT_RATIO)
    df0 = mask_aoa(df0)
    df0['device_class'] = df0['user_id'].map(read_device_classes(data_dir)).fillna(
        'ant' + df0['n_antennas'].astype(int).astype(str))
    log(f'{df0.user_id.nunique()} users, {len(df0):,} rows; antennas: '
        f'{df0.groupby("user_id").n_antennas.first().value_counts().to_dict()}')

    if 'voronoi_zone_name' in df0.columns and df0['voronoi_zone_name'].notna().any():
        df0['zone_code'] = pd.factorize(df0['voronoi_zone_name'].astype(str))[0].astype(float)
        log(f'zones: {df0["voronoi_zone_name"].value_counts().to_dict()}')
    uid_class = df0.groupby('user_id')['device_class'].first().to_dict()
    log(f'device classes: {pd.Series(uid_class).value_counts().to_dict()}')
    rows, csv_path = [], out / 'device_generalization.csv'
    torch_device = Z.get_device()

    def drop(feats):
        """With --drop-crossings, remove windows that span a Voronoi-zone change."""
        if not args.drop_crossings:
            return feats
        keep = ~feats[4]
        return tuple(a[keep] for a in feats)
    t_all = time.time()
    for seed in args.seeds:
        df, _, _ = make_unseen_user_split(df0.copy(), Z.TRAIN_RATIO, seed)
        tr = df[df.split == 'train']
        te = df[df.split == 'test']
        if args.class_split:
            tr = tr[tr.device_class.isin(args.train_classes)] if args.train_classes else tr[tr.n_antennas == 4]
        test_sets = {cond: perturb_rss(te, cond[0], cond[1], seed * 100 + i)
                     for i, cond in enumerate(CONDITIONS)}
        for rep in REPS:
            flat = [m for m in args.models if m != 'gru']
            if flat:
                Xtr, Ytr, _, _, Ctr = window_features(tr, rep, args.h, args.aoa)
                if args.drop_crossings:
                    Xtr, Ytr = Xtr[~Ctr], Ytr[~Ctr]
                te_flat = {c: drop(window_features(d, rep, args.h, args.aoa)) for c, d in test_sets.items()}
            if 'gru' in args.models:
                Str, SYtr, _, Suid, SCtr = sequence_features(tr, rep, args.h, args.aoa)
                if args.drop_crossings:
                    Str, SYtr, Suid = Str[~SCtr], SYtr[~SCtr], Suid[~SCtr]
                te_seq = {c: drop(sequence_features(d, rep, args.h, args.aoa)) for c, d in test_sets.items()}
            for model in args.models:
                t0 = time.time()
                if model == 'gru':
                    est = GRURegressor(seed, torch_device).fit(Str, SYtr, Suid)
                    te_feats = te_seq
                else:
                    est = Z.build_classical(model, seed)
                    est.fit(np.nan_to_num(Xtr) if model != 'xgboost' else Xtr, Ytr)
                    te_feats = te_flat
                for (kind, sigma), (Xte, Yte, ant, uid, cross) in te_feats.items():
                    P = est.predict(np.nan_to_num(Xte) if model not in ('xgboost', 'gru') else Xte)
                    err = np.linalg.norm(P - Yte, axis=1)
                    groups = {'all': np.ones(len(err), bool), 'multi': ant > 1, 'single': ant == 1}
                    cls = pd.Series(uid).map(uid_class).values
                    groups.update({f'cls_{c}': cls == c for c in sorted(set(cls))})
                    groups.update({'crossing': cross, 'interior': ~cross})
                    for gname, m in groups.items():
                        if m.any():
                            rows.append(dict(seed=seed, model=model, rep=rep, h=0 if rep == 'snap' else args.h,
                                             cond=kind, sigma=sigma, group=gname, n=int(m.sum()),
                                             mae=round(float(err[m].mean()), 4)))
                log(f'seed {seed} {model:13s} {rep:5s}: '
                    + ' '.join(f'{k[0][0]}{k[1]:g}={np.mean([r["mae"] for r in rows if r["seed"] == seed and r["model"] == model and r["rep"] == rep and r["cond"] == k[0] and r["sigma"] == k[1] and r["group"] == "all"]):.2f}'
                               for k in CONDITIONS)
                    + f' ({time.time() - t0:.0f}s)')
                pd.DataFrame(rows).to_csv(csv_path, index=False)

    res = pd.DataFrame(rows)
    summ = (res.groupby(['model', 'group', 'cond', 'sigma', 'rep'])['mae']
            .agg(['mean', 'std']).round(3).reset_index())
    summ.to_csv(out / 'device_generalization_summary.csv', index=False)
    piv = summ.pivot_table(
        index=['model', 'group', 'cond', 'sigma'], columns='rep', values='mean')[REPS]
    (out / 'device_generalization_summary.txt').write_text(piv.round(2).to_string())
    (out / 'run_info.json').write_text(json.dumps(dict(
        data=str(data_dir), aoa=args.aoa, class_split=args.class_split, h=args.h, seeds=args.seeds,
        models=args.models, conditions=CONDITIONS, drift_step_db=DRIFT_STEP_DB, quant_step_db=QUANT_STEP_DB,
        static_device_features='not used', minutes=round((time.time() - t_all) / 60, 1)), indent=2))
    log('[OK] Report saved to: ' + str(out / 'device_generalization_summary.txt') + '\n' + piv.round(2).to_string())


if __name__ == '__main__':
    main()
