"""
B2: Seed repeats and confidence intervals across all seven model families.

A5 established the noise floor on the two cheap models only (k-NN, XGBoost), so
section 5.7 currently has to say that the deep models have not been repeated at
all. That is the weakest sentence in the report: the section 6 scorecard ranks
seven families by single-seed point estimates, and the top four sit within a few
tenths of a metre of each other. Without error bars there is no way to say whether
that ranking means anything.

This repeats the full Campaign B protocol over seeds, at h=0 and h=5, for every
family. The seed drives both the train/test user split and model initialisation.

Two quantities are reported and they answer different questions:

  * the *marginal* spread across seeds - how much a single reported number could
    have moved by luck. This is the noise floor a reader should apply to any
    claimed delta.
  * the *seed-paired* history gain (h=0 minus h=5 within each seed) - the correct
    test of the mechanism, because both arms then share a user split and the
    dominant source of variance cancels.

Usage:
    python seed_repeats_all_models.py
    python seed_repeats_all_models.py --seeds 42 1 7 --models knn xgboost cnn
    python seed_repeats_all_models.py --depths 0 5 --epochs 30
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


def run_one(name, df_tr, df_te, h, seed, device, epochs):
    """Train one family at one depth on one split; return the metric block."""
    masked = name == 'mask_aware_cnn'
    if masked:
        df_tr, df_te = Z.apply_aoa_mask(df_tr), Z.apply_aoa_mask(df_te)
        cols = csi_dataset.SIGNAL_COLS + ['has_valid_aoa']
    else:
        cols = csi_dataset.SIGNAL_COLS

    with Z.signal_cols(cols):
        tr, te = Z.make_datasets(df_tr, df_te, h)
        ts, tm = tr.targ_std, tr.targ_mean
        if name in Z.DEEP:
            torch.manual_seed(seed)
            np.random.seed(seed)
            net = Z.build_net(name, h, in_channels=len(cols))
            pred = Z.train_deep(net, tr, te, ts, tm, device, name=name, epochs=epochs)
            _, Y, _, _, ant = Z.flatten(te)
        else:
            X_tr, Y_tr, _, _, _ = Z.flatten(tr)
            X_te, Y, _, _, ant = Z.flatten(te)
            model = Z.build_classical(name, seed)
            model.fit(X_tr, Y_tr)
            pred = model.predict(X_te) * ts + tm
    return Z.evaluate(pred, Y * ts + tm, ant)


def main():
    ap = argparse.ArgumentParser(
        description='Seed repeats across all seven model families (B2).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python seed_repeats_all_models.py
  python seed_repeats_all_models.py --seeds 42 1 7 --models knn cnn
  python seed_repeats_all_models.py --depths 0 5 --epochs 30
""")
    ap.add_argument('--seeds', type=int, nargs='+', default=[42, 1, 7, 13, 99])
    ap.add_argument('--depths', type=int, nargs='+', default=[0, 5])
    ap.add_argument('--models', nargs='+', default=list(Z.ALL_MODELS),
                    choices=list(Z.ALL_MODELS))
    ap.add_argument('--epochs', type=int, default=Z.EPOCHS)
    ap.add_argument('--single-ant-ratio', type=float, default=Z.SINGLE_ANT_RATIO)
    args = ap.parse_args()

    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'seed_repeats_all_models_{run_ts}')
    out_dir.mkdir(parents=True, exist_ok=True)

    device = Z.get_device()
    data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
    data_dir = sorted(data_base.glob('sim_data_300users_*'))[-1]
    bs_pos = np.array(_read_bs_position_3d(data_dir))

    log(f'device={device} | seeds={args.seeds} | depths={args.depths}')
    log(f'models={args.models}')

    raw = {}                       # (model, h) -> list of per-seed metric blocks
    t_start = time.time()
    for seed in args.seeds:
        t_seed = time.time()
        df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=seed,
                                         single_ant_ratio=args.single_ant_ratio)
        df, _, test_uids = make_unseen_user_split(df, Z.TRAIN_RATIO, seed)
        df_tr, df_te = df[df.split == 'train'], df[df.split == 'test']
        log('=' * 84)
        log(f'SEED {seed}  ({len(test_uids)} test users)')
        log('=' * 84)
        for h in args.depths:
            for name in args.models:
                t0 = time.time()
                m = run_one(name, df_tr, df_te, h, seed, device, args.epochs)
                m['seed'] = seed
                m['n_test_users'] = int(len(test_uids))
                raw.setdefault((name, h), []).append(m)
                log(f'  h={h:<3}{name:<16} MAE {m["mae"]:7.3f} m | '
                    f'multi {m["multi_mae"]:6.3f} single {m["single_mae"]:6.3f} | '
                    f'{time.time() - t0:.0f}s')
        log(f'  seed {seed} complete in {time.time() - t_seed:.0f}s')

    results = {'meta': {'dataset': str(data_dir), 'seeds': args.seeds,
                        'depths': args.depths, 'models': args.models,
                        'epochs': args.epochs, 'device': str(device),
                        'protocol': 'Campaign B, disjoint-user split, '
                                    'early stopping on test MAE'},
               'per_config': {}}

    log('')
    log('=' * 84)
    log('MARGINAL SEED VARIABILITY (mean +/- 95% CI, and full range)')
    log('=' * 84)
    log(f'{"model":<17}{"h":>3}{"MAE mean":>11}{"95% CI":>10}{"min":>9}{"max":>9}{"spread":>9}')
    log('-' * 84)
    for (name, h), runs in sorted(raw.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        maes = [r['mae'] for r in runs]
        rec = {
            'runs': runs,
            'mae_mean': float(np.mean(maes)),
            'mae_std': float(np.std(maes, ddof=1)) if len(maes) > 1 else 0.0,
            'mae_ci95': Z.ci95(maes),
            'mae_min': float(min(maes)), 'mae_max': float(max(maes)),
            'mae_spread': float(max(maes) - min(maes)),
            'multi_mean': float(np.mean([r['multi_mae'] for r in runs])),
            'multi_ci95': Z.ci95([r['multi_mae'] for r in runs]),
            'single_mean': float(np.mean([r['single_mae'] for r in runs])),
            'single_ci95': Z.ci95([r['single_mae'] for r in runs]),
        }
        results['per_config'][f'{name}_h{h}'] = rec
        log(f'{name:<17}{h:>3}{rec["mae_mean"]:>11.3f}{rec["mae_ci95"]:>9.3f}m'
            f'{rec["mae_min"]:>9.3f}{rec["mae_max"]:>9.3f}{rec["mae_spread"]:>9.3f}')

    # ── seed-paired history gain ─────────────────────────────────────────────
    lo, hi = args.depths[0], args.depths[-1]
    verdict = {}
    if lo != hi:
        log('')
        log('=' * 84)
        log(f'SEED-PAIRED HISTORY GAIN  h={lo} -> h={hi}')
        log('=' * 84)
        for name in args.models:
            a = results['per_config'].get(f'{name}_h{lo}')
            b = results['per_config'].get(f'{name}_h{hi}')
            if not (a and b):
                continue
            by_seed_a = {r['seed']: r['mae'] for r in a['runs']}
            by_seed_b = {r['seed']: r['mae'] for r in b['runs']}
            pairs = [by_seed_a[s] - by_seed_b[s] for s in by_seed_a if s in by_seed_b]
            gm, gc = float(np.mean(pairs)), Z.ci95(pairs)
            verdict[name] = {
                'gain_mean_m': round(gm, 4), 'gain_ci95_m': round(gc, 4),
                'gain_pct': round(100 * gm / a['mae_mean'], 2),
                'marginal_spread_at_h0_m': round(a['mae_spread'], 4),
                'n_pairs': len(pairs),
                'significant': bool(gm - gc > 0),
            }
            log(f'{name:<17} {gm:+7.3f} m +/- {gc:5.3f} ({100 * gm / a["mae_mean"]:+5.2f}%) | '
                f'marginal spread at h={lo}: {a["mae_spread"]:5.3f} m | '
                f'{"SIGNIFICANT" if gm - gc > 0 else "not significant"}')
    results['verdict'] = verdict

    # ── is the scorecard ranking resolved? ───────────────────────────────────
    at_hi = {n: results['per_config'][f'{n}_h{hi}']
             for n in args.models if f'{n}_h{hi}' in results['per_config']}
    ranking = sorted(at_hi.items(), key=lambda kv: kv[1]['mae_mean'])
    log('')
    log('=' * 84)
    log(f'SCORECARD AT h={hi}: IS THE RANKING RESOLVED?')
    log('=' * 84)
    ties = []
    for i, (name, rec) in enumerate(ranking):
        band = f'[{rec["mae_mean"] - rec["mae_ci95"]:.3f}, {rec["mae_mean"] + rec["mae_ci95"]:.3f}]'
        log(f'  {i + 1}. {name:<17}{rec["mae_mean"]:7.3f} m  CI {band}')
    for i in range(len(ranking) - 1):
        a_n, a_r = ranking[i]
        b_n, b_r = ranking[i + 1]
        # overlapping CIs -> the pair is not separated by this many seeds
        if a_r['mae_mean'] + a_r['mae_ci95'] >= b_r['mae_mean'] - b_r['mae_ci95']:
            ties.append([a_n, b_n])
    results['ranking'] = [{'model': n, 'mae_mean': r['mae_mean'],
                           'mae_ci95': r['mae_ci95']} for n, r in ranking]
    results['unresolved_adjacent_pairs'] = ties
    if len(args.seeds) < 2:
        # a single seed gives CI = 0, which would read as "everything separated"
        results['unresolved_adjacent_pairs'] = None
        log('  single seed - no confidence intervals, separation undetermined.')
    elif ties:
        log(f'  {len(ties)} adjacent pair(s) with overlapping CIs -> not separated:')
        for a_n, b_n in ties:
            log(f'    {a_n} vs {b_n}')
    else:
        log('  every adjacent pair is separated at 95%.')

    floor = max((v['marginal_spread_at_h0_m'] for v in verdict.values()), default=0.0)
    results['noise_floor_m'] = round(floor, 4)
    log('')
    log(f'Marginal seed-to-seed spread reaches {floor:.3f} m. Any claimed delta below')
    log('roughly that magnitude is unresolved by a single run.')
    log(f'total wall time: {time.time() - t_start:.0f}s')

    out = out_dir / 'seed_repeats_all_models_summary.json'
    out.write_text(json.dumps(results, indent=1), encoding='utf-8')
    log(f'saved -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
