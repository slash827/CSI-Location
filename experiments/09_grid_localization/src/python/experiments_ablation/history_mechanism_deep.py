"""
History-mechanism diagnostic for the neural families.

history_mechanism_diagnostic.py answers "which channels carry the history
gain" for the classical models only. This runs the same question on the four
neural families, so the answer no longer has to be inferred for them. The AoA
impairment can be changed with the same options as
history_mechanism_followup.py, to test whether the neural gain is also the
averaging of per-report AoA error.

A network needs a fixed [13 x (h+1)] input, so a condition cannot drop
columns. Instead, every channel that is NOT allowed its history is held at its
current value across the whole window: it then carries no information about
earlier steps. All conditions share the same windows and the same users.

    condition    channels that keep their real h+1 steps
    snap         none (every channel constant at its current value)
    rss_hist     rss, sinr, d_rss, delta_t
    angle_hist   sin/cos az/el, d_az, delta_t
    ray_hist     ray_x, ray_y, d_ray_x, d_ray_y, delta_t
    angle_mean   none; the angle channels are constant at their window mean
    full         all

Protocol is train_deep from model_zoo, unchanged: the checkpoint is selected
on test MAE, identically for every condition.

Usage (from the repository root):
    E=experiments/09_grid_localization/src/python/experiments_ablation
    .venv/Scripts/python $E/history_mechanism_deep.py --data-dir <dataset>
"""
import argparse
import copy
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import history_mechanism_diagnostic as D
from history_mechanism_diagnostic import ANGLE_SIDE, RAY_SIDE, RSS_SIDE, SIGNAL_COLS, TIME_SIDE
from history_mechanism_followup import keep_awake, paired, prepare_correlated

BASELINE = 'snap'
KEEP = {
    'snap': [],
    'rss_hist': RSS_SIDE + TIME_SIDE,
    'angle_hist': ANGLE_SIDE + TIME_SIDE,
    'ray_hist': RAY_SIDE + TIME_SIDE,
    'angle_mean': [],
    'full': SIGNAL_COLS,
}


def hold_current(seq, keep, mean_of=()):
    """Copy of a [n_channels, L] window with history removed from some channels.

    Channels in `keep` are untouched. Channels in `mean_of` become constant at
    their window mean. Every other channel becomes constant at its current
    (last) value.
    """
    out = seq.copy()
    for c in range(seq.shape[0]):
        # rows past SIGNAL_COLS are extra inputs (the mask-aware CNN's validity
        # flag); they are constant per user, so holding them changes nothing
        name = SIGNAL_COLS[c] if c < len(SIGNAL_COLS) else None
        if name in keep:
            continue
        out[c, :] = seq[c].mean() if name in mean_of else seq[c, -1]
    return out


def conditioned(ds, cond):
    """Shallow copy of a dataset whose windows are rewritten for one condition."""
    new = copy.copy(ds)
    mean_of = ANGLE_SIDE if cond == 'angle_mean' else ()
    new.samples = [{**s, 'seq': hold_current(s['seq'], KEEP[cond], mean_of)} for s in ds.samples]
    return new


def main():
    ap = argparse.ArgumentParser(
        description='Which channels carry the history gain, for the neural families.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python history_mechanism_deep.py --data-dir results/grid_localization/grid_25x25/sim_data_300users_2026-07-25_11-46-11
  python history_mechanism_deep.py --data-dir <dataset> --models cnn --seeds 42 --epochs 3
""")
    ap.add_argument('--data-dir', required=True, help='dataset folder; no glob')
    ap.add_argument('--seeds', type=int, nargs='+', default=[42, 1, 7, 13, 99])
    ap.add_argument('--models', nargs='+', default=['cnn', 'gru'],
                    choices=['cnn', 'gru', 'cnn_attn', 'mask_aware_cnn'])
    ap.add_argument('--conditions', nargs='+', default=list(KEEP), choices=list(KEEP))
    ap.add_argument('--history', type=int, default=5)
    ap.add_argument('--epochs', type=int, default=None)
    ap.add_argument('--aoa-noise-std', type=float, default=4.0,
                    help='Gaussian AoA error in degrees (default 4.0)')
    ap.add_argument('--aoa-quant-step', type=float, default=5.0,
                    help='AoA quantisation step in degrees (default 5.0); use a tiny value for none')
    ap.add_argument('--aoa-noise-corr', type=float, default=None,
                    help='lag-1 correlation of the AoA error along a walk (AR(1)); '
                         'omit for the original independent error')
    args = ap.parse_args()

    keep_awake()
    import torch
    import model_zoo as Z
    from model_zoo import PROJECT_ROOT, log
    from pipelines.multi_user_pipeline_regression import _read_bs_position_3d
    from pipelines.multi_user_200_pipeline import make_unseen_user_split
    from utils import csi_dataset
    from utils.csi_dataset import load_and_prepare_data

    if list(csi_dataset.SIGNAL_COLS) != SIGNAL_COLS:
        raise RuntimeError(f'SIGNAL_COLS changed: {csi_dataset.SIGNAL_COLS}')
    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir
    if not data_dir.is_dir():
        raise SystemExit(f'dataset not found: {data_dir}')
    if BASELINE not in args.conditions:
        args.conditions = [BASELINE] + args.conditions

    h = args.history
    epochs = args.epochs or Z.EPOCHS
    device = Z.get_device()
    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    aoa_tag = ('' if (args.aoa_noise_std, args.aoa_quant_step, args.aoa_noise_corr) == (4.0, 5.0, None)
               else f'aoa{args.aoa_noise_std:g}n{args.aoa_quant_step:g}q_')
    if args.aoa_noise_corr is not None:
        aoa_tag += f'rho{args.aoa_noise_corr:g}_'
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'history_mechanism_deep_{aoa_tag}{data_dir.name}_{"-".join(args.models)}_{run_ts}')
    # exist_ok=False: two runs started in the same second must not share a folder
    out_dir.mkdir(parents=True, exist_ok=False)
    bs_pos = np.array(_read_bs_position_3d(data_dir))
    log(f'dataset={data_dir.name} | h={h} | seeds={args.seeds} | models={args.models} | device={device}')

    raw = {n: {c: [] for c in args.conditions} for n in args.models}
    t_start = time.time()
    for seed in args.seeds:
        if args.aoa_noise_corr is None:
            df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=seed,
                                             single_ant_ratio=Z.SINGLE_ANT_RATIO,
                                             aoa_noise_std_deg=args.aoa_noise_std,
                                             aoa_quant_step_deg=args.aoa_quant_step)
        else:
            df = prepare_correlated(data_dir, bs_pos, seed, Z.SINGLE_ANT_RATIO,
                                    args.aoa_noise_std, args.aoa_quant_step, args.aoa_noise_corr)
        df, _, _ = make_unseen_user_split(df, Z.TRAIN_RATIO, seed)
        df_tr, df_te = df[df.split == 'train'], df[df.split == 'test']
        # the mask-aware CNN reads one extra channel, so it gets its own datasets
        data = {}
        for masked in sorted({n == 'mask_aware_cnn' for n in args.models}):
            if masked:
                with Z.signal_cols(SIGNAL_COLS + ['has_valid_aoa']):
                    data[masked] = Z.make_datasets(Z.apply_aoa_mask(df_tr), Z.apply_aoa_mask(df_te), h)
            else:
                data[masked] = Z.make_datasets(df_tr, df_te, h)
        tr, te = next(iter(data.values()))
        ts, tm = tr.targ_std, tr.targ_mean
        _, Y, uid, _, ant = Z.flatten(te)
        true = Y * ts + tm
        log('=' * 84)
        log(f'SEED {seed}: {len(te):,} test windows')
        for cond in args.conditions:
            cond_data = {k: (conditioned(a, cond), conditioned(b, cond)) for k, (a, b) in data.items()}
            for name in args.models:
                t0 = time.time()
                tr_c, te_c = cond_data[name == 'mask_aware_cnn']
                torch.manual_seed(seed)
                np.random.seed(seed)
                net = Z.build_net(name, h)
                pred = Z.train_deep(net, tr_c, te_c, ts, tm, device, name=name, epochs=epochs)
                groups, _ = D.per_group_metrics(pred, true, ant, uid)
                raw[name][cond].append({'seed': seed, 'elapsed_sec': round(time.time() - t0, 1),
                                        'groups': groups})
                log(f'  {name:<10}{cond:<12}| multi {groups["multi"]["mae"]:6.3f} '
                    f'single {groups["single"]["mae"]:6.3f} m | {time.time() - t0:.0f}s')

    summary = {}
    log('')
    log('=' * 84)
    log(f'SEED-PAIRED GAIN vs {BASELINE} (m, +ve = lower error), mean +/- Student-t 95%')
    log('=' * 84)
    for name in args.models:
        summary[name] = {}
        for cond in args.conditions:
            rec = {}
            for g in D.GROUPS:
                maes = [r['groups'][g]['mae'] for r in raw[name][cond]]
                rec[g] = {'mae_mean': float(np.mean(maes)),
                          'radial_mean': float(np.mean([r['groups'][g]['radial_mean'] for r in raw[name][cond]])),
                          'tangential_mean': float(np.mean([r['groups'][g]['tangential_mean'] for r in raw[name][cond]]))}
                if cond != BASELINE:
                    rec[g]['gain_vs_snap'] = paired([r['groups'][g]['mae'] for r in raw[name][BASELINE]], maes)
            summary[name][cond] = rec
            if cond != BASELINE:
                f = lambda g: (f'{g} {rec[g]["gain_vs_snap"]["gain_mean_m"]:+6.3f} +/- '
                               f'{rec[g]["gain_vs_snap"]["gain_t95_m"] or float("nan"):5.3f}')
                log(f'  {name:<10}{cond:<12}{f("multi")} | {f("single")}')

    results = {
        'meta': {'dataset': data_dir.name, 'h': h, 'seeds': args.seeds, 'models': args.models,
                 'conditions': {c: KEEP[c] for c in args.conditions}, 'baseline': BASELINE,
                 'epochs': epochs, 'device': str(device),
                 'aoa_noise_std_deg': args.aoa_noise_std, 'aoa_quant_step_deg': args.aoa_quant_step,
                 'aoa_noise_lag1_corr': args.aoa_noise_corr,
                 'interval': 'Student-t 95% over seed-paired differences',
                 'protocol': 'macro-cell protocol: unseen-user split; channels without history are '
                             'held at their current value; early stopping on test MAE, as in model_zoo',
                 'wall_time_sec': round(time.time() - t_start, 1)},
        'summary': summary,
        'per_seed': raw,
    }
    out = out_dir / 'history_mechanism_deep_summary.json'
    out.write_text(json.dumps(results, indent=1), encoding='utf-8')
    log(f'saved -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
