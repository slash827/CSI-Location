"""
Experiment 3: XGBoost per-history-depth hyperparameter re-tune.

Question this closes: earlier runs showed configurations where adding history made
XGBoost/RF *worse*. Working hypothesis is that the fixed default hyperparameters
were near-optimal for the h=0 snapshot feature set, so enlarging the input space
without re-fitting capacity/regularization confounded the comparison.

Protocol:
  - Tuning happens ONLY on training users, split further into sub-train / val by
    user id. Test users are never touched during tuning.
  - For each h: Optuna TPE, N_TRIALS trials, objective = 2D MAE on the val users.
  - Then refit on the full training set with the best params and evaluate once on
    the held-out test users.
  - Baseline arm = the pipeline's fixed defaults at the same h, same data.

Output: does the history curve keep its shape once each depth gets a fair fit?
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

import optuna
from xgboost import XGBRegressor

optuna.logging.set_verbosity(optuna.logging.WARNING)

SEED = 42
SINGLE_ANT_RATIO = 0.15
TRAIN_RATIO = 0.80
VAL_USER_RATIO = 0.20      # of the training users, held out for tuning
H_GRID = [0, 1, 3, 5, 10]
N_TRIALS = 20

# the pipeline's fixed defaults - the baseline arm
DEFAULT_PARAMS = dict(n_estimators=50, max_depth=5, learning_rate=0.15,
                      subsample=0.8, colsample_bytree=0.8, random_state=SEED)

RUN_TS = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
OUT_DIR = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
           / f'xgb_per_h_retune_{RUN_TS}')
OUT_DIR.mkdir(parents=True, exist_ok=True)

np.random.seed(SEED)


def log(msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)


def flatten(ds):
    n = len(ds)
    d = ds.samples[0]['seq'].size + ds.samples[0]['static'].size
    X = np.empty((n, d), dtype=np.float32)
    Y = np.empty((n, 2), dtype=np.float32)
    ant = np.empty(n, dtype=np.int64)
    for i, s in enumerate(ds.samples):
        X[i] = np.concatenate([s['seq'].ravel(), s['static'].ravel()])
        Y[i] = s['target']
        ant[i] = s['n_antennas']
    return X, Y, ant


def mae_2d(P, Y, ts, tm):
    return float(np.linalg.norm((P * ts + tm) - (Y * ts + tm), axis=1).mean())


def eval_full(P, Y, ant, ts, tm):
    err = np.linalg.norm((P * ts + tm) - (Y * ts + tm), axis=1)
    multi, single = ant > 1, ant == 1
    return dict(mae=float(err.mean()), p50=float(np.median(err)),
                p90=float(np.percentile(err, 90)),
                multi_mae=float(err[multi].mean()) if multi.any() else None,
                single_mae=float(err[single].mean()) if single.any() else None)


# ── data ──────────────────────────────────────────────────────────────────────
log('loading Campaign B dataset...')
data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
DATA_DIR = sorted(data_base.glob('sim_data_300users_*'))[-1]
bs_pos = np.array(_read_bs_position_3d(DATA_DIR))

df_filt, multi_uids, keep_single = load_and_prepare_data(
    DATA_DIR, bs_pos, seed=SEED, single_ant_ratio=SINGLE_ANT_RATIO)
df_filt, train_uids, test_uids = make_unseen_user_split(df_filt, TRAIN_RATIO, SEED)

# carve a validation user set out of the TRAINING users only
train_uid_arr = np.array(sorted(train_uids))
rng = np.random.RandomState(SEED)
perm = rng.permutation(train_uid_arr)
n_val = int(len(perm) * VAL_USER_RATIO)
val_uids = set(perm[:n_val].tolist())
subtrain_uids = set(perm[n_val:].tolist())

df_sub = df_filt[df_filt.user_id.isin(subtrain_uids)]
df_val = df_filt[df_filt.user_id.isin(val_uids)]
df_tr = df_filt[df_filt.split == 'train']
df_te = df_filt[df_filt.split == 'test']

log(f'sub-train {len(subtrain_uids)} users / val {len(val_uids)} users '
    f'/ test {len(test_uids)} users (test untouched during tuning)')

results = {'meta': {
    'dataset': str(DATA_DIR), 'seed': SEED, 'n_trials': N_TRIALS,
    'default_params': DEFAULT_PARAMS,
    'n_subtrain_users': len(subtrain_uids), 'n_val_users': len(val_uids),
    'n_test_users': len(test_uids),
}, 'per_h': {}}


def build(df_a, df_b, h):
    """Fit dataset stats on df_a, apply to both."""
    a = DerivedCSI1DDataset(df_a, h=h)
    b = DerivedCSI1DDataset(df_b, h=h,
                            sig_mean=a.sig_mean, sig_std=a.sig_std,
                            stat_mean=a.stat_mean, stat_std=a.stat_std,
                            targ_mean=a.targ_mean, targ_std=a.targ_std,
                            speed_mean=a.speed_mean, speed_std=a.speed_std)
    return a, b


for h in H_GRID:
    log('=' * 70)
    log(f'h = {h}')
    t_h = time.time()

    # tuning arena: sub-train -> val
    sub_ds, val_ds = build(df_sub, df_val, h)
    Xs, Ys, _ = flatten(sub_ds)
    Xv, Yv, _ = flatten(val_ds)
    ts_s, tm_s = sub_ds.targ_std, sub_ds.targ_mean

    def objective(trial):
        p = dict(
            n_estimators=trial.suggest_int('n_estimators', 50, 600, step=50),
            max_depth=trial.suggest_int('max_depth', 3, 12),
            learning_rate=trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            subsample=trial.suggest_float('subsample', 0.5, 1.0),
            colsample_bytree=trial.suggest_float('colsample_bytree', 0.5, 1.0),
            min_child_weight=trial.suggest_int('min_child_weight', 1, 20),
            reg_lambda=trial.suggest_float('reg_lambda', 1e-3, 20.0, log=True),
            reg_alpha=trial.suggest_float('reg_alpha', 1e-4, 5.0, log=True),
            random_state=SEED, n_jobs=-1, tree_method='hist',
            multi_strategy='one_output_per_tree',
        )
        m = XGBRegressor(**p)
        m.fit(Xs, Ys, verbose=False)
        return mae_2d(m.predict(Xv), Yv, ts_s, tm_s)

    study = optuna.create_study(direction='minimize',
                                sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=False)
    best_params = dict(study.best_params)
    log(f'  best val MAE {study.best_value:.3f} m  after {N_TRIALS} trials')

    # final arena: full train -> test (single evaluation)
    tr_ds, te_ds = build(df_tr, df_te, h)
    Xtr, Ytr, _ = flatten(tr_ds)
    Xte, Yte, ant_te = flatten(te_ds)
    ts, tm = tr_ds.targ_std, tr_ds.targ_mean

    # baseline arm: fixed defaults
    t0 = time.time()
    m_def = XGBRegressor(**DEFAULT_PARAMS, n_jobs=-1, tree_method='hist',
                         multi_strategy='one_output_per_tree')
    m_def.fit(Xtr, Ytr, verbose=False)
    def_res = eval_full(m_def.predict(Xte), Yte, ant_te, ts, tm)
    def_res['train_sec'] = round(time.time() - t0, 1)

    # tuned arm
    t0 = time.time()
    m_tun = XGBRegressor(**best_params, random_state=SEED, n_jobs=-1,
                         tree_method='hist', multi_strategy='one_output_per_tree')
    m_tun.fit(Xtr, Ytr, verbose=False)
    tun_res = eval_full(m_tun.predict(Xte), Yte, ant_te, ts, tm)
    tun_res['train_sec'] = round(time.time() - t0, 1)

    results['per_h'][f'h={h}'] = {
        'h': h, 'n_features': int(Xtr.shape[1]),
        'default': def_res, 'tuned': tun_res,
        'best_params': best_params,
        'best_val_mae': round(study.best_value, 4),
        'elapsed_sec': round(time.time() - t_h, 1),
    }
    log(f'  default MAE {def_res["mae"]:7.3f} m | tuned MAE {tun_res["mae"]:7.3f} m '
        f'| tuning bought {def_res["mae"] - tun_res["mae"]:+.3f} m '
        f'| {results["per_h"][f"h={h}"]["elapsed_sec"]}s')

# ── history curves under both regimes ─────────────────────────────────────────
log('=' * 70)
log('HISTORY CURVE, both regimes')
b_def = results['per_h']['h=0']['default']['mae']
b_tun = results['per_h']['h=0']['tuned']['mae']
curve = {}
for h in H_GRID:
    r = results['per_h'][f'h={h}']
    d, t = r['default']['mae'], r['tuned']['mae']
    curve[f'h={h}'] = {
        'default_mae': round(d, 4),
        'default_gain_pct': round(100.0 * (b_def - d) / b_def, 2),
        'tuned_mae': round(t, 4),
        'tuned_gain_pct': round(100.0 * (b_tun - t) / b_tun, 2),
    }
    log(f'  h={h:<2d} | default {d:7.3f} ({curve[f"h={h}"]["default_gain_pct"]:+6.2f}%) '
        f'| tuned {t:7.3f} ({curve[f"h={h}"]["tuned_gain_pct"]:+6.2f}%)')
results['history_curve'] = curve

mono_def = all(curve[f'h={h}']['default_gain_pct'] >= -0.01 for h in [1, 3, 5])
mono_tun = all(curve[f'h={h}']['tuned_gain_pct'] >= -0.01 for h in [1, 3, 5])
results['verdict'] = {
    'history_helps_default_through_h5': bool(mono_def),
    'history_helps_tuned_through_h5': bool(mono_tun),
}
log(f'history helps at h=1,3,5 -- defaults: {mono_def} | re-tuned: {mono_tun}')

out_json = OUT_DIR / 'xgb_per_h_retune_summary.json'
out_json.write_text(json.dumps(results, indent=1), encoding='utf-8')
log(f'saved -> {out_json}')
log('DONE')
