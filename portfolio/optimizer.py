"""Optimizador de cartera de Markowitz: maximización del Ratio de Sharpe.

Resuelve, mediante `scipy.optimize.minimize` (SLSQP), el problema de la
cartera tangente: los pesos que maximizan el Ratio de Sharpe de la cartera.

    minimizar_w   -(w'μ - Rf) / sqrt(w'Σw)      [equivale a maximizar el Sharpe]
    sujeto a      Σ w_i = 1
                  w_i >= 0   para todo i          (no se permite venta en corto)
                  w_i <= peso_max(perfil)          (Subfase 3.3, opcional)
                  Σ w_i∈RF∪Monetario >= min_RF(perfil)   (Subfase 3.3, opcional)
                  Σ w_i∈RV <= max_RV(perfil)              (Subfase 3.3, opcional)

donde `μ` es el vector de retornos esperados (CAPM), `Σ` la matriz de
covarianzas anualizada, y `Rf` la tasa libre de riesgo.

Desde la Subfase 3.3, `optimize_max_sharpe` acepta opcionalmente un
`portfolio.constraints.ProfileConstraints` (junto con la clase de cada
activo) para añadir las 3 restricciones adicionales de arriba. Si no se
pasan (por defecto), el comportamiento es IDÉNTICO al de la Subfase 3.2:
únicamente `Σw=1` y `w>=0`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from portfolio.constraints import ProfileConstraints, build_equity_mask, build_fixed_income_mask
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


def _build_weight_bounds(
    n_assets: int, profile_constraints: ProfileConstraints | None
) -> tuple[tuple[float, float | None], ...]:
    """Límite superior por activo: sin tope (Subfase 3.2) o `max_weight_per_asset` (Subfase 3.3)."""
    upper_bound = profile_constraints.max_weight_per_asset if profile_constraints is not None else None
    return tuple((_MIN_WEIGHT_BOUND, upper_bound) for _ in range(n_assets))


def _build_composition_constraints(
    asset_classes: np.ndarray, profile_constraints: ProfileConstraints
) -> tuple[dict[str, object], ...]:
    """Restricciones lineales de composición: piso de renta fija, techo de renta variable."""
    fixed_income_mask = build_fixed_income_mask(asset_classes)
    equity_mask = build_equity_mask(asset_classes)
    min_fixed_income = profile_constraints.min_fixed_income_weight
    max_equity = profile_constraints.max_equity_weight

    return (
        {"type": "ineq", "fun": lambda w: np.dot(fixed_income_mask, w) - min_fixed_income},
        {"type": "ineq", "fun": lambda w: max_equity - np.dot(equity_mask, w)},
    )


def optimize_max_sharpe(
    expected_returns: np.ndarray,
    covariance_matrix: np.ndarray,
    risk_free_rate: float,
    asset_classes: np.ndarray | None = None,
    profile_constraints: ProfileConstraints | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    tolerance: float = DEFAULT_TOLERANCE,
) -> OptimizationResult:
    """Encuentra los pesos que maximizan el Ratio de Sharpe de la cartera.

    Función pura: no descarga datos, no depende de Streamlit. El punto de
    partida del solver es la cartera de pesos iguales (1/n cada uno): un
    punto neutro que no sesga la solución hacia ningún activo y que ya es
    factible (suma 1, todos positivos, dentro de cualquier tope razonable).

    Args:
        expected_returns: vector (n_activos,) de retornos esperados (p. ej. CAPM).
        covariance_matrix: matriz (n_activos, n_activos) de covarianzas anualizada.
        risk_free_rate: tasa libre de riesgo anual.
        asset_classes: vector (n_activos,) con la clase de cada activo
            ("Renta Variable"/"Renta Fija"/"Monetario", ver `config.py`).
            Obligatorio si se pasa `profile_constraints`; se ignora si no.
        profile_constraints: bandas de asignación del perfil (ver
            `portfolio.constraints.get_constraints_for_profile`). Si es
            `None` (valor por defecto), el comportamiento es idéntico al de
            la Subfase 3.2: sin peso máximo por activo ni bandas de
            composición renta fija/variable.
        max_iterations: límite de iteraciones del solver SLSQP.
        tolerance: tolerancia de convergencia del solver (`ftol`).

    Returns:
        `OptimizationResult` con los pesos óptimos (suman 1, ninguno negativo,
        y si se pasaron restricciones, ninguno por encima del tope) y las
        métricas de la cartera resultante. `converged=False` indica que el
        solver no encontró un punto que satisfaga todas las restricciones
        simultáneamente (ver nota sobre factibilidad en
        `docs/markowitz_metodologia.md`); en ese caso `weights` es el mejor
        punto factible que el solver pudo alcanzar, no el óptimo exacto.

    Raises:
        ValueError: si las dimensiones son incompatibles, si `covariance_matrix`
            no es una matriz de covarianzas válida (no semidefinida positiva),
            o si se pasa `profile_constraints` sin `asset_classes` (o con una
            longitud incompatible).
    """
    validate_dimensions_match(expected_returns, covariance_matrix)
    validate_positive_semidefinite_covariance(covariance_matrix)

    n_assets = len(expected_returns)

    if profile_constraints is not None:
        if asset_classes is None:
            raise ValueError(
                "profile_constraints requiere asset_classes (la clase de cada activo) para "
                "poder construir las bandas de composición renta fija/renta variable."
            )
        if len(asset_classes) != n_assets:
            raise ValueError(
                f"Dimensiones incompatibles: {n_assets} retornos esperados frente a "
                f"{len(asset_classes)} clases de activo."
            )

    initial_weights = np.full(n_assets, 1.0 / n_assets)
    bounds = _build_weight_bounds(n_assets, profile_constraints)
    constraints: list[dict[str, object]] = [{"type": "eq", "fun": lambda w: np.sum(w) - _TARGET_WEIGHT_SUM}]
    if profile_constraints is not None:
        assert asset_classes is not None  # validado arriba; ayuda a mypy a estrechar el tipo
        constraints.extend(_build_composition_constraints(asset_classes, profile_constraints))

    result = minimize(
        fun=_negative_sharpe_ratio,
        x0=initial_weights,
        args=(expected_returns, covariance_matrix, risk_free_rate),
        method="SLSQP",
        bounds=bounds,
        constraints=tuple(constraints),
        options={"maxiter": max_iterations, "ftol": tolerance},
    )

    # El solver respeta los `bounds` con precision practicamente exacta, pero las
    # restricciones de igualdad/desigualdad solo se cumplen hasta `tolerance`. Se
    # limpia cualquier resto de ruido numerico negativo y se renormaliza la suma
    # a 1.0 exacto, para que el resultado cumpla las garantias documentadas (pesos
    # >= 0, suma exactamente 1) sin depender de la precision interna del solver.
    # Nota: si `converged` es False por infactibilidad (ver Raises/Returns), esta
    # limpieza se aplica igualmente sobre el mejor punto encontrado por el solver.
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
