"""
Where do the 20-30 m errors of the macro-cell study come from?

Reads the per-sample errors saved by history_mechanism_diagnostic.py
(errors_first_seed.npz: true and predicted positions, error, range from the BS, antenna
count, user) and produces, per model and device group:
  * the fraction of samples within 5, 10, 20 and 40 m, the mean and the median error,
    next to the error of always guessing the mean training position;
  * a map of the mean error by true position, snapshot against full window;
  * mean error by range from the serving BS.

Nothing is re-trained. Usage (from the repository root):
    .venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/error_maps_macro.py \
        --npz experiments/09_grid_localization/docs/results_of_record/diagnostics_2026_10/baseline_uniform_nlos/errors_first_seed.npz \
        --out-dir results/error_audit/macro_uniform_nlos
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

GROUPS = (('multi', lambda a: a > 1, 'multi-antenna'), ('single', lambda a: a <= 1, 'single-antenna'))
CELL_M = 4.0
RANGE_EDGES = [0, 25, 50, 75, 100, 125, 150, 200]


def stats(err, guess_err):
    return {
        'n': int(len(err)), 'mean_m': float(err.mean()), 'median_m': float(np.median(err)),
        'p90_m': float(np.percentile(err, 90)),
        'within_5m': float((err <= 5).mean()), 'within_10m': float((err <= 10).mean()),
        'within_20m': float((err <= 20).mean()), 'within_40m': float((err <= 40).mean()),
        'constant_guess_mean_m': float(guess_err.mean()),
    }


def position_map(ax, xy, err, bs, vmax):
    bins = np.arange(np.floor(xy.min() / CELL_M / 4) * CELL_M * 4, xy.max() + CELL_M * 4, CELL_M * 4)
    s, xe, ye = np.histogram2d(xy[:, 0], xy[:, 1], bins=[bins, bins], weights=err)
    n, _, _ = np.histogram2d(xy[:, 0], xy[:, 1], bins=[bins, bins])
    m = np.where(n >= 5, s / np.maximum(n, 1), np.nan)
    im = ax.pcolormesh(xe, ye, m.T, cmap='viridis', vmin=0, vmax=vmax, shading='flat')
    ax.plot(0, 0, marker='*', color='white', markeredgecolor='black', markersize=12, linestyle='none')
    ax.set_xlim(xe[0] - 5, 15)
    ax.set_ylim(ye[0] - 5, 15)
    ax.set_aspect('equal')
    return im


def main():
    ap = argparse.ArgumentParser(
        description='Error distribution and error maps for the macro-cell study.',
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('Usage')[1])
    ap.add_argument('--npz', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--models', nargs='+', default=['xgboost', 'random_forest'])
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    z = np.load(args.npz)
    true_xy, bs = z['true_xy'], np.zeros(2)
    # true_xy is stored relative to the serving BS: range_m equals the distance to the origin exactly
    assert np.allclose(np.hypot(*true_xy.T), z['range_m'], atol=1e-3), 'true_xy is not BS-relative'
    ant, rng_m = z['n_antennas'], z['range_m']
    result = {}
    for gname, sel, glabel in GROUPS:
        g = sel(ant)
        guess = np.linalg.norm(true_xy[g] - true_xy[g].mean(0), axis=1)
        for model in args.models:
            for cond in ('snap', 'full'):
                result[f'{model}/{cond}/{gname}'] = stats(z[f'{model}__{cond}__err'][g], guess)
    (out / 'error_distribution.json').write_text(json.dumps(result, indent=2))

    print(f'{"model/cond/group":<28}{"mean":>7}{"median":>8}{"<=5m":>7}{"<=10m":>7}{"<=20m":>7}{"<=40m":>7}{"guess":>8}')
    for k, v in result.items():
        print(f'{k:<28}{v["mean_m"]:7.1f}{v["median_m"]:8.1f}{100*v["within_5m"]:6.0f}%{100*v["within_10m"]:6.0f}%'
              f'{100*v["within_20m"]:6.0f}%{100*v["within_40m"]:6.0f}%{v["constant_guess_mean_m"]:8.1f}')

    # maps: one row per group, columns snapshot / full window, first model
    model = args.models[0]
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.6), sharex=True, sharey=True)
    vmax = 60.0
    for r, (gname, sel, glabel) in enumerate(GROUPS):
        g = sel(ant)
        for c, (cond, clabel) in enumerate((('snap', 'no history'), ('full', 'with history'))):
            im = position_map(axes[r, c], true_xy[g], z[f'{model}__{cond}__err'][g], bs, vmax)
            axes[r, c].set_title(f'{glabel}, {clabel}\nmean {z[f"{model}__{cond}__err"][g].mean():.1f} m', fontsize=9)
    fig.colorbar(im, ax=axes, label='mean position error (m)', shrink=0.8)
    for a in axes[-1]:
        a.set_xlabel('x (m)')
    for a in axes[:, 0]:
        a.set_ylabel('y (m)')
    fig.savefig(out / f'error_map_{model}.png', dpi=160, bbox_inches='tight')
    plt.close(fig)

    # error against range
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), sharey=True)
    mid = 0.5 * (np.array(RANGE_EDGES[:-1]) + np.array(RANGE_EDGES[1:]))
    for ax, (gname, sel, glabel) in zip(axes, GROUPS):
        g = sel(ant)
        for cond, ls in (('snap', '--'), ('full', '-')):
            e = z[f'{model}__{cond}__err'][g]
            ms = [e[(rng_m[g] >= a) & (rng_m[g] < b)].mean() if ((rng_m[g] >= a) & (rng_m[g] < b)).any() else np.nan
                  for a, b in zip(RANGE_EDGES[:-1], RANGE_EDGES[1:])]
            ax.plot(mid, ms, ls, marker='o', markersize=3, label='no history' if cond == 'snap' else 'with history')
        ax.set_title(glabel, fontsize=9)
        ax.set_xlabel('range from serving BS (m)')
        ax.grid(alpha=0.3)
    axes[0].set_ylabel('mean position error (m)')
    axes[0].legend(frameon=False)
    fig.savefig(out / f'error_by_range_{model}.png', dpi=160, bbox_inches='tight')
    plt.close(fig)

    # error histogram
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), sharey=True)
    for ax, (gname, sel, glabel) in zip(axes, GROUPS):
        g = sel(ant)
        for cond, col in (('snap', '#999999'), ('full', '#2a78d6')):
            ax.hist(z[f'{model}__{cond}__err'][g], bins=np.arange(0, 121, 4), alpha=0.65, color=col, density=True,
                    label='no history' if cond == 'snap' else 'with history')
        ax.set_title(glabel, fontsize=9)
        ax.set_xlabel('position error (m)')
    axes[0].set_ylabel('density')
    axes[0].legend(frameon=False)
    fig.savefig(out / f'error_histogram_{model}.png', dpi=160, bbox_inches='tight')
    plt.close(fig)
    print('wrote', out)


if __name__ == '__main__':
    main()
