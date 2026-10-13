"""
Metric audit (instructor request M1/M2, 2026-10-12): known predictions must give
known accuracy and MAE, and the two metrics must satisfy
    MAE = (1 - accuracy) x mean distance of the wrong predictions
because every correct prediction contributes exactly 0 m.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines.multi_user_pipeline import compute_mae, evaluate_split  # noqa: E402

SPACING = 2.0


@pytest.fixture
def lookup():
    """5 x 5 grid, ids 1..25, row-major, 2 m spacing."""
    return {i + 1: ((i % 5) * SPACING, (i // 5) * SPACING) for i in range(25)}


def test_all_correct_is_zero(lookup):
    y = np.arange(1, 26)
    r = evaluate_split(y, y, lookup, spacing=SPACING)
    assert r['accuracy'] == 100.0 and r['mae'] == 0.0 and r['mpe'] == 0.0


def test_all_one_cell_to_the_right_is_one_spacing(lookup):
    true = np.array([1, 2, 3, 6, 7])
    pred = true + 1                       # neighbouring cell, 2 m away
    r = evaluate_split(true, pred, lookup, spacing=SPACING)
    assert r['accuracy'] == 0.0
    assert r['mae'] == pytest.approx(2.0)
    assert r['mpe'] == pytest.approx(1.0)


def test_diagonal_neighbour_is_sqrt2_spacing(lookup):
    r = evaluate_split(np.array([1]), np.array([7]), lookup, spacing=SPACING)
    assert r['mae'] == pytest.approx(2.0 * np.sqrt(2))


def test_corner_to_corner_is_the_grid_diagonal(lookup):
    assert compute_mae(np.array([1]), np.array([25]), lookup) == pytest.approx(8.0 * np.sqrt(2))


def test_mae_is_mean_of_the_distances_not_of_the_squares(lookup):
    # one sample 2 m off, one sample 6 m off -> mean 4 m (RMSE would be sqrt(20) = 4.47)
    assert compute_mae(np.array([1, 1]), np.array([2, 4]), lookup) == pytest.approx(4.0)


def test_mae_identity_accuracy_times_wrong_distance(lookup):
    """80 % exact and the rest 6 m off must give an MAE of 1.2 m, never 20-30 m."""
    rng = np.random.RandomState(0)
    true = rng.randint(1, 23, size=1000)
    pred = true.copy()
    wrong = rng.permutation(1000)[:200]   # 20 % wrong
    pred[wrong] = true[wrong] + 3         # 3 cells to the right = 6 m, same row for ids with column < 3
    keep = ((true[wrong] - 1) % 5) < 2    # keep only cases that stay in the row
    pred[wrong[~keep]] = true[wrong[~keep]]
    r = evaluate_split(true, pred, lookup, spacing=SPACING)
    wrong_mask = true != pred
    mean_wrong = compute_mae(true[wrong_mask], pred[wrong_mask], lookup)
    assert mean_wrong == pytest.approx(6.0)
    assert r['mae'] == pytest.approx((1 - r['accuracy'] / 100) * mean_wrong)
    assert r['mae'] < 2.0


def test_mae_cannot_exceed_the_grid_diagonal(lookup):
    rng = np.random.RandomState(1)
    t, p = rng.randint(1, 26, 500), rng.randint(1, 26, 500)
    assert compute_mae(t, p, lookup) <= 8.0 * np.sqrt(2) + 1e-9
