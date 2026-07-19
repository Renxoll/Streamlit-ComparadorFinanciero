"""Hoja 6: resumen final y exportación a PDF.

Adaptada en la Subfase 3.5 para consumir `PortfolioAllocation` en vez de
`MarkowitzSelection`. Se retiran los conceptos "Mejor banco"/"Mejor
aseguradora" y "Criterio de beta" (ya no describen el mecanismo real de
construcción de cartera desde que el optimizador usa el universo completo,
ver `ui/sections/markowitz_portfolio.py`) y se sustituyen por las
restricciones de asignación REALMENTE aplicadas
(`portfolio.constraints.ProfileConstraints`). El número de activos del
universo se calcula dinámicamente a partir de `allocation.entries`, ya no
está hardcodeado a "7".
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.models import InvestorInputs
from portfolio.allocation import PortfolioAllocation
from portfolio.constraints import get_constraints_for_profile
from reports.pdf_export import build_summary_pdf
from ui.components import format_decimal, format_percentage


def render(investor: InvestorInputs, allocation: PortfolioAllocation) -> None:
    """Renderiza la tarjeta resumen y el botón de descarga del PDF ejecutivo."""
    st.header("HOJA 6: RESUMEN FINAL DEL SISTEMA DE RECOMENDACIÓN")

    perfil_actual = st.session_state.perfil_calc
    profile_constraints = get_constraints_for_profile(perfil_actual)
    numero_posiciones = sum(1 for entry in allocation.entries if entry.weight > 0)

    df_resumen_card = pd.DataFrame({
        "Concepto Metodológico": [
            "Usuario", "Perfil inversor", "Universo analizado",
            "Número de activos en el universo", "Número de posiciones en cartera",
            "Modelo de rentabilidad", "Modelo de optimización", "Restricciones aplicadas",
            "Rentabilidad esperada de la cartera", "Sharpe de la cartera",
        ],
        "Valor Asignado": [
            investor.nombre, perfil_actual, "Bancos, aseguradoras y ETFs UCITS de la Unión Europea",
            str(len(allocation.entries)), str(numero_posiciones),
            "CAPM", "Markowitz (máximo Ratio de Sharpe)",
            f"Peso máx. {profile_constraints.max_weight_per_asset:.0%} por activo; "
            f"mín. {profile_constraints.min_fixed_income_weight:.0%} renta fija/monetario",
            format_percentage(allocation.expected_return),
            format_decimal(allocation.sharpe_ratio),
        ],
    })

    col_card, col_pdf = st.columns([2, 1])
    with col_card:
        st.table(df_resumen_card)

    with col_pdf:
        st.write("### Exportación Documental")
        st.write("Genera el acta oficial de resultados de la recomendación de inversión.")
        st.download_button(
            label="📥 Descargar Ficha de Resultados (PDF)",
            data=build_summary_pdf(df_resumen_card),
            file_name="Resumen_Ejecutivo.pdf",
            mime="application/pdf",
        )
