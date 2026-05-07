"""Tests for _apply_aoa_noise — the AoA impairment model applied at data load time.

This is critical because all AoA experiment results depend on it.
Two properties must hold:
  1. Outputs are quantized to exact 5° multiples.
  2. The noise is user-specific (different seeds per user) and reproducible.
"""
import sys
import numpy as np
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipelines.multi_user_pipeline import _apply_aoa_noise, AOA_NOISE_STD_DEG, AOA_QUANT_STEP_DEG


def _make_ud(user_id: int, n: int = 500, az_val: float = 45.0, el_val: float = -10.0):
    """Minimal user dict with constant AoA values."""
    rng = np.random.default_rng(0)
    return {
        'user_id':  user_id,
        'rss':      rng.normal(-70, 5, n),
        'sinr':     rng.normal(15, 3, n),
        'aoa_az':   np.full(n, az_val),
        'aoa_el':   np.full(n, el_val),
        'x_pos':    np.zeros(n),
        'y_pos':    np.zeros(n),
        'grid_point_id':   np.ones(n, dtype=int),
        'voronoi_cell_id': np.ones(n, dtype=int),
        'step_index':      np.arange(n),
        'device': {'n_antennas': 2, 'antenna_gain_db': 0.0, 'ue_height_m': 1.5},
    }


class TestAoANoiseModel:

    def test_output_is_quantized_to_5_degree_steps(self):
        ud = _apply_aoa_noise(_make_ud(user_id=1))
        az_mod = np.round(ud['aoa_az'] % AOA_QUANT_STEP_DEG, 6)
        el_mod = np.round(ud['aoa_el'] % AOA_QUANT_STEP_DEG, 6)
        assert (az_mod == 0).all(), "Azimuth values not quantized to 5° steps"
        assert (el_mod == 0).all(), "Elevation values not quantized to 5° steps"

    def test_noise_is_applied(self):
        """Output must differ from input — noise was actually added."""
        ud = _make_ud(user_id=1, n=1000, az_val=90.0, el_val=-15.0)
        az_before = ud['aoa_az'].copy()
        el_before = ud['aoa_el'].copy()
        _apply_aoa_noise(ud)
        assert not np.all(ud['aoa_az'] == az_before), "Azimuth unchanged — noise not applied"
        assert not np.all(ud['aoa_el'] == el_before), "Elevation unchanged — noise not applied"

    def test_noise_is_zero_mean(self):
        """Large-sample mean of noisy output ≈ clean input (bias < 1°)."""
        n = 10000
        true_az = 120.0
        ud = _make_ud(user_id=1, n=n, az_val=true_az)
        _apply_aoa_noise(ud)
        mean_az = ud['aoa_az'].mean()
        assert abs(mean_az - true_az) < 1.0, \
            f"Azimuth noise has bias: mean={mean_az:.2f}°, expected≈{true_az}°"

    def test_reproducible_per_user(self):
        """Same user_id always produces same noise sequence."""
        ud1 = _make_ud(user_id=3, n=200)
        ud2 = _make_ud(user_id=3, n=200)
        _apply_aoa_noise(ud1)
        _apply_aoa_noise(ud2)
        assert np.array_equal(ud1['aoa_az'], ud2['aoa_az'])
        assert np.array_equal(ud1['aoa_el'], ud2['aoa_el'])

    def test_different_users_get_different_noise(self):
        """Different user_ids must produce different noise sequences."""
        ud1 = _make_ud(user_id=1, n=200, az_val=0.0)
        ud2 = _make_ud(user_id=2, n=200, az_val=0.0)
        _apply_aoa_noise(ud1)
        _apply_aoa_noise(ud2)
        assert not np.array_equal(ud1['aoa_az'], ud2['aoa_az']), \
            "Users 1 and 2 got identical AoA noise — seeds are not user-specific"

    def test_noise_std_is_roughly_correct(self):
        """Empirical spread of noisy - clean values should be ≈ AOA_NOISE_STD_DEG (4°)."""
        n = 50000
        ud = _make_ud(user_id=1, n=n, az_val=0.0)
        _apply_aoa_noise(ud)
        # After quantization the std will be slightly different from 4°,
        # but should be within [2°, 8°]
        std = np.std(ud['aoa_az'])
        assert 2.0 < std < 8.0, \
            f"AoA noise std={std:.2f}° is outside expected range [2°, 8°]"

    def test_none_aoa_fields_are_not_modified(self):
        """If aoa_az/aoa_el are None, _apply_aoa_noise must leave them as None."""
        ud = _make_ud(user_id=1)
        ud['aoa_az'] = None
        ud['aoa_el'] = None
        result = _apply_aoa_noise(ud)
        assert result['aoa_az'] is None
        assert result['aoa_el'] is None

    def test_azimuth_and_elevation_use_different_seeds(self):
        """Azimuth and elevation must be independently noised."""
        ud = _make_ud(user_id=1, n=500, az_val=0.0, el_val=0.0)
        _apply_aoa_noise(ud)
        assert not np.array_equal(ud['aoa_az'], ud['aoa_el']), \
            "Azimuth and elevation got identical noise — seeds are not independent"
