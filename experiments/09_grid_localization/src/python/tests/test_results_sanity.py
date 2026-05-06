"""
Integration sanity tests — run against the actual saved CSV results.

These tests do NOT re-train models. They load the existing results_summary.csv
files and check that values are physically plausible and internally consistent.

They would catch:
  - The original SINR bug (SINR 30 dB too negative → MAE would be implausibly high)
  - AoA azimuth range mismatch (wrong BS position used in simulation)
  - Cross-experiment ordering violations (BASE_H must beat BASE)
  - NE-BS vs center-BS ordering of AoA gain

Skipped automatically if the result files don't exist (e.g. on a clean clone).
"""
import sys
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT        = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
CENTER_CSV  = ROOT / 'results' / 'multi_user_voronoi_15x15' / 'csvs' / 'results_summary.csv'
NE_CSV      = ROOT / 'results' / 'ne_bs_voronoi_15x15'      / 'csvs' / 'results_summary.csv'
CENTER_DATA = ROOT / 'results' / 'grid_localization' / 'grid_15x15' / 'sim_data_multi_user_2026-03-02_19-41-39'
NE_DATA     = ROOT / 'results' / 'grid_localization' / 'grid_15x15' / 'sim_data_ne_bs_2026-04-11_20-11-48'


def _load(path):
    if not path.exists():
        pytest.skip(f"Results file not found: {path}")
    return pd.read_csv(path)


# ── plausibility checks on center-BS results ──────────────────────────────────

class TestCenterBSResultsPlausibility:

    def test_accuracy_in_valid_range(self):
        df = _load(CENTER_CSV)
        assert (df['accuracy_%'] >= 0).all()
        assert (df['accuracy_%'] <= 100).all()

    def test_mae_positive(self):
        df = _load(CENTER_CSV)
        assert (df['mae_m'] >= 0).all(), "Negative MAE detected"

    def test_mae_below_grid_diagonal(self):
        """MAE must be below the 15×15 grid diagonal (≈40 m). Any value above this
        is physically impossible — would indicate a coordinate or label bug."""
        df = _load(CENTER_CSV)
        grid_diagonal = np.sqrt(2) * (14 * 2)  # 14 steps × 2 m spacing ≈ 39.6 m
        assert (df['mae_m'] <= grid_diagonal).all(), \
            f"MAE exceeds grid diagonal ({grid_diagonal:.1f} m):\n{df[df['mae_m'] > grid_diagonal]}"

    def test_base_h_beats_base(self):
        """BASE_H must outperform BASE for both models — this is the core thesis."""
        df = _load(CENTER_CSV)
        for model in ['xgboost', 'rf']:
            base_acc   = df[(df['model'] == model) & (df['experiment'] == 'BASE')  ]['accuracy_%'].iloc[0]
            base_h_acc = df[(df['model'] == model) & (df['experiment'] == 'BASE_H')]['accuracy_%'].iloc[0]
            assert base_h_acc > base_acc, \
                f"{model}: BASE_H ({base_h_acc:.1f}%) did not beat BASE ({base_acc:.1f}%)"

    def test_aoa_experiments_beat_non_aoa(self):
        """BASE_A must beat BASE for both models."""
        df = _load(CENTER_CSV)
        for model in ['xgboost', 'rf']:
            base_acc  = df[(df['model'] == model) & (df['experiment'] == 'BASE')  ]['accuracy_%'].iloc[0]
            base_a_acc = df[(df['model'] == model) & (df['experiment'] == 'BASE_A')]['accuracy_%'].iloc[0]
            assert base_a_acc > base_acc, \
                f"{model}: BASE_A ({base_a_acc:.1f}%) did not beat BASE ({base_acc:.1f}%)"

    def test_device_params_add_value(self):
        """BASE_H_dp must beat BASE_H."""
        df = _load(CENTER_CSV)
        for model in ['xgboost', 'rf']:
            h_acc    = df[(df['model'] == model) & (df['experiment'] == 'BASE_H')   ]['accuracy_%'].iloc[0]
            h_dp_acc = df[(df['model'] == model) & (df['experiment'] == 'BASE_H_dp')]['accuracy_%'].iloc[0]
            assert h_dp_acc > h_acc, \
                f"{model}: BASE_H_dp ({h_dp_acc:.1f}%) did not beat BASE_H ({h_acc:.1f}%)"

    def test_aoa_gain_is_large_at_center_bs(self):
        """AoA gain (BASE_A_H - BASE_H) at center BS must be > 20 pp for XGBoost.
        The known result is +33 pp. Anything below 20 pp would suggest AoA is broken."""
        df = _load(CENTER_CSV)
        base_h   = df[(df['model'] == 'xgboost') & (df['experiment'] == 'BASE_H')  ]['accuracy_%'].iloc[0]
        base_a_h = df[(df['model'] == 'xgboost') & (df['experiment'] == 'BASE_A_H')]['accuracy_%'].iloc[0]
        aoa_gain = base_a_h - base_h
        assert aoa_gain > 20.0, \
            f"AoA gain at center BS is only {aoa_gain:.1f} pp — expected >20 pp (known: ~33 pp)"


# ── plausibility checks on NE-BS results ──────────────────────────────────────

class TestNEBSResultsPlausibility:

    def test_accuracy_in_valid_range(self):
        df = _load(NE_CSV)
        assert (df['accuracy_%'] >= 0).all()
        assert (df['accuracy_%'] <= 100).all()

    def test_mae_positive_and_bounded(self):
        df = _load(NE_CSV)
        grid_diagonal = np.sqrt(2) * (14 * 2)
        assert (df['mae_m'] >= 0).all()
        assert (df['mae_m'] <= grid_diagonal).all()

    def test_base_h_beats_base(self):
        df = _load(NE_CSV)
        for model in ['xgboost', 'rf']:
            base_acc   = df[(df['model'] == model) & (df['experiment'] == 'BASE')  ]['accuracy_%'].iloc[0]
            base_h_acc = df[(df['model'] == model) & (df['experiment'] == 'BASE_H')]['accuracy_%'].iloc[0]
            assert base_h_acc > base_acc, \
                f"NE BS — {model}: BASE_H ({base_h_acc:.1f}%) did not beat BASE ({base_acc:.1f}%)"


# ── key comparative claim: AoA gain shrinks at NE BS ─────────────────────────

class TestCenterVsNEBSComparison:

    def test_aoa_gain_smaller_at_ne_bs(self):
        """AoA gain (BASE_A_H - BASE_H, XGBoost) must be smaller at NE BS than center BS.
        This is the central finding of the placement study."""
        center = _load(CENTER_CSV)
        ne     = _load(NE_CSV)

        def aoa_gain(df):
            base_h   = df[(df['model'] == 'xgboost') & (df['experiment'] == 'BASE_H')  ]['accuracy_%'].iloc[0]
            base_a_h = df[(df['model'] == 'xgboost') & (df['experiment'] == 'BASE_A_H')]['accuracy_%'].iloc[0]
            return base_a_h - base_h

        gain_center = aoa_gain(center)
        gain_ne     = aoa_gain(ne)

        assert gain_ne < gain_center, \
            f"AoA gain at NE BS ({gain_ne:.1f} pp) is not less than center BS ({gain_center:.1f} pp)"
        assert gain_ne < 15.0, \
            f"AoA gain at NE BS ({gain_ne:.1f} pp) is suspiciously high — expected <15 pp (known: ~7 pp)"

    def test_history_gain_similar_both_placements(self):
        """History gain (BASE_H - BASE, XGBoost) must be similar at both BS positions (within 8 pp).
        A large difference would indicate the configurations are not comparable."""
        center = _load(CENTER_CSV)
        ne     = _load(NE_CSV)

        def hist_gain(df):
            base   = df[(df['model'] == 'xgboost') & (df['experiment'] == 'BASE')  ]['accuracy_%'].iloc[0]
            base_h = df[(df['model'] == 'xgboost') & (df['experiment'] == 'BASE_H')]['accuracy_%'].iloc[0]
            return base_h - base

        gain_center = hist_gain(center)
        gain_ne     = hist_gain(ne)
        assert abs(gain_ne - gain_center) < 8.0, \
            f"History gain differs by {abs(gain_ne - gain_center):.1f} pp between placements — " \
            f"expected similar (~23 pp each)"


# ── AoA azimuth range sanity check against raw simulation data ────────────────

class TestSimulationDataSanity:

    def test_ne_bs_aoa_azimuth_is_in_sw_quadrant(self):
        """All AoA azimuth values for the NE-BS experiment must lie in ~195°–255°.
        If the wrong BS position was used, azimuths would span the full circle."""
        if not NE_DATA.exists():
            pytest.skip(f"NE-BS simulation data not found: {NE_DATA}")
        import scipy.io as sio
        candidates = sorted(NE_DATA.glob('user1_*.mat'))
        if not candidates:
            pytest.skip("user1_*.mat not found in NE-BS data dir")
        mat = sio.loadmat(str(candidates[0]), squeeze_me=True)
        aoa_az = mat['aoa_az']
        az_range = aoa_az.max() - aoa_az.min()
        assert az_range < 120.0, \
            f"NE-BS AoA azimuth range is {az_range:.1f}° — expected <120° (all UEs in SW quadrant). " \
            f"Was the wrong BS position used?"

    def test_center_bs_aoa_azimuth_spans_wide(self):
        """Center-BS AoA azimuths must span a wide angle (>180°) since BS is at grid center."""
        if not CENTER_DATA.exists():
            pytest.skip(f"Center-BS simulation data not found: {CENTER_DATA}")
        import scipy.io as sio
        candidates = sorted(CENTER_DATA.glob('user1_*.mat'))
        if not candidates:
            pytest.skip("user1_*.mat not found in center-BS data dir")
        mat = sio.loadmat(str(candidates[0]), squeeze_me=True)
        aoa_az = mat['aoa_az']
        az_range = aoa_az.max() - aoa_az.min()
        assert az_range > 180.0, \
            f"Center-BS AoA azimuth range is only {az_range:.1f}° — expected >180°"

    def test_sinr_in_physically_plausible_range(self):
        """SINR must be in a plausible range (−30 to +60 dB).
        The original SINR bug produced values around −50 to −70 dB."""
        if not CENTER_DATA.exists():
            pytest.skip(f"Center-BS simulation data not found: {CENTER_DATA}")
        import scipy.io as sio
        candidates = sorted(CENTER_DATA.glob('user1_*.mat'))
        if not candidates:
            pytest.skip("user1_*.mat not found")
        mat = sio.loadmat(str(candidates[0]), squeeze_me=True)
        sinr = mat['sinr']
        assert sinr.min() > -35.0, \
            f"SINR minimum is {sinr.min():.1f} dB — may indicate the 30 dB calibration bug"
        assert sinr.max() < 65.0, \
            f"SINR maximum is {sinr.max():.1f} dB — physically implausible"
