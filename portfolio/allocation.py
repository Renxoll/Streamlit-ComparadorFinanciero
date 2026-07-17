"""Asignación de capital: traduce pesos óptimos + capital del inversor en una
cartera invertible, en euros.

Este módulo NO realiza ninguna optimización: toma como entrada el resultado
YA CALCULADO de `portfolio.optimizer.optimize_max_sharpe` (o cualquier vector
de pesos válido) y las métricas por activo de `core.capm.build_universe_metrics`,
y produce una `PortfolioAllocation` con el monto en euros de cada posición y
las métricas agregadas de la cartera resultante.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

import config
from portfolio.metrics import portfolio_beta
from portfolio.optimizer import OptimizationResult

# Decimales monetarios: los importes se reparten y verifican a nivel de céntimo.
_CENTS_DECIMALS = 2


@dataclass(frozen=True)
class AllocationEntry:
    """Una posición concreta de la cartera invertible: un activo y su asignación de capital."""

    ticker: str
    name: str
    asset_class: str
    weight: float
    allocated_capital: float
    expected_return: float
    beta: float
    sharpe_ratio: float
    volatility: float


@dataclass(frozen=True)
class PortfolioAllocation:
    """Cartera invertible final: posiciones concretas + métricas agregadas de cartera."""

    entries: tuple[AllocationEntry, ...]
    total_capital: float
    expected_return: float
    volatility: float
    beta: float
    sharpe_ratio: float
    fixed_income_percentage: float
    equity_percentage: float
    money_market_percentage: float


def _allocate_capital_across_entries(weights: np.ndarray, total_capital: float) -> list[float]:
    """Reparte `total_capital` según `weights`, sin perder ni un céntimo.

    La aritmética se hace en CÉNTIMOS ENTEROS (no en euros con decimales): así, la
    desviación de redondeo que produce repartir un total entre N pesos independientes
    se calcula y corrige de forma exacta (aritmética de enteros de Python, sin el
    redondeo binario de los floats), y se aplica íntegramente a la ÚLTIMA posición.

    Nota sobre cómo verificar el resultado: `sum(resultado)` puede diferir de
    `total_capital` en un residuo del orden de 1e-10 al comparar con `==`, por la
    conocida falta de asociatividad de la suma de floats en IEEE-754 (p. ej.
    `37.80 + 28.99 != round(37.80 + 28.99, 2)` a veces, en binario). La cifra en
    céntimos SÍ es exacta; para comprobar "ningún céntimo perdido" hay que comparar
    `round(sum(resultado), 2) == round(total_capital, 2)`, no `==` directo.
    """
    total_capital_cents = round(total_capital * 100)
    allocated_cents = [round(float(weight) * total_capital_cents) for weight in weights]
    rounding_drift_cents = total_capital_cents - sum(allocated_cents)
    if allocated_cents:
        allocated_cents[-1] += rounding_drift_cents
    return [cents / 100 for cents in allocated_cents]


def build_portfolio_allocation(
    universe_metrics: pd.DataFrame,
    optimization_result: OptimizationResult,
    total_capital: float,
) -> PortfolioAllocation:
    """Construye la cartera invertible final a partir de una optimización y un capital.

    No realiza ningún cálculo de optimización: únicamente traduce
    `optimization_result.weights` y `total_capital` en una cartera con montos
    en euros, y agrega las métricas de cartera ya calculadas (más la Beta de
    cartera, que el optimizador no calcula).

    Args:
        universe_metrics: métricas por activo (salida de `core.capm.build_universe_metrics`),
            con una fila por activo EN EL MISMO ORDEN que `optimization_result.weights`.
        optimization_result: resultado de `portfolio.optimizer.optimize_max_sharpe`
            sobre ese mismo universo (mismo orden de activos).
        total_capital: capital total del inversor, en euros. Debe ser positivo.

    Returns:
        `PortfolioAllocation` con una `AllocationEntry` por activo (incluidos los
        de peso 0) y las métricas agregadas de la cartera. La suma de
        `allocated_capital`, en céntimos, es EXACTAMENTE la de `total_capital`
        (ver nota de redondeo en `_allocate_capital_across_entries` sobre cómo
        comparar sumas de floats monetarios correctamente).

    Raises:
        ValueError: si `universe_metrics` y `optimization_result.weights` no
            tienen la misma longitud, o si `total_capital` no es positivo.
    """
    weights = optimization_result.weights
    if len(universe_metrics) != len(weights):
        raise ValueError(
            f"Dimensiones incompatibles: {len(universe_metrics)} activos en universe_metrics "
            f"frente a {len(weights)} pesos en optimization_result."
        )
    if total_capital <= 0:
        raise ValueError(f"El capital total debe ser positivo (recibido: {total_capital}).")

    betas = universe_metrics[config.COL_BETA].to_numpy()
    asset_classes = universe_metrics[config.COL_CLASE_ACTIVO].to_numpy()

    allocated_capital = _allocate_capital_across_entries(weights, total_capital)

    entries = tuple(
        AllocationEntry(
            ticker=str(row[config.COL_TICKER]),
            name=str(row[config.COL_EMPRESA]),
            asset_class=str(row[config.COL_CLASE_ACTIVO]),
            weight=float(weight),
            allocated_capital=capital,
            expected_return=float(row[config.COL_CAPM]),
            beta=float(row[config.COL_BETA]),
            sharpe_ratio=float(row[config.COL_SHARPE]),
            volatility=float(row[config.COL_VOL_ANUAL]),
        )
        for (_, row), weight, capital in zip(universe_metrics.iterrows(), weights, allocated_capital)
    )

    fixed_income_percentage = float(np.dot(weights, (asset_classes == config.CLASE_RENTA_FIJA).astype(float)))
    equity_percentage = float(np.dot(weights, (asset_classes == config.CLASE_RENTA_VARIABLE).astype(float)))
    money_market_percentage = float(np.dot(weights, (asset_classes == config.CLASE_MONETARIO).astype(float)))

    return PortfolioAllocation(
        entries=entries,
        total_capital=total_capital,
        expected_return=optimization_result.expected_return,
        volatility=optimization_result.volatility,
        beta=portfolio_beta(weights, betas),
        sharpe_ratio=optimization_result.sharpe_ratio,
        fixed_income_percentage=fixed_income_percentage,
        equity_percentage=equity_percentage,
        money_market_percentage=money_market_percentage,
    )
