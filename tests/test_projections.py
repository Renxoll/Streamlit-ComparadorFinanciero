"""Pruebas unitarias de core/projections.py: funciones puras, sin red ni Streamlit.

Incluye la verificación matemática de la Subfase 4.3/4.4: `project_portfolio_by_asset`
coincide EXACTAMENTE con `project_compound_growth` (tasa blended) en el año 1, y lo
supera (nunca lo iguala por debajo) para años posteriores, tal como predice la
desigualdad de Jensen para una función convexa `x -> x^t` con `t >= 1`.
"""
from __future__ import annotations

import pytest

from core.projections import blended_annual_rate, project_compound_growth, project_portfolio_by_asset


def test_project_compound_growth_returns_years_plus_one_values() -> None:
    result = project_compound_growth(1000.0, 0.05, 3)
    assert len(result) == 4
    assert result[0] == pytest.approx(1000.0)
    assert result[3] == pytest.approx(1000.0 * 1.05**3)


def test_blended_annual_rate_is_weighted_average() -> None:
    assert blended_annual_rate(0.08, 0.5, 0.02, 0.5) == pytest.approx(0.05)


# --- project_portfolio_by_asset ---


def test_single_entry_matches_project_compound_growth() -> None:
    """Con una unica posicion, ambos metodos deben coincidir en todos los años."""
    entries = [(1000.0, 0.05)]
    by_asset = project_portfolio_by_asset(entries, 10)
    blended = project_compound_growth(1000.0, 0.05, 10)
    assert by_asset == pytest.approx(blended)


def test_multiple_entries_match_blended_exactly_at_year_one() -> None:
    """Identidad matematica (Subfase 4.3): en el año 1, Σwᵢ(1+rᵢ) = 1 + Σwᵢrᵢ,
    es decir, ambos metodos coinciden exactamente."""
    entries = [(600.0, 0.08), (400.0, 0.02)]
    total_capital = sum(capital for capital, _ in entries)
    blended_rate = sum(capital * rate for capital, rate in entries) / total_capital

    by_asset = project_portfolio_by_asset(entries, 1)
    blended = project_compound_growth(total_capital, blended_rate, 1)

    assert by_asset[1] == pytest.approx(blended[1])


def test_year_zero_equals_total_initial_capital() -> None:
    entries = [(600.0, 0.08), (400.0, 0.02)]
    result = project_portfolio_by_asset(entries, 5)
    assert result[0] == pytest.approx(1000.0)


@pytest.mark.parametrize("years", [2, 5, 10, 20, 30])
def test_by_asset_never_falls_below_blended_for_years_beyond_one(years: int) -> None:
    """Desigualdad de Jensen: Σwᵢ(1+rᵢ)^t >= (1+r_blended)^t para t >= 1, con
    igualdad solo si t=1 o todos los rᵢ son iguales. Aqui rᵢ difieren, por lo que
    la desigualdad debe ser estricta para years > 1."""
    entries = [(600.0, 0.08), (400.0, 0.02)]
    total_capital = sum(capital for capital, _ in entries)
    blended_rate = sum(capital * rate for capital, rate in entries) / total_capital

    by_asset_value = project_portfolio_by_asset(entries, years)[-1]
    blended_value = project_compound_growth(total_capital, blended_rate, years)[-1]

    assert by_asset_value > blended_value


def test_empty_entries_returns_zeros() -> None:
    result = project_portfolio_by_asset([], 5)
    assert result == [0.0] * 6


def test_returns_years_plus_one_values() -> None:
    entries = [(500.0, 0.03), (500.0, 0.06)]
    result = project_portfolio_by_asset(entries, 7)
    assert len(result) == 8


def test_deviation_grows_with_dispersion_of_rates() -> None:
    """A mayor dispersion de tasas entre posiciones (mismo capital, misma tasa media),
    mayor debe ser la desviacion frente al metodo blended, para el mismo horizonte."""
    years = 20
    low_dispersion = [(500.0, 0.045), (500.0, 0.055)]  # media 5%, dispersion baja
    high_dispersion = [(500.0, 0.01), (500.0, 0.09)]  # media 5%, dispersion alta

    blended_value = project_compound_growth(1000.0, 0.05, years)[-1]
    low_dispersion_value = project_portfolio_by_asset(low_dispersion, years)[-1]
    high_dispersion_value = project_portfolio_by_asset(high_dispersion, years)[-1]

    low_deviation = low_dispersion_value - blended_value
    high_deviation = high_dispersion_value - blended_value

    assert 0 < low_deviation < high_deviation
