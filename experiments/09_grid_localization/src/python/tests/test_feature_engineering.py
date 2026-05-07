"""
Tests for feature engineering functions in multi_user_pipeline.py:
  - build_history_features
  - build_delta_features
  - get_feature_cols
  - make_split
  - build_grid_lookup
  - compute_mae
"""
import sys
import numpy as np
import pandas as pd
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipelines.multi_user_pipeline import (
    build_history_features,
    build_delta_features,
    get_feature_cols,
    make_split,
    build_grid_lookup,
    compute_mae,
)


# ── fixtures ───────────────────────────────────────────────────────────────────

def _make_df(n_steps=20, n_users=2, rng_seed=0) -> pd.DataFrame:
    """Minimal DataFrame that mimics load_all_users() output."""
    rng = np.random.default_rng(rng_seed)
    rows = []
    for uid in range(1, n_users + 1):
        for step in range(n_steps):
            gp = (step % 4) + 1          # 4 grid points, 1-indexed
            rows.append({
                'user_id':       uid,
                'step_index':    step,
                'grid_point_id': gp,
                'rss':           rng.normal(-70, 5),
                'sinr':          rng.normal(15, 3),
                'aoa_azimuth':   rng.uniform(-30, 30),
                'aoa_elevation': rng.uniform(-20, -5),
                'x_pos':         float(gp * 2),
                'y_pos':         float(gp * 2),
                'n_antennas':    2,
                'antenna_gain_db': 0.0,
                'ue_height':     1.5,
            })
    df = pd.DataFrame(rows)
    return df


# ── get_feature_cols ───────────────────────────────────────────────────────────

class TestGetFeatureCols:
    def test_h0_absolute(self):
        cols = get_feature_cols(h=0)
        assert cols == ['rss_lag0', 'sinr_lag0']

    def test_h3_absolute_count(self):
        cols = get_feature_cols(h=3)
        # 2 metrics × (h+1) lags = 8 columns
        assert len(cols) == 8
        assert 'rss_lag0' in cols
        assert 'rss_lag3' in cols
        assert 'sinr_lag3' in cols

    def test_h3_absolute_with_aoa(self):
        cols = get_feature_cols(h=3, include_aoa=True)
        # 4 metrics × 4 lags = 16 columns
        assert len(cols) == 16
        assert 'aoa_az_lag0' in cols
        assert 'aoa_el_lag3' in cols

    def test_h3_delta_count(self):
        cols = get_feature_cols(h=3, mode='delta')
        # 2 metrics × (h+1): lag0 + 3 deltas = 8 columns
        assert len(cols) == 8
        assert 'rss_lag0' in cols
        assert 'rss_delta1' in cols
        assert 'rss_delta3' in cols
        assert 'rss_lag1' not in cols    # delta mode has no lag1

    def test_delta_aoa_count(self):
        cols = get_feature_cols(h=2, include_aoa=True, mode='delta')
        # 4 metrics × 3 (lag0 + 2 deltas) = 12 columns
        assert len(cols) == 12

    def test_extra_cols_appended(self):
        cols = get_feature_cols(h=1, extra_cols=['n_antennas', 'ue_height'])
        assert 'feat_n_antennas' in cols
        assert 'feat_ue_height' in cols

    def test_absolute_delta_same_length(self):
        """Absolute and delta modes must produce the same number of columns."""
        assert len(get_feature_cols(h=3)) == len(get_feature_cols(h=3, mode='delta'))


# ── build_history_features ─────────────────────────────────────────────────────

class TestBuildHistoryFeatures:
    def test_output_shape(self):
        df = _make_df(n_steps=20, n_users=2)
        h = 3
        out = build_history_features(df, h=h)
        # Each user loses h rows at the front
        expected_rows = 2 * (20 - h)
        assert len(out) == expected_rows

    def test_lag0_equals_current_rss(self):
        # build_history_features keeps the original 'rss' column in meta,
        # so rss_lag0 must equal it directly (no merge needed — avoids rss_x/rss_y collision).
        df = _make_df(n_steps=10, n_users=1)
        out = build_history_features(df, h=2)
        assert np.allclose(out['rss_lag0'], out['rss'])

    def test_lag1_is_previous_step(self):
        df = _make_df(n_steps=10, n_users=1)
        out = build_history_features(df, h=1)
        # For each row, rss_lag1 should equal rss from step_index - 1
        for _, row in out.iterrows():
            prev = df[(df['user_id'] == row['user_id']) &
                      (df['step_index'] == row['step_index'] - 1)]
            if len(prev) == 1:
                assert abs(row['rss_lag1'] - prev['rss'].values[0]) < 1e-9

    def test_no_nan_in_output(self):
        df = _make_df(n_steps=15, n_users=2)
        out = build_history_features(df, h=3)
        feat_cols = get_feature_cols(h=3)
        assert out[feat_cols].isna().sum().sum() == 0

    def test_users_not_cross_contaminated(self):
        """Lag values must not bleed across user boundaries."""
        df = _make_df(n_steps=10, n_users=2)
        out = build_history_features(df, h=2)
        for uid in out['user_id'].unique():
            u_rows = out[out['user_id'] == uid]
            assert (u_rows['user_id'] == uid).all()

    def test_extra_cols_present(self):
        df = _make_df(n_steps=10, n_users=1)
        out = build_history_features(df, h=1, extra_cols=['n_antennas'])
        assert 'feat_n_antennas' in out.columns

    def test_aoa_cols_present_when_requested(self):
        df = _make_df(n_steps=10, n_users=1)
        out = build_history_features(df, h=1, include_aoa=True)
        assert 'aoa_az_lag0' in out.columns
        assert 'aoa_el_lag1' in out.columns

    def test_h0_no_rows_dropped(self):
        df = _make_df(n_steps=10, n_users=1)
        out = build_history_features(df, h=0)
        assert len(out) == 10


# ── build_delta_features ───────────────────────────────────────────────────────

class TestBuildDeltaFeatures:
    def test_output_shape_matches_absolute(self):
        df = _make_df(n_steps=20, n_users=2)
        h = 3
        abs_out   = build_history_features(df, h=h)
        delta_out = build_delta_features(df, h=h)
        assert len(delta_out) == len(abs_out)

    def test_lag0_is_absolute(self):
        # build_delta_features keeps the original 'rss' column in meta,
        # so rss_lag0 must equal it directly.
        df = _make_df(n_steps=10, n_users=1)
        out = build_delta_features(df, h=2)
        assert np.allclose(out['rss_lag0'], out['rss'])

    def test_delta1_is_first_difference(self):
        """delta1[t] = rss[t] - rss[t-1]."""
        df = _make_df(n_steps=10, n_users=1)
        out = build_delta_features(df, h=1)
        for _, row in out.iterrows():
            curr = df[(df['user_id'] == row['user_id']) &
                      (df['step_index'] == row['step_index'])]['rss'].values
            prev = df[(df['user_id'] == row['user_id']) &
                      (df['step_index'] == row['step_index'] - 1)]['rss'].values
            if len(curr) == 1 and len(prev) == 1:
                expected = curr[0] - prev[0]
                assert abs(row['rss_delta1'] - expected) < 1e-9

    def test_no_absolute_lag_cols_in_delta_mode(self):
        df = _make_df(n_steps=10, n_users=1)
        out = build_delta_features(df, h=3)
        for col in out.columns:
            assert not (col.startswith('rss_lag') and col != 'rss_lag0'), \
                f"Unexpected absolute lag column in delta output: {col}"

    def test_no_nan_in_output(self):
        df = _make_df(n_steps=15, n_users=2)
        out = build_delta_features(df, h=3)
        feat_cols = get_feature_cols(h=3, mode='delta')
        assert out[feat_cols].isna().sum().sum() == 0

    def test_feature_count_equals_absolute(self):
        abs_cols   = get_feature_cols(h=3)
        delta_cols = get_feature_cols(h=3, mode='delta')
        assert len(abs_cols) == len(delta_cols)


# ── make_split ─────────────────────────────────────────────────────────────────

class TestMakeSplit:
    def test_split_ratio(self):
        df = _make_df(n_steps=100, n_users=1)
        out = make_split(df, test_ratio=0.2)
        n_test  = (out['split'] == 'test').sum()
        n_train = (out['split'] == 'train').sum()
        assert n_test == 20
        assert n_train == 80

    def test_test_is_last_chronologically(self):
        """All test steps must come after all train steps (per user)."""
        df = _make_df(n_steps=50, n_users=2)
        out = make_split(df, test_ratio=0.2)
        for uid in out['user_id'].unique():
            train_max = out.loc[(out['user_id'] == uid) & (out['split'] == 'train'),
                                'step_index'].max()
            test_min  = out.loc[(out['user_id'] == uid) & (out['split'] == 'test'),
                                'step_index'].min()
            assert train_max < test_min

    def test_no_leakage(self):
        df = _make_df(n_steps=100, n_users=3)
        out = make_split(df, test_ratio=0.2)
        for uid in out['user_id'].unique():
            train_steps = set(out.loc[(out['user_id'] == uid) & (out['split'] == 'train'),
                                      'step_index'])
            test_steps  = set(out.loc[(out['user_id'] == uid) & (out['split'] == 'test'),
                                      'step_index'])
            assert len(train_steps & test_steps) == 0

    def test_all_rows_assigned(self):
        df = _make_df(n_steps=20, n_users=2)
        out = make_split(df)
        assert out['split'].isna().sum() == 0
        assert set(out['split'].unique()) == {'train', 'test'}


# ── build_grid_lookup ──────────────────────────────────────────────────────────

class TestBuildGridLookup:
    def test_all_grid_points_present(self):
        df = _make_df(n_steps=40, n_users=1)
        lookup = build_grid_lookup(df)
        assert set(lookup.keys()) == set(df['grid_point_id'].unique())

    def test_coordinates_are_means(self):
        df = _make_df(n_steps=40, n_users=1)
        lookup = build_grid_lookup(df)
        for gp, (mx, my) in lookup.items():
            grp = df[df['grid_point_id'] == gp]
            assert abs(mx - grp['x_pos'].mean()) < 1e-9
            assert abs(my - grp['y_pos'].mean()) < 1e-9


# ── compute_mae ────────────────────────────────────────────────────────────────

class TestComputeMAE:
    def _lookup(self):
        # 4 points on a regular 2m grid
        return {1: (5.0, 5.0), 2: (7.0, 5.0), 3: (5.0, 7.0), 4: (7.0, 7.0)}

    def test_perfect_prediction_is_zero(self):
        lk = self._lookup()
        ids = np.array([1, 2, 3, 4])
        assert compute_mae(ids, ids, lk) == pytest.approx(0.0)

    def test_adjacent_error_is_2m(self):
        lk = self._lookup()
        # Predict point 2 for every true point 1 → distance = 2m
        true = np.array([1, 1, 1])
        pred = np.array([2, 2, 2])
        assert compute_mae(true, pred, lk) == pytest.approx(2.0)

    def test_diagonal_error(self):
        lk = self._lookup()
        # Point 1 (5,5) → point 4 (7,7): diagonal = 2√2
        true = np.array([1])
        pred = np.array([4])
        assert compute_mae(true, pred, lk) == pytest.approx(2 * np.sqrt(2))

    def test_average_over_samples(self):
        lk = self._lookup()
        # Half correct, half 2m off
        true = np.array([1, 1])
        pred = np.array([1, 2])
        assert compute_mae(true, pred, lk) == pytest.approx(1.0)
