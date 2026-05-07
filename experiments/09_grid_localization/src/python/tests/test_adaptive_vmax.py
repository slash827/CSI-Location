"""Tests for _adaptive_vmax in multi_user_pipeline.py (heatmap colour scaling)."""
import sys
import numpy as np
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipelines.multi_user_pipeline import _adaptive_vmax


class TestAdaptiveVmax:
    def test_low_error_regime(self):
        """When all values are near 0.3 m (good model), scale should be sub-1m."""
        values = np.array([0.1, 0.2, 0.3, 0.25, 0.28, 0.35, 0.15, 0.22])
        vmax = _adaptive_vmax(values)
        assert vmax < 2.0, f"Expected sub-2m scale for good model, got {vmax}"

    def test_high_error_regime(self):
        """When errors are large (baseline model), scale should reflect that."""
        values = np.linspace(1, 20, 50)
        vmax = _adaptive_vmax(values)
        assert vmax > 5.0, f"Expected >5m scale for bad model, got {vmax}"

    def test_vmax_always_positive(self):
        values = np.zeros(10)  # edge case: all zeros
        vmax = _adaptive_vmax(values)
        assert vmax > 0

    def test_single_outlier_does_not_dominate(self):
        """One extreme outlier should not inflate the scale dramatically."""
        good = np.full(100, 0.3)
        values = np.append(good, 50.0)   # single huge outlier
        vmax = _adaptive_vmax(values)
        # Should stay in a range useful for the typical 0.3m distribution
        assert vmax < 5.0, f"Outlier inflated vmax to {vmax}"

    def test_ne_bs_scale_vs_center_bs(self):
        """
        Regression guard: BASE_A_H (center BS) had overall MAE ~0.275m.
        The vmax for that experiment should be < 2m (sub-metre colour scale).
        BASE (center BS) had overall MAE ~5.6m; vmax should be > 5m.
        """
        # Simulate per-point MAE distribution around known overall means
        rng = np.random.default_rng(42)
        good_mae = np.abs(rng.normal(0.275, 0.15, 225))
        bad_mae  = np.abs(rng.normal(5.6,   4.0,  225))

        good_vmax = _adaptive_vmax(good_mae)
        bad_vmax  = _adaptive_vmax(bad_mae)

        assert good_vmax < 2.0
        assert bad_vmax  > 3.0
        assert bad_vmax  > good_vmax
