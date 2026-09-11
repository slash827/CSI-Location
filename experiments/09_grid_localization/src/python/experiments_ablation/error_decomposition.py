"""
Decompose Campaign B positioning error into range (radial) and bearing
(tangential) components relative to the serving base station.

This is the diagnostic that separates the two hardware cohorts: whether a model's
residual error lies along the BS bearing (a range-estimation failure) or
perpendicular to it (the distance-ring ambiguity). Targets are already expressed
as offsets from the serving BS, so the BS sits at the origin and the unit vector
to the true position gives the radial direction directly.

Usage:
    python error_decomposition.py
    python error_decomposition.py --history 10
"""
import argparse
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'src' / 'python'))

from pipelines.multi_user_pipeline_regression import _read_bs_position_3d
from pipelines.multi_user_200_pipeline import make_unseen_user_split
from utils.csi_dataset import DerivedCSI1DDataset, load_and_prepare_data
from xgboost import XGBRegressor


def flatten(ds):
    X = np.array([np.concatenate([s['seq'].ravel(), s['static'].ravel()])
                  for s in ds.samples], dtype=np.float32)
    Y = np.array([s['target'] for s in ds.samples], dtype=np.float32)
    ant = np.array([s['n_antennas'] for s in ds.samples])
    return X, Y, ant


def main():
    ap = argparse.ArgumentParser(
        description='Split Campaign B error into radial (range) and tangential (bearing) parts.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python error_decomposition.py
  python error_decomposition.py --history 10 --seed 7
""")
    ap.add_argument('--history', type=int, default=5)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--single-ant-ratio', type=float, default=0.15)
    args = ap.parse_args()

    data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
    data_dir = sorted(data_base.glob('sim_data_300users_*'))[-1]
    bs_pos = np.array(_read_bs_position_3d(data_dir))

    df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=args.seed,
                                     single_ant_ratio=args.single_ant_ratio)
    df, _, _ = make_unseen_user_split(df, 0.8, args.seed)

    tr = DerivedCSI1DDataset(df[df.split == 'train'], h=args.history)
    te = DerivedCSI1DDataset(df[df.split == 'test'], h=args.history,
                             sig_mean=tr.sig_mean, sig_std=tr.sig_std,
                             stat_mean=tr.stat_mean, stat_std=tr.stat_std,
                             targ_mean=tr.targ_mean, targ_std=tr.targ_std,
                             speed_mean=tr.speed_mean, speed_std=tr.speed_std)

    X_tr, Y_tr, _ = flatten(tr)
    X_te, Y_te, ant = flatten(te)

    model = XGBRegressor(n_estimators=50, max_depth=5, learning_rate=0.15,
                         subsample=0.8, colsample_bytree=0.8, random_state=args.seed,
                         n_jobs=-1, tree_method='hist',
                         multi_strategy='one_output_per_tree')
    model.fit(X_tr, Y_tr)

    pred = model.predict(X_te) * tr.targ_std + tr.targ_mean
    true = Y_te * tr.targ_std + tr.targ_mean

    # targets are offsets from the serving BS, so the BS is the origin
    rng = np.linalg.norm(true, axis=1)
    unit = true / rng[:, None]
    delta = pred - true
    radial = np.abs((delta * unit).sum(axis=1))
    tangential = np.abs(delta[:, 0] * unit[:, 1] - delta[:, 1] * unit[:, 0])
    total = np.linalg.norm(delta, axis=1)

    print(f'dataset: {data_dir.name} | h={args.history} | seed={args.seed}')
    print(f'range to serving BS: p10 {np.percentile(rng, 10):.1f} m, '
          f'median {np.percentile(rng, 50):.1f} m, p90 {np.percentile(rng, 90):.1f} m')
    print()
    header = f'{"cohort":<12}{"total":>9}{"radial":>10}{"tangential":>12}{"radial share":>14}'
    print(header)
    print('-' * len(header))
    for label, mask in (('all', np.ones(len(total), bool)),
                        ('multi-ant', ant > 1),
                        ('single-ant', ant == 1)):
        r, t = radial[mask].mean(), tangential[mask].mean()
        share = 100 * r ** 2 / (r ** 2 + t ** 2)
        print(f'{label:<12}{total[mask].mean():>8.2f}m{r:>9.2f}m{t:>11.2f}m{share:>13.0f}%')

    print()
    print('geometric prediction, cross-range = R * tan(theta), at mean range '
          f'{rng.mean():.1f} m:')
    for label, theta in (('multi-ant, 3.5 deg measured', 3.5),
                         ('single-ant, 15.8 deg measured', 15.8)):
        print(f'  {label:<32}{rng.mean() * np.tan(np.radians(theta)):>8.2f} m')


if __name__ == '__main__':
    sys.exit(main())
