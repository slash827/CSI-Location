"""
Irregular and incomplete history on the 15x15 controlled grid.

Question: in practice a user's report history is not a clean, evenly spaced sequence. Do sequence models still gain from
history when older reports are missing (masked) or arrive at uneven times, and does giving the model the time of each
report help? Reference: the regular window (the reports at lags 0..K).

Every condition gives the model the current report plus K older reports. Per report the network receives RSS, SINR
(standardized; with AoA also sin/cos azimuth, elevation, AoA validity), a validity flag for the report, and, unless
the condition hides it, the report's age in steps (lag / LAG_SCALE). Conditions:
  regular       lags 1..K
  mask30/mask60 lags 1..K, each older report dropped with probability 0.3 / 0.6 (zeroed, validity flag 0)
  gap2/gap4     K older reports at irregular lags: gaps between reports ~ Geometric with mean 2 / 4 steps
  gap2_noage    as gap2, but without the age channel (does knowing the timestamps matter?)
  mismatch_gap2 network trained on regular windows, tested on gap2 windows (robustness, no retraining)
  snapshot      current report only (K = 0)
Test windows are drawn with their own random seed. XGBoost is run on the flattened inputs of regular, mask30 and gap2
(dropped reports as NaN, age as a feature) as the tree reference.

Usage (from the repository root):
    .venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/grid_history_irregular.py \
        --data-dir results/grid_localization/grid_15x15/sim_data_ne_bs_2026-10-13_11-23-43 \
        --out-dir results/history_irregular/ne_mixed --k 10 --seeds 2
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

H_MAX = 80        # deepest lag available to the irregular windows (steps)
LAG_SCALE = 40.0  # age channel = lag / LAG_SCALE
CONDITIONS = ['snapshot', 'regular', 'mask30', 'mask60', 'gap2', 'gap4', 'gap2_noage', 'mismatch_gap2']


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def draw_lags(n, k, kind, rng):
    """[n, k] lags of the older reports (ascending) and [n, k] validity (False = report missing)."""
    if kind in ('regular', 'mask30', 'mask60'):
        lags = np.tile(np.arange(1, k + 1), (n, 1))
        valid = np.ones((n, k), bool)
        if kind != 'regular':
            p = 0.3 if kind == 'mask30' else 0.6
            valid = rng.random_sample((n, k)) >= p
        return lags, valid
    mean_gap = 2.0 if kind.startswith('gap2') else 4.0
    lags = np.minimum(np.cumsum(rng.geometric(1.0 / mean_gap, size=(n, k)), axis=1), H_MAX)
    return lags, np.ones((n, k), bool)


def gather(arr_lags, lags):
    """arr_lags [n, H_MAX+1] (column = lag) -> [n, k] values at the given lags."""
    return np.take_along_axis(arr_lags, lags, axis=1)


def build_inputs(feat, aoa, stats, lags, valid, age=True):
    """Sequence tensor [n, C, k+1] ordered oldest -> newest, plus a flat matrix for XGBoost."""
    n = len(feat)
    lag_all = np.concatenate([lags[:, ::-1], np.zeros((n, 1), int)], axis=1)          # oldest .. current
    val_all = np.concatenate([valid[:, ::-1], np.ones((n, 1), bool)], axis=1)
    def stack(prefix):
        return np.stack([feat[f'{prefix}_lag{l}'].values for l in range(H_MAX + 1)], axis=1)
    chans, flat = [], []
    for ch in ('rss', 'sinr'):
        v = gather(stack(ch), lag_all)
        z = np.where(val_all, (v - stats[ch][0]) / stats[ch][1], 0.0)
        chans.append(z)
        flat.append(np.where(val_all, v, np.nan))
    if aoa:
        az = gather(stack('aoa_az'), lag_all)
        el = gather(stack('aoa_el'), lag_all)
        ok = val_all & np.isfinite(az) & np.isfinite(el)
        azr = np.deg2rad(np.where(ok, az, 0.0))
        chans += [np.where(ok, np.sin(azr), 0.0), np.where(ok, np.cos(azr), 0.0), np.where(ok, el, 0.0) / 90.0, ok.astype(float)]
        flat += [np.where(ok, az, np.nan), np.where(ok, el, np.nan)]
    chans.append(val_all.astype(float))
    if age:
        chans.append(lag_all / LAG_SCALE)
        flat.append(lag_all.astype(float))
    X = np.stack(chans, axis=1).astype(np.float32)
    F = np.concatenate(flat, axis=1).astype(np.float32)
    return X, F


def main():
    ap = argparse.ArgumentParser(
        description='Irregular and incomplete history on the 15x15 controlled grid.',
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('Usage')[1])
    ap.add_argument('--data-dir', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--k', type=int, default=10, help='number of older reports per window')
    ap.add_argument('--seeds', type=int, default=2)
    ap.add_argument('--models', nargs='+', default=['gru', 'xgboost'], choices=['gru', 'cnn', 'gru_attn', 'cnn_attn', 'xgboost'])
    ap.add_argument('--conditions', nargs='+', default=CONDITIONS, choices=CONDITIONS)
    ap.add_argument('--experiments', nargs='+', default=['BASE'], choices=['BASE', 'BASE_A'])
    ap.add_argument('--n-jobs', type=int, default=6)
    args = ap.parse_args()

    import torch
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
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

    rows, csv_path = [], out / 'history_irregular.csv'
    for exp in args.experiments:
        aoa = exp == 'BASE_A'
        feat = mu.build_history_features(df, H_MAX, include_aoa=aoa)
        tr = (feat['split'] == 'train').values
        te = (feat['split'] == 'test').values
        trf, tef = feat[tr], feat[te]
        y_tr = trf['grid_point_id'].map(l2i).values.astype(np.int64)
        y_te_lab = tef['grid_point_id'].values
        val_mask = np.zeros(len(trf), bool)
        for _, g in trf.reset_index(drop=True).groupby('user_id'):
            val_mask[g.index[int(len(g) * 0.9):]] = True
        stats = {c: (float(trf[f'{c}_lag0'].mean()), float(trf[f'{c}_lag0'].std()) + 1e-6) for c in ('rss', 'sinr')}
        log(f'{exp}: train {tr.sum():,}, test {te.sum():,}, {len(labels)} cells')

        for cond in args.conditions:
            k = 0 if cond == 'snapshot' else args.k
            kind = {'snapshot': 'regular', 'gap2_noage': 'gap2', 'mismatch_gap2': 'regular'}.get(cond, cond)
            age = cond != 'gap2_noage'
            rtr, rte = np.random.RandomState(11), np.random.RandomState(22)
            lags_tr, val_tr = draw_lags(len(trf), k, kind, rtr)
            Xtr, Ftr = build_inputs(trf, aoa, stats, lags_tr, val_tr, age)
            te_kind = 'gap2' if cond == 'mismatch_gap2' else kind
            lags_te, val_te = draw_lags(len(tef), k, te_kind, rte)
            Xte, Fte = build_inputs(tef, aoa, stats, lags_te, val_te, age)
            for model in args.models:
                if model == 'xgboost' and cond not in ('snapshot', 'regular', 'mask30', 'gap2'):
                    continue
                t0 = time.time()
                if model == 'xgboost':
                    clf = mu.get_model('xgboost', len(labels))
                    clf.fit(Ftr, y_tr)
                    preds = [(0, i2l[clf.predict(Fte)], None)]
                else:
                    preds = []
                    for seed in range(args.seeds):
                        p, ep, _ = ghe.train_cnn(Xtr[~val_mask], y_tr[~val_mask], Xtr[val_mask], y_tr[val_mask], Xte,
                                                 len(labels), seed, device, kind=model)
                        preds.append((seed, i2l[p], ep))
                for seed, pred, ep in preds:
                    r = mu.evaluate_split(y_te_lab, pred, grid_lookup, spacing=spacing)
                    rows.append(dict(model=model, experiment=exp, condition=cond, k=k, seed=seed,
                                     accuracy=round(r['accuracy'], 3), mae=round(r['mae'], 4), epochs=ep,
                                     mean_lag_oldest=float(lags_te[:, -1].mean()) if k else 0.0,
                                     secs=round(time.time() - t0, 1)))
                    log(f'{exp} {cond:14s} {model}: {r["accuracy"]:.1f}% / {r["mae"]:.2f} m (seed {seed})')
                pd.DataFrame(rows).to_csv(csv_path, index=False)

    res = pd.DataFrame(rows)
    summ = res.groupby(['experiment', 'condition', 'model'])[['accuracy', 'mae']].agg(['mean', 'std']).round(3)
    summ.to_csv(out / 'history_irregular_summary.csv')
    (out / 'config.json').write_text(json.dumps(dict(data_dir=str(data_dir), k=args.k, seeds=args.seeds, h_max=H_MAX,
                                                     lag_scale=LAG_SCALE, conditions=args.conditions), indent=2))
    log('[OK] Results saved to: ' + str(csv_path) + '\n' + summ.to_string())


if __name__ == '__main__':
    main()
