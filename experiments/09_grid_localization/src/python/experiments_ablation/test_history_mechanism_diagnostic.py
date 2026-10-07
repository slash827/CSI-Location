"""
Tests for the pure helpers in history_mechanism_diagnostic.py. No dataset or
model code is needed: run with pytest, or directly with python.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import history_mechanism_diagnostic as D


def _sample_window(h):
    """A flattened sample whose values encode (channel, step): 100*c + t; statics -1, -2, -3."""
    L = h + 1
    seq = np.array([[100 * c + t for t in range(L)] for c in range(len(D.SIGNAL_COLS))], float)
    return np.concatenate([seq.ravel(), [-1.0, -2.0, -3.0]])


def _decode(x):
    """Turn selected values back into {channel name: sorted steps} plus statics."""
    chans, statics = {}, []
    for v in x:
        if v < 0:
            statics.append(v)
        else:
            c, t = divmod(int(v), 100)
            chans.setdefault(D.SIGNAL_COLS[c], []).append(t)
    return chans, statics


def test_full_selects_everything():
    h = 5
    x = _sample_window(h)
    idx = D.feature_index('full', h)
    assert len(idx) == len(D.SIGNAL_COLS) * (h + 1) + D.N_STATIC
    assert np.array_equal(x[idx], x)


def test_snap_is_current_step_of_every_channel():
    h = 5
    chans, statics = _decode(_sample_window(h)[D.feature_index('snap', h)])
    assert set(chans) == set(D.SIGNAL_COLS)
    assert all(steps == [h] for steps in chans.values())
    assert statics == [-1.0, -2.0, -3.0]


def test_pure_snap_drops_differences_and_time():
    h = 5
    chans, _ = _decode(_sample_window(h)[D.feature_index('pure_snap', h)])
    assert not set(chans) & set(D.DIFF_COLS)
    assert set(chans) == set(D.SIGNAL_COLS) - set(D.DIFF_COLS)
    assert all(steps == [h] for steps in chans.values())


def test_partial_history_conditions():
    h = 5
    for cond, lagged in (('rss_hist', D.RSS_SIDE), ('angle_hist', D.ANGLE_SIDE), ('ray_hist', D.RAY_SIDE)):
        chans, _ = _decode(_sample_window(h)[D.feature_index(cond, h)])
        assert set(chans) == set(D.SIGNAL_COLS), cond
        for name, steps in chans.items():
            if name in lagged or name in D.TIME_SIDE:
                assert steps == list(range(h + 1)), (cond, name)
            else:
                assert steps == [h], (cond, name)


def test_channel_groups_partition_signal_cols():
    groups = D.RSS_SIDE + D.ANGLE_SIDE + D.RAY_SIDE + D.TIME_SIDE
    assert sorted(groups) == sorted(D.SIGNAL_COLS)
    assert len(groups) == len(set(groups))


def test_decompose_radial_and_tangential():
    true = np.array([[10.0, 0.0], [0.0, 20.0]])
    pred = np.array([[13.0, 0.0],    # 3 m purely radial
                     [4.0, 20.0]])   # 4 m purely tangential
    total, radial, tangential, rng = D.decompose(pred, true)
    assert np.allclose(total, [3.0, 4.0])
    assert np.allclose(radial, [3.0, 0.0])
    assert np.allclose(tangential, [0.0, 4.0])
    assert np.allclose(rng, [10.0, 20.0])


def test_per_group_metrics_counts_and_within_r():
    true = np.array([[30.0, 0.0], [50.0, 0.0], [90.0, 0.0], [130.0, 0.0]])
    pred = true + np.array([[4.0, 0.0], [0.0, 8.0], [15.0, 0.0], [0.0, 25.0]])
    ant = np.array([4, 2, 1, 1])
    uid = np.array([1, 2, 3, 3])
    los = np.array([True, False, True, False])
    res, err = D.per_group_metrics(pred, true, ant, uid, los)
    assert np.allclose(err, [4, 8, 15, 25])
    assert res['multi']['n_samples'] == 2 and res['multi']['n_users'] == 2
    assert res['single']['n_samples'] == 2 and res['single']['n_users'] == 1
    assert np.isclose(res['multi']['mae'], 6.0)
    assert np.isclose(res['all']['within_5m'], 0.25)
    assert np.isclose(res['all']['within_10m'], 0.5)
    assert np.isclose(res['all']['within_20m'], 0.75)
    assert res['all']['range_bins']['<40']['n'] == 1
    assert res['all']['range_bins']['>=120']['mae'] == 25.0
    assert np.isclose(res['multi']['radial_mean'], 2.0)
    assert np.isclose(res['multi']['tangential_mean'], 4.0)
    assert res['all']['los']['LOS']['n'] == 2


def test_empty_group_is_reported_not_crashed():
    true = np.array([[30.0, 0.0]])
    res, _ = D.per_group_metrics(true + 1.0, true, np.array([4]), np.array([7]))
    assert res['single'] == {'n_samples': 0, 'n_users': 0}


def test_paired_gain():
    pg = D.paired_gain([20.0, 22.0, 21.0], [18.0, 19.0, 19.0])
    assert np.isclose(pg['gain_mean_m'], 7.0 / 3)
    assert pg['n_pairs'] == 3
    assert pg['clears_ci'] is True
    assert D.paired_gain([None, None], [1.0, 2.0]) is None


def test_aligned_values_matches_dataset_order():
    import pandas as pd
    h = 2
    df = pd.DataFrame({
        'user_id':    [5, 5, 5, 5, 3, 3, 3, 9],
        'step_index': [3, 0, 2, 1, 2, 0, 1, 0],
        'is_los':     [True, False, False, True, True, False, False, True],
    })
    # dataset order: users ascending (3, then 5; 9 has too few rows), steps ascending, first h dropped
    sample_uids = np.array([3, 5, 5])
    vals = D.aligned_values(df, 'is_los', h, sample_uids)
    assert list(vals) == [True, False, True]
    try:
        D.aligned_values(df, 'is_los', h, np.array([5, 3, 5]))
    except RuntimeError:
        pass
    else:
        raise AssertionError('misaligned user ids were not detected')


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    for t in tests:
        t()
        print(f'ok  {t.__name__}')
    print(f'{len(tests)} passed')
