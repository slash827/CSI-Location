"""
Experiment 5: is a single global process noise the wrong model for a
speed-heterogeneous population?

Experiment 4 showed every model family recovers from the notebook's Q=0.5 once Q
is raised, with the gain plateauing from Q~16. But Campaign B users span 0.1 to
15 m/s, and the Kalman process-noise term Q = diag([q dt^2, q dt^2, q, q]) is
applied with one global q to all of them. A constant-velocity model with a small q
cannot track a 15 m/s vehicle that changes heading, while a large q wastes the
motion model on a static user.

This tests a physically-motivated alternative: scale the process noise per user by
that user's own speed,

    q_user = k * v_user

so the filter's assumed manoeuvre magnitude is proportional to how fast the user
actually moves. Swept over k and compared against the best global Q.

Classical models only (k-NN, Random Forest, XGBoost) to keep the run short; the
question is about the filter, not the estimator.
"""
import sys, json, time, datetime
from pathlib import Path
import numpy as np

# Resolve the repo root from this file's own location, so the script runs on any
# machine. experiments_ablation/ sits five levels below the root.
PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'src' / 'python'))

from pipelines.multi_user_pipeline_regression import _read_bs_position_3d
from pipelines.multi_user_200_pipeline import make_unseen_user_split
from utils.csi_dataset import DerivedCSI1DDataset, load_and_prepare_data
from utils.training_utils import run_kalman_and_rts_2d

from sklearn.neighbors import KNeighborsRegressor
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

SEED, H, SINGLE_ANT_RATIO, TRAIN_RATIO = 42, 5, 0.15, 0.80
GLOBAL_Q = [0.03, 0.06, 0.125, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
K_GRID = [0.01, 0.02, 0.04, 0.08, 0.15, 0.3, 0.5, 1.0, 2.0]
R_FIXED = 15.0

RUN_TS = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
OUT_DIR = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
           / f'per_user_process_noise_{RUN_TS}')
OUT_DIR.mkdir(parents=True, exist_ok=True)
np.random.seed(SEED)


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


log('loading...')
base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
DATA_DIR = sorted(base.glob('sim_data_300users_*'))[-1]
df, _, _ = load_and_prepare_data(DATA_DIR, np.array(_read_bs_position_3d(DATA_DIR)),
                                 seed=SEED, single_ant_ratio=SINGLE_ANT_RATIO)
df, train_uids, test_uids = make_unseen_user_split(df, TRAIN_RATIO, SEED)
tr_ds = DerivedCSI1DDataset(df[df.split == 'train'], h=H)
te_ds = DerivedCSI1DDataset(df[df.split == 'test'], h=H,
                            sig_mean=tr_ds.sig_mean, sig_std=tr_ds.sig_std,
                            stat_mean=tr_ds.stat_mean, stat_std=tr_ds.stat_std,
                            targ_mean=tr_ds.targ_mean, targ_std=tr_ds.targ_std,
                            speed_mean=tr_ds.speed_mean, speed_std=tr_ds.speed_std)
TS, TM = tr_ds.targ_std, tr_ds.targ_mean


def flat(ds):
    n = len(ds)
    d = ds.samples[0]['seq'].size + ds.samples[0]['static'].size
    X = np.empty((n, d), np.float32); Y = np.empty((n, 2), np.float32)
    uid = np.empty(n, np.int64); dt = np.empty(n, np.float64)
    for i, s in enumerate(ds.samples):
        X[i] = np.concatenate([s['seq'].ravel(), s['static'].ravel()])
        Y[i] = s['target']; uid[i] = s['user_id']; dt[i] = s['delta_t']
    return X, Y, uid, dt


Xtr, Ytr, _, _ = flat(tr_ds)
Xte, Yte, UID, DT = flat(te_ds)
Y_m = Yte * TS + TM
TEST_USERS = np.unique(UID)
# per-user speed: grid spacing is 4 m, step duration is spacing / speed
SPACING = 4.0
user_speed = {u: SPACING / float(np.median(DT[UID == u])) for u in TEST_USERS}
log(f'{len(TEST_USERS)} test users | speed range '
    f'{min(user_speed.values()):.2f}-{max(user_speed.values()):.2f} m/s')


def smooth(P_m, q_of_user, R=R_FIXED):
    out = np.zeros_like(P_m)
    for u in TEST_USERS:
        m = (UID == u)
        _, rts = run_kalman_and_rts_2d(Y_m[m], P_m[m], DT[m],
                                       process_noise_std=q_of_user(u), R_std=R)
        out[m] = rts
    return float(np.linalg.norm(out - Y_m, axis=1).mean())


log('training classical models...')
models = {}
models['knn_h5'] = KNeighborsRegressor(5, n_jobs=-1).fit(Xtr, Ytr).predict(Xte) * TS + TM
models['random_forest_h5'] = RandomForestRegressor(
    n_estimators=150, max_features='sqrt', max_depth=16, min_samples_leaf=5,
    random_state=SEED, n_jobs=-1).fit(Xtr, Ytr).predict(Xte) * TS + TM
models['xgboost_h5'] = XGBRegressor(
    n_estimators=50, max_depth=5, learning_rate=0.15, subsample=0.8,
    colsample_bytree=0.8, random_state=SEED, n_jobs=-1, tree_method='hist',
    multi_strategy='one_output_per_tree').fit(Xtr, Ytr).predict(Xte) * TS + TM

results = {'meta': dict(dataset=str(DATA_DIR), h=H, seed=SEED, R=R_FIXED,
                        global_q=GLOBAL_Q, k_grid=K_GRID,
                        n_test_users=int(len(TEST_USERS)))}

for name, P in models.items():
    raw = float(np.linalg.norm(P - Y_m, axis=1).mean())
    log(f'--- {name}: raw {raw:.3f} m')
    rec = {'raw_mae': round(raw, 4), 'global': {}, 'per_user': {}}

    for q in GLOBAL_Q:
        mae = smooth(P, lambda u, q=q: q)
        rec['global'][f'Q={q}'] = dict(rts_mae=round(mae, 4),
                                       gain_pct=round(100 * (raw - mae) / raw, 2))
        log(f'    global  Q={q:<6g} RTS {mae:7.3f} ({100*(raw-mae)/raw:+6.2f}%)')

    for k in K_GRID:
        mae = smooth(P, lambda u, k=k: k * user_speed[u])
        rec['per_user'][f'k={k}'] = dict(rts_mae=round(mae, 4),
                                         gain_pct=round(100 * (raw - mae) / raw, 2))
        log(f'    per-user k={k:<5g} (q=k*v) RTS {mae:7.3f} ({100*(raw-mae)/raw:+6.2f}%)')

    best_g = min(rec['global'].values(), key=lambda x: x['rts_mae'])
    best_p = min(rec['per_user'].values(), key=lambda x: x['rts_mae'])
    rec['best_global'] = best_g
    rec['best_per_user'] = best_p
    rec['per_user_beats_global'] = bool(best_p['rts_mae'] < best_g['rts_mae'])
    log(f'    best global {best_g["rts_mae"]:.3f} ({best_g["gain_pct"]:+.2f}%) | '
        f'best per-user {best_p["rts_mae"]:.3f} ({best_p["gain_pct"]:+.2f}%) | '
        f'per-user wins: {rec["per_user_beats_global"]}')
    results[name] = rec

out = OUT_DIR / 'per_user_process_noise_summary.json'
out.write_text(json.dumps(results, indent=1), encoding='utf-8')
log(f'saved -> {out}')
log('DONE')
