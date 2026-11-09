"""
Middle layer: per-UE CSV logs of Alon's heterogeneous-device simulator -> the project's frame.

Alon's simulator (fork of Omri's QuaDRiGa framework, branch heterogeneous-ue-device-classes)
writes one CSV per UE with columns
    timestamp, x, y, area_id, rsrp, rsrq, sinr, cqi, serving_bs, distance, device_class
This module turns them into the DataFrame layout the macro-cell scripts use
(user_id, step_index, rss, sinr, x_pos, y_pos, delta_t, device_class, ...).

It also checks temporal consistency, which the history and difference experiments depend on:
the lag-1 autocorrelation of RSRP after removing the distance trend. In a spatially consistent
channel, a UE that moves a few centimetres between reports keeps almost the same shadowing,
so the correlation is high; values near 0 mean every report is an independent draw, and the
differences between consecutive reports are then noise. (The sample logs of 2026-11-06 give
0.03 to 0.12, because the simulator builds a new qd_layout for every report.)

Usage (from the repository root):
    .venv/Scripts/python experiments/09_grid_localization/src/python/utils/alon_csv_loader.py \
        --csv-dir experiments/09_grid_localization/Simulation-Nov-2026/omri_simulator_not_for_claims
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = ['timestamp', 'x', 'y', 'rsrp', 'sinr', 'serving_bs', 'distance', 'device_class']


def load_alon_csvs(csv_dir):
    """Load every ue_*.csv in csv_dir into one DataFrame in the project's column names."""
    files = sorted(Path(csv_dir).glob('ue_*.csv'))
    if not files:
        raise FileNotFoundError(f'No ue_*.csv files in {csv_dir}')
    frames = []
    for f in files:
        d = pd.read_csv(f)
        missing = [c for c in REQUIRED if c not in d.columns]
        if missing:
            raise ValueError(f'{f.name}: missing columns {missing}')
        d = d.sort_values('timestamp').reset_index(drop=True)
        frames.append(pd.DataFrame({
            'user_id': int(f.stem.split('_')[1]),
            'step_index': np.arange(1, len(d) + 1),
            'timestamp_sec': d['timestamp'].astype(float),
            'delta_t': d['timestamp'].diff().fillna(d['timestamp'].diff().median()).astype(float),
            'rss': d['rsrp'].astype(float),
            'sinr': d['sinr'].astype(float),
            'rsrq': d.get('rsrq', np.nan),
            'cqi': d.get('cqi', np.nan),
            'x_pos': d['x'].astype(float),
            'y_pos': d['y'].astype(float),
            'area_id': d.get('area_id', np.nan),
            'serving_bs': d['serving_bs'].astype(int),
            'distance': d['distance'].astype(float),
            'device_class': d['device_class'].astype(str),
        }))
    return pd.concat(frames, ignore_index=True)


def consistency_report(df):
    """Per UE: step length, RSRP lag-1 autocorrelation after a log-distance fit, clipping share."""
    rows = []
    for uid, d in df.groupby('user_id'):
        step = np.hypot(d.x_pos.diff(), d.y_pos.diff())
        same = d.serving_bs.eq(d.serving_bs.shift())
        a, b = np.polyfit(np.log10(d.distance.clip(lower=1)), d.rss, 1)
        resid = d.rss - (a * np.log10(d.distance.clip(lower=1)) + b)
        rows.append(dict(user_id=uid, device_class=d.device_class.iloc[0], n=len(d),
                         median_step_m=round(float(step.median()), 3),
                         lag1_corr=round(float(resid[same].autocorr(1)), 3),
                         diff_std_db=round(float(resid.diff()[same].std()), 2),
                         level_std_db=round(float(resid.std()), 2),
                         rsrp_clipped=round(float((d.rss >= -40).mean()), 3)))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(
        description="Load Alon's per-UE CSV logs and check their temporal consistency.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('Usage')[1])
    ap.add_argument('--csv-dir', required=True)
    args = ap.parse_args()
    df = load_alon_csvs(args.csv_dir)
    print(f'{df.user_id.nunique()} UEs, {len(df):,} reports; classes {df.groupby("user_id").device_class.first().value_counts().to_dict()}')
    print(consistency_report(df).to_string(index=False))


if __name__ == '__main__':
    main()
