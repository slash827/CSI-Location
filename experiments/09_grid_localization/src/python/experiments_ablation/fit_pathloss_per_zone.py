"""
A3: Fit the path-loss exponent and shadow-fading spread per Voronoi zone.

The range-resolution argument in report section 7.5 uses textbook constants
(gamma = 4, sigma = 6 dB) to derive a 1-sigma range uncertainty of 32.9 m at the
macro campaign's median range. That bound is load-bearing: it supports the claim
that the measured multi-antenna radial error of 13.69 m is *better* than naive
path-loss ranging, and therefore that history, SINR and elevation contribute real
range information. Resting it on assumed constants is a weakness.

This fits both from the data.

Model, per zone:

    rss ~ b0 + b1 * 10*log10(r) + b2 * antenna_gain_db + b3 * log2(n_antennas)

so that -b1 estimates gamma. The device terms are controls, not nuisance: RSS
carries a per-device antenna gain offset (-3.97 to +1.99 dB here) and rises with
antenna count through maximum-ratio combining, and leaving either uncontrolled
would inflate the residual and bias the exponent. The residual standard deviation
estimates the combined shadow-fading and small-scale spread.

Usage:
    python fit_pathloss_per_zone.py
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'src' / 'python'))

from pipelines.multi_user_pipeline_regression import _read_bs_position_3d
from utils.csi_dataset import load_and_prepare_data

VORONOI = [
    {"center": [35.0, 15.0], "scenario": "LOS",  "name": "Highway"},
    {"center": [95.0, 15.0], "scenario": "NLOS", "name": "Shopping"},
    {"center": [75.0,  5.0], "scenario": "NLOS", "name": "Residential"},
    {"center": [60.0, 90.0], "scenario": "LOS",  "name": "Park"},
]


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def assign_zone(x, y):
    c = np.array([z['center'] for z in VORONOI])
    d = np.sqrt((x[:, None] - c[None, :, 0]) ** 2 + (y[:, None] - c[None, :, 1]) ** 2)
    return np.argmin(d, axis=1)


def fit(rss, r, gain, n_ant):
    """OLS of rss on 10log10(r) with device controls. Returns gamma, sigma, R^2, n."""
    ok = (r > 1.0) & np.isfinite(rss)
    rss, r, gain, n_ant = rss[ok], r[ok], gain[ok], n_ant[ok]
    X = np.column_stack([np.ones_like(r), 10.0 * np.log10(r), gain, np.log2(n_ant)])
    beta, *_ = np.linalg.lstsq(X, rss, rcond=None)
    resid = rss - X @ beta
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((rss - rss.mean()) ** 2))
    return {
        'gamma': float(-beta[1]),
        'sigma_db': float(resid.std(ddof=X.shape[1])),
        'r2': float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float('nan'),
        'n': int(len(rss)),
        'mean_range_m': float(r.mean()),
        'gain_coef': float(beta[2]),
        'n_ant_coef': float(beta[3]),
    }


def sigma_range(gamma, sigma_db, r):
    """1-sigma range uncertainty implied by fitted constants at range r."""
    sens = 10.0 * gamma / (r * np.log(10.0))     # dB per metre
    return sens, sigma_db / sens


def main():
    ap = argparse.ArgumentParser(
        description='Fit path-loss exponent and shadow fading per Voronoi zone (A3).')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--single-ant-ratio', type=float, default=0.15)
    args = ap.parse_args()

    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'pathloss_fit_{run_ts}')
    out_dir.mkdir(parents=True, exist_ok=True)

    log('loading...')
    data_base = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_25x25'
    data_dir = sorted(data_base.glob('sim_data_300users_*'))[-1]
    bs_pos = np.array(_read_bs_position_3d(data_dir))
    df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=args.seed,
                                     single_ant_ratio=args.single_ant_ratio)

    r = np.sqrt((df.x_pos - bs_pos[0]) ** 2 + (df.y_pos - bs_pos[1]) ** 2).values
    zone = assign_zone(df.x_pos.values, df.y_pos.values)
    rss = df.rss.values.astype(float)
    gain = df.antenna_gain_db.values.astype(float)
    n_ant = df.n_antennas.values.astype(float)

    results = {'meta': {'dataset': str(data_dir), 'n_rows': int(len(df)),
                        'model': 'rss ~ 1 + 10log10(r) + antenna_gain_db + log2(n_antennas)'},
               'zones': {}}

    log('=' * 74)
    log('FITTED PATH-LOSS PARAMETERS')
    log('=' * 74)
    log(f'{"zone":<14}{"scen":<6}{"n":>8}{"range":>8}{"gamma":>8}{"sigma_dB":>10}{"R^2":>7}')
    log('-' * 74)
    for i, z in enumerate(VORONOI):
        m = zone == i
        f = fit(rss[m], r[m], gain[m], n_ant[m])
        f['scenario'] = z['scenario']
        results['zones'][z['name']] = f
        log(f'{z["name"]:<14}{z["scenario"]:<6}{f["n"]:>8}{f["mean_range_m"]:>8.1f}'
            f'{f["gamma"]:>8.2f}{f["sigma_db"]:>10.2f}{f["r2"]:>7.3f}')

    for lab in ('LOS', 'NLOS'):
        idx = [i for i, z in enumerate(VORONOI) if z['scenario'] == lab]
        m = np.isin(zone, idx)
        f = fit(rss[m], r[m], gain[m], n_ant[m])
        results['zones'][lab] = f
        log(f'{lab:<14}{"":<6}{f["n"]:>8}{f["mean_range_m"]:>8.1f}'
            f'{f["gamma"]:>8.2f}{f["sigma_db"]:>10.2f}{f["r2"]:>7.3f}')

    pooled = fit(rss, r, gain, n_ant)
    results['zones']['POOLED'] = pooled
    log(f'{"POOLED":<14}{"":<6}{pooled["n"]:>8}{pooled["mean_range_m"]:>8.1f}'
        f'{pooled["gamma"]:>8.2f}{pooled["sigma_db"]:>10.2f}{pooled["r2"]:>7.3f}')

    # recompute the section 7.5 table with fitted rather than assumed constants
    log('')
    log('=' * 74)
    log('RANGE RESOLUTION: assumed (gamma=4, sigma=6) vs fitted (pooled)')
    log('=' * 74)
    log(f'{"range":<12}{"dB/m assumed":>14}{"sig_r assumed":>15}'
        f'{"dB/m fitted":>14}{"sig_r fitted":>14}')
    log('-' * 74)
    table = {}
    for lab, rr in [('10 m (15x15)', 10.0), ('40 m (NE BS)', 40.0),
                    ('56 m (p10)', 56.3), ('95 m (median)', 95.3),
                    ('126 m (p90)', 126.2)]:
        sa, ua = sigma_range(4.0, 6.0, rr)
        sf, uf = sigma_range(pooled['gamma'], pooled['sigma_db'], rr)
        table[lab] = {'assumed_db_per_m': round(sa, 4), 'assumed_sigma_r_m': round(ua, 2),
                      'fitted_db_per_m': round(sf, 4), 'fitted_sigma_r_m': round(uf, 2)}
        log(f'{lab:<12}{sa:>14.3f}{ua:>14.1f} m{sf:>14.3f}{uf:>13.1f} m')
    results['range_resolution'] = table
    results['comparison'] = {
        'assumed_gamma': 4.0, 'fitted_gamma': round(pooled['gamma'], 3),
        'assumed_sigma_db': 6.0, 'fitted_sigma_db': round(pooled['sigma_db'], 3),
        'measured_multi_ant_radial_error_m': 13.69,
        'fitted_sigma_r_at_median_m': table['95 m (median)']['fitted_sigma_r_m'],
    }
    log('')
    log(f'measured multi-antenna radial error: 13.69 m')
    log(f'fitted naive-ranging bound at median range: '
        f'{table["95 m (median)"]["fitted_sigma_r_m"]:.1f} m')
    beats = 13.69 < table['95 m (median)']['fitted_sigma_r_m']
    results['comparison']['model_beats_naive_ranging'] = bool(beats)
    log('claim "model beats naive path-loss ranging": '
        + ('HOLDS with fitted constants' if beats else 'DOES NOT HOLD with fitted constants'))

    out = out_dir / 'pathloss_fit_summary.json'
    out.write_text(json.dumps(results, indent=1), encoding='utf-8')
    log(f'saved -> {out}')


if __name__ == '__main__':
    sys.exit(main())
