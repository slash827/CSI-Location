"""
Experiment 1: k-NN transition-history sweep  (adds a 5th paradigm to the universality figure)
Experiment 2: Kalman/RTS process-noise re-tune (why does smoothing degrade every model?)

Reuses the exact Campaign B protocol from notebooks 06/07:
  load_and_prepare_data -> make_unseen_user_split -> DerivedCSI1DDataset

Validation gate: k-NN at h=0 must reproduce the master benchmark's 27.857 m MAE.
"""
import sys, json, time, datetime
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path('d:/gilad/projects/Academy/CSI-Location')
sys.path.insert(0, str(PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'src' / 'python'))

from pipelines.multi_user_pipeline_regression import _read_bs_position_3d
from pipelines.multi_user_200_pipeline import make_unseen_user_split
from utils.csi_dataset import DerivedCSI1DDataset, load_and_prepare_data
from utils.training_utils import apply_kalman_smoother

from sklearn.neighbors import KNeighborsRegressor

SEED = 42
SINGLE_ANT_RATIO = 0.15
TRAIN_RATIO = 0.80
H_GRID = [0, 1, 3, 5, 10]
K_NEIGHBORS = 5

RUN_TS = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
OUT_DIR = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
           / f'knn_sweep_rts_retune_{RUN_TS}')
OUT_DIR.mkdir(parents=True, exist_ok=True)

np.random.seed(SEED)


def log(msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)


def flatten(ds):
    """DerivedCSI1DDataset -> flat design matrix + metadata arrays."""
    n = len(ds)
    seq0 = ds.samples[0]['seq']
    d = seq0.size + ds.samples[0]['static'].size
    X = np.empty((n, d), dtype=np.float32)
    Y = np.empty((n, 2), dtype=np.float32)
    uid = np.empty(n, dtype=np.int64)
    dt = np.empty(n, dtype=np.float64)
    ant = np.empty(n, dtype=np.int64)
    for i, s in enumerate(ds.samples):
        X[i] = np.concatenate([s['seq'].ravel(), s['static'].ravel()])
        Y[i] = s['target']
        uid[i] = s['user_id']
        dt[i] = s['delta_t']
        ant[i] = s['n_antennas']
    return X, Y, uid, dt, ant


def metrics(err):
    return dict(mae=float(err.mean()), p50=float(np.median(err)), p90=float(np.percentile(err, 90)))


def cohort_metrics(err, ant):
    m = metrics(err)
    multi, single = ant > 1, ant == 1
    m['multi_mae'] = float(err[multi].mean()) if multi.any() else None
    m['single_mae'] = float(err[single].mean()) if single.any() else None
    m['n_multi'] = int(multi.sum())
    m['n_single'] = int(single.sum())
    return m


# ── data ──────────────────────────────────────────────────────────────────────
log('loading Campaign B dataset...')
data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
DATA_DIR = sorted(data_base.glob('sim_data_300users_*'))[-1]
bs_pos = np.array(_read_bs_position_3d(DATA_DIR))

df_filt, multi_uids, keep_single = load_and_prepare_data(
    DATA_DIR, bs_pos, seed=SEED, single_ant_ratio=SINGLE_ANT_RATIO)
df_filt, train_uids, test_uids = make_unseen_user_split(df_filt, TRAIN_RATIO, SEED)
df_tr = df_filt[df_filt.split == 'train']
df_te = df_filt[df_filt.split == 'test']
log(f'{len(df_tr):,} train / {len(df_te):,} test rows | {len(test_uids)} unseen test users')

results = {'meta': {
    'dataset': str(DATA_DIR), 'seed': SEED, 'k_neighbors': K_NEIGHBORS,
    'train_rows': int(len(df_tr)), 'test_rows': int(len(df_te)),
    'n_test_users': int(len(test_uids)),
}}

# ══ EXPERIMENT 1: k-NN history sweep ══════════════════════════════════════════
log('=' * 70)
log('EXPERIMENT 1 — k-NN history sweep')
log('=' * 70)

knn_sweep = {}
preds_cache = {}

for h in H_GRID:
    t0 = time.time()
    tr_ds = DerivedCSI1DDataset(df_tr, h=h)
    te_ds = DerivedCSI1DDataset(
        df_te, h=h,
        sig_mean=tr_ds.sig_mean, sig_std=tr_ds.sig_std,
        stat_mean=tr_ds.stat_mean, stat_std=tr_ds.stat_std,
        targ_mean=tr_ds.targ_mean, targ_std=tr_ds.targ_std,
        speed_mean=tr_ds.speed_mean, speed_std=tr_ds.speed_std)

    Xtr, Ytr, _, _, _ = flatten(tr_ds)
    Xte, Yte, uid_te, dt_te, ant_te = flatten(te_ds)

    knn = KNeighborsRegressor(n_neighbors=K_NEIGHBORS, n_jobs=-1)
    knn.fit(Xtr, Ytr)
    P = knn.predict(Xte)

    # de-normalise back to metres
    ts, tm = tr_ds.targ_std, tr_ds.targ_mean
    P_m = P * ts + tm
    Y_m = Yte * ts + tm
    err = np.linalg.norm(P_m - Y_m, axis=1)

    m = cohort_metrics(err, ant_te)
    m['h'] = h
    m['fit_predict_sec'] = round(time.time() - t0, 1)
    m['n_features'] = int(Xtr.shape[1])
    knn_sweep[f'h={h}'] = m
    preds_cache[h] = dict(P_m=P_m, Y_m=Y_m, uid=uid_te, dt=dt_te, ant=ant_te)

    log(f'  h={h:<2d} | MAE {m["mae"]:7.3f} m | P50 {m["p50"]:7.3f} | P90 {m["p90"]:7.3f} '
        f'| multi {m["multi_mae"]:6.3f} | single {m["single_mae"]:6.3f} '
        f'| {m["n_features"]:3d} feats | {m["fit_predict_sec"]}s')

base = knn_sweep['h=0']['mae']
for h in H_GRID:
    k = f'h={h}'
    knn_sweep[k]['cumulative_delta_mae'] = round(knn_sweep[k]['mae'] - base, 4)
    knn_sweep[k]['cumulative_gain_pct'] = round(100.0 * (base - knn_sweep[k]['mae']) / base, 2)

results['knn_history_sweep'] = knn_sweep

# validation gate against the published master benchmark
published_knn_h0 = 27.85657520761358
delta = abs(knn_sweep['h=0']['mae'] - published_knn_h0)
results['meta']['validation_knn_h0_published'] = published_knn_h0
results['meta']['validation_knn_h0_delta'] = round(delta, 4)
results['meta']['validation_passed'] = bool(delta < 0.5)
log(f'VALIDATION: k-NN h=0 = {knn_sweep["h=0"]["mae"]:.3f} m vs published '
    f'{published_knn_h0:.3f} m (delta {delta:.3f}) '
    f'-> {"MATCH" if delta < 0.5 else "MISMATCH"}')

# ══ EXPERIMENT 2: Kalman/RTS process-noise re-tune ════════════════════════════
log('=' * 70)
log('EXPERIMENT 2 — Kalman/RTS re-tune on k-NN h=5 predictions')
log('=' * 70)
log('Notebook defaults are process_noise_std=0.5, R_std=15.0 -> all models degrade.')

c = preds_cache[5]
P_m, Y_m, uid_te, dt_te, ant_te = c['P_m'], c['Y_m'], c['uid'], c['dt'], c['ant']
raw_mae = float(np.linalg.norm(P_m - Y_m, axis=1).mean())
log(f'raw k-NN h=5 MAE = {raw_mae:.3f} m  (this is what smoothing must beat)')

test_user_list = np.unique(uid_te)
Q_GRID = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0]
R_GRID = [5.0, 10.0, 15.0, 25.0, 40.0]

rts_grid = []
best = None
for q in Q_GRID:
    for r in R_GRID:
        kf_p, rts_p = apply_kalman_smoother(P_m, Y_m, uid_te, dt_te, test_user_list,
                                            process_noise_std=q, R_std=r)
        kf_mae = float(np.linalg.norm(kf_p - Y_m, axis=1).mean())
        rts_mae = float(np.linalg.norm(rts_p - Y_m, axis=1).mean())
        rec = dict(process_noise_std=q, R_std=r,
                   kf_mae=round(kf_mae, 4), rts_mae=round(rts_mae, 4),
                   kf_gain_pct=round(100.0 * (raw_mae - kf_mae) / raw_mae, 2),
                   rts_gain_pct=round(100.0 * (raw_mae - rts_mae) / raw_mae, 2))
        rts_grid.append(rec)
        if best is None or rts_mae < best['rts_mae']:
            best = rec
        log(f'  Q={q:5.1f} R={r:5.1f} | KF {kf_mae:7.3f} ({rec["kf_gain_pct"]:+6.2f}%) '
            f'| RTS {rts_mae:7.3f} ({rec["rts_gain_pct"]:+6.2f}%)')

results['rts_retune'] = {
    'raw_mae': round(raw_mae, 4),
    'notebook_default': next(x for x in rts_grid
                             if x['process_noise_std'] == 0.5 and x['R_std'] == 15.0),
    'best': best,
    'grid': rts_grid,
    'q_grid': Q_GRID, 'r_grid': R_GRID,
}

log('-' * 70)
d = results['rts_retune']['notebook_default']
log(f'notebook default (Q=0.5, R=15): RTS {d["rts_mae"]:.3f} m ({d["rts_gain_pct"]:+.2f}%)')
log(f'best found (Q={best["process_noise_std"]}, R={best["R_std"]}): '
    f'RTS {best["rts_mae"]:.3f} m ({best["rts_gain_pct"]:+.2f}%)')
log('VERDICT: ' + ('smoothing RECOVERABLE with re-tuned Q/R'
                   if best['rts_gain_pct'] > 0 else
                   'smoothing HURTS at every (Q,R) tested -> report as negative result'))

out_json = OUT_DIR / 'knn_sweep_rts_retune_summary.json'
out_json.write_text(json.dumps(results, indent=1), encoding='utf-8')
log(f'saved -> {out_json}')
log('DONE')
