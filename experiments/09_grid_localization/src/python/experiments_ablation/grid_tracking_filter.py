"""
Tracking filter on top of a snapshot model, 15x15 controlled grid.

Question: does using history through a motion model (an HMM filter over the cell probabilities of a snapshot model)
give a gain like the learned history of the sequence models? This is the classical way to use transitions and the
baseline a reviewer would ask for.

Snapshot model: XGBoost or Random Forest on the current report only (RSS+SINR, optionally AoA) gives p_t(c) for every
cell. Motion model: the cell-to-cell transition matrix T estimated from the training walks (counts of consecutive grid
points per user). Causal forward filter: alpha_t ∝ (alpha_{t-1} T^g) · p_t(c) / prior(c), where g is the number of
steps since the previous report; prediction = argmax alpha_t. It uses past reports only, like the sequence models.
The forward-backward smoother also uses future reports and is reported only as an upper bound (not causal).

Conditions (as in grid_history_irregular.py, applied to the whole test sequence; scored only at steps with a report):
  regular: every step; mask30 / mask60: each report missing with probability 0.3 / 0.6; gap2 / gap4: reports at
  random gaps, geometric with mean 2 / 4 steps.
Note: on this grid every step moves to a neighbouring cell, so the estimated motion model matches the simulation
almost exactly, which favours the filter.

Usage (from the repository root):
    .venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/grid_tracking_filter.py \
        --data-dir results/grid_localization/grid_15x15/sim_data_ne_bs_2026-10-13_11-23-43 \
        --out-dir results/tracking_filter/ne_mixed
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

CONDITIONS = ['regular', 'mask30', 'mask60', 'gap2', 'gap4']


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def transition_matrix(df_train, l2i, n):
    """Row-stochastic T[i, j] = P(next cell j | cell i), from consecutive steps of each training walk."""
    T = np.zeros((n, n))
    for _, g in df_train.sort_values(['user_id', 'step_index']).groupby('user_id'):
        c = g['grid_point_id'].map(l2i).values
        np.add.at(T, (c[:-1], c[1:]), 1.0)
    T += 1e-6
    return T / T.sum(1, keepdims=True)


def arrivals(n, cond, rng):
    """Boolean mask of the steps that carry a report."""
    if cond == 'regular':
        return np.ones(n, bool)
    if cond.startswith('mask'):
        p = 0.3 if cond == 'mask30' else 0.6
        a = rng.random_sample(n) >= p
        a[0] = True
        return a
    mean_gap = 2.0 if cond == 'gap2' else 4.0
    idx = np.cumsum(rng.geometric(1.0 / mean_gap, size=n)) - 1
    a = np.zeros(n, bool)
    a[idx[idx < n]] = True
    a[0] = True
    return a


def run_filter(P, prior, T_pows, arrive, smooth=False):
    """P [n, C] snapshot probabilities for one user's test sequence. Returns predicted cell index at arrival steps."""
    L = P / np.maximum(prior, 1e-12)
    steps = np.flatnonzero(arrive)
    alpha = []
    a = prior.copy()
    prev = None
    for t in steps:
        if prev is not None:
            a = a @ T_pows(t - prev)
        a = a * L[t]
        a /= a.sum()
        alpha.append(a)
        prev = t
    alpha = np.array(alpha)
    if not smooth:
        return steps, alpha.argmax(1)
    beta = np.ones_like(alpha)
    for k in range(len(steps) - 2, -1, -1):
        Tg = T_pows(steps[k + 1] - steps[k])
        b = Tg @ (L[steps[k + 1]] * beta[k + 1])
        beta[k] = b / b.sum()
    post = alpha * beta
    return steps, post.argmax(1)


def main():
    ap = argparse.ArgumentParser(
        description='HMM tracking filter on top of a snapshot model, 15x15 grid.',
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('Usage')[1])
    ap.add_argument('--data-dir', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--models', nargs='+', default=['xgboost', 'rf'], choices=['xgboost', 'rf'])
    ap.add_argument('--experiments', nargs='+', default=['BASE'], choices=['BASE', 'BASE_A'])
    ap.add_argument('--conditions', nargs='+', default=CONDITIONS, choices=CONDITIONS)
    ap.add_argument('--n-jobs', type=int, default=6)
    args = ap.parse_args()

    mu.N_JOBS = args.n_jobs
    data_dir, out = Path(args.data_dir), Path(args.out_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f'Simulation data not found: {data_dir}')
    out.mkdir(parents=True, exist_ok=True)

    df = mu.make_split(mu.load_all_users(data_dir, sinr_dependent_aoa=True))
    grid_lookup = mu.build_grid_lookup(df)
    spacing = mu.get_grid_spacing(data_dir)
    labels = sorted(df['grid_point_id'].unique())
    l2i = {l: i for i, l in enumerate(labels)}
    i2l = np.array(labels)
    n = len(labels)
    T = transition_matrix(df[df['split'] == 'train'], l2i, n)
    cache = {1: T}

    def T_pows(g):
        if g not in cache:
            cache[g] = np.linalg.matrix_power(T, g)
        return cache[g]
    log(f'{len(df):,} rows, {n} cells; mean self-transition {np.diag(T).mean():.3f}, '
        f'mean nonzero successors {(T > 1e-4).sum(1).mean():.1f}')

    rows, csv_path = [], out / 'tracking_filter.csv'
    for exp in args.experiments:
        aoa = exp == 'BASE_A'
        feat = mu.build_history_features(df, 0, include_aoa=aoa).sort_values(['user_id', 'step_index'])
        cols = mu.get_feature_cols(0, include_aoa=aoa)
        tr = (feat['split'] == 'train').values
        te = feat[~tr]
        y_tr = feat.loc[tr, 'grid_point_id'].map(l2i).values
        prior = np.bincount(y_tr, minlength=n).astype(float)
        prior /= prior.sum()
        for model in args.models:
            t0 = time.time()
            clf = mu.get_model(model, n)
            Xtr = feat.loc[tr, cols].values.astype(np.float32)
            Xte = te[cols].values.astype(np.float32)
            if model == 'rf':
                Xtr, Xte = np.nan_to_num(Xtr), np.nan_to_num(Xte)
            clf.fit(Xtr, y_tr)
            P_all = np.zeros((len(te), n))
            P_all[:, clf.classes_] = clf.predict_proba(Xte)
            log(f'{exp} {model}: snapshot model trained ({time.time() - t0:.0f}s)')
            for cond in args.conditions:
                rng = np.random.RandomState(22)
                res = {'snapshot': ([], []), 'filter': ([], []), 'smoother': ([], [])}
                for uid in te['user_id'].unique():
                    m = (te['user_id'] == uid).values
                    P, y = P_all[m], te.loc[m, 'grid_point_id'].values
                    arrive = arrivals(len(P), cond, rng)
                    steps, pf = run_filter(P, prior, T_pows, arrive)
                    _, ps = run_filter(P, prior, T_pows, arrive, smooth=True)
                    res['snapshot'][0].append(y[steps]); res['snapshot'][1].append(i2l[P[steps].argmax(1)])
                    res['filter'][0].append(y[steps]); res['filter'][1].append(i2l[pf])
                    res['smoother'][0].append(y[steps]); res['smoother'][1].append(i2l[ps])
                for method, (yt, yp) in res.items():
                    r = mu.evaluate_split(np.concatenate(yt), np.concatenate(yp), grid_lookup, spacing=spacing)
                    rows.append(dict(experiment=exp, snapshot_model=model, condition=cond, method=method,
                                     accuracy=round(r['accuracy'], 3), mae=round(r['mae'], 4),
                                     n_scored=int(sum(len(a) for a in yt))))
                    log(f'{exp} {model} {cond:8s} {method:9s}: {r["accuracy"]:.1f}% / {r["mae"]:.2f} m')
                pd.DataFrame(rows).to_csv(csv_path, index=False)
    (out / 'config.json').write_text(json.dumps(dict(data_dir=str(data_dir), models=args.models,
                                                     conditions=args.conditions), indent=2))
    log('[OK] Results saved to: ' + str(csv_path))


if __name__ == '__main__':
    main()
