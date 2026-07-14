"""Proyeccion de capital compuesto.

Fase 1: se extrae la formula original tal cual (aplica una unica tasa sobre el
capital COMPLETO, sin repartir por activo). La correccion que proyecta cada
activo con su capital efectivamente asignado y suma los resultados
(observacion 7 del tutor) se implementa en la Fase 4, una vez exista una
asignacion real de pesos por activo (Fase 3).
"""
from __future__ import annotations


def project_compound_growth(initial_capital: float, annual_rate: float, years: int) -> list[float]:
    """Proyecta capitalizacion compuesta anual de `initial_capital` a `annual_rate` durante `years`.

    Devuelve una lista de `years + 1` valores (desde el año 0 hasta `years`).
    """
    return [initial_capital * ((1 + annual_rate) ** year) for year in range(years + 1)]


def blended_annual_rate(rate_a: float, weight_a: float, rate_b: float, weight_b: float) -> float:
    """Tasa anual combinada como promedio ponderado de dos tasas."""
    return (weight_a * rate_a) + (weight_b * rate_b)
