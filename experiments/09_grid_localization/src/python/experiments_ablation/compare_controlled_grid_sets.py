"""
One table across the controlled-grid data sets (propagation sweep) from their results_summary.csv.

For every set, placement and model: accuracy and MAE of BASE, BASE_H3, BASE_A, BASE_A_H3,
the history gain (BASE -> BASE_H3, BASE_A -> BASE_A_H3, in pp and metres) and the AoA gain
(BASE_H3 -> BASE_A_H3). Writes a CSV and a Markdown table.

Usage (from the repository root):
    .venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/compare_controlled_grid_sets.py \
        --out-dir results/controlled_grid_2026_10
"""
import argparse
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
SETS = [  # label, folder suffix
    ('RMa LOS 3.0 GHz', 'rmalos_30'),
    ('Mixed per-cell 3.0 GHz', 'mixed_30'),
    ('NLOS 3.0 GHz', 'nlos_30'),
    ('NLOS 3.5 GHz', 'nlos35'),
]
EXPS = ['BASE', 'BASE_H3', 'BASE_A', 'BASE_A_H3']
MODELS = ['xgboost', 'rf']


def load(path):
    if not path.exists():
        return None
    with open(path, newline='', encoding='utf-8') as f:
        return {(r['model'], r['experiment']): (float(r['accuracy_%']), float(r['mae_m'])) for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser(
        description='Compare the controlled-grid propagation sets.',
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('Usage')[1])
    ap.add_argument('--out-dir', default=str(PROJECT_ROOT / 'results' / 'controlled_grid_2026_10'))
    args = ap.parse_args()
    root = Path(args.out_dir)
    rows = []
    for label, suffix in SETS:
        for placement, folder in (('centre', 'centre_bs'), ('NE', 'ne_bs')):
            d = load(root / f'{folder}_{suffix}' / 'csvs' / 'results_summary.csv')
            if d is None:
                continue
            for m in MODELS:
                if any((m, e) not in d for e in EXPS):
                    continue
                r = {'set': label, 'placement': placement, 'model': m}
                for e in EXPS:
                    r[f'{e}_acc'], r[f'{e}_mae'] = d[(m, e)]
                r['hist_gain_pp'] = r['BASE_H3_acc'] - r['BASE_acc']
                r['hist_gain_m'] = r['BASE_mae'] - r['BASE_H3_mae']
                r['hist_gain_aoa_pp'] = r['BASE_A_H3_acc'] - r['BASE_A_acc']
                r['hist_gain_aoa_m'] = r['BASE_A_mae'] - r['BASE_A_H3_mae']
                r['aoa_gain_pp'] = r['BASE_A_H3_acc'] - r['BASE_H3_acc']
                rows.append(r)
    if not rows:
        raise SystemExit(f'No result folders found under {root}')
    cols = list(rows[0].keys())
    with open(root / 'comparison_sets.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()} for r in rows)
    lines = ['| Set | BS | Model | BASE | BASE_H3 | BASE_A | BASE_A_H3 | history gain (no AoA) | history gain (AoA) | AoA gain (H3) |',
             '|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        cells = [f"{r[f'{e}_acc']:.1f}% / {r[f'{e}_mae']:.2f} m" for e in EXPS]
        lines.append(f"| {r['set']} | {r['placement']} | {r['model']} | " + ' | '.join(cells)
                     + f" | {r['hist_gain_pp']:+.1f} pp, {r['hist_gain_m']:+.2f} m | {r['hist_gain_aoa_pp']:+.1f} pp, {r['hist_gain_aoa_m']:+.2f} m"
                     f" | {r['aoa_gain_pp']:+.1f} pp |")
    (root / 'comparison_sets.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
