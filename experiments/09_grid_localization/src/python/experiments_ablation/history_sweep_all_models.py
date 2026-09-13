"""
B3: One history sweep, one protocol, all seven model families.

The universality figure (`universal_delta_mae_history_curves.png`) currently
plots four curves drawn from three different experiments:

  * 1D-CNN      - Campaign B, disjoint-user split, 2D MAE.           (correct)
  * XGBoost, RF - the July 200-user sweeps on raw features.          (other protocol)
  * GRU         - the July *single-user* exploration, chronological
                  20% split, 3D MAE, raw AoA angles, hidden_dim=64.  (leaky split)

The GRU curve is the problem. A chronological split within one user's walk puts
test samples spatially between training samples, so the model interpolates a track
it has already seen. That is why it reads 8.534 m where Campaign B's GRU reads
18.518 m, and why its gain reads -50.4% where every honest curve reads -6% to -16%.
Plotting it beside the others overstates exactly the claim the figure exists to
support.

This script measures all seven families at h in {0,1,3,5,10} under one protocol -
the Campaign B disjoint-user split, 2D MAE, the same derived features and the same
early-stopping rule - so the figure can be rebuilt from a single run.

Usage:
    python history_sweep_all_models.py
    python history_sweep_all_models.py --models cnn gru --depths 0 5
    python history_sweep_all_models.py --epochs 30
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

# distance covered per step, from the simulator: delta_t = spacing / speed and
# every step advances exactly one grid cell, so this is constant (see B1, §5.8)
GRID_SPACING_M = 4.0


def run_one(name, df_tr, df_te, h, seed, device, epochs):
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
            n_params = sum(p.numel() for p in net.parameters())
            pred = Z.train_deep(net, tr, te, ts, tm, device, name=name, epochs=epochs)
            _, Y, _, dt, ant = Z.flatten(te)
        else:
            X_tr, Y_tr, _, _, _ = Z.flatten(tr)
            X_te, Y, _, dt, ant = Z.flatten(te)
            model = Z.build_classical(name, seed)
            model.fit(X_tr, Y_tr)
            pred = model.predict(X_te) * ts + tm
            n_params = None
    m = Z.evaluate(pred, Y * ts + tm, ant)
    m['n_params'] = n_params
    m['median_delta_t_s'] = float(np.median(dt))
    m['window_s'] = float(np.median(dt) * h)
    m['window_m'] = float(GRID_SPACING_M * h)
    return m


def main():
    ap = argparse.ArgumentParser(
        description='History sweep across all seven model families, one protocol (B3).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python history_sweep_all_models.py
  python history_sweep_all_models.py --models cnn gru --depths 0 5
  python history_sweep_all_models.py --epochs 30
""")
    ap.add_argument('--depths', type=int, nargs='+', default=[0, 1, 3, 5, 10])
    ap.add_argument('--models', nargs='+', default=list(Z.ALL_MODELS),
                    choices=list(Z.ALL_MODELS))
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--epochs', type=int, default=Z.EPOCHS)
    ap.add_argument('--single-ant-ratio', type=float, default=Z.SINGLE_ANT_RATIO)
    args = ap.parse_args()

    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'history_sweep_all_models_{run_ts}')
    out_dir.mkdir(parents=True, exist_ok=True)

    device = Z.get_device()
    data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
    data_dir = sorted(data_base.glob('sim_data_300users_*'))[-1]
    bs_pos = np.array(_read_bs_position_3d(data_dir))

    log(f'device={device} | seed={args.seed} | depths={args.depths}')
    log(f'models={args.models}')

    df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=args.seed,
                                     single_ant_ratio=args.single_ant_ratio)
    df, _, test_uids = make_unseen_user_split(df, Z.TRAIN_RATIO, args.seed)
    df_tr, df_te = df[df.split == 'train'], df[df.split == 'test']
    log(f'{len(df_tr):,} train rows / {len(df_te):,} test rows '
        f'({len(test_uids)} disjoint test users)')

    curves = {}
    t_start = time.time()
    for name in args.models:
        log('=' * 88)
        log(f'MODEL: {Z.DISPLAY_NAME[name]}  ({name})')
        log('=' * 88)
        curves[name] = {}
        for h in args.depths:
            t0 = time.time()
            m = run_one(name, df_tr, df_te, h, args.seed, device, args.epochs)
            m['train_time_s'] = round(time.time() - t0, 1)
            curves[name][f'h{h}'] = m
            log(f'  h={h:<3} MAE {m["mae"]:7.3f} m | p50 {m["p50"]:6.3f} '
                f'p90 {m["p90"]:6.3f} | multi {m["multi_mae"]:6.3f} '
                f'single {m["single_mae"]:6.3f} | {m["train_time_s"]:.0f}s')

    results = {
        'meta': {
            'dataset': str(data_dir), 'seed': args.seed, 'depths': args.depths,
            'models': args.models, 'epochs': args.epochs, 'device': str(device),
            'n_test_users': int(len(test_uids)),
            'grid_spacing_m': GRID_SPACING_M,
            'protocol': 'Campaign B: disjoint-user split, 2D MAE, derived features, '
                        'early stopping on test MAE. Identical for every family and depth.',
        },
        'curves': curves,
    }

    # ── summary table ────────────────────────────────────────────────────────
    log('')
    log('=' * 88)
    log('HISTORY CURVES, ONE PROTOCOL (2D MAE, metres)')
    log('=' * 88)
    hdr = f'{"model":<17}' + ''.join(f'{"h=" + str(h):>9}' for h in args.depths)
    log(hdr + f'{"best h":>8}{"gain %":>9}')
    log('-' * 88)
    summary = {}
    for name in args.models:
        maes = [curves[name][f'h{h}']['mae'] for h in args.depths]
        base = maes[0]
        best_i = int(np.argmin(maes))
        best_h = args.depths[best_i]
        gain = 100 * (base - maes[best_i]) / base
        summary[name] = {
            'mae_by_depth': {f'h{h}': round(v, 4) for h, v in zip(args.depths, maes)},
            'delta_pct_by_depth': {f'h{h}': round(100 * (v - base) / base, 3)
                                   for h, v in zip(args.depths, maes)},
            'baseline_h0_mae': round(base, 4),
            'best_h': best_h,
            'best_mae': round(maes[best_i], 4),
            'gain_pct': round(gain, 3),
            'monotonic': bool(all(b <= a + 1e-9 for a, b in zip(maes, maes[1:]))),
            'window_m_at_best': GRID_SPACING_M * best_h,
        }
        log(f'{name:<17}' + ''.join(f'{v:>9.3f}' for v in maes)
            + f'{best_h:>8}{gain:>8.2f}%')
    results['summary'] = summary

    gains = {n: s['gain_pct'] for n, s in summary.items()}
    all_improve = all(g > 0 for g in gains.values())
    results['verdict'] = {
        'n_models': len(summary),
        'n_improved': int(sum(1 for g in gains.values() if g > 0)),
        'all_families_improve': bool(all_improve),
        'gain_min_pct': round(min(gains.values()), 3),
        'gain_max_pct': round(max(gains.values()), 3),
        'best_h_values': {n: s['best_h'] for n, s in summary.items()},
    }
    log('')
    log(f'families improving with history: {results["verdict"]["n_improved"]}/{len(summary)}'
        f'  (gains {min(gains.values()):.2f}% to {max(gains.values()):.2f}%)')
    log(f'best h per family: {results["verdict"]["best_h_values"]}')
    log(f'total wall time: {time.time() - t_start:.0f}s')

    out = out_dir / 'history_sweep_all_models_summary.json'
    out.write_text(json.dumps(results, indent=1), encoding='utf-8')
    log(f'saved -> {out}')
    log('')
    log('Rebuild the figure with:')
    log(f'  python plotting/plot_unified_delta_mae.py --summary "{out}"')
    return 0


if __name__ == '__main__':
    sys.exit(main())
