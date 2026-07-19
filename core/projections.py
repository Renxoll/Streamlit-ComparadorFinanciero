"""Proyeccion de capital compuesto.

Fase 1: se extrajo `project_compound_growth` tal cual del original (aplica una
unica tasa sobre el capital COMPLETO, sin repartir por activo). Se mantiene
SIN MODIFICAR por retrocompatibilidad (Subfase 4.4): sigue siendo la funcion
correcta para proyectar un unico capital a una unica tasa fija.

Subfase 4.4: se añade `project_portfolio_by_asset`, que proyecta una cartera
de N posiciones componiendo cada una por separado (capital propio, tasa
propia) y sumando los resultados año a año — el metodo correcto para una
cartera sin rebalanceo, frente a `project_compound_growth` aplicado al total
(que asume implicitamente, sin declararlo, un rebalanceo continuo a los
pesos iniciales). Ver `docs/financial_validation.md` (Subfase 4.3) para la
demostracion matematica (desigualdad de Jensen) y la cuantificacion empirica
de la diferencia entre ambos metodos.
"""
from __future__ import annotations

from typing import Iterable


def project_compound_growth(initial_capital: float, annual_rate: float, years: int) -> list[float]:
    """Proyecta capitalizacion compuesta anual de `initial_capital` a `annual_rate` durante `years`.

    Devuelve una lista de `years + 1` valores (desde el año 0 hasta `years`).
    """
    return [initial_capital * ((1 + annual_rate) ** year) for year in range(years + 1)]


def blended_annual_rate(rate_a: float, weight_a: float, rate_b: float, weight_b: float) -> float:
    """Tasa anual combinada como promedio ponderado de dos tasas."""
    return (weight_a * rate_a) + (weight_b * rate_b)


def project_portfolio_by_asset(entries: Iterable[tuple[float, float]], years: int) -> list[float]:
    """Proyecta una cartera de N posiciones, cada una compuesta con su propio capital y tasa.

    Modelo BUY & HOLD: cada posicion crece de forma independiente a su propia
    rentabilidad esperada, sin ningun rebalanceo periodico a los pesos
    iniciales (a diferencia de `project_compound_growth` aplicado al capital
    total, que asume ese rebalanceo de forma implicita). Es el metodo
    matematicamente correcto para "cuanto valdra la cartera si no se toca":
    por la desigualdad de Jensen, el resultado es siempre >= el de
    `project_compound_growth` con la tasa blended equivalente, y coincide
    exactamente con el en el año 1 (ver Subfase 4.3).

    Args:
        entries: iterable de tuplas `(capital_asignado, retorno_esperado_anual)`,
            una por posicion de la cartera (p. ej. construido a partir de
            `PortfolioAllocation.entries` por quien llama).
        years: numero de años a proyectar.

    Returns:
        Lista de `years + 1` valores (desde el año 0 hasta `years`): la suma,
        en cada año, del valor compuesto de todas las posiciones.
    """
    entries_list = list(entries)
    return [
        sum(capital * (1 + annual_rate) ** year for capital, annual_rate in entries_list)
        for year in range(years + 1)
    ]
