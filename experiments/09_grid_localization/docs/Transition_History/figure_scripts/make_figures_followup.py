"""
Figures for the 2026-10-12 follow-up runs. Reads only the JSON files under
docs/results_of_record/followup_2026_10/ and writes PDFs into ../figures/.

    python figure_scripts/make_figures_followup.py            # from Transition_History/

Figures
    fig_angle_decomposition   which part of the angle history carries the gain
    fig_aoa_error_model       the gain under different AoA impairments
    fig_region_control        LOS-region vs NLOS-region gain, with and without real LOS
    fig_blocked_by_width      multi-antenna gain in the blocked stretch, by strip width
    fig_controlled_grid_placement  regenerated 15x15 grid, BS at centre vs beyond the corner
    fig_regression25_no_aoa   25x25 regression without AoA, three propagation sets, chronological and block-shuffled
    fig_controlled_grid_sets  controlled grid accuracy, three propagation sets, both BS positions
    fig_history_extended      history depth up to 15: trees, window-mean trees, CNN, GRU, GRU with the older reports shuffled (mixed set)
"""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
FIG = HERE.parent / 'figures'
REC = HERE.parents[1] / 'results_of_record' / 'followup_2026_10'

# categorical slots 1-3 of the validated default palette, plus neutrals
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
INK, MUTED, GRID = '#0b0b0b', '#52514e', '#d9d8d3'
MODELS = (('xgboost', 'XGBoost', BLUE), ('random_forest', 'Random Forest', ORANGE))
YLAB = 'Error reduction vs. $h=0$ (m)'

plt.rcParams.update({
    'font.size': 8, 'axes.titlesize': 8.5, 'axes.labelsize': 8, 'xtick.labelsize': 7.5,
    'ytick.labelsize': 7.5, 'legend.fontsize': 7.5, 'font.family': 'serif',
    'axes.edgecolor': MUTED, 'axes.labelcolor': INK, 'text.color': INK,
    'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.spines.top': False,
    'axes.spines.right': False, 'axes.linewidth': 0.6, 'pdf.fonttype': 42,
    'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.4, 'axes.axisbelow': True,
})


def load(rel):
    folder = REC / rel
    return json.loads(next(folder.glob('*.json')).read_text(encoding='utf-8'))


def gain(d, model, cond, group='multi', stratum='all'):
    g = d['summary'][model][cond][group]['gain_vs_snap'][stratum]
    return g['gain_mean_m'], g['gain_t95_m']


def save(fig, name):
    fig.savefig(FIG / f'{name}.pdf', bbox_inches='tight')
    plt.close(fig)
    print('wrote', FIG / f'{name}.pdf')


def bars(ax, x, vals, width, color, label=None):
    m = [v[0] for v in vals]
    e = [v[1] for v in vals]
    ax.bar(x, m, width, color=color, label=label, zorder=3, linewidth=0)
    ax.errorbar(x, m, yerr=e, fmt='none', ecolor=INK, elinewidth=0.7, capsize=1.8, capthick=0.7, zorder=4)


def angle_decomposition():
    d = load('uniform_nlos')
    conds = [('full', 'All\nchannels'), ('angle_hist', 'Angle\nhistory'), ('el_hist', 'Elevation\nonly'),
             ('az_hist', 'Azimuth\nonly'), ('angle_mean', 'Angle mean\n(no order)'),
             ('angle_shuffled', 'Angle history\nshuffled'), ('rss_hist', 'RSS\nhistory')]
    fig, ax = plt.subplots(figsize=(6.4, 2.7))
    x = np.arange(len(conds))
    for k, (m, name, col) in enumerate(MODELS):
        bars(ax, x + (k - 0.5) * 0.38, [gain(d, m, c) for c, _ in conds], 0.36, col, name)
    ax.set_xticks(x)
    ax.set_xticklabels([n for _, n in conds], fontsize=7)
    ax.axhline(0, color=MUTED, linewidth=0.6, zorder=3)
    ax.set_ylabel(YLAB)
    ax.set_ylim(-0.6, 4.6)
    ax.legend(frameon=False, loc='upper center', ncol=2)
    ax.grid(axis='x', visible=False)
    save(fig, 'fig_angle_decomposition')


def aoa_error_model():
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.6, 2.9), gridspec_kw={'width_ratios': [1.45, 1]})
    cases = [('aoa_impairment/corr_rho0', 'Report\n$4^\\circ$ + $5^\\circ$'),
             ('aoa_impairment/clean', 'Exact\nAoA'),
             ('aoa_impairment/quant5_only', '$5^\\circ$ steps\nonly'),
             ('aoa_impairment/noise4_only', '$4^\\circ$ noise\nonly'),
             ('aoa_impairment/noise8_quant5', '$8^\\circ$ + $5^\\circ$')]
    data = [load(p) for p, _ in cases]
    x = np.arange(len(cases))
    for k, (m, name, col) in enumerate(MODELS):
        bars(a, x + (k - 0.5) * 0.38, [gain(d, m, 'full') for d in data], 0.36, col, name)
    a.set_xticks(x)
    a.set_xticklabels([n for _, n in cases], fontsize=6.8)
    a.axhline(0, color=MUTED, linewidth=0.6, zorder=3)
    a.set_ylabel(YLAB)
    a.set_title('(a) Type of AoA error', loc='left')
    a.set_ylim(-1.4, 4.6)
    a.legend(frameon=False, loc='upper center', ncol=2)
    a.grid(axis='x', visible=False)

    rhos = [0, 0.5, 0.9, 0.99]
    runs = [load(f'aoa_impairment/corr_rho{r:g}') for r in rhos]
    xs = np.arange(len(rhos))
    for m, name, col in MODELS:
        v = [gain(d, m, 'full') for d in runs]
        b.errorbar(xs, [t[0] for t in v], yerr=[t[1] for t in v], color=col, linewidth=1.1, marker='o',
                   markersize=3.5, capsize=1.8, elinewidth=0.7, label=name, zorder=3)
    # neural models: mean of the four families at the report's setting (rho = 0) and at rho = 0.9
    neural = {0: ['neural_uniform_nlos/cnn-gru', 'neural_uniform_nlos/cnn_attn', 'neural_uniform_nlos/mask_aware_cnn'],
              2: ['neural_corr_rho0.9/cnn-gru', 'neural_corr_rho0.9/cnn_attn-mask_aware_cnn']}
    pts = {}
    for pos, rels in neural.items():
        vals = []
        for rel in rels:
            d = load(rel)
            vals += [d['summary'][m]['full']['multi']['gain_vs_snap']['gain_mean_m'] for m in d['meta']['models']]
        assert len(vals) == 4, rels
        pts[pos] = (np.mean(vals), min(vals), max(vals))
    b.vlines(list(pts), [p[1] for p in pts.values()], [p[2] for p in pts.values()], color=AQUA, linewidth=1.0, zorder=3)
    b.plot(list(pts), [p[0] for p in pts.values()], 's', color=AQUA, markersize=3.8, zorder=4,
           label='Neural models\n(mean and range of 4)')
    b.axhline(0, color=MUTED, linewidth=0.6, zorder=2)
    b.set_xticks(xs)
    b.set_xticklabels(['0', '0.5', '0.9', '0.99'])
    b.set_xlabel('Correlation of AoA error between\nsuccessive reports')
    b.set_ylabel(YLAB)
    b.set_title('(b) Persistence of the error', loc='left')
    b.set_ylim(-0.3, 4.6)
    b.legend(frameon=False, loc='upper right', fontsize=7)
    save(fig, 'fig_aoa_error_model')


def region_control():
    u, mx = load('uniform_nlos'), load('mixed_propagation')
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.5), sharey=True)
    for ax, (m, name, _) in zip(axes, MODELS):
        x = np.arange(2)
        for k, (d, lab, col) in enumerate(((u, 'Uniform NLOS (no LOS exists)', MUTED),
                                           (mx, 'Mixed LOS/NLOS', BLUE))):
            vals = [gain(d, m, 'full', stratum=s) for s in ('geo_LOS', 'geo_NLOS')]
            bars(ax, x + (k - 0.5) * 0.38, vals, 0.36, col, lab if m == 'xgboost' else None)
        ax.set_xticks(x)
        ax.set_xticklabels(['LOS regions\n(Highway, Park)', 'NLOS regions\n(Shopping, Resid.)'], fontsize=7)
        ax.set_ylim(0, 4.6)
        ax.set_title(name, loc='left')
        ax.grid(axis='x', visible=False)
    axes[0].set_ylabel(YLAB)
    axes[0].legend(frameon=False, loc='upper right', fontsize=7)
    save(fig, 'fig_region_control')


def blocked_by_width():
    d = load('blocked_los')
    widths = [5, 10, 20, 40, 80, 100, 120, 150]
    fig, ax = plt.subplots(figsize=(5.2, 2.6))
    for m, name, col in MODELS:
        v = [gain(d, m, 'full', stratum=f'blocked_w{w}') for w in widths]
        ax.errorbar(range(len(widths)), [t[0] for t in v], yerr=[t[1] for t in v], color=col, linewidth=1.1,
                    marker='o', markersize=3.5, capsize=1.8, elinewidth=0.7, label=f'{name}, blocked stretch', zorder=3)
        mu, hw = gain(d, m, 'full', stratum='unblocked')
        ax.axhspan(mu - hw, mu + hw, color=col, alpha=0.13, linewidth=0, zorder=1)
        ax.axhline(mu, color=col, linewidth=0.7, linestyle=(0, (4, 2)), zorder=2)
    ax.text(-0.3, 1.6, 'Dashed line and band: mean and 95% interval\noutside the blocked stretch', ha='left', va='top',
            fontsize=7, color=MUTED)
    ax.set_xticks(range(len(widths)))
    ax.set_xticklabels(widths)
    ax.set_xlabel('Width of the blocked strip (m)')
    ax.set_ylabel(YLAB)
    ax.set_ylim(0, 8.6)
    ax.legend(frameon=False, loc='lower right', ncol=1, fontsize=7)
    ax.grid(axis='x', visible=False)
    save(fig, 'fig_blocked_by_width')


def controlled_grid_placement():
    rec = HERE.parents[1] / 'results_of_record' / 'controlled_grid_2026_10'
    exps = ['BASE', 'BASE_H3', 'BASE_A', 'BASE_A_H3']
    labs = ['RSS+SINR\n$h=0$', 'RSS+SINR\n$h=3$', '+AoA\n$h=0$', '+AoA\n$h=3$']
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.5), sharey=True)
    for ax, (folder, title) in zip(axes, (('centre_bs', 'BS at the grid center'), ('ne_bs', 'BS beyond the corner'))):
        rows = list(csv.DictReader(open(rec / folder / 'results_summary.csv', encoding='utf-8')))
        acc = {(r['model'], r['experiment']): float(r['accuracy_%']) for r in rows}
        x = np.arange(len(exps))
        for k, (m, name, col) in enumerate((('xgboost', 'XGBoost', BLUE), ('rf', 'Random Forest', ORANGE))):
            v = [acc[(m, e)] for e in exps]
            ax.bar(x + (k - 0.5) * 0.38, v, 0.36, color=col, label=name if folder == 'centre_bs' else None)
        ax.set_xticks(x)
        ax.set_xticklabels(labs, fontsize=7)
        ax.set_ylim(0, 80)
        ax.set_title(title, loc='left')
        ax.grid(axis='x', visible=False)
    axes[0].set_ylabel('Exact-cell accuracy (%)')
    axes[0].legend(frameon=False, loc='upper left', fontsize=7)
    save(fig, 'fig_controlled_grid_placement')


def regression25_no_aoa():
    rec = HERE.parents[1] / 'results_of_record' / 'regression_25x25_2026_10'
    sets = (('UMi LOS', 'umilos_30_fixednoise'), ('NLOS', 'nlos_30_fixednoise'), ('Mixed', 'mixed_30_fixednoise'))

    def mae(folder, run, model, exp):
        rows = list(csv.DictReader(open(rec / folder / run / 'results_summary.csv', encoding='utf-8')))
        return next(float(r['3d_mae_m']) for r in rows if r['model'] == model and r['experiment'] == exp)

    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.6), sharey=True)
    series = (('xgboost', 'BASE', 'XGBoost, h=0', BLUE, 0.45), ('xgboost', 'BASE_H3', 'XGBoost, h=3', BLUE, 1.0),
              ('rf', 'BASE', 'Random Forest, h=0', ORANGE, 0.45), ('rf', 'BASE_H3', 'Random Forest, h=3', ORANGE, 1.0))
    for ax, (run, title) in zip(axes, (('tuned', 'Chronological split'), ('segment_shuffle', 'Shuffled 5-step blocks'))):
        x = np.arange(len(sets))
        for k, (model, exp, label, col, alpha) in enumerate(series):
            v = [mae(folder, run, model, exp) for _, folder in sets]
            ax.bar(x + (k - 1.5) * 0.2, v, 0.19, color=col, alpha=alpha, label=label if run == 'tuned' else None)
        ax.set_xticks(x)
        ax.set_xticklabels([n for n, _ in sets], fontsize=7.5)
        ax.set_title(title, loc='left')
        ax.grid(axis='x', visible=False)
    axes[0].set_ylabel('3D position error (m)')
    axes[0].legend(frameon=False, fontsize=6.5, loc='upper left', ncol=1)
    save(fig, 'fig_regression25_no_aoa')


def controlled_grid_sets():
    rec = HERE.parents[1] / 'results_of_record' / 'controlled_grid_2026_10' / 'comparison_sets.csv'
    rows = list(csv.DictReader(open(rec, encoding='utf-8')))
    sets = (('RMa LOS', 'RMa LOS 3.0 GHz', MUTED), ('Mixed per-cell', 'Mixed per-cell 3.0 GHz', BLUE), ('Uniform NLOS', 'NLOS 3.0 GHz', ORANGE))
    exps = ['BASE', 'BASE_H3', 'BASE_A', 'BASE_A_H3']
    labs = ['$h=0$', '$h=3$', 'AoA\n$h=0$', 'AoA\n$h=3$']
    fig, axes = plt.subplots(2, 2, figsize=(6.6, 4.6), sharey=True, sharex=True)
    for r, (model, mname) in enumerate((('xgboost', 'XGBoost'), ('rf', 'Random Forest'))):
        for c, (pl, pname) in enumerate((('centre', 'BS at the grid center'), ('NE', 'BS beyond the corner'))):
            ax = axes[r, c]
            x = np.arange(len(exps))
            for k, (sname, skey, col) in enumerate(sets):
                row = next(q for q in rows if q['set'] == skey and q['placement'] == pl and q['model'] == model)
                ax.bar(x + (k - 1) * 0.27, [float(row[f'{e}_acc']) for e in exps], 0.25, color=col,
                       label=sname if (r == 0 and c == 0) else None)
            ax.set_xticks(x)
            ax.set_xticklabels(labs, fontsize=7)
            ax.set_title(f'{mname}, {pname}', loc='left', fontsize=8)
            ax.set_ylim(0, 85)
            ax.grid(axis='x', visible=False)
    for ax in axes[:, 0]:
        ax.set_ylabel('Exact-cell accuracy (%)')
    axes[0, 0].legend(frameon=False, fontsize=7, loc='upper left')
    fig.text(0.5, -0.01, 'First two groups of bars: RSS and SINR; last two: AoA added', ha='center', fontsize=7, color=MUTED)
    save(fig, 'fig_controlled_grid_sets')


def history_extended_fig():
    rec = HERE.parents[1] / 'results_of_record' / 'history_extended'

    def load(t):
        parts = [rec / t / 'history_extended.csv', rec / f'{t}_wmgru' / 'history_extended_wmgru.csv', rec / f'{t}_shufold' / 'history_extended.csv']
        rows = []
        for p in parts:
            rows += list(csv.DictReader(open(p, encoding='utf-8')))
        return rows

    def curve(rows, exp, model):
        acc = {}
        for r in rows:
            if r['experiment'] == exp and r['model'] == model:
                acc.setdefault(int(r['h']), []).append(float(r['mae']))
        hs = sorted(acc)
        return hs, [float(np.mean(acc[h])) for h in hs]

    sty = (('xgboost', 'XGBoost', BLUE, '-'), ('rf', 'Random Forest', ORANGE, '-'), ('cnn', '1D-CNN', AQUA, '-'), ('gru', 'GRU', INK, '-'),
           ('rf_wm', 'RF, window mean only', ORANGE, (0, (3, 2))), ('gru_shufold', 'GRU, older reports shuffled', INK, (0, (1, 2))))
    fig, axes = plt.subplots(2, 2, figsize=(6.8, 4.8), sharex=True)
    for r, (exp, ename) in enumerate((('BASE', 'RSS+SINR'), ('BASE_A', 'RSS+SINR+AoA'))):
        for c, (t, tname) in enumerate((('ne_mixed', 'BS beyond the corner'), ('centre_mixed', 'BS at the grid center'))):
            ax = axes[r, c]
            rows = load(t)
            for m, lab, col, ls in sty:
                hs, v = curve(rows, exp, m)
                ax.plot(hs, v, ls=ls, color=col, marker='o', markersize=2.5, linewidth=1.1, label=lab if (r == 0 and c == 0) else None)
            ax.set_title(f'{ename}, {tname}', loc='left', fontsize=8)
            ax.set_xticks([0, 1, 3, 5, 7, 10, 15])
    for ax in axes[:, 0]:
        ax.set_ylabel('Mean position error (m)')
    for ax in axes[1]:
        ax.set_xlabel('History depth $h$')
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=3, frameon=False, fontsize=7, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, 'fig_history_extended')


if __name__ == '__main__':
    FIG.mkdir(exist_ok=True)
    angle_decomposition()
    aoa_error_model()
    region_control()
    blocked_by_width()
    controlled_grid_placement()
    regression25_no_aoa()
    controlled_grid_sets()
    history_extended_fig()
