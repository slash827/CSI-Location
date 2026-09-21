"""
B6: History's advantage inside a targeted LOS -> blocked (NLOS) -> LOS crossing.

Straight-line trajectories at constant speed cross a rectangular NLOS strip
between two LOS regions (run_b6_los_blocked_los.m). During the blocked
interval a snapshot model has almost nothing to go on, while a history model
carries the pre-blockage heading through. This is the sharpest isolation of
the mechanism available in this project (proposed directly to Alon Levin).

One model is trained on all training users per depth, exactly as
history_gain_by_zone.py does — the split by blocked/non-blocked and by strip
width happens at evaluation, so this asks where a single deployed model's
gain lands, not "train a specialist for each strip width."

Report Delta-MAE WITHIN THE BLOCKED INTERVAL SPECIFICALLY, not pooled over
the whole walk — the pooled number is diluted by the (much larger) LOS
segments.

Prediction: history's advantage should grow with blockage duration up to the
point where the pre-blockage heading stops being informative, then decay. A
clean peak (in gain vs strip width, at fixed h) is strong evidence; a flat
curve is evidence against.

Usage:
    python b6_los_blocked_los_analysis.py
    python b6_los_blocked_los_analysis.py --depths 0 1 3 5 10
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / 'experiments' / '09_grid_localization' / 'src' / 'python'))

from pipelines.multi_user_pipeline_regression import _read_bs_position_3d
from pipelines.multi_user_200_pipeline import make_unseen_user_split
from utils.csi_dataset import DerivedCSI1DDataset, load_and_prepare_data
from xgboost import XGBRegressor


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def load_b6_extra_fields(data_dir):
    """B6-specific per-snapshot fields not covered by the generic loader:
    in_blocked_segment and strip_width_m. Read directly from the .mat files,
    same file set and same step_index order load_200_users produces."""
    mat_files = sorted((Path(data_dir) / 'mat_files').glob('user*.mat'))
    if not mat_files:
        mat_files = sorted(Path(data_dir).glob('user*.mat'))
    rows = []
    for f in mat_files:
        mat = loadmat(f)
        u_id = int(mat['user_id_val'][0, 0])
        step_idx = mat['step_index'].flatten().astype(np.int32)
        in_blocked = mat['in_blocked_segment'].flatten().astype(bool)
        width = float(mat['strip_width_m'][0, 0])
        rows.append(pd.DataFrame({
            'user_id': u_id, 'step_index': step_idx,
            'in_blocked_segment': in_blocked, 'strip_width_m': width,
        }))
    return pd.concat(rows, ignore_index=True)


def flatten(ds):
    n = len(ds)
    d = ds.samples[0]['seq'].size + ds.samples[0]['static'].size
    X = np.empty((n, d), np.float32)
    Y = np.empty((n, 2), np.float32)
    for i, s in enumerate(ds.samples):
        X[i] = np.concatenate([s['seq'].ravel(), s['static'].ravel()])
        Y[i] = s['target']
    return X, Y


def main():
    ap = argparse.ArgumentParser(
        description='History gain within the blocked interval, B6.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python b6_los_blocked_los_analysis.py
  python b6_los_blocked_los_analysis.py --depths 0 1 3 5 10 --seed 7
""")
    ap.add_argument('--depths', type=int, nargs='+', default=[0, 1, 3, 5, 10])
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--single-ant-ratio', type=float, default=0.15)
    args = ap.parse_args()

    run_ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    out_dir = (PROJECT_ROOT / 'results' / 'notebook_experiments' / 'multi_user_poc'
               / f'b6_los_blocked_los_{run_ts}')
    out_dir.mkdir(parents=True, exist_ok=True)

    log('loading...')
    data_base = PROJECT_ROOT / 'results' / 'b6_los_blocked_los'
    data_dir = sorted(data_base.glob('sim_data_b6_*'))[-1]
    bs_pos = np.array(_read_bs_position_3d(data_dir))
    df, _, _ = load_and_prepare_data(data_dir, bs_pos, seed=args.seed,
                                     single_ant_ratio=args.single_ant_ratio)

    extra = load_b6_extra_fields(data_dir)
    df = df.merge(extra, on=['user_id', 'step_index'], how='left', validate='one_to_one')
    assert df['in_blocked_segment'].notna().all(), 'merge dropped rows — user_id/step_index mismatch'

    df, _, test_uids = make_unseen_user_split(df, 0.8, args.seed)
    df_tr = df[df.split == 'train']
    df_te = df[df.split == 'test']
    log(f'{len(df_tr):,} train / {len(df_te):,} test rows ({len(test_uids)} disjoint test users)')

    strip_widths = sorted(df['strip_width_m'].unique())
    log(f'strip widths: {strip_widths}')

    results = {'meta': {'dataset': str(data_dir), 'seed': args.seed,
                        'depths': args.depths, 'strip_widths_m': strip_widths},
               'by_depth': {}}

    for h in args.depths:
        t0 = time.time()
        tr = DerivedCSI1DDataset(df_tr, h=h)
        te = DerivedCSI1DDataset(df_te, h=h,
                                 sig_mean=tr.sig_mean, sig_std=tr.sig_std,
                                 stat_mean=tr.stat_mean, stat_std=tr.stat_std,
                                 targ_mean=tr.targ_mean, targ_std=tr.targ_std,
                                 speed_mean=tr.speed_mean, speed_std=tr.speed_std)
        X_tr, Y_tr = flatten(tr)
        X_te, Y_te = flatten(te)

        # DerivedCSI1DDataset drops the first h rows of each user — rebuild the
        # aligned blocked/width vectors the same way rather than reusing df_te order
        blocked_te, width_te = [], []
        for uid, udf in df_te.groupby('user_id'):
            udf = udf.sort_values('step_index')
            if len(udf) < h + 1:
                continue
            blocked_te.append(udf['in_blocked_segment'].values[h:])
            width_te.append(udf['strip_width_m'].values[h:])
        blocked_te = np.concatenate(blocked_te).astype(bool)
        width_te = np.concatenate(width_te)
        assert len(blocked_te) == len(X_te), f'alignment broken: {len(blocked_te)} vs {len(X_te)}'

        model = XGBRegressor(n_estimators=50, max_depth=5, learning_rate=0.15,
                             subsample=0.8, colsample_bytree=0.8,
                             random_state=args.seed, n_jobs=-1, tree_method='hist',
                             multi_strategy='one_output_per_tree')
        model.fit(X_tr, Y_tr)
        pred = model.predict(X_te) * tr.targ_std + tr.targ_mean
        true = Y_te * tr.targ_std + tr.targ_mean
        err = np.linalg.norm(pred - true, axis=1)

        rec = {'overall_mae': float(err.mean()), 'elapsed_sec': round(time.time() - t0, 1)}
        rec['blocked'] = {'mae': float(err[blocked_te].mean()), 'n': int(blocked_te.sum())}
        rec['unblocked'] = {'mae': float(err[~blocked_te].mean()), 'n': int((~blocked_te).sum())}
        rec['blocked_by_width'] = {}
        for w in strip_widths:
            m = blocked_te & (width_te == w)
            if m.sum() > 0:
                rec['blocked_by_width'][str(w)] = {'mae': float(err[m].mean()), 'n': int(m.sum())}
        results['by_depth'][f'h={h}'] = rec
        log(f'  h={h:<2d} overall {rec["overall_mae"]:6.3f} m | '
            f'blocked {rec["blocked"]["mae"]:6.3f} | unblocked {rec["unblocked"]["mae"]:6.3f} '
            f'| {rec["elapsed_sec"]}s')

    # gain within the blocked interval specifically, vs each stratum's own h=0
    base = args.depths[0]
    log('=' * 78)
    log(f'HISTORY GAIN WITHIN THE BLOCKED INTERVAL (vs h={base})')
    log('=' * 78)
    gains = {}
    header = (f'{"stratum":<16}{"n":>7}' + ''.join(f'{"h="+str(h):>10}' for h in args.depths)
              + f'{"best gain":>11}')
    log(header)
    log('-' * len(header))

    for label, path in [('blocked', ['blocked']), ('unblocked', ['unblocked'])]:
        maes = [results['by_depth'][f'h={h}']['blocked' if label == 'blocked' else 'unblocked']['mae']
                for h in args.depths]
        n = results['by_depth'][f'h={base}']['blocked' if label == 'blocked' else 'unblocked']['n']
        best_gain = 100.0 * (maes[0] - min(maes)) / maes[0]
        gains[label] = {'maes': dict(zip([f'h={h}' for h in args.depths], [round(m, 4) for m in maes])),
                        'best_gain_pct': round(best_gain, 2), 'n': n}
        log(f'{label:<16}{n:>7}' + ''.join(f'{m:>10.3f}' for m in maes) + f'{best_gain:>10.2f}%')

    log('-' * len(header))
    gains['blocked_by_width'] = {}
    for w in strip_widths:
        maes = [results['by_depth'][f'h={h}']['blocked_by_width'].get(str(w), {}).get('mae', np.nan)
                for h in args.depths]
        n = results['by_depth'][f'h={base}']['blocked_by_width'].get(str(w), {}).get('n', 0)
        if n == 0 or np.isnan(maes[0]):
            continue
        best_gain = float(100.0 * (maes[0] - np.nanmin(maes)) / maes[0])
        gains['blocked_by_width'][str(w)] = {
            'maes': dict(zip([f'h={h}' for h in args.depths], [round(float(m), 4) for m in maes])),
            'best_gain_pct': round(best_gain, 2), 'n': int(n)}
        log(f'width={w:<10.0f}{n:>7}' + ''.join(f'{m:>10.3f}' for m in maes) + f'{best_gain:>10.2f}%')
    results['gains'] = gains

    log('-' * 78)
    widths_sorted = sorted(gains['blocked_by_width'].keys(), key=float)
    gain_curve = [gains['blocked_by_width'][w]['best_gain_pct'] for w in widths_sorted]
    peak_idx = int(np.argmax(gain_curve)) if gain_curve else None
    # A single noisy interior spike is NOT a peak — require the peak to also
    # exceed every point AFTER it by a real margin (sustained decline, not a
    # one-point dip-then-recover). Below this margin, or a monotonic rise
    # all the way to the widest strip tested, does not confirm the
    # predicted grows-then-decays shape; it means the true peak (if any)
    # lies outside the range of widths tested, or the shape isn't real.
    MIN_DECAY_MARGIN_PP = 5.0
    is_clean_peak = False
    if peak_idx is not None and 0 < peak_idx < len(gain_curve) - 1:
        after_peak_max = max(gain_curve[peak_idx + 1:])
        is_clean_peak = bool((gain_curve[peak_idx] - after_peak_max) >= MIN_DECAY_MARGIN_PP)
    still_rising_at_max_width = bool(peak_idx == len(gain_curve) - 1) if peak_idx is not None else False
    results['verdict'] = {
        'blocked_gain_pct': gains['blocked']['best_gain_pct'],
        'unblocked_gain_pct': gains['unblocked']['best_gain_pct'],
        'gain_by_width_pct': dict(zip(widths_sorted, gain_curve)),
        'peak_at_width_m': widths_sorted[peak_idx] if peak_idx is not None else None,
        'clean_peak_with_sustained_decay': is_clean_peak,
        'still_rising_at_widest_tested': still_rising_at_max_width,
    }
    log(f'blocked-interval gain {gains["blocked"]["best_gain_pct"]:+.2f}%  vs  '
        f'unblocked gain {gains["unblocked"]["best_gain_pct"]:+.2f}%')
    log(f'gain by strip width: {dict(zip(widths_sorted, [round(g,2) for g in gain_curve]))}')
    if is_clean_peak:
        log(f'clean peak at width={widths_sorted[peak_idx]} with sustained decay after it '
            f'(evidence FOR the mechanism)')
    elif still_rising_at_max_width:
        log(f'still rising at the widest strip tested ({widths_sorted[-1]} m) — '
            f'no decay observed yet; the predicted peak, if real, lies beyond this range')
    else:
        log('no clean peak-then-sustained-decay pattern — likely single-seed noise; '
            'this needs the seed-repeat check, not a single run, before drawing a conclusion')

    out = out_dir / 'b6_los_blocked_los_summary.json'
    out.write_text(json.dumps(results, indent=1), encoding='utf-8')
    log(f'saved -> {out}')


if __name__ == '__main__':
    sys.exit(main())
