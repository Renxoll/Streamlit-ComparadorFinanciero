"""Pruebas unitarias de core/capm.py: funciones puras, sin red ni Streamlit."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core import capm


def _returns(values: list[float]) -> pd.Series:
    index = pd.date_range("2024-01-01", periods=len(values), freq="D")
    return pd.Series(values, index=index)


def test_compute_beta_of_market_against_itself_is_one() -> None:
    market = _returns([0.01, -0.02, 0.03, 0.00, 0.015])
    aligned = capm.align_returns(market, market)
    assert capm.compute_beta(aligned) == pytest.approx(1.0)


def test_compute_beta_zero_market_variance_defaults_to_one() -> None:
    asset = _returns([0.01, -0.02, 0.03, 0.00, 0.015])
    flat_market = _returns([0.0, 0.0, 0.0, 0.0, 0.0])
    aligned = capm.align_returns(asset, flat_market)
    assert capm.compute_beta(aligned) == 1.0


def test_align_returns_keeps_only_common_dates() -> None:
    asset = pd.Series([0.01, 0.02, 0.03], index=pd.date_range("2024-01-01", periods=3, freq="D"))
    market = pd.Series([0.01, 0.02], index=pd.date_range("2024-01-01", periods=2, freq="D"))
    aligned = capm.align_returns(asset, market)
    assert len(aligned) == 2
    assert list(aligned.columns) == ["asset", "market"]


def test_annualized_volatility_scales_by_sqrt_trading_days() -> None:
    daily = _returns([0.01, -0.01, 0.01, -0.01, 0.01])
    expected = daily.std() * np.sqrt(capm.TRADING_DAYS_PER_YEAR)
    assert capm.annualized_volatility(daily) == pytest.approx(expected)


def test_capm_expected_return_formula() -> None:
    result = capm.capm_expected_return(beta=1.2, risk_free_rate=0.02, market_premium=0.05)
    assert result == pytest.approx(0.02 + 1.2 * 0.05)


def test_sharpe_ratio_formula() -> None:
    assert capm.sharpe_ratio(expected_return=0.08, risk_free_rate=0.02, volatility=0.20) == pytest.approx(0.3)


def test_sharpe_ratio_zero_volatility_does_not_raise() -> None:
    assert capm.sharpe_ratio(expected_return=0.08, risk_free_rate=0.02, volatility=0.0) == 0.0


def test_score_moderate_profile_penalizes_distance_and_volatility() -> None:
    low_score = capm.score_moderate_profile(beta=1.0, volatility=0.10)
    high_score = capm.score_moderate_profile(beta=1.8, volatility=0.10)
    assert low_score < high_score


@pytest.mark.parametrize(
    "beta,expected_eligible",
    [(1.0, True), (0.75, True), (1.25, True), (1.26, False), (0.74, False)],
)
def test_is_eligible_moderate_profile_respects_bounds(beta: float, expected_eligible: bool) -> None:
    assert capm.is_eligible_moderate_profile(beta) is expected_eligible


def test_annualized_covariance_is_symmetric() -> None:
    a = _returns([0.01, 0.02, -0.01, 0.03, 0.00])
    b = _returns([0.02, 0.01, 0.00, 0.02, -0.01])
    assert capm.annualized_covariance(a, b) == pytest.approx(capm.annualized_covariance(b, a))


def test_combined_portfolio_volatility_matches_two_asset_formula() -> None:
    volatility = capm.combined_portfolio_volatility(
        vol_a=0.20, weight_a=0.5, vol_b=0.15, weight_b=0.5, covariance_ab=0.01
    )
    expected = np.sqrt((0.5**2 * 0.20**2) + (0.5**2 * 0.15**2) + (2 * 0.5 * 0.5 * 0.01))
    assert volatility == pytest.approx(expected)


class _FakeService:
    """Doble de prueba de MarketDataService: devuelve series fijas sin red."""

    def __init__(self, returns_by_ticker: dict[str, pd.Series]) -> None:
        self._returns_by_ticker = returns_by_ticker

    def get_returns(self, ticker: str, period: str) -> pd.Series:
        return self._returns_by_ticker[ticker]


def test_build_universe_metrics_produces_one_row_per_asset() -> None:
    universe = [
        {"Sector": "Banco", "Empresa": "Banco Test", "Ticker": "BANK.MC", "Producto": "Acción"},
        {"Sector": "Seguros", "Empresa": "Seguro Test", "Ticker": "INS.MC", "Producto": "Acción"},
    ]
    market_returns = _returns([0.01, -0.01, 0.02, 0.00, 0.01])
    service = _FakeService({
        "^BENCH": market_returns,
        "BANK.MC": _returns([0.015, -0.02, 0.025, 0.005, 0.01]),
        "INS.MC": _returns([0.005, -0.005, 0.01, -0.002, 0.008]),
    })

    result = capm.build_universe_metrics(
        service=service,
        universe=universe,
        benchmark_ticker="^BENCH",
        risk_free_rate=0.02,
        market_premium=0.05,
    )

    assert len(result) == 2
    assert set(result["Sector"]) == {"Banco", "Seguros"}
    assert (result["Perfil objetivo"] == "Moderado").all()
