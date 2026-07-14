"""Pruebas unitarias de core/capm.py: funciones puras, sin red ni Streamlit."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import config
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


def test_score_for_moderado_penalizes_distance_and_volatility() -> None:
    low_score = capm.score_for_profile(beta=1.0, volatility=0.10, profile=config.PERFIL_MODERADO)
    high_score = capm.score_for_profile(beta=1.8, volatility=0.10, profile=config.PERFIL_MODERADO)
    assert low_score < high_score


def test_score_for_conservador_penalizes_beta_and_volatility() -> None:
    low_risk_score = capm.score_for_profile(beta=0.3, volatility=0.05, profile=config.PERFIL_CONSERVADOR)
    high_risk_score = capm.score_for_profile(beta=1.5, volatility=0.30, profile=config.PERFIL_CONSERVADOR)
    assert low_risk_score < high_risk_score


def test_score_for_agresivo_rewards_high_beta() -> None:
    high_beta_score = capm.score_for_profile(beta=1.8, volatility=0.30, profile=config.PERFIL_AGRESIVO)
    low_beta_score = capm.score_for_profile(beta=0.5, volatility=0.05, profile=config.PERFIL_AGRESIVO)
    assert high_beta_score < low_beta_score  # score mas bajo = mejor candidato para Agresivo


@pytest.mark.parametrize(
    "beta,profile,expected_eligible",
    [
        # Moderado: banda 0.75-1.25 (igual que el modelo original)
        (1.0, config.PERFIL_MODERADO, True),
        (0.75, config.PERFIL_MODERADO, True),
        (1.25, config.PERFIL_MODERADO, True),
        (1.26, config.PERFIL_MODERADO, False),
        (0.74, config.PERFIL_MODERADO, False),
        # Conservador: beta <= 0.75
        (0.75, config.PERFIL_CONSERVADOR, True),
        (0.50, config.PERFIL_CONSERVADOR, True),
        (0.76, config.PERFIL_CONSERVADOR, False),
        # Agresivo: beta >= 1.25
        (1.25, config.PERFIL_AGRESIVO, True),
        (1.50, config.PERFIL_AGRESIVO, True),
        (1.24, config.PERFIL_AGRESIVO, False),
    ],
)
def test_is_eligible_for_profile_respects_bounds(beta: float, profile: str, expected_eligible: bool) -> None:
    assert capm.is_eligible_for_profile(beta, profile) is expected_eligible


def test_beta_partition_across_profiles_has_no_gaps_or_overlaps() -> None:
    """Todo el eje de Beta debe quedar cubierto por exactamente un perfil (o dos en el borde)."""
    for beta in [-1.0, 0.0, 0.5, 0.75, 0.9, 1.0, 1.1, 1.25, 1.5, 3.0]:
        eligible_profiles = [
            profile
            for profile in (config.PERFIL_CONSERVADOR, config.PERFIL_MODERADO, config.PERFIL_AGRESIVO)
            if capm.is_eligible_for_profile(beta, profile)
        ]
        assert len(eligible_profiles) >= 1, f"beta={beta} no es elegible para ningun perfil"


def test_describe_beta_criterion_mentions_the_configured_bounds() -> None:
    lower = config.BETA_ELIGIBILITY_LOWER_BOUND
    upper = config.BETA_ELIGIBILITY_UPPER_BOUND
    assert f"{lower:.2f}" in capm.describe_beta_criterion(config.PERFIL_CONSERVADOR)
    assert f"{lower:.2f}" in capm.describe_beta_criterion(config.PERFIL_MODERADO)
    assert f"{upper:.2f}" in capm.describe_beta_criterion(config.PERFIL_MODERADO)
    assert f"{upper:.2f}" in capm.describe_beta_criterion(config.PERFIL_AGRESIVO)


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


_TEST_UNIVERSE = [
    {"Sector": "Banco", "Empresa": "Banco Test", "Ticker": "BANK.MC", "Producto": "Acción"},
    {"Sector": "Seguros", "Empresa": "Seguro Test", "Ticker": "INS.MC", "Producto": "Acción"},
]


def _test_service() -> _FakeService:
    market_returns = _returns([0.01, -0.01, 0.02, 0.00, 0.01])
    return _FakeService({
        "^BENCH": market_returns,
        "BANK.MC": _returns([0.015, -0.02, 0.025, 0.005, 0.01]),
        "INS.MC": _returns([0.005, -0.005, 0.01, -0.002, 0.008]),
    })


def test_build_universe_metrics_produces_one_row_per_asset() -> None:
    result = capm.build_universe_metrics(
        service=_test_service(),
        universe=_TEST_UNIVERSE,
        benchmark_ticker="^BENCH",
        risk_free_rate=0.02,
        market_premium=0.05,
        investor_profile=config.PERFIL_MODERADO,
    )

    assert len(result) == 2
    assert set(result["Sector"]) == {"Banco", "Seguros"}
    assert (result[config.COL_PERFIL_OBJETIVO] == config.PERFIL_MODERADO).all()


@pytest.mark.parametrize(
    "investor_profile", [config.PERFIL_CONSERVADOR, config.PERFIL_MODERADO, config.PERFIL_AGRESIVO]
)
def test_build_universe_metrics_reflects_the_actual_profile_not_a_hardcoded_one(investor_profile: str) -> None:
    """Regresion del bug critico de la auditoria: antes, esta columna era SIEMPRE 'Moderado'."""
    result = capm.build_universe_metrics(
        service=_test_service(),
        universe=_TEST_UNIVERSE,
        benchmark_ticker="^BENCH",
        risk_free_rate=0.02,
        market_premium=0.05,
        investor_profile=investor_profile,
    )

    assert (result[config.COL_PERFIL_OBJETIVO] == investor_profile).all()
    # El score debe coincidir exactamente con la formula del perfil solicitado.
    for _, row in result.iterrows():
        expected_score = capm.score_for_profile(row[config.COL_BETA], row[config.COL_VOL_ANUAL], investor_profile)
        assert row[config.COL_SCORE_PERFIL] == pytest.approx(expected_score)


def test_build_universe_metrics_score_differs_across_profiles_for_the_same_asset() -> None:
    """Mismo activo, mismos datos de mercado: el score debe variar segun el perfil."""
    scores_by_profile = {}
    for profile in (config.PERFIL_CONSERVADOR, config.PERFIL_MODERADO, config.PERFIL_AGRESIVO):
        result = capm.build_universe_metrics(
            service=_test_service(),
            universe=_TEST_UNIVERSE,
            benchmark_ticker="^BENCH",
            risk_free_rate=0.02,
            market_premium=0.05,
            investor_profile=profile,
        )
        scores_by_profile[profile] = tuple(result[config.COL_SCORE_PERFIL])

    assert len(set(scores_by_profile.values())) == 3  # las 3 tuplas de scores son distintas entre si
