"""
Naive baseline for the macro-cell study: ignore every measurement and always
predict the mean training position.

This is the error a model must beat to have learned anything from the
channel. It uses the same data preparation and the same unseen-user split as
seed_repeats_all_models.py and history_mechanism_diagnostic.py, so its numbers
sit beside theirs seed for seed. Two variants are reported:

    centroid        mean position of all training samples
    centroid_group  mean position of the training samples of the same device
                    group (multi- or single-antenna), which a model can also
                    learn because n_antennas is an input

Usage (from the repository root):
    E=experiments/09_grid_localization/src/python/experiments_ablation
    .venv/Scripts/python $E/naive_position_baseline.py --data-dir <dataset>
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from history_mechanism_followup import DEFAULT_SEEDS, shape_metrics, t_ci


def main():
    ap = argparse.ArgumentParser(
        description='Constant-position baseline for the macro-cell study.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python naive_position_baseline.py --data-dir results/grid_localization/grid_25x25/sim_data_300users_2026-07-25_11-46-11
""")
    ap.add_argument('--data-dir', required=True, help='dataset folder; no glob')
    ap.add_argument('--seeds', type=int, nargs='+', default=DEFAULT_SEEDS)
    ap.add_argument('--single-ant-ratio', type=float, default=0.15)
    args = ap.parse_args()

    import model_zoo as Z
    from model_zoo import PROJECT_ROOT, log
    from pipelines.multi_user_pipeline_regression import _read_bs_position_3d
    from pipelines.multi_user_200_pipeline import make_unseen_user_split
    from utils.csi_dataset import load_and_prepare_data

    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir
    if not data_dir.is_dir():
        raise SystemExit(f'dataset not found: {data_dir}')
    bs_pos = np.array(_read_bs_position_3d(data_dir))
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'naive_position_baseline_{data_dir.name}_{time.strftime("%Y-%m-%d_%H-%M-%S")}')
    out_dir.mkdir(parents=True, exist_ok=False)

    per_seed = []
    for seed in args.seeds:
        df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=seed,
                                         single_ant_ratio=args.single_ant_ratio)
        df, _, _ = make_unseen_user_split(df, Z.TRAIN_RATIO, seed)
        tr, te = df[df.split == 'train'], df[df.split == 'test']
        xy = lambda d: d[['target_x', 'target_y']].values.astype(float)
        true, ant_te, ant_tr = xy(te), te['n_antennas'].values, tr['n_antennas'].values
        rec = {'seed': seed}
        for g, m_te, m_tr in (('all', np.ones(len(te), bool), np.ones(len(tr), bool)),
                              ('multi', ant_te > 1, ant_tr > 1),
                              ('single', ant_te == 1, ant_tr == 1)):
            rec[g] = {'n_samples': int(m_te.sum()), 'n_users': int(te.loc[m_te, 'user_id'].nunique())}
            for name, centre in (('centroid', xy(tr).mean(axis=0)),
                                 ('centroid_group', xy(tr)[m_tr].mean(axis=0))):
                pred = np.tile(centre, (int(m_te.sum()), 1))
                err = np.linalg.norm(pred - true[m_te], axis=1)
                rec[g][name] = {'mae': float(err.mean()), 'p50': float(np.median(err)),
                                'p90': float(np.percentile(err, 90)),
                                **{k: v for k, v in shape_metrics(pred, true[m_te]).items()
                                   if k in ('radial_mae', 'tangential_mae')}}
        per_seed.append(rec)
        log(f'seed {seed}: centroid MAE all {rec["all"]["centroid"]["mae"]:.2f} | '
            f'multi {rec["multi"]["centroid"]["mae"]:.2f} | single {rec["single"]["centroid"]["mae"]:.2f} m')

    summary = {}
    for g in ('all', 'multi', 'single'):
        summary[g] = {}
        for name in ('centroid', 'centroid_group'):
            summary[g][name] = {}
            for k in ('mae', 'p50', 'p90', 'radial_mae', 'tangential_mae'):
                mean, half, _ = t_ci([r[g][name][k] for r in per_seed])
                summary[g][name][k] = {'mean': mean, 't95': half}
        s = summary[g]
        log(f'{g:<7} centroid {s["centroid"]["mae"]["mean"]:.2f} +/- {s["centroid"]["mae"]["t95"]:.2f} m | '
            f'own-group centroid {s["centroid_group"]["mae"]["mean"]:.2f} +/- {s["centroid_group"]["mae"]["t95"]:.2f} m')

    out = out_dir / 'naive_position_baseline_summary.json'
    out.write_text(json.dumps({'meta': {'dataset': data_dir.name, 'seeds': args.seeds,
                                        'single_ant_ratio': args.single_ant_ratio,
                                        'interval': 'Student-t 95% over seeds'},
                               'summary': summary, 'per_seed': per_seed}, indent=1), encoding='utf-8')
    log(f'saved -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
