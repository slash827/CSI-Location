"""
B5: Random Forest per-history-depth hyperparameter re-tune.

Section 5.5 re-tuned XGBoost only, and found the history curve keeps its shape
once every depth gets a fair fit. Random Forest is the family that most needs the
same treatment:

  * it is the one model whose single-antenna error (38.904 m) is *worse* than the
    h=0 k-NN baseline (37.142 m), despite a far better overall MAE;
  * it is the family where history degraded results in the earlier tuned 25x25
    regression study, which is the observation that motivated the XGBoost re-tune
    in the first place;
  * it has the smallest history gain of the seven families in the B3 sweep
    (12.54%), so if fixed hyperparameters are suppressing the gain anywhere, here
    is where it should show.

Protocol mirrors xgb_per_h_retune.py exactly, swapping the estimator, so the two
results are directly comparable:
  - Tuning happens ONLY on training users, split further into sub-train / val by
    user id. Test users are never touched during tuning.
  - For each h: Optuna TPE, N_TRIALS trials, objective = 2D MAE on the val users.
  - Then refit on the full training set with the best params and evaluate once on
    the held-out test users.
  - Baseline arm = the master benchmark's fixed defaults at the same h, same data.

Note on cost: a Random Forest fit runs 40-120 s against XGBoost's 10-26 s, so the
search space caps n_estimators lower than a leisurely run would. The point is a
fair fit per depth, not the best forest obtainable.

Usage:
    python rf_per_h_retune.py
    python rf_per_h_retune.py --trials 10 --depths 0 5
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'src' / 'python'))

from pipelines.multi_user_pipeline_regression import _read_bs_position_3d
from pipelines.multi_user_200_pipeline import make_unseen_user_split
from utils.csi_dataset import DerivedCSI1DDataset, load_and_prepare_data

import optuna
from sklearn.ensemble import RandomForestRegressor

optuna.logging.set_verbosity(optuna.logging.WARNING)

SEED = 42
SINGLE_ANT_RATIO = 0.15
TRAIN_RATIO = 0.80
VAL_USER_RATIO = 0.20      # of the training users, held out for tuning

# the master benchmark's fixed defaults - the baseline arm
DEFAULT_PARAMS = dict(n_estimators=150, max_features='sqrt', max_depth=16,
                      min_samples_leaf=5, random_state=SEED)


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


def build(df_a, df_b, h):
    """Fit dataset stats on df_a, apply to both."""
    a = DerivedCSI1DDataset(df_a, h=h)
    b = DerivedCSI1DDataset(df_b, h=h,
                            sig_mean=a.sig_mean, sig_std=a.sig_std,
                            stat_mean=a.stat_mean, stat_std=a.stat_std,
                            targ_mean=a.targ_mean, targ_std=a.targ_std,
                            speed_mean=a.speed_mean, speed_std=a.speed_std)
    return a, b


def main():
    ap = argparse.ArgumentParser(
        description='Random Forest per-depth Optuna re-tune (B5).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python rf_per_h_retune.py
  python rf_per_h_retune.py --trials 10 --depths 0 5
""")
    ap.add_argument('--depths', type=int, nargs='+', default=[0, 1, 3, 5, 10])
    ap.add_argument('--trials', type=int, default=20)
    ap.add_argument('--seed', type=int, default=SEED)
    args = ap.parse_args()

    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'rf_per_h_retune_{run_ts}')
    out_dir.mkdir(parents=True, exist_ok=True)

    np.random.seed(args.seed)

    log('loading Campaign B dataset...')
    data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
    data_dir = sorted(data_base.glob('sim_data_300users_*'))[-1]
    bs_pos = np.array(_read_bs_position_3d(data_dir))

    df_filt, _, _ = load_and_prepare_data(
        data_dir, bs_pos, seed=args.seed, single_ant_ratio=SINGLE_ANT_RATIO)
    df_filt, train_uids, test_uids = make_unseen_user_split(df_filt, TRAIN_RATIO, args.seed)

    # carve a validation user set out of the TRAINING users only
    train_uid_arr = np.array(sorted(train_uids))
    rng = np.random.RandomState(args.seed)
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
        'dataset': str(data_dir), 'seed': args.seed, 'n_trials': args.trials,
        'estimator': 'RandomForestRegressor',
        'default_params': {k: v for k, v in DEFAULT_PARAMS.items()},
        'n_subtrain_users': len(subtrain_uids), 'n_val_users': len(val_uids),
        'n_test_users': len(test_uids),
        'protocol': 'mirrors xgb_per_h_retune.py; tuned on training users only',
    }, 'per_h': {}}

    for h in args.depths:
        log('=' * 78)
        log(f'h = {h}')
        t_h = time.time()

        sub_ds, val_ds = build(df_sub, df_val, h)
        Xs, Ys, _ = flatten(sub_ds)
        Xv, Yv, _ = flatten(val_ds)
        ts_s, tm_s = sub_ds.targ_std, sub_ds.targ_mean

        def objective(trial):
            p = dict(
                n_estimators=trial.suggest_int('n_estimators', 100, 400, step=50),
                max_depth=trial.suggest_int('max_depth', 8, 32),
                min_samples_leaf=trial.suggest_int('min_samples_leaf', 1, 20),
                min_samples_split=trial.suggest_int('min_samples_split', 2, 20),
                max_features=trial.suggest_categorical(
                    'max_features', ['sqrt', 'log2', 0.3, 0.5, 0.8]),
                random_state=args.seed, n_jobs=-1,
            )
            m = RandomForestRegressor(**p)
            m.fit(Xs, Ys)
            return mae_2d(m.predict(Xv), Yv, ts_s, tm_s)

        study = optuna.create_study(direction='minimize',
                                    sampler=optuna.samplers.TPESampler(seed=args.seed))
        study.optimize(objective, n_trials=args.trials, show_progress_bar=False)
        best_params = dict(study.best_params)
        log(f'  best val MAE {study.best_value:.3f} m after {args.trials} trials')
        log(f'  best params: {best_params}')

        # final arena: full train -> test (single evaluation)
        tr_ds, te_ds = build(df_tr, df_te, h)
        Xtr, Ytr, _ = flatten(tr_ds)
        Xte, Yte, ant_te = flatten(te_ds)
        ts, tm = tr_ds.targ_std, tr_ds.targ_mean

        t0 = time.time()
        m_def = RandomForestRegressor(**DEFAULT_PARAMS, n_jobs=-1)
        m_def.fit(Xtr, Ytr)
        def_res = eval_full(m_def.predict(Xte), Yte, ant_te, ts, tm)
        def_res['train_sec'] = round(time.time() - t0, 1)

        t0 = time.time()
        m_tun = RandomForestRegressor(**best_params, random_state=args.seed, n_jobs=-1)
        m_tun.fit(Xtr, Ytr)
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
            f'| single-ant {def_res["single_mae"]:.3f} -> {tun_res["single_mae"]:.3f} '
            f'| {results["per_h"][f"h={h}"]["elapsed_sec"]:.0f}s')

    # ── history curves under both regimes ────────────────────────────────────
    log('=' * 78)
    log('HISTORY CURVE, both regimes')
    lo = args.depths[0]
    b_def = results['per_h'][f'h={lo}']['default']['mae']
    b_tun = results['per_h'][f'h={lo}']['tuned']['mae']
    curve = {}
    for h in args.depths:
        r = results['per_h'][f'h={h}']
        d, t = r['default']['mae'], r['tuned']['mae']
        curve[f'h={h}'] = {
            'default_mae': round(d, 4),
            'default_gain_pct': round(100.0 * (b_def - d) / b_def, 2),
            'tuned_mae': round(t, 4),
            'tuned_gain_pct': round(100.0 * (b_tun - t) / b_tun, 2),
        }
        log(f'  h={h:<3d}| default {d:7.3f} ({curve[f"h={h}"]["default_gain_pct"]:+6.2f}%) '
            f'| tuned {t:7.3f} ({curve[f"h={h}"]["tuned_gain_pct"]:+6.2f}%)')
    results['history_curve'] = curve

    later = [h for h in args.depths if h > lo]
    mono_def = all(curve[f'h={h}']['default_gain_pct'] >= -0.01 for h in later)
    mono_tun = all(curve[f'h={h}']['tuned_gain_pct'] >= -0.01 for h in later)

    # the question that motivated B5: does a fair fit per depth rescue the
    # single-antenna cohort, which is the one place RF trails the k-NN baseline?
    sing = {f'h={h}': {
        'default': results['per_h'][f'h={h}']['default']['single_mae'],
        'tuned': results['per_h'][f'h={h}']['tuned']['single_mae'],
    } for h in args.depths}
    best_single = min(v['tuned'] for v in sing.values())

    results['verdict'] = {
        'history_helps_default': bool(mono_def),
        'history_helps_tuned': bool(mono_tun),
        'single_antenna_by_depth': sing,
        'best_tuned_single_mae': round(best_single, 4),
        'knn_h0_single_baseline': 37.142,
        'beats_knn_single_baseline': bool(best_single < 37.142),
    }
    log(f'history helps at every depth past h={lo} -- '
        f'defaults: {mono_def} | re-tuned: {mono_tun}')
    log(f'best tuned single-antenna MAE {best_single:.3f} m vs k-NN h=0 baseline '
        f'37.142 m -> {"beats it" if best_single < 37.142 else "still worse"}')

    out_json = out_dir / 'rf_per_h_retune_summary.json'
    out_json.write_text(json.dumps(results, indent=1), encoding='utf-8')
    log(f'saved -> {out_json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
