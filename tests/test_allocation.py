"""Pruebas exhaustivas de portfolio/allocation.py: funciones puras, sin red ni Streamlit.

Incluye pruebas unitarias con universos sintéticos pequeños (control total sobre
los números) y una prueba de integración completa optimizer + allocation con el
universo real de 13 activos (datos congelados, ver tests/fixtures_real_universe.py).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import config
from tests import fixtures_real_universe as real_universe
from portfolio.allocation import AllocationEntry, PortfolioAllocation, build_portfolio_allocation
from portfolio.constraints import get_constraints_for_profile
from portfolio.optimizer import OptimizationResult, optimize_max_sharpe


def _synthetic_universe_metrics() -> pd.DataFrame:
    """Universo sintético de 3 activos, con números fáciles de verificar a mano."""
    return pd.DataFrame({
        config.COL_TICKER: ["AAA", "BBB", "CCC"],
        config.COL_EMPRESA: ["Empresa A", "Empresa B", "Empresa C"],
        config.COL_CLASE_ACTIVO: [config.CLASE_RENTA_VARIABLE, config.CLASE_RENTA_FIJA, config.CLASE_MONETARIO],
        config.COL_BETA: [1.2, 0.1, 0.0],
        config.COL_CAPM: [0.08, 0.03, 0.02],
        config.COL_SHARPE: [0.30, 0.10, 0.05],
        config.COL_VOL_ANUAL: [0.20, 0.05, 0.01],
    })


def _synthetic_optimization_result(weights: np.ndarray) -> OptimizationResult:
    return OptimizationResult(
        weights=weights,
        expected_return=0.05,
        volatility=0.10,
        sharpe_ratio=0.30,
        converged=True,
        message="Optimization terminated successfully",
        iterations=10,
    )


# --- Capital: suma exacta, ningun euro desaparece ---


@pytest.mark.parametrize("total_capital", [10000.0, 10000.37, 999.99, 1234567.89, 100.01, 33.33])
def test_allocated_capital_sum_matches_total_capital_exactly(total_capital: float) -> None:
    universe_metrics = _synthetic_universe_metrics()
    weights = np.array([0.5, 0.3, 0.2])
    result = _synthetic_optimization_result(weights)

    allocation = build_portfolio_allocation(universe_metrics, result, total_capital)

    total_allocated = sum(entry.allocated_capital for entry in allocation.entries)
    # Comparacion a nivel de centimo: ver nota de redondeo en portfolio/allocation.py
    # sobre por que no se debe comparar con `==` directo en floats monetarios.
    assert round(total_allocated, 2) == round(total_capital, 2)


def test_no_cent_is_lost_even_with_many_small_weights() -> None:
    """Caso adverso para el redondeo: muchos pesos pequeños que individualmente
    redondean con perdida, para verificar que la correccion en la ultima posicion
    absorbe toda la desviacion acumulada."""
    universe_metrics = pd.DataFrame({
        config.COL_TICKER: [f"T{i}" for i in range(7)],
        config.COL_EMPRESA: [f"Empresa {i}" for i in range(7)],
        config.COL_CLASE_ACTIVO: [config.CLASE_RENTA_VARIABLE] * 7,
        config.COL_BETA: [1.0] * 7,
        config.COL_CAPM: [0.05] * 7,
        config.COL_SHARPE: [0.2] * 7,
        config.COL_VOL_ANUAL: [0.15] * 7,
    })
    weights = np.array([1 / 7] * 7)
    result = _synthetic_optimization_result(weights)

    allocation = build_portfolio_allocation(universe_metrics, result, total_capital=1000.00)

    total_allocated = sum(entry.allocated_capital for entry in allocation.entries)
    assert round(total_allocated, 2) == 1000.00
    assert all(entry.allocated_capital >= 0 for entry in allocation.entries)


def test_zero_weight_assets_still_appear_with_zero_capital() -> None:
    universe_metrics = _synthetic_universe_metrics()
    weights = np.array([1.0, 0.0, 0.0])
    result = _synthetic_optimization_result(weights)

    allocation = build_portfolio_allocation(universe_metrics, result, total_capital=10000.0)

    assert len(allocation.entries) == 3  # incluye los activos con peso 0
    zero_weight_entries = [e for e in allocation.entries if e.weight == 0.0]
    assert len(zero_weight_entries) == 2
    assert all(e.allocated_capital == 0.0 for e in zero_weight_entries)


# --- Porcentajes por clase de activo ---


def test_class_percentages_match_manual_calculation() -> None:
    universe_metrics = _synthetic_universe_metrics()  # RV, RF, Monetario, en ese orden
    weights = np.array([0.5, 0.3, 0.2])
    result = _synthetic_optimization_result(weights)

    allocation = build_portfolio_allocation(universe_metrics, result, total_capital=10000.0)

    assert allocation.equity_percentage == pytest.approx(0.5)
    assert allocation.fixed_income_percentage == pytest.approx(0.3)
    assert allocation.money_market_percentage == pytest.approx(0.2)


def test_class_percentages_sum_to_one() -> None:
    universe_metrics = _synthetic_universe_metrics()
    weights = np.array([0.6, 0.25, 0.15])
    result = _synthetic_optimization_result(weights)

    allocation = build_portfolio_allocation(universe_metrics, result, total_capital=5000.0)

    total_percentage = (
        allocation.equity_percentage + allocation.fixed_income_percentage + allocation.money_market_percentage
    )
    assert total_percentage == pytest.approx(1.0)


# --- Metricas de cartera: consistencia ---


def test_portfolio_level_metrics_are_reused_from_optimization_result_without_recomputation() -> None:
    """allocation.py NO debe recalcular retorno/volatilidad/Sharpe de cartera: debe
    reutilizar los ya calculados por el optimizador (evita duplicar la formula y
    cualquier riesgo de que diverjan)."""
    universe_metrics = _synthetic_universe_metrics()
    weights = np.array([0.5, 0.3, 0.2])
    result = _synthetic_optimization_result(weights)

    allocation = build_portfolio_allocation(universe_metrics, result, total_capital=10000.0)

    assert allocation.expected_return == result.expected_return
    assert allocation.volatility == result.volatility
    assert allocation.sharpe_ratio == result.sharpe_ratio


def test_portfolio_beta_matches_manual_weighted_average() -> None:
    universe_metrics = _synthetic_universe_metrics()  # betas: 1.2, 0.1, 0.0
    weights = np.array([0.5, 0.3, 0.2])
    result = _synthetic_optimization_result(weights)

    allocation = build_portfolio_allocation(universe_metrics, result, total_capital=10000.0)

    expected_beta = 0.5 * 1.2 + 0.3 * 0.1 + 0.2 * 0.0
    assert allocation.beta == pytest.approx(expected_beta)


def test_allocation_entry_fields_match_universe_metrics_row() -> None:
    universe_metrics = _synthetic_universe_metrics()
    weights = np.array([0.5, 0.3, 0.2])
    result = _synthetic_optimization_result(weights)

    allocation = build_portfolio_allocation(universe_metrics, result, total_capital=10000.0)

    first_entry = allocation.entries[0]
    assert first_entry.ticker == "AAA"
    assert first_entry.name == "Empresa A"
    assert first_entry.asset_class == config.CLASE_RENTA_VARIABLE
    assert first_entry.weight == pytest.approx(0.5)
    assert first_entry.allocated_capital == pytest.approx(5000.0)
    assert first_entry.expected_return == pytest.approx(0.08)
    assert first_entry.beta == pytest.approx(1.2)
    assert first_entry.sharpe_ratio == pytest.approx(0.30)
    assert first_entry.volatility == pytest.approx(0.20)


# --- Validacion de entradas ---


def test_dimension_mismatch_raises() -> None:
    universe_metrics = _synthetic_universe_metrics()
    result = _synthetic_optimization_result(np.array([0.5, 0.5]))  # solo 2 pesos, universo tiene 3
    with pytest.raises(ValueError, match="Dimensiones incompatibles"):
        build_portfolio_allocation(universe_metrics, result, total_capital=10000.0)


@pytest.mark.parametrize("total_capital", [0.0, -100.0])
def test_non_positive_capital_raises(total_capital: float) -> None:
    universe_metrics = _synthetic_universe_metrics()
    result = _synthetic_optimization_result(np.array([0.5, 0.3, 0.2]))
    with pytest.raises(ValueError, match="positivo"):
        build_portfolio_allocation(universe_metrics, result, total_capital=total_capital)


def test_allocation_entry_is_immutable() -> None:
    entry = AllocationEntry(
        ticker="AAA", name="Empresa A", asset_class=config.CLASE_RENTA_VARIABLE, weight=0.5,
        allocated_capital=5000.0, expected_return=0.08, beta=1.2, sharpe_ratio=0.3, volatility=0.2,
    )
    with pytest.raises(AttributeError):
        entry.weight = 0.9  # type: ignore[misc]


def test_portfolio_allocation_is_immutable() -> None:
    allocation = PortfolioAllocation(
        entries=(), total_capital=1000.0, expected_return=0.05, volatility=0.1, beta=1.0,
        sharpe_ratio=0.3, fixed_income_percentage=0.3, equity_percentage=0.5, money_market_percentage=0.2,
    )
    with pytest.raises(AttributeError):
        allocation.total_capital = 2000.0  # type: ignore[misc]


# --- Integracion optimizer + allocation, universo real completo (13 activos) ---


@pytest.mark.parametrize(
    "profile", [config.PERFIL_CONSERVADOR, config.PERFIL_MODERADO, config.PERFIL_AGRESIVO]
)
def test_full_integration_optimizer_and_allocation_with_real_universe(profile: str) -> None:
    profile_constraints = get_constraints_for_profile(profile)
    optimization_result = optimize_max_sharpe(
        real_universe.EXPECTED_RETURNS,
        real_universe.COVARIANCE_MATRIX,
        real_universe.RISK_FREE_RATE,
        asset_classes=real_universe.ASSET_CLASSES,
        profile_constraints=profile_constraints,
    )
    universe_metrics = real_universe.build_universe_metrics(investor_profile=profile)

    allocation = build_portfolio_allocation(universe_metrics, optimization_result, total_capital=25000.0)

    assert len(allocation.entries) == len(real_universe.TICKERS)
    assert round(sum(e.allocated_capital for e in allocation.entries), 2) == 25000.0
    assert all(entry.allocated_capital >= 0 for entry in allocation.entries)

    total_percentage = (
        allocation.equity_percentage + allocation.fixed_income_percentage + allocation.money_market_percentage
    )
    assert total_percentage == pytest.approx(1.0)
    assert allocation.fixed_income_percentage + allocation.money_market_percentage >= (
        profile_constraints.min_fixed_income_weight - 1e-4
    )

    # Ningun peso individual supera el tope del perfil, ni en fraccion ni en capital.
    max_allowed_capital = 25000.0 * profile_constraints.max_weight_per_asset
    for entry in allocation.entries:
        assert entry.weight <= profile_constraints.max_weight_per_asset + 1e-6
        assert entry.allocated_capital <= max_allowed_capital + 0.01  # +1 centimo de margen de redondeo
