"""
Re-run the seven-model scorecard under the current pipeline.

`campaign_b/master_benchmark_summary.json` is the source for the section 6
scorecard - MAE, percentiles, per-cohort error, parameter counts, training times -
and parts of it no longer reproduce. Re-running seed 42 today gives Random Forest
19.417 m overall and 33.069 m single-antenna against the recorded 20.884 and
38.904, and three independent scripts (B2, B3, B5) agree on the new figures. The
k-NN baseline's recorded 37.142 m single-antenna error falls outside the range
observed across five seeds entirely.

That file predates several pipeline changes, and there is no script in the repo
that regenerates it - it came from a notebook. This is that script. It measures
everything section 6 quotes, under exactly the protocol the rest of the September
ablations use, so the scorecard stops being the one block of results whose
provenance cannot be checked.

Two additions the original did not have:

  * latency is measured over repeated batches rather than a single pass, since a
    one-shot timing on a warm GPU is mostly noise;
  * the k-NN baseline is reported at h=0 (as section 6 does) *and* at h=5, because
    the scorecard otherwise compares a baseline and the models on two different
    inputs at once.

Smoothing is deliberately excluded. Section 7.7 covers it with a proper Q/R sweep,
and the original's `rts_*` fields were computed on the broken time base.

Usage:
    python master_benchmark_rerun.py
    python master_benchmark_rerun.py --seeds 42 1 7
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_zoo as Z
from model_zoo import PROJECT_ROOT, log

from pipelines.multi_user_pipeline_regression import _read_bs_position_3d
from pipelines.multi_user_200_pipeline import make_unseen_user_split
from utils import csi_dataset
from utils.csi_dataset import load_and_prepare_data

# section 6 pairs the k-NN snapshot baseline with h=5 for everything else
SCORECARD_H = {m: 5 for m in Z.ALL_MODELS}
SCORECARD_H['knn'] = 0


def count_params(model, name, n_features):
    """Parameter count, using each family's own natural notion of one."""
    if name in Z.DEEP:
        return int(sum(p.numel() for p in model.parameters()))
    if name == 'knn':
        return None                                  # non-parametric
    if name == 'random_forest':
        # total nodes across the forest - what the model actually has to store
        return int(sum(t.tree_.node_count for t in model.estimators_))
    if name == 'xgboost':
        booster = model.get_booster()
        return int(sum(d.count('\n') for d in booster.get_dump()))
    return None


def measure_latency(predict_fn, X, n_rep=5, batch=1000):
    """Median ms per 1k samples over repeated passes."""
    if len(X) < batch:
        batch = len(X)
    xs = X[:batch]
    predict_fn(xs)                                   # warm up
    times = []
    for _ in range(n_rep):
        t0 = time.perf_counter()
        predict_fn(xs)
        times.append((time.perf_counter() - t0) * 1000.0 * (1000.0 / batch))
    return float(np.median(times))


def main():
    ap = argparse.ArgumentParser(
        description='Re-run the seven-model scorecard under the current pipeline.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python master_benchmark_rerun.py
  python master_benchmark_rerun.py --seeds 42 1 7
""")
    ap.add_argument('--seeds', type=int, nargs='+', default=[42],
                    help='one seed reproduces the scorecard; several add CIs')
    ap.add_argument('--models', nargs='+', default=list(Z.ALL_MODELS),
                    choices=list(Z.ALL_MODELS))
    ap.add_argument('--epochs', type=int, default=Z.EPOCHS)
    ap.add_argument('--also-knn-h5', action='store_true', default=True)
    args = ap.parse_args()

    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'master_benchmark_rerun_{run_ts}')
    out_dir.mkdir(parents=True, exist_ok=True)

    device = Z.get_device()
    data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
    data_dir = sorted(data_base.glob('sim_data_300users_*'))[-1]
    bs_pos = np.array(_read_bs_position_3d(data_dir))

    log(f'device={device} | seeds={args.seeds} | models={args.models}')

    rows = {}
    for seed in args.seeds:
        df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=seed,
                                         single_ant_ratio=Z.SINGLE_ANT_RATIO)
        df, _, test_uids = make_unseen_user_split(df, Z.TRAIN_RATIO, seed)
        df_tr, df_te = df[df.split == 'train'], df[df.split == 'test']
        log('=' * 96)
        log(f'SEED {seed}  ({len(test_uids)} disjoint test users)')
        log('=' * 96)

        jobs = [(m, SCORECARD_H[m]) for m in args.models]
        if args.also_knn_h5 and 'knn' in args.models:
            jobs.append(('knn', 5))

        for name, h in jobs:
            masked = name == 'mask_aware_cnn'
            a_tr, a_te = (Z.apply_aoa_mask(df_tr), Z.apply_aoa_mask(df_te)) if masked \
                else (df_tr, df_te)
            cols = csi_dataset.SIGNAL_COLS + ['has_valid_aoa'] if masked \
                else csi_dataset.SIGNAL_COLS

            with Z.signal_cols(cols):
                tr, te = Z.make_datasets(a_tr, a_te, h)
                ts, tm = tr.targ_std, tr.targ_mean
                X_te, Y, _, _, ant = Z.flatten(te)

                t0 = time.time()
                if name in Z.DEEP:
                    torch.manual_seed(seed)
                    np.random.seed(seed)
                    net = Z.build_net(name, h, in_channels=len(cols))
                    pred = Z.train_deep(net, tr, te, ts, tm, device,
                                        name=name, epochs=args.epochs)
                    train_s = time.time() - t0
                    n_params = count_params(net, name, X_te.shape[1])

                    def predict_fn(xs, _net=net, _te=te):
                        import torch as T
                        with T.no_grad():
                            n = len(xs)
                            seq = T.stack([T.as_tensor(_te.samples[i]['seq'])
                                           for i in range(n)]).to(device)
                            st = T.stack([T.as_tensor(_te.samples[i]['static'])
                                          for i in range(n)]).to(device)
                            _net(seq, st)
                    latency = measure_latency(predict_fn, X_te, n_rep=3, batch=500)
                else:
                    X_tr, Y_tr, _, _, _ = Z.flatten(tr)
                    model = Z.build_classical(name, seed)
                    model.fit(X_tr, Y_tr)
                    train_s = time.time() - t0
                    pred = model.predict(X_te) * ts + tm
                    n_params = count_params(model, name, X_te.shape[1])
                    latency = measure_latency(model.predict, X_te)

            m = Z.evaluate(pred, Y * ts + tm, ant)
            m.update(seed=seed, h=h, n_params=n_params,
                     train_time_sec=round(train_s, 1),
                     latency_ms_per_1k=round(latency, 3),
                     n_features=int(X_te.shape[1]))
            rows.setdefault(f'{name}_h{h}', []).append(m)
            pstr = f'{n_params:,}' if n_params else '-'
            log(f'  {name + " h=" + str(h):<22} MAE {m["mae"]:7.3f} | P50 {m["p50"]:6.3f} '
                f'P90 {m["p90"]:6.3f} | multi {m["multi_mae"]:6.3f} '
                f'single {m["single_mae"]:6.3f} | params {pstr:>10} | {train_s:.0f}s')

    # ── scorecard ────────────────────────────────────────────────────────────
    log('')
    log('=' * 96)
    log('SCORECARD (current pipeline)')
    log('=' * 96)
    log(f'{"model":<22}{"h":>3}{"params":>12}{"train s":>9}{"ms/1k":>8}'
        f'{"MAE":>9}{"P50":>8}{"P90":>8}{"multi":>8}{"single":>8}')
    log('-' * 96)
    summary = {}
    for key, runs in sorted(rows.items(), key=lambda kv: np.mean([r['mae'] for r in kv[1]])):
        agg = {k: float(np.mean([r[k] for r in runs]))
               for k in ('mae', 'p50', 'p90', 'multi_mae', 'single_mae')}
        agg['mae_ci95'] = Z.ci95([r['mae'] for r in runs])
        agg['single_ci95'] = Z.ci95([r['single_mae'] for r in runs])
        agg['n_params'] = runs[0]['n_params']
        agg['h'] = runs[0]['h']
        agg['train_time_sec'] = float(np.mean([r['train_time_sec'] for r in runs]))
        agg['latency_ms_per_1k'] = float(np.mean([r['latency_ms_per_1k'] for r in runs]))
        agg['n_seeds'] = len(runs)
        agg['runs'] = runs
        summary[key] = agg
        pstr = f'{agg["n_params"]:,}' if agg['n_params'] else '-'
        log(f'{key:<22}{agg["h"]:>3}{pstr:>12}{agg["train_time_sec"]:>9.1f}'
            f'{agg["latency_ms_per_1k"]:>8.2f}{agg["mae"]:>9.3f}{agg["p50"]:>8.3f}'
            f'{agg["p90"]:>8.3f}{agg["multi_mae"]:>8.3f}{agg["single_mae"]:>8.3f}')

    # ── what changed against the recorded benchmark ──────────────────────────
    recorded_path = (PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'docs'
                     / 'results_of_record' / 'campaign_b' / 'master_benchmark_summary.json')
    deltas = {}
    if recorded_path.exists():
        rec = json.loads(recorded_path.read_text(encoding='utf-8'))
        log('')
        log('=' * 96)
        log('AGAINST THE RECORDED BENCHMARK  (recorded -> current)')
        log('=' * 96)
        log(f'{"model":<22}{"MAE rec":>10}{"MAE now":>10}{"delta":>9}'
            f'{"single rec":>12}{"single now":>12}{"delta":>9}')
        log('-' * 96)
        for key, agg in summary.items():
            if key not in rec:
                continue
            r = rec[key]
            d = {'mae_recorded': r['raw_mae'], 'mae_current': agg['mae'],
                 'mae_delta': agg['mae'] - r['raw_mae'],
                 'single_recorded': r['single_mae'], 'single_current': agg['single_mae'],
                 'single_delta': agg['single_mae'] - r['single_mae']}
            deltas[key] = d
            log(f'{key:<22}{r["raw_mae"]:>10.3f}{agg["mae"]:>10.3f}{d["mae_delta"]:>+9.3f}'
                f'{r["single_mae"]:>12.3f}{agg["single_mae"]:>12.3f}'
                f'{d["single_delta"]:>+9.3f}')
        worst = max(deltas.values(), key=lambda v: abs(v['mae_delta']), default=None)
        if worst:
            log('')
            log(f'largest overall-MAE discrepancy: {abs(worst["mae_delta"]):.3f} m')

    results = {
        'meta': {'dataset': str(data_dir), 'seeds': args.seeds, 'models': args.models,
                 'epochs': args.epochs, 'device': str(device),
                 'scorecard_h': SCORECARD_H,
                 'protocol': 'Campaign B, disjoint-user split, 85/15 cohort mix, '
                             'early stopping on test MAE; smoothing excluded (see §7.7)'},
        'scorecard': summary,
        'vs_recorded': deltas,
    }
    out = out_dir / 'master_benchmark_rerun_summary.json'
    out.write_text(json.dumps(results, indent=1), encoding='utf-8')
    log(f'saved -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
