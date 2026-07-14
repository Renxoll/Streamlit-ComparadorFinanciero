"""Estructuras de datos (DTOs) compartidas entre secciones de la interfaz.

Se centralizan aqui para que el flujo de datos entre `ui/sections/*.py` este
tipado explicitamente, en vez de depender de variables sueltas compartidas por
convencion (como ocurria en el `app.py` original).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class InvestorInputs:
    """Datos capturados en la Hoja 1 (datos del inversor)."""

    nombre: str
    edad: int
    importe: float
    plazo: int
    risk_free_rate: float
    market_premium: float


@dataclass
class MarkowitzSelection:
    """Resultado del cruce entre los ganadores sectoriales (Hoja 4).

    Nota: en la Fase 1 esto sigue siendo la heuristica "mejor banco + mejor
    aseguradora" con mezcla manual de pesos. La Fase 3 sustituye el origen de
    este resultado por una optimizacion real de Markowitz sobre N activos,
    manteniendo esta misma estructura como contrato con las hojas 5 y 6.
    """

    mejor_banco: pd.Series
    mejor_seguro: pd.Series
    peso_banco: float
    peso_seguro: float
    beta_conjunta: float
    rentabilidad_conjunta: float
    volatilidad_conjunta: float
    sharpe_conjunto: float
    covarianza_anualizada: float
