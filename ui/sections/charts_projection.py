"""Hoja 5: proyección y gráficos de la cartera optimizada.

Adaptada en la Subfase 3.5 para consumir `PortfolioAllocation` (N activos)
en vez de la antigua heurística de 2 activos (`MarkowitzSelection`). No se
recalcula nada nuevo: se reutiliza `core.projections.project_compound_growth`
(sin cambios desde la Fase 1) sobre el capital y la rentabilidad esperada
YA calculados por `portfolio.allocation.build_portfolio_allocation`.

Limitación conocida, heredada y NO resuelta en esta subfase: la proyección
sigue aplicando una única tasa (la rentabilidad esperada agregada de la
cartera) al capital total, en vez de proyectar cada posición con su capital
asignado y sumar los resultados — matemáticamente más correcto para
horizontes de varios años (observación 7 del tutor, señalada desde la
auditoría inicial). Esa corrección requiere una fase propia centrada en el
modelo de proyección; no forma parte del alcance de "integrar el
optimizador en la UI".
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.models import InvestorInputs
from core.projections import project_compound_growth
from portfolio.allocation import PortfolioAllocation
from ui.components import format_decimal, format_percentage


def render(investor: InvestorInputs, allocation: PortfolioAllocation) -> None:
    """Renderiza la proyección de capital y el resumen de la cartera optimizada."""
    st.header("HOJA 5: VISUALIZACIÓN DE RESULTADOS")

    anios = list(range(int(investor.plazo) + 1))
    proyeccion = project_compound_growth(allocation.total_capital, allocation.expected_return, investor.plazo)
    df_proyeccion = pd.DataFrame({"Año": anios, "Cartera optimizada": proyeccion})

    col_tabla_proy, col_indicadores = st.columns([1.3, 1.7])

    with col_tabla_proy:
        st.subheader("Proyección de Capital (€)")
        st.dataframe(
            df_proyeccion.style.format({"Cartera optimizada": "{:,.2f} €"}),
            hide_index=True,
        )

    with col_indicadores:
        st.subheader("Resumen de la cartera")
        df_resumen = pd.DataFrame({
            "Indicador": [
                "Capital total", "Rentabilidad esperada", "Volatilidad", "Beta de cartera",
                "Sharpe de cartera", "% Renta Variable", "% Renta Fija", "% Monetario",
            ],
            "Valor": [
                f"{allocation.total_capital:,.2f} €",
                format_percentage(allocation.expected_return),
                format_percentage(allocation.volatility),
                format_decimal(allocation.beta),
                format_decimal(allocation.sharpe_ratio),
                format_percentage(allocation.equity_percentage, decimals=1),
                format_percentage(allocation.fixed_income_percentage, decimals=1),
                format_percentage(allocation.money_market_percentage, decimals=1),
            ],
        })
        st.dataframe(df_resumen, hide_index=True, use_container_width=True)

    st.subheader("Evolución temporal del capital invertido")
    st.line_chart(df_proyeccion.set_index("Año"))
