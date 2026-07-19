"""Pruebas exhaustivas de portfolio/optimizer.py: funciones puras, sin red ni Streamlit.

Incluye un caso analítico verificable a mano (2 activos no correlacionados,
solución de forma cerrada conocida) y un caso de integración con datos reales
del universo de 11 activos (congelados como fixture: la descarga real se hizo
una única vez para construir este archivo, no se repite en cada ejecución de
la suite, para mantenerla rápida y determinista).
"""
from __future__ import annotations

import numpy as np
import pytest

import config
from tests import fixtures_real_universe as real_universe
from portfolio import constraints as constraints_module
from portfolio import metrics
from portfolio.constraints import get_constraints_for_profile
from portfolio.optimizer import optimize_max_sharpe

# --- Caso analítico verificable a mano ---
#
# 2 activos SIN correlación (covarianza cruzada = 0). Para este caso particular,
# la cartera tangente (máximo Sharpe) sin restricción activa tiene solución cerrada:
#   w_i ∝ (mu_i - Rf) / sigma_i^2         (Sigma^-1 (mu - Rf*1), diagonal por no-correlacion)
# normalizada para que sum(w) = 1. Con Rf=0.02, activo A: mu=0.10, sigma=0.20;
# activo B: mu=0.06, sigma=0.10:
#   w_A_raw = (0.10-0.02)/0.20^2 = 2.0   w_B_raw = (0.06-0.02)/0.10^2 = 4.0
#   w_A = 2/6 = 0.3333...                 w_B = 4/6 = 0.6667...
# Ambos pesos ya son >= 0, así que la restricción de no venta en corto no está
# activa y la solución con restricciones coincide con la solución cerrada.
_ANALYTIC_RISK_FREE_RATE = 0.02
_ANALYTIC_EXPECTED_RETURNS = np.array([0.10, 0.06])
_ANALYTIC_COVARIANCE = np.array([[0.20**2, 0.0], [0.0, 0.10**2]])
_ANALYTIC_EXPECTED_WEIGHTS = np.array([1 / 3, 2 / 3])


def test_optimizer_matches_closed_form_solution_for_uncorrelated_assets() -> None:
    result = optimize_max_sharpe(_ANALYTIC_EXPECTED_RETURNS, _ANALYTIC_COVARIANCE, _ANALYTIC_RISK_FREE_RATE)

    assert result.converged is True
    np.testing.assert_allclose(result.weights, _ANALYTIC_EXPECTED_WEIGHTS, atol=1e-4)

    expected_return = 1 / 3 * 0.10 + 2 / 3 * 0.06
    expected_volatility = np.sqrt((1 / 3) ** 2 * 0.04 + (2 / 3) ** 2 * 0.01)
    expected_sharpe = (expected_return - _ANALYTIC_RISK_FREE_RATE) / expected_volatility

    assert result.expected_return == pytest.approx(expected_return, abs=1e-4)
    assert result.volatility == pytest.approx(expected_volatility, abs=1e-4)
    assert result.sharpe_ratio == pytest.approx(expected_sharpe, abs=1e-4)


# --- Propiedades generales que debe cumplir cualquier solución del optimizador ---


def test_optimizer_weights_sum_to_one() -> None:
    result = optimize_max_sharpe(_ANALYTIC_EXPECTED_RETURNS, _ANALYTIC_COVARIANCE, _ANALYTIC_RISK_FREE_RATE)
    metrics.validate_weights_sum_to_one(result.weights)  # no debe lanzar


def test_optimizer_never_returns_negative_weights() -> None:
    result = optimize_max_sharpe(_ANALYTIC_EXPECTED_RETURNS, _ANALYTIC_COVARIANCE, _ANALYTIC_RISK_FREE_RATE)
    metrics.validate_no_short_selling(result.weights)  # no debe lanzar
    assert (result.weights >= 0.0).all()


def test_optimizer_converges_for_a_well_conditioned_problem() -> None:
    result = optimize_max_sharpe(_ANALYTIC_EXPECTED_RETURNS, _ANALYTIC_COVARIANCE, _ANALYTIC_RISK_FREE_RATE)
    assert result.converged is True
    assert result.iterations > 0


def test_optimizer_result_beats_a_naive_equal_weight_portfolio() -> None:
    """La cartera optima debe tener, como minimo, el mismo Sharpe que 1/n (nunca peor)."""
    result = optimize_max_sharpe(_ANALYTIC_EXPECTED_RETURNS, _ANALYTIC_COVARIANCE, _ANALYTIC_RISK_FREE_RATE)

    equal_weights = np.full(2, 0.5)
    equal_weight_return = metrics.portfolio_expected_return(equal_weights, _ANALYTIC_EXPECTED_RETURNS)
    equal_weight_volatility = metrics.portfolio_volatility(equal_weights, _ANALYTIC_COVARIANCE)
    equal_weight_sharpe = metrics.portfolio_sharpe_ratio(
        equal_weight_return, _ANALYTIC_RISK_FREE_RATE, equal_weight_volatility
    )

    assert result.sharpe_ratio >= equal_weight_sharpe


# --- Validacion de entradas ---


def test_optimizer_raises_on_dimension_mismatch() -> None:
    with pytest.raises(ValueError, match="Dimensiones incompatibles"):
        optimize_max_sharpe(np.array([0.1, 0.2, 0.3]), _ANALYTIC_COVARIANCE, _ANALYTIC_RISK_FREE_RATE)


def test_optimizer_raises_on_non_positive_semidefinite_covariance() -> None:
    invalid_covariance = np.array([[1.0, 2.0], [2.0, 1.0]])  # autovalores 3 y -1
    with pytest.raises(ValueError, match="no es semidefinida positiva"):
        optimize_max_sharpe(_ANALYTIC_EXPECTED_RETURNS, invalid_covariance, _ANALYTIC_RISK_FREE_RATE)


# --- Integracion con el universo real (11 activos): datos congelados, sin red ---
#
# `expected_returns` y `covariance_matrix` son la salida REAL de
# `core.capm.build_universe_metrics` + `portfolio.covariance.build_annualized_covariance_matrix`
# sobre `config.UNIVERSO_ACTIVOS` (Rf=0.02, prima=0.055, periodo=5y), capturada una unica vez.
# Se congela como constante para que la suite de tests siga siendo rapida y determinista
# (sin ella, cada ejecucion de pytest dependeria de la disponibilidad de Yahoo Finance).
_REAL_UNIVERSE_TICKERS = [
    "SAN.MC", "BNP.PA", "INGA.AS", "ALV.DE", "CS.PA", "MAP.MC", "G.MI",
    "EUNL.DE", "EXW1.DE", "AGGH.MI", "XEON.DE",
]
_REAL_UNIVERSE_EXPECTED_RETURNS = np.array([
    0.08861395, 0.08246623, 0.08002628, 0.06297696, 0.06410116, 0.05429772,
    0.05695851, 0.05381993, 0.07353916, 0.02152072, 0.02003974,
])
_REAL_UNIVERSE_COVARIANCE = np.array([
    [9.54905946e-02, 6.39565258e-02, 6.11361506e-02, 3.83306413e-02, 3.99974587e-02, 3.75851033e-02, 3.27814214e-02, 2.13984438e-02, 3.84587554e-02, -1.76485934e-04, 2.71015214e-05],
    [6.39565258e-02, 8.11780038e-02, 6.25284944e-02, 3.55799697e-02, 4.05214293e-02, 3.16081975e-02, 3.14797948e-02, 1.86545610e-02, 3.50864274e-02, -4.21721106e-04, 2.27259537e-05],
    [6.11361506e-02, 6.25284944e-02, 7.78262728e-02, 3.41968918e-02, 3.82307106e-02, 3.06502576e-02, 2.89114860e-02, 1.84822803e-02, 3.36697759e-02, -1.39978543e-03, 2.13199496e-05],
    [3.83306413e-02, 3.55799697e-02, 3.41968918e-02, 3.85072976e-02, 3.14533741e-02, 2.41965527e-02, 2.57353893e-02, 1.37089656e-02, 2.42588348e-02, 1.18071144e-04, 2.62609195e-05],
    [3.99974587e-02, 4.05214293e-02, 3.82307106e-02, 3.14533741e-02, 4.48879792e-02, 2.61190728e-02, 2.71537740e-02, 1.41465058e-02, 2.51264660e-02, -1.54840201e-04, 2.70937747e-05],
    [3.75851033e-02, 3.16081975e-02, 3.06502576e-02, 2.41965527e-02, 2.61190728e-02, 4.42119137e-02, 2.22394640e-02, 1.11838364e-02, 1.90731085e-02, -1.21007370e-04, 7.93213242e-06],
    [3.27814214e-02, 3.14797948e-02, 2.89114860e-02, 2.57353893e-02, 2.71537740e-02, 2.22394640e-02, 3.75620404e-02, 1.25135010e-02, 2.07550884e-02, 6.32902363e-05, 1.80065150e-05],
    [2.13984438e-02, 1.86545610e-02, 1.84822803e-02, 1.37089656e-02, 1.41465058e-02, 1.11838364e-02, 1.25135010e-02, 2.01688873e-02, 1.88652551e-02, 5.05171160e-04, -2.16431387e-06],
    [3.84587554e-02, 3.50864274e-02, 3.36697759e-02, 2.42588348e-02, 2.51264660e-02, 1.90731085e-02, 2.07550884e-02, 1.88652551e-02, 3.01354967e-02, 8.48000151e-04, 1.87611195e-05],
    [-1.76485934e-04, -4.21721106e-04, -1.39978543e-03, 1.18071144e-04, -1.54840201e-04, -1.21007370e-04, 6.32902363e-05, 5.05171160e-04, 8.48000151e-04, 2.19586181e-03, 1.81127330e-06],
    [2.71015214e-05, 2.27259537e-05, 2.13199496e-05, 2.62609195e-05, 2.70937747e-05, 7.93213242e-06, 1.80065150e-05, -2.16431387e-06, 1.87611195e-05, 1.81127330e-06, 6.47865390e-06],
])
_REAL_UNIVERSE_RISK_FREE_RATE = 0.02


def test_optimizer_converges_and_returns_valid_weights_for_the_real_universe() -> None:
    result = optimize_max_sharpe(
        _REAL_UNIVERSE_EXPECTED_RETURNS, _REAL_UNIVERSE_COVARIANCE, _REAL_UNIVERSE_RISK_FREE_RATE
    )

    assert result.converged is True
    assert len(result.weights) == len(_REAL_UNIVERSE_TICKERS)
    metrics.validate_weights_sum_to_one(result.weights)
    metrics.validate_no_short_selling(result.weights)
    assert result.sharpe_ratio > 0


def test_optimizer_on_real_universe_concentrates_without_a_max_weight_constraint() -> None:
    """Documenta el efecto esperado en esta subfase (sin tope por activo todavia):
    el optimizador de Markowitz sin restriccion de concentracion tiende a
    concentrarse en pocos activos (maximizacion de errores de Michaud, 1989),
    exactamente el comportamiento que la Subfase 3.3 corrige con un peso maximo
    por activo. Este test deja constancia objetiva del problema antes de la
    correccion, igual que se hizo con el sesgo del perfil inversor en la Fase 2.
    """
    result = optimize_max_sharpe(
        _REAL_UNIVERSE_EXPECTED_RETURNS, _REAL_UNIVERSE_COVARIANCE, _REAL_UNIVERSE_RISK_FREE_RATE
    )
    largest_weight = result.weights.max()
    assert largest_weight > 0.5  # un unico activo concentra mas de la mitad de la cartera


# --- Subfase 3.3: restricciones por perfil ---
#
# Mismo orden de tickers que en `_REAL_UNIVERSE_TICKERS`: 9 activos de renta
# variable (7 acciones + 2 ETFs de renta variable), 1 ETF de renta fija, 1 ETF
# monetario (ver config.UNIVERSO_ACTIVOS).
_REAL_UNIVERSE_ASSET_CLASSES = np.array(
    [config.CLASE_RENTA_VARIABLE] * 9 + [config.CLASE_RENTA_FIJA, config.CLASE_MONETARIO]
)


def test_optimizer_without_profile_constraints_is_unchanged_from_subfase_3_2() -> None:
    """Retrocompatibilidad explicita: no pasar profile_constraints da el mismo resultado
    que en la Subfase 3.2 (mismo caso analitico, misma solucion cerrada esperada)."""
    result = optimize_max_sharpe(_ANALYTIC_EXPECTED_RETURNS, _ANALYTIC_COVARIANCE, _ANALYTIC_RISK_FREE_RATE)
    np.testing.assert_allclose(result.weights, _ANALYTIC_EXPECTED_WEIGHTS, atol=1e-4)


def test_optimizer_with_profile_constraints_requires_asset_classes() -> None:
    profile_constraints = get_constraints_for_profile(config.PERFIL_MODERADO)
    with pytest.raises(ValueError, match="asset_classes"):
        optimize_max_sharpe(
            _REAL_UNIVERSE_EXPECTED_RETURNS,
            _REAL_UNIVERSE_COVARIANCE,
            _REAL_UNIVERSE_RISK_FREE_RATE,
            profile_constraints=profile_constraints,
        )


def test_optimizer_with_profile_constraints_rejects_mismatched_asset_classes_length() -> None:
    profile_constraints = get_constraints_for_profile(config.PERFIL_MODERADO)
    with pytest.raises(ValueError, match="Dimensiones incompatibles"):
        optimize_max_sharpe(
            _REAL_UNIVERSE_EXPECTED_RETURNS,
            _REAL_UNIVERSE_COVARIANCE,
            _REAL_UNIVERSE_RISK_FREE_RATE,
            asset_classes=_REAL_UNIVERSE_ASSET_CLASSES[:-1],
            profile_constraints=profile_constraints,
        )


@pytest.mark.parametrize("profile", [config.PERFIL_MODERADO, config.PERFIL_AGRESIVO])
def test_optimizer_converges_and_respects_max_weight_for_moderado_and_agresivo(profile: str) -> None:
    """Conservador se prueba aparte: ver test_conservador_constraints_are_infeasible_with_current_universe."""
    profile_constraints = get_constraints_for_profile(profile)
    result = optimize_max_sharpe(
        _REAL_UNIVERSE_EXPECTED_RETURNS,
        _REAL_UNIVERSE_COVARIANCE,
        _REAL_UNIVERSE_RISK_FREE_RATE,
        asset_classes=_REAL_UNIVERSE_ASSET_CLASSES,
        profile_constraints=profile_constraints,
    )
    assert result.converged is True
    metrics.validate_weights_sum_to_one(result.weights)
    metrics.validate_no_short_selling(result.weights)
    assert result.weights.max() <= profile_constraints.max_weight_per_asset + 1e-6


def test_moderado_respects_minimum_fixed_income_band() -> None:
    profile_constraints = get_constraints_for_profile(config.PERFIL_MODERADO)
    result = optimize_max_sharpe(
        _REAL_UNIVERSE_EXPECTED_RETURNS,
        _REAL_UNIVERSE_COVARIANCE,
        _REAL_UNIVERSE_RISK_FREE_RATE,
        asset_classes=_REAL_UNIVERSE_ASSET_CLASSES,
        profile_constraints=profile_constraints,
    )
    fixed_income_mask = constraints_module.build_fixed_income_mask(_REAL_UNIVERSE_ASSET_CLASSES)
    fixed_income_weight = float(np.dot(fixed_income_mask, result.weights))
    assert fixed_income_weight >= profile_constraints.min_fixed_income_weight - 1e-4


def test_agresivo_respects_minimum_fixed_income_band() -> None:
    profile_constraints = get_constraints_for_profile(config.PERFIL_AGRESIVO)
    result = optimize_max_sharpe(
        _REAL_UNIVERSE_EXPECTED_RETURNS,
        _REAL_UNIVERSE_COVARIANCE,
        _REAL_UNIVERSE_RISK_FREE_RATE,
        asset_classes=_REAL_UNIVERSE_ASSET_CLASSES,
        profile_constraints=profile_constraints,
    )
    fixed_income_mask = constraints_module.build_fixed_income_mask(_REAL_UNIVERSE_ASSET_CLASSES)
    fixed_income_weight = float(np.dot(fixed_income_mask, result.weights))
    assert fixed_income_weight >= profile_constraints.min_fixed_income_weight - 1e-4


def test_conservador_with_only_two_fixed_income_assets_now_raises_instead_of_silently_failing() -> None:
    """Hallazgo de la Subfase 3.3 (11 activos, solo 2 de renta fija/monetario: AGGH.MI,
    XEON.DE): con el tope de 25% por activo, la capacidad maxima combinada de renta fija
    es 2*0.25=50%, por debajo del 60% que exige Conservador -> INFACTIBLE.

    En la Subfase 3.3 esto se traducia en `converged=False` sin mas explicacion. Desde la
    Subfase 3.4, `optimize_max_sharpe` valida la factibilidad ANTES de llamar a scipy y
    lanza `InfeasibleConstraintsError` con un mensaje explicito (ver Parte 2 de esta
    subfase). Este test fija ese cambio de comportamiento deliberado usando el fixture
    congelado de 11 activos de la Subfase 3.2/3.3 (que sigue siendo una escena
    estructuralmente infactible, aunque el universo REAL ya se amplio -- ver el test
    siguiente para la prueba con el universo real y factible de 13 activos).
    """
    profile_constraints = get_constraints_for_profile(config.PERFIL_CONSERVADOR)
    with pytest.raises(constraints_module.InfeasibleConstraintsError, match="renta fija"):
        optimize_max_sharpe(
            _REAL_UNIVERSE_EXPECTED_RETURNS,
            _REAL_UNIVERSE_COVARIANCE,
            _REAL_UNIVERSE_RISK_FREE_RATE,
            asset_classes=_REAL_UNIVERSE_ASSET_CLASSES,
            profile_constraints=profile_constraints,
        )


def test_conservador_is_feasible_and_converges_with_the_expanded_13_asset_universe() -> None:
    """Verifica la solucion adoptada en la Subfase 3.4 (Parte 1): con los 2 ETFs de
    renta fija añadidos (IBGS.AS, IEAC.AS), el universo pasa a tener 4 activos de renta
    fija/monetario. Capacidad maxima = 4*0.25 = 100%, muy por encima del 60% exigido ->
    Conservador ya es factible y el optimizador converge normalmente."""
    profile_constraints = get_constraints_for_profile(config.PERFIL_CONSERVADOR)
    result = optimize_max_sharpe(
        real_universe.EXPECTED_RETURNS,
        real_universe.COVARIANCE_MATRIX,
        real_universe.RISK_FREE_RATE,
        asset_classes=real_universe.ASSET_CLASSES,
        profile_constraints=profile_constraints,
    )

    assert result.converged is True
    fixed_income_mask = constraints_module.build_fixed_income_mask(real_universe.ASSET_CLASSES)
    fixed_income_weight = float(np.dot(fixed_income_mask, result.weights))
    assert fixed_income_weight >= profile_constraints.min_fixed_income_weight - 1e-4
    assert result.weights.max() <= profile_constraints.max_weight_per_asset + 1e-6
    metrics.validate_weights_sum_to_one(result.weights)
    metrics.validate_no_short_selling(result.weights)


def test_constraints_eliminate_the_extreme_concentration_from_subfase_3_2() -> None:
    """Comparacion directa Subfase 3.2 vs 3.3: la misma optimizacion (mismo universo,
    mismos retornos/covarianza) sin restricciones concentraba el 97% de la cartera en
    2 activos (ver test_optimizer_on_real_universe_concentrates_without_a_max_weight_constraint);
    con las restricciones de perfil Moderado, ningun activo supera el 35% y el riesgo
    se reparte entre mas posiciones."""
    unconstrained = optimize_max_sharpe(
        _REAL_UNIVERSE_EXPECTED_RETURNS, _REAL_UNIVERSE_COVARIANCE, _REAL_UNIVERSE_RISK_FREE_RATE
    )
    assert unconstrained.weights.max() > 0.5  # el hallazgo de la Subfase 3.2

    profile_constraints = get_constraints_for_profile(config.PERFIL_MODERADO)
    constrained = optimize_max_sharpe(
        _REAL_UNIVERSE_EXPECTED_RETURNS,
        _REAL_UNIVERSE_COVARIANCE,
        _REAL_UNIVERSE_RISK_FREE_RATE,
        asset_classes=_REAL_UNIVERSE_ASSET_CLASSES,
        profile_constraints=profile_constraints,
    )

    assert constrained.weights.max() <= profile_constraints.max_weight_per_asset + 1e-6
    assert constrained.weights.max() < unconstrained.weights.max()

    number_of_meaningful_positions_unconstrained = int(np.sum(unconstrained.weights > 0.01))
    number_of_meaningful_positions_constrained = int(np.sum(constrained.weights > 0.01))
    assert number_of_meaningful_positions_constrained > number_of_meaningful_positions_unconstrained


# --- Subfase 3.4: universo real completo (13 activos), los 3 perfiles ---


@pytest.mark.parametrize(
    "profile", [config.PERFIL_CONSERVADOR, config.PERFIL_MODERADO, config.PERFIL_AGRESIVO]
)
def test_optimizer_converges_for_all_profiles_with_the_real_13_asset_universe(profile: str) -> None:
    profile_constraints = get_constraints_for_profile(profile)
    result = optimize_max_sharpe(
        real_universe.EXPECTED_RETURNS,
        real_universe.COVARIANCE_MATRIX,
        real_universe.RISK_FREE_RATE,
        asset_classes=real_universe.ASSET_CLASSES,
        profile_constraints=profile_constraints,
    )

    assert result.converged is True
    assert len(result.weights) == len(real_universe.TICKERS)
    metrics.validate_weights_sum_to_one(result.weights)
    metrics.validate_no_short_selling(result.weights)
    assert result.weights.max() <= profile_constraints.max_weight_per_asset + 1e-6

    fixed_income_mask = constraints_module.build_fixed_income_mask(real_universe.ASSET_CLASSES)
    fixed_income_weight = float(np.dot(fixed_income_mask, result.weights))
    assert fixed_income_weight >= profile_constraints.min_fixed_income_weight - 1e-4
