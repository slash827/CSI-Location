"""
Error distribution and error maps for the 25x25 regression runs (five pooled device profiles, NE BS).

Reads the per-sample test predictions written by multi_user_pipeline_regression.py --save-predictions
(<run>/predictions/<experiment>__<model>.npz: true and predicted positions, error, user, Voronoi cell) and produces
  * error_distribution.json / .md: mean, median, 90th percentile and the fraction of samples within 5, 10, 20 and 40 m
    per experiment and device profile, next to the error of always guessing the mean test position;
  * error_map_<model>.png: mean error by true position, one panel per experiment;
  * error_by_range_<model>.png: mean error against the distance from the BS;
  * error_histogram_<model>.png: distribution of the position error.

Nothing is re-trained. Usage (from the repository root):
    .venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/error_maps_regression25.py \
        --pred-dir results/regression_25x25_2026_10/mixed_30_maps/predictions \
        --out-dir results/error_audit/regression25_mixed --model xgboost
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

EXPERIMENTS = (('BASE', 'RSS+SINR, no history'), ('BASE_H3', 'RSS+SINR, h=3'),
               ('BASE_A', 'with AoA, no history'), ('BASE_A_H3', 'with AoA, h=3'))
BIN_M = 8.0
RANGE_EDGES = [0, 20, 40, 60, 80, 100, 120, 160]


def stats(err, guess_err):
    return {
        'n': int(len(err)), 'mean_m': float(err.mean()), 'median_m': float(np.median(err)),
        'p90_m': float(np.percentile(err, 90)),
        'within_5m': float((err <= 5).mean()), 'within_10m': float((err <= 10).mean()),
        'within_20m': float((err <= 20).mean()), 'within_40m': float((err <= 40).mean()),
        'constant_guess_mean_m': float(guess_err.mean()),
    }


def position_map(ax, xy, err, vmax):
    lo, hi = np.floor(xy.min() / BIN_M) * BIN_M, xy.max() + BIN_M
    bins = np.arange(lo, hi + BIN_M, BIN_M)
    s, xe, ye = np.histogram2d(xy[:, 0], xy[:, 1], bins=[bins, bins], weights=err)
    n, _, _ = np.histogram2d(xy[:, 0], xy[:, 1], bins=[bins, bins])
    m = np.where(n >= 5, s / np.maximum(n, 1), np.nan)
    im = ax.pcolormesh(xe, ye, m.T, cmap='viridis', vmin=0, vmax=vmax, shading='flat')
    ax.set_aspect('equal')
    return im


def main():
    ap = argparse.ArgumentParser(
        description='Error distribution and error maps for the 25x25 regression runs.',
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('Usage')[1])
    ap.add_argument('--pred-dir', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--model', default='xgboost')
    args = ap.parse_args()
    pred_dir, out = Path(args.pred_dir), Path(args.out_dir)
    if not pred_dir.exists():
        raise FileNotFoundError(f'Predictions not found: {pred_dir}')
    out.mkdir(parents=True, exist_ok=True)

    data = {}
    for key, _ in EXPERIMENTS:
        f = pred_dir / f'{key}__{args.model}.npz'
        if not f.exists():
            raise FileNotFoundError(f'Missing prediction file: {f}')
        data[key] = np.load(f)
    bs = data['BASE']['bs_pos']
    users = sorted(set(int(u) for u in data['BASE']['user_id']))

    result, lines = {}, []
    lines.append('| experiment | profile | n | mean (m) | median (m) | p90 (m) | <=5 m | <=10 m | <=20 m | <=40 m | guess (m) |')
    lines.append('|---|---|---|---|---|---|---|---|---|---|---|')
    for key, _ in EXPERIMENTS:
        z = data[key]
        for label, sel in [('all', np.ones(len(z['error_m']), bool))] + [(f'user {u}', z['user_id'] == u) for u in users]:
            xy = z['true_xyz'][sel][:, :2]
            guess = np.linalg.norm(xy - xy.mean(0), axis=1)
            s = stats(z['error_m'][sel], guess)
            result[f'{key}/{label}'] = s
            lines.append(f'| {key} | {label} | {s["n"]} | {s["mean_m"]:.1f} | {s["median_m"]:.1f} | {s["p90_m"]:.1f} | '
                         f'{100*s["within_5m"]:.0f}% | {100*s["within_10m"]:.0f}% | {100*s["within_20m"]:.0f}% | '
                         f'{100*s["within_40m"]:.0f}% | {s["constant_guess_mean_m"]:.1f} |')
    (out / 'error_distribution.json').write_text(json.dumps(result, indent=2))
    (out / 'error_distribution.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))

    vmax = float(np.percentile(np.concatenate([data[k]['error_m'] for k, _ in EXPERIMENTS]), 90))
    fig, axes = plt.subplots(1, 4, figsize=(11.5, 3.4), sharex=True, sharey=True)
    for ax, (key, label) in zip(axes, EXPERIMENTS):
        z = data[key]
        im = position_map(ax, z['true_xyz'][:, :2], z['error_m'], vmax)
        ax.plot(bs[0], bs[1], marker='*', color='white', markeredgecolor='black', markersize=11, linestyle='none')
        ax.set_title(f'{label}\nmean {z["error_m"].mean():.1f} m', fontsize=8.5)
        ax.set_xlabel('x (m)')
    axes[0].set_ylabel('y (m)')
    fig.colorbar(im, ax=axes, label='mean position error (m)', shrink=0.85)
    fig.savefig(out / f'error_map_{args.model}.png', dpi=160, bbox_inches='tight')
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    mid = 0.5 * (np.array(RANGE_EDGES[:-1]) + np.array(RANGE_EDGES[1:]))
    for (key, label), ls in zip(EXPERIMENTS, ('--', '-', '--', '-')):
        z = data[key]
        rng = np.linalg.norm(z['true_xyz'][:, :2] - bs[:2], axis=1)
        ms = [z['error_m'][(rng >= a) & (rng < b)].mean() if ((rng >= a) & (rng < b)).any() else np.nan
              for a, b in zip(RANGE_EDGES[:-1], RANGE_EDGES[1:])]
        ax.plot(mid, ms, ls, marker='o', markersize=3, label=label)
    ax.set_xlabel('distance from the BS (m)')
    ax.set_ylabel('mean position error (m)')
    ax.grid(alpha=0.3)
    ax.legend(frameon=False, fontsize=7.5)
    fig.savefig(out / f'error_by_range_{args.model}.png', dpi=160, bbox_inches='tight')
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    hi = float(np.percentile(data['BASE']['error_m'], 99))
    for (key, label), col in zip(EXPERIMENTS, ('#999999', '#2a78d6', '#d9822b', '#1f9d55')):
        ax.hist(data[key]['error_m'], bins=np.linspace(0, hi, 40), histtype='step', density=True, color=col, label=label)
    ax.set_xlabel('position error (m)')
    ax.set_ylabel('density')
    ax.legend(frameon=False, fontsize=7.5)
    fig.savefig(out / f'error_histogram_{args.model}.png', dpi=160, bbox_inches='tight')
    plt.close(fig)
    print('wrote', out)


if __name__ == '__main__':
    main()
