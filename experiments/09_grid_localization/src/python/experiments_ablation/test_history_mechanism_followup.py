"""
Tests for the pure helpers in history_mechanism_followup.py. No dataset or
model code is needed: run with pytest, or directly with python.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import history_mechanism_diagnostic as D
import history_mechanism_followup as F

H = 5
L = H + 1


def _windows(n=4):
    """n flattened samples whose values encode (sample, channel, step): 1000*i + 100*c + t."""
    rows = []
    for i in range(n):
        seq = np.array([[1000 * i + 100 * c + t for t in range(L)] for c in range(len(D.SIGNAL_COLS))], float)
        rows.append(np.concatenate([seq.ravel(), [-1.0, -2.0, -3.0]]))
    return np.array(rows, dtype=np.float32)


def _chan(X, name):
    c = D.SIGNAL_COLS.index(name)
    return X[:, c * L:(c + 1) * L]


def test_subset_index_matches_diagnostic_angle_hist():
    assert np.array_equal(F.subset_index(D.ANGLE_SIDE + D.TIME_SIDE, H), D.feature_index('angle_hist', H))


def test_az_and_el_conditions_lag_only_their_channels():
    X = _windows()
    n_snap = len(D.feature_index('snap', H))
    az = F.build_condition('az_hist', X, H, seed=0, tag=0)
    el = F.build_condition('el_hist', X, H, seed=0, tag=0)
    assert az.shape[1] == n_snap + H * len(F.AZ_SIDE + D.TIME_SIDE)
    assert el.shape[1] == n_snap + H * len(F.EL_SIDE + D.TIME_SIDE)
    steps = lambda M, c: sorted(int(v) % 100 for v in M[0] if v >= 0 and int(v) // 100 == c)
    assert steps(az, D.SIGNAL_COLS.index('sin_az')) == list(range(L))
    assert steps(az, D.SIGNAL_COLS.index('sin_el')) == [H]
    assert steps(el, D.SIGNAL_COLS.index('sin_el')) == list(range(L))
    assert steps(el, D.SIGNAL_COLS.index('d_az')) == [H]


def test_window_stats_are_order_free():
    X = _windows()
    perm = F.shuffle_lags(X, D.ANGLE_SIDE, H, np.random.default_rng(0))
    for with_std in (False, True):
        a = F.window_stats(X, D.ANGLE_SIDE, H, with_std)
        b = F.window_stats(perm, D.ANGLE_SIDE, H, with_std)
        assert a.shape[1] == len(D.ANGLE_SIDE) * (2 if with_std else 1)
        assert np.allclose(a, b, rtol=1e-5)
    c = D.SIGNAL_COLS.index('sin_az')
    assert np.isclose(F.window_stats(X, ['sin_az'], H, False)[0, 0], 100 * c + (L - 1) / 2)


def test_shuffle_keeps_current_step_and_other_channels():
    X = _windows(200)
    S = F.shuffle_lags(X, D.ANGLE_SIDE, H, np.random.default_rng(1))
    for name in D.SIGNAL_COLS:
        a, b = _chan(X, name), _chan(S, name)
        assert np.array_equal(a[:, -1], b[:, -1]), name
        if name in D.ANGLE_SIDE:
            assert np.array_equal(np.sort(a, axis=1), np.sort(b, axis=1)), name
        else:
            assert np.array_equal(a, b), name
    assert not np.array_equal(_chan(X, 'sin_az'), _chan(S, 'sin_az'))
    # one permutation per sample, shared by the channels
    order = lambda name: np.argsort(_chan(S, name)[:, :-1], axis=1)
    assert np.array_equal(order('sin_az'), order('d_az'))
    assert np.array_equal(X[:, -3:], S[:, -3:])


def test_shuffled_condition_differs_between_train_and_test_tags():
    X = _windows(50)
    a = F.build_condition('angle_shuffled', X, H, seed=3, tag=0)
    b = F.build_condition('angle_shuffled', X, H, seed=3, tag=1)
    assert a.shape == X[:, D.feature_index('angle_hist', H)].shape
    assert not np.array_equal(a, b)
    assert np.array_equal(a, F.build_condition('angle_shuffled', X, H, seed=3, tag=0))


def test_snap_los_appends_flag():
    X = _windows()
    los = np.array([True, False, True, False])
    out = F.build_condition('snap_los', X, H, seed=0, tag=0, los=los)
    assert out.shape[1] == len(D.feature_index('snap', H)) + 1
    assert list(out[:, -1]) == [1.0, 0.0, 1.0, 0.0]


def test_aligned_windows_and_crossing():
    h = 2
    df = pd.DataFrame({
        'user_id':    [5, 5, 5, 5, 3, 3, 3, 9],
        'step_index': [3, 0, 2, 1, 2, 0, 1, 0],
        'is_los':     [True, False, False, True, True, False, False, True],
    })
    # user 3 sorted: F F T ; user 5 sorted: F T F T ; user 9 too short
    win = F.aligned_windows(df, 'is_los', h, np.array([3, 5, 5])).astype(bool)
    assert win.tolist() == [[False, False, True], [False, True, False], [True, False, True]]
    assert np.array_equal(win[:, -1], D.aligned_values(df, 'is_los', h, np.array([3, 5, 5])))
    try:
        F.aligned_windows(df, 'is_los', h, np.array([5, 3, 5]))
    except RuntimeError:
        pass
    else:
        raise AssertionError('misaligned user ids were not detected')


def test_assign_region_nearest_centre():
    x = np.array([35.0, 95.0, 75.0, 60.0, 0.0])
    y = np.array([15.0, 15.0, 5.0, 90.0, 96.0])
    assert list(F.assign_region(x, y)) == [0, 1, 2, 3, 3]


def test_paired_uses_student_t():
    pg = F.paired([20.0, 22.0, 21.0], [18.0, 19.0, 19.0])
    assert np.isclose(pg['gain_mean_m'], 7.0 / 3)
    d = np.array([2.0, 3.0, 2.0])
    assert np.isclose(pg['gain_t95_m'], 4.302652729911275 * d.std(ddof=1) / np.sqrt(3))
    assert pg['n_positive'] == 3 and pg['clears_t95'] is True
    assert F.paired([None, None], [1.0, 2.0]) is None


def test_shape_metrics():
    true = np.array([[10.0, 0.0], [0.0, 20.0], [30.0, 0.0]])
    pred = np.array([[13.0, 0.0], [4.0, 20.0], [30.0, 0.0]])   # 3 m radial, 4 m tangential, exact
    s = F.shape_metrics(pred, true)
    assert np.isclose(s['radial_mae'], 1.0) and np.isclose(s['tangential_mae'], 4.0 / 3)
    assert np.isclose(s['radial_share_sq'], 9.0 / 25.0)
    assert np.isclose(s['radial_bias'], 1.0)


def test_ar1_noise_std_and_correlation():
    rng = np.random.default_rng(0)
    for rho in (0.0, 0.9):
        e = F.ar1_noise(200_000, 4.0, rho, rng)
        assert abs(e.std() - 4.0) < 0.15
        assert abs(np.corrcoef(e[:-1], e[1:])[0, 1] - rho) < 0.02
    assert np.allclose(np.diff(F.ar1_noise(50, 4.0, 1.0, rng)), 0.0)


def test_remove_interference_gives_snr():
    df = pd.DataFrame({'rss': np.array([-60.0, -80.0], np.float32),
                       'antenna_gain_db': np.array([3.0, 0.0], np.float32),
                       'sinr': np.array([5.0, 7.0], np.float32), 'other': [1, 2]})
    out = F.remove_interference(df)
    assert np.allclose(out['sinr'], [-60.0 - 3.0 + 104.0, -80.0 + 104.0])
    assert list(df['sinr']) == [5.0, 7.0] and list(out['other']) == [1, 2]


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    for t in tests:
        t()
        print(f'ok  {t.__name__}')
    print(f'{len(tests)} passed')
