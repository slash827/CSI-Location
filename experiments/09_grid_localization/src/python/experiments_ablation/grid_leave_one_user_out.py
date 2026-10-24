"""
Leave-one-user-out test on the 15x15 controlled grid.

Question (claim map C5/C6, hypothesis H1): the grid trains and tests on the same users (first 80 % of each walk
against the last 20 %), while the macro study tests on unseen users. Does RSS/SINR, and the gain from history, carry
over to a device the model has never seen?

Two splits, same test rows (the last 20 % of each user's walk):
  time   train on the first 80 % of all five users' walks (the usual split)
  louo   train on the first 80 % of the other four users' walks only; the test user is unseen
Models: XGBoost and Random Forest at h = 0 and h = 3, GRU at h = 0 and h = 10 (one seed). RSS+SINR, no AoA by default.
Also reports how similar the users' channel maps are: correlation between users of the per-cell mean RSS (and SINR).

Usage (from the repository root):
    .venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/grid_leave_one_user_out.py \
        --data-dir results/grid_localization/grid_15x15/sim_data_ne_bs_2026-10-13_11-23-43 \
        --out-dir results/leave_one_user_out/ne_mixed
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pipelines.multi_user_pipeline as mu  # noqa: E402
import grid_history_extended as ghe  # noqa: E402

H_SEQ = 10


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def main():
    ap = argparse.ArgumentParser(
        description='Leave-one-user-out test on the 15x15 grid.',
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('Usage')[1])
    ap.add_argument('--data-dir', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--experiment', default='BASE', choices=['BASE', 'BASE_A'])
    ap.add_argument('--n-jobs', type=int, default=6)
    args = ap.parse_args()

    import torch
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    mu.N_JOBS = args.n_jobs
    data_dir, out = Path(args.data_dir), Path(args.out_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f'Simulation data not found: {data_dir}')
    out.mkdir(parents=True, exist_ok=True)
    aoa = args.experiment == 'BASE_A'

    df = mu.make_split(mu.load_all_users(data_dir, sinr_dependent_aoa=True))
    grid_lookup = mu.build_grid_lookup(df)
    spacing = mu.get_grid_spacing(data_dir)
    labels = sorted(df['grid_point_id'].unique())
    l2i = {l: i for i, l in enumerate(labels)}
    i2l = np.array(labels)
    n = len(labels)
    users = sorted(df['user_id'].unique())

    # how similar are the users' channel maps? per-cell mean, correlation between users
    maps = {}
    for ch in ('rss', 'sinr'):
        pc = df.groupby(['user_id', 'grid_point_id'])[ch].mean().unstack(0)
        maps[ch] = pc.corr().round(3)
        off = (pc.sub(pc.mean(1), axis=0)).mean().round(2)
        log(f'{ch}: per-cell mean correlation between users\n{maps[ch]}\nmean offset per user (dB): {off.to_dict()}')
    (out / 'map_similarity.json').write_text(json.dumps({k: v.to_dict() for k, v in maps.items()}, indent=2))

    feat = mu.build_history_features(df, H_SEQ, include_aoa=aoa).sort_values(['user_id', 'step_index']).reset_index(drop=True)
    is_tr = (feat['split'] == 'train').values
    y = feat['grid_point_id'].map(l2i).values.astype(np.int64)

    rows, csv_path = [], out / 'leave_one_user_out.csv'

    def score(model, h, split, test_user, pred_lab):
        m = (feat['user_id'].values == test_user) & ~is_tr
        r = mu.evaluate_split(feat.loc[m, 'grid_point_id'].values, pred_lab, grid_lookup, spacing=spacing)
        rows.append(dict(model=model, h=h, split=split, test_user=int(test_user), accuracy=round(r['accuracy'], 3),
                         mae=round(r['mae'], 4)))
        log(f'{split:5s} {model:8s} h={h:2d} user {test_user}: {r["accuracy"]:.1f}% / {r["mae"]:.2f} m')

    def fit_predict(model, h, train_mask, test_mask):
        if model in ('xgboost', 'rf'):
            cols = mu.get_feature_cols(h, include_aoa=aoa)
            Xtr = feat.loc[train_mask, cols].values.astype(np.float32)
            Xte = feat.loc[test_mask, cols].values.astype(np.float32)
            if model == 'rf':
                Xtr, Xte = np.nan_to_num(Xtr), np.nan_to_num(Xte)
            ytr = y[train_mask]
            present = np.unique(ytr)
            clf = mu.get_model(model, len(present))
            remap = {c: i for i, c in enumerate(present)}
            clf.fit(Xtr, np.array([remap[c] for c in ytr]))
            return i2l[present[clf.predict(Xte)]]
        trf = feat[train_mask].reset_index(drop=True)
        val = np.zeros(len(trf), bool)
        for _, g in trf.groupby('user_id'):
            val[g.index[int(len(g) * 0.9):]] = True
        st = {c: (trf[f'{c}_lag0'].mean(), trf[f'{c}_lag0'].std() + 1e-6) for c in ('rss', 'sinr')}
        X = ghe.sequence_tensor(trf, h, aoa, st)
        ytr = y[train_mask]
        pred, _, _ = ghe.train_cnn(X[~val], ytr[~val], X[val], ytr[val], ghe.sequence_tensor(feat[test_mask], h, aoa, st),
                                   n, 0, device, kind='gru')
        return i2l[pred]

    configs = [('xgboost', 0), ('xgboost', 3), ('rf', 0), ('rf', 3), ('gru', 0), ('gru', H_SEQ)]
    for model, h in configs:
        t0 = time.time()
        # time split: one model on all users, scored per user
        test_all = ~is_tr
        pred = fit_predict(model, h, is_tr, test_all)
        uid_te = feat.loc[test_all, 'user_id'].values
        for u in users:
            score(model, h, 'time', u, pred[uid_te == u])
        # leave one user out
        for u in users:
            tr_m = is_tr & (feat['user_id'].values != u)
            te_m = (~is_tr) & (feat['user_id'].values == u)
            score(model, h, 'louo', u, fit_predict(model, h, tr_m, te_m))
        pd.DataFrame(rows).to_csv(csv_path, index=False)
        log(f'{model} h={h} done ({time.time() - t0:.0f}s)')

    res = pd.DataFrame(rows)
    summ = res.groupby(['model', 'h', 'split'])[['accuracy', 'mae']].mean().round(3).unstack('split')
    summ.to_csv(out / 'leave_one_user_out_summary.csv')
    log('[OK] Results saved to: ' + str(csv_path) + '\n' + summ.to_string())


if __name__ == '__main__':
    main()
