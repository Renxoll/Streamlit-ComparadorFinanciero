"""Estructuras de datos (DTOs) compartidas entre secciones de la interfaz.

Se centralizan aqui para que el flujo de datos entre `ui/sections/*.py` este
tipado explicitamente, en vez de depender de variables sueltas compartidas por
convencion (como ocurria en el `app.py` original).

Nota (Subfase 3.5): `MarkowitzSelection` (heuristica "mejor banco + mejor
aseguradora" de 2 activos, Fases 1-2) se eliminó de este módulo. El contrato
entre Hoja 4, Hoja 5 y Hoja 6 es ahora `portfolio.allocation.PortfolioAllocation`,
que sustituye por completo al modelo antiguo — no se mantienen dos estructuras
paralelas para el mismo propósito.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InvestorInputs:
    """Datos capturados en la Hoja 1 (datos del inversor)."""

    nombre: str
    edad: int
    importe: float
    plazo: int
    risk_free_rate: float
    market_premium: float
