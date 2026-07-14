"""Utilidades de formato reutilizadas por varias secciones de la interfaz.

Antes de esta extraccion, cada hoja formateaba numeros con `f"{x:.4f}"` /
`f"{x*100:.2f}%"` repetidos de forma independiente (Hoja 3, Hoja 4, Hoja 5),
con riesgo de inconsistencia si se cambiaba el numero de decimales en un solo
sitio. Centralizarlo aqui resuelve esa duplicacion (observacion 9 del tutor).
"""
from __future__ import annotations


def format_decimal(value: float, decimals: int = 4) -> str:
    """Formatea un numero con un numero fijo de decimales (ej. 0.8231)."""
    return f"{value:.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Formatea una fraccion como porcentaje (ej. 0.055 -> '5.50%')."""
    return f"{value * 100:.{decimals}f}%"
