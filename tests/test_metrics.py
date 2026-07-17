"""Pruebas unitarias de portfolio/metrics.py: funciones puras, sin red ni Streamlit."""
from __future__ import annotations

import numpy as np
import pytest

from portfolio import metrics


def test_portfolio_expected_return_is_weighted_average() -> None:
    weights = np.array([0.5, 0.5])
    expected_returns = np.array([0.10, 0.06])
    assert metrics.portfolio_expected_return(weights, expected_returns) == pytest.approx(0.08)


def test_portfolio_variance_matches_hand_calculation_for_uncorrelated_assets() -> None:
    weights = np.array([0.5, 0.5])
    covariance_matrix = np.array([[0.04, 0.0], [0.0, 0.01]])
    # w'Sigma w = 0.5^2*0.04 + 0.5^2*0.01 (covarianza cruzada = 0)
    expected_variance = (0.5**2 * 0.04) + (0.5**2 * 0.01)
    assert metrics.portfolio_variance(weights, covariance_matrix) == pytest.approx(expected_variance)


def test_portfolio_variance_matches_hand_calculation_with_correlation() -> None:
    weights = np.array([0.6, 0.4])
    covariance_matrix = np.array([[0.04, 0.01], [0.01, 0.02]])
    expected_variance = (
        (0.6**2 * 0.04) + (0.4**2 * 0.02) + (2 * 0.6 * 0.4 * 0.01)
    )
    assert metrics.portfolio_variance(weights, covariance_matrix) == pytest.approx(expected_variance)


def test_portfolio_volatility_is_sqrt_of_variance() -> None:
    weights = np.array([1.0, 0.0])
    covariance_matrix = np.array([[0.09, 0.0], [0.0, 0.04]])
    assert metrics.portfolio_volatility(weights, covariance_matrix) == pytest.approx(0.3)


def test_portfolio_beta_is_weighted_average() -> None:
    weights = np.array([0.25, 0.75])
    betas = np.array([1.2, 0.8])
    assert metrics.portfolio_beta(weights, betas) == pytest.approx(0.25 * 1.2 + 0.75 * 0.8)


def test_portfolio_sharpe_ratio_matches_formula() -> None:
    sharpe = metrics.portfolio_sharpe_ratio(expected_return=0.08, risk_free_rate=0.02, volatility=0.20)
    assert sharpe == pytest.approx(0.3)


def test_portfolio_sharpe_ratio_zero_volatility_does_not_raise() -> None:
    assert metrics.portfolio_sharpe_ratio(expected_return=0.08, risk_free_rate=0.02, volatility=0.0) == 0.0


# --- Validaciones ---


def test_validate_weights_sum_to_one_accepts_valid_weights() -> None:
    metrics.validate_weights_sum_to_one(np.array([0.3, 0.3, 0.4]))  # no debe lanzar


def test_validate_weights_sum_to_one_rejects_invalid_sum() -> None:
    with pytest.raises(ValueError, match="deben sumar 1.0"):
        metrics.validate_weights_sum_to_one(np.array([0.3, 0.3, 0.3]))


def test_validate_no_short_selling_accepts_non_negative_weights() -> None:
    metrics.validate_no_short_selling(np.array([0.0, 0.5, 0.5]))  # no debe lanzar


def test_validate_no_short_selling_rejects_negative_weight() -> None:
    with pytest.raises(ValueError, match="no short-selling"):
        metrics.validate_no_short_selling(np.array([-0.1, 0.6, 0.5]))


def test_validate_square_matrix_accepts_square() -> None:
    metrics.validate_square_matrix(np.eye(3))  # no debe lanzar


def test_validate_square_matrix_rejects_non_square() -> None:
    with pytest.raises(ValueError, match="debe ser cuadrada"):
        metrics.validate_square_matrix(np.ones((2, 3)))


def test_validate_dimensions_match_accepts_compatible_shapes() -> None:
    metrics.validate_dimensions_match(np.array([1.0, 2.0, 3.0]), np.eye(3))  # no debe lanzar


def test_validate_dimensions_match_rejects_incompatible_shapes() -> None:
    with pytest.raises(ValueError, match="Dimensiones incompatibles"):
        metrics.validate_dimensions_match(np.array([1.0, 2.0]), np.eye(3))


def test_validate_positive_semidefinite_covariance_accepts_valid_covariance() -> None:
    covariance_matrix = np.array([[0.04, 0.01], [0.01, 0.02]])
    metrics.validate_positive_semidefinite_covariance(covariance_matrix)  # no debe lanzar


def test_validate_positive_semidefinite_covariance_rejects_invalid_matrix() -> None:
    # Autovalores de [[1,2],[2,1]]: 3 y -1 -> no es semidefinida positiva.
    invalid_matrix = np.array([[1.0, 2.0], [2.0, 1.0]])
    with pytest.raises(ValueError, match="no es semidefinida positiva"):
        metrics.validate_positive_semidefinite_covariance(invalid_matrix)
