"""Optimizador de cartera de Markowitz: maximización del Ratio de Sharpe.

Resuelve, mediante `scipy.optimize.minimize` (SLSQP), el problema de la
cartera tangente: los pesos que maximizan el Ratio de Sharpe de la cartera,
sujeto ÚNICAMENTE a las restricciones estructurales mínimas de cualquier
cartera real:

    minimizar_w   -(w'μ - Rf) / sqrt(w'Σw)      [equivale a maximizar el Sharpe]
    sujeto a      Σ w_i = 1
                  w_i >= 0   para todo i          (no se permite venta en corto)

donde `μ` es el vector de retornos esperados (CAPM), `Σ` la matriz de
covarianzas anualizada, y `Rf` la tasa libre de riesgo.

Las restricciones específicas por perfil inversor (bandas mínimas de renta
fija/variable, peso máximo por activo) se añaden en `portfolio.constraints`
(Subfase 3.3) como restricciones adicionales pasadas a `scipy.optimize.minimize`,
sin modificar esta función.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from portfolio.metrics import (
    portfolio_expected_return,
    portfolio_sharpe_ratio,
    portfolio_volatility,
    validate_dimensions_match,
    validate_positive_semidefinite_covariance,
)

# --- Parametros del solver (ninguno vive fuera de este bloque: cero numeros magicos) ---
DEFAULT_MAX_ITERATIONS = 500
DEFAULT_TOLERANCE = 1e-9
_TARGET_WEIGHT_SUM = 1.0
_MIN_WEIGHT_BOUND = 0.0  # no se permite venta en corto
_MAX_WEIGHT_BOUND: float | None = None  # sin tope superior en esta subfase (llega en la 3.3)
_WEIGHT_CLEANUP_TOLERANCE = 1e-10  # por debajo de esto, un peso se considera ruido numerico


@dataclass(frozen=True)
class OptimizationResult:
    """Resultado de una optimización de cartera de máximo Sharpe."""

    weights: np.ndarray
    expected_return: float
    volatility: float
    sharpe_ratio: float
    converged: bool
    message: str
    iterations: int


def _negative_sharpe_ratio(
    weights: np.ndarray,
    expected_returns: np.ndarray,
    covariance_matrix: np.ndarray,
    risk_free_rate: float,
) -> float:
    """Función objetivo del solver: el negativo del Sharpe (minimizarla maximiza el Sharpe)."""
    expected_return = portfolio_expected_return(weights, expected_returns)
    volatility = portfolio_volatility(weights, covariance_matrix)
    return -portfolio_sharpe_ratio(expected_return, risk_free_rate, volatility)


def optimize_max_sharpe(
    expected_returns: np.ndarray,
    covariance_matrix: np.ndarray,
    risk_free_rate: float,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    tolerance: float = DEFAULT_TOLERANCE,
) -> OptimizationResult:
    """Encuentra los pesos que maximizan el Ratio de Sharpe de la cartera.

    Función pura: no descarga datos, no conoce tickers ni clases de activo,
    no depende de Streamlit. Recibe únicamente los 3 insumos matemáticos del
    problema y devuelve los pesos óptimos junto con las métricas de la
    cartera resultante.

    El punto de partida del solver es la cartera de pesos iguales (1/n cada
    uno): es un punto neutro que no sesga la solución hacia ningún activo en
    particular y garantiza que el punto inicial ya es factible (suma 1,
    todos positivos).

    Args:
        expected_returns: vector (n_activos,) de retornos esperados (p. ej. CAPM).
        covariance_matrix: matriz (n_activos, n_activos) de covarianzas anualizada.
        risk_free_rate: tasa libre de riesgo anual.
        max_iterations: límite de iteraciones del solver SLSQP.
        tolerance: tolerancia de convergencia del solver (`ftol`).

    Returns:
        `OptimizationResult` con los pesos óptimos (suman 1, ninguno negativo)
        y las métricas de la cartera resultante.

    Raises:
        ValueError: si las dimensiones de `expected_returns`/`covariance_matrix`
            son incompatibles, o si `covariance_matrix` no es una matriz de
            covarianzas válida (no semidefinida positiva).
    """
    validate_dimensions_match(expected_returns, covariance_matrix)
    validate_positive_semidefinite_covariance(covariance_matrix)

    n_assets = len(expected_returns)
    initial_weights = np.full(n_assets, 1.0 / n_assets)
    bounds = tuple((_MIN_WEIGHT_BOUND, _MAX_WEIGHT_BOUND) for _ in range(n_assets))
    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - _TARGET_WEIGHT_SUM},)

    result = minimize(
        fun=_negative_sharpe_ratio,
        x0=initial_weights,
        args=(expected_returns, covariance_matrix, risk_free_rate),
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": max_iterations, "ftol": tolerance},
    )

    # El solver respeta los `bounds` con precision practicamente exacta, pero la
    # restriccion de igualdad (suma=1) solo se cumple hasta `tolerance`. Se limpia
    # cualquier resto de ruido numerico negativo y se renormaliza la suma a 1.0
    # exacto, para que el resultado cumpla las garantias documentadas (pesos >= 0,
    # suma exactamente 1) sin depender de la precision interna del solver.
    weights = np.clip(result.x, _MIN_WEIGHT_BOUND, None)
    weights[weights < _WEIGHT_CLEANUP_TOLERANCE] = 0.0
    weights = weights / weights.sum()

    expected_return = portfolio_expected_return(weights, expected_returns)
    volatility = portfolio_volatility(weights, covariance_matrix)
    sharpe = portfolio_sharpe_ratio(expected_return, risk_free_rate, volatility)

    return OptimizationResult(
        weights=weights,
        expected_return=expected_return,
        volatility=volatility,
        sharpe_ratio=sharpe,
        converged=bool(result.success),
        message=str(result.message),
        iterations=int(result.nit),
    )
