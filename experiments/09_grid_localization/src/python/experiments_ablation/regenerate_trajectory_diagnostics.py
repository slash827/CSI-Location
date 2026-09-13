"""
B4: Regenerate the per-user trajectory diagnostics with a correct time base.

The trajectory figures in the report (Figures 5 and 6) were produced by notebooks
06 and 07 before the `delta_t` defect was found. `DerivedCSI1DDataset` standardises
SIGNAL_COLS in place, and `delta_t` is one of them, so the per-sample time step
handed to the Kalman/RTS smoother was a z-score rather than seconds: 85.8% of
values were negative and got clamped to 0.01 s by `max(0.01, dt)`, which destroys
the state transition. Fixed in commit dee50dd.

The damage is visible in the old figures. The green smoothed track collapses to a
short stub near the middle of the walk, and the smoothed error sawtooths between
0 and 30 m against a raw error of about 10 m. Smoothing appeared to *hurt*.

Two things change here:

  1. The time base is correct, so the smoother integrates real seconds.
  2. The filter is run at the process noise the cross-model sweep found for this
     architecture (section 7.7) rather than the notebook default of Q=0.5. With a
     correct dt the 1D-CNN optimum is Q=4.0, R=40.0, worth +3.65% population MAE;
     the old default is within noise of doing nothing.

Both smoothed tracks are drawn, default and tuned, so the figure documents the fix
rather than silently replacing one curve with another.

Usage:
    python regenerate_trajectory_diagnostics.py
    python regenerate_trajectory_diagnostics.py --users 119 250
    python regenerate_trajectory_diagnostics.py --auto-select --epochs 30
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_zoo as Z
from model_zoo import PROJECT_ROOT, log

from pipelines.multi_user_pipeline_regression import _read_bs_position_3d
from pipelines.multi_user_200_pipeline import make_unseen_user_split
from utils.csi_dataset import load_and_prepare_data
from utils.training_utils import apply_kalman_smoother

FIGURES_DIR = (PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'docs' / 'figures')

# section 7.7, post-fix sweep. The notebook default is kept for comparison.
DEFAULT_Q, DEFAULT_R = 0.5, 15.0
TUNED_Q, TUNED_R = 4.0, 40.0

# Targets are already displacements from the serving BS (csi_dataset builds them
# as ue_xy - bs_pos[:2]), so the BS sits at the origin of this frame and no further
# offset is applied when plotting.


def per_user_trajectory_figure(uid, n_ant, true_xy, raw_xy, rts_def, rts_tun,
                               unc, label, out_path):
    """Two-panel diagnostic: spatial track on the left, error timeline right."""
    err_raw = np.linalg.norm(raw_xy - true_xy, axis=1)
    err_def = np.linalg.norm(rts_def - true_xy, axis=1)
    err_tun = np.linalg.norm(rts_tun - true_xy, axis=1)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(19, 7.6), dpi=150)

    # ── left: trajectory, in metres relative to the serving BS ───────────────
    t_rel, r_rel, d_rel, u_rel = true_xy, raw_xy, rts_def, rts_tun

    # ground truth sits on top: the smoothed tracks loop over it repeatedly and
    # the figure is useless if the reference path is buried
    ax1.plot(t_rel[:, 0], t_rel[:, 1], color='black', lw=3.2,
             label=f'Ground truth (user {uid})', zorder=9)
    ax1.scatter(r_rel[:, 0], r_rel[:, 1], s=17, color='#4b9cd3', alpha=0.55,
                edgecolors='none', label=f'1D-CNN raw (MAE {err_raw.mean():.2f} m)',
                zorder=3)
    ax1.plot(d_rel[:, 0], d_rel[:, 1], color='#c0392b', lw=1.2, alpha=0.55,
             label=f'RTS, notebook default Q={DEFAULT_Q} (MAE {err_def.mean():.2f} m)',
             zorder=4)
    ax1.plot(u_rel[:, 0], u_rel[:, 1], color='#1e8449', lw=1.5, alpha=0.75,
             label=f'RTS, tuned Q={TUNED_Q} R={TUNED_R} (MAE {err_tun.mean():.2f} m)',
             zorder=6)
    ax1.scatter([0], [0], marker='^', s=240, color='red', edgecolors='darkred',
                zorder=7, label='Serving BS (origin)')

    ax1.set_title(f'[{label}] User {uid} trajectory '
                  f'(antennas = {n_ant}, raw MAE = {err_raw.mean():.2f} m)',
                  fontsize=13, fontweight='bold')
    ax1.set_xlabel('X relative to BS (m)', fontsize=11, fontweight='semibold')
    ax1.set_ylabel('Y relative to BS (m)', fontsize=11, fontweight='semibold')
    ax1.grid(True, linestyle='--', alpha=0.4)
    ax1.legend(fontsize=9, framealpha=0.95, loc='best')
    ax1.set_aspect('equal', adjustable='datalim')

    # ── right: error timeline ────────────────────────────────────────────────
    steps = np.arange(len(err_raw))
    ax2.plot(steps, err_raw, color='#4b9cd3', lw=1.3, label='Raw 2D error (m)')
    ax2.plot(steps, err_def, color='#c0392b', lw=1.1, alpha=0.8,
             label=f'RTS default Q={DEFAULT_Q}')
    ax2.plot(steps, err_tun, color='#1e8449', lw=1.5,
             label=f'RTS tuned Q={TUNED_Q}')
    if unc is not None and np.nanmedian(unc) > 0.5:
        ax2.plot(steps, unc, color='#b03a8c', lw=1.1, linestyle='--', alpha=0.8,
                 label='Model uncertainty head')
    ax2.axhline(err_raw.mean(), color='black', lw=1.2, linestyle=':',
                label=f'Mean raw error ({err_raw.mean():.2f} m)')

    ax2.set_title(f'User {uid}: step-by-step error and uncertainty',
                  fontsize=13, fontweight='bold')
    ax2.set_xlabel('Trajectory step index $t$', fontsize=11, fontweight='semibold')
    ax2.set_ylabel('Error / uncertainty (m)', fontsize=11, fontweight='semibold')
    ax2.grid(True, linestyle='--', alpha=0.4)
    ax2.legend(fontsize=9, framealpha=0.95, loc='upper right')
    ax2.set_ylim(bottom=0)

    fig.suptitle('Regenerated with a correct $\\Delta t$ time base (commit dee50dd). '
                 'The non-causal RTS pass now tracks the walk instead of collapsing; '
                 'the causal Kalman pass still degrades it (§7.7).',
                 fontsize=11.5, y=1.005)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    return dict(uid=int(uid), n_antennas=int(n_ant),
                raw_mae=float(err_raw.mean()),
                rts_default_mae=float(err_def.mean()),
                rts_tuned_mae=float(err_tun.mean()),
                n_steps=int(len(err_raw)), figure=out_path.name)


def main():
    ap = argparse.ArgumentParser(
        description='Regenerate trajectory diagnostics with the fixed time base (B4).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python regenerate_trajectory_diagnostics.py
  python regenerate_trajectory_diagnostics.py --users 119 250
  python regenerate_trajectory_diagnostics.py --auto-select
""")
    ap.add_argument('--users', type=int, nargs='+', default=[119, 250],
                    help='user ids to plot; must be in the test split')
    ap.add_argument('--auto-select', action='store_true',
                    help='additionally plot the best multi-antenna and worst '
                         'single-antenna test users found by this run')
    ap.add_argument('--history', type=int, default=5)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--epochs', type=int, default=Z.EPOCHS)
    args = ap.parse_args()

    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'trajectory_diagnostics_{run_ts}')
    out_dir.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    device = Z.get_device()
    data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
    data_dir = sorted(data_base.glob('sim_data_300users_*'))[-1]
    bs_pos = np.array(_read_bs_position_3d(data_dir))

    log(f'device={device} | h={args.history} | seed={args.seed}')
    df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=args.seed,
                                     single_ant_ratio=Z.SINGLE_ANT_RATIO)
    df, _, test_uids = make_unseen_user_split(df, Z.TRAIN_RATIO, args.seed)
    df_tr, df_te = df[df.split == 'train'], df[df.split == 'test']

    tr, te = Z.make_datasets(df_tr, df_te, args.history)
    ts, tm = tr.targ_std, tr.targ_mean
    log(f'{len(tr):,} train / {len(te):,} test windows')

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    net = Z.build_net('cnn', args.history)
    log('training 1D-CNN...')
    pred_m = Z.train_deep(net, tr, te, ts, tm, device, name='cnn', epochs=args.epochs)

    _, Y, uid, dt, ant = Z.flatten(te)
    true_m = Y * ts + tm
    test_users = np.unique(uid)

    # the uncertainty head, for the right-hand panel
    unc_all = np.full(len(uid), np.nan)
    try:
        from torch.utils.data import DataLoader
        net.eval()
        vals = []
        with torch.no_grad():
            for b in DataLoader(te, batch_size=Z.BATCH_SIZE, shuffle=False):
                _, _, u = net(b['seq'].to(device), b['static'].to(device))
                vals.append(u.cpu().numpy().ravel())
        # the head predicts a scalar spread in normalised target units; scale it
        # back with the same statistics used to de-normalise the positions
        scale = float(np.mean(ts)) if np.ndim(ts) else float(ts)
        unc_all = np.concatenate(vals) * scale
    except Exception as exc:                       # plotting aid only
        log(f'  uncertainty head unavailable ({exc}); omitting from panel B')

    raw_mae = float(np.linalg.norm(pred_m - true_m, axis=1).mean())
    kf_d, rts_d = apply_kalman_smoother(pred_m, true_m, uid, dt, test_users,
                                        process_noise_std=DEFAULT_Q, R_std=DEFAULT_R)
    kf_t, rts_t = apply_kalman_smoother(pred_m, true_m, uid, dt, test_users,
                                        process_noise_std=TUNED_Q, R_std=TUNED_R)
    mae = lambda P: float(np.linalg.norm(P - true_m, axis=1).mean())
    log('=' * 78)
    log(f'population raw MAE          {raw_mae:.3f} m')
    log(f'RTS, notebook default Q={DEFAULT_Q:<4} {mae(rts_d):.3f} m '
        f'({100 * (raw_mae - mae(rts_d)) / raw_mae:+.2f}%)')
    log(f'RTS, tuned Q={TUNED_Q} R={TUNED_R}      {mae(rts_t):.3f} m '
        f'({100 * (raw_mae - mae(rts_t)) / raw_mae:+.2f}%)')
    log(f'Kalman (causal), tuned      {mae(kf_t):.3f} m '
        f'({100 * (raw_mae - mae(kf_t)) / raw_mae:+.2f}%)')
    log('=' * 78)

    # per-user MAE, for selection and for the summary
    per_user = {}
    for u in test_users:
        m = uid == u
        per_user[int(u)] = dict(
            raw=float(np.linalg.norm(pred_m[m] - true_m[m], axis=1).mean()),
            rts_tuned=float(np.linalg.norm(rts_t[m] - true_m[m], axis=1).mean()),
            n_ant=int(ant[m][0]), n=int(m.sum()))

    wanted = list(args.users)
    if args.auto_select:
        multi = {u: v for u, v in per_user.items() if v['n_ant'] > 1}
        single = {u: v for u, v in per_user.items() if v['n_ant'] == 1}
        if multi:
            wanted.append(min(multi, key=lambda u: multi[u]['raw']))
        if single:
            wanted.append(max(single, key=lambda u: single[u]['raw']))
    seen, order = set(), []
    for u in wanted:
        if u not in seen:
            seen.add(u)
            order.append(u)

    figures = []
    for u in order:
        if u not in per_user:
            log(f'  user {u} is not in the test split for seed {args.seed}, skipping')
            continue
        m = uid == u
        n_ant = per_user[u]['n_ant']
        # keep the report's existing filenames so its links stay valid
        label = 'BEST' if n_ant > 1 else 'WORST'
        fname = f'diagnostic_{label}_user_{u}_ant{n_ant}.png'
        rec = per_user_trajectory_figure(
            u, n_ant, true_m[m], pred_m[m], rts_d[m], rts_t[m],
            None if np.all(np.isnan(unc_all[m])) else unc_all[m],
            label, FIGURES_DIR / fname)
        figures.append(rec)
        log(f'  {fname}: raw {rec["raw_mae"]:.2f} | default {rec["rts_default_mae"]:.2f} '
            f'| tuned {rec["rts_tuned_mae"]:.2f} m')

    summary = {
        'meta': {'dataset': str(data_dir), 'h': args.history, 'seed': args.seed,
                 'epochs': args.epochs, 'model': '1D-CNN',
                 'default_filter': {'Q': DEFAULT_Q, 'R': DEFAULT_R},
                 'tuned_filter': {'Q': TUNED_Q, 'R': TUNED_R},
                 'note': 'regenerated after the delta_t fix (dee50dd)'},
        'population': {
            'raw_mae': round(raw_mae, 4),
            'rts_default_mae': round(mae(rts_d), 4),
            'rts_tuned_mae': round(mae(rts_t), 4),
            'kf_tuned_mae': round(mae(kf_t), 4),
            'rts_tuned_gain_pct': round(100 * (raw_mae - mae(rts_t)) / raw_mae, 3),
        },
        'figures': figures,
        'per_user': per_user,
    }
    out = out_dir / 'trajectory_diagnostics_summary.json'
    out.write_text(json.dumps(summary, indent=1), encoding='utf-8')
    log(f'saved -> {out}')
    log(f'figures written to {FIGURES_DIR}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
