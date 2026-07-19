"""Hoja 5: proyección y gráficos de la cartera optimizada.

Adaptada en la Subfase 3.5 para consumir `PortfolioAllocation` (N activos)
en vez de la antigua heurística de 2 activos (`MarkowitzSelection`).

Subfase 4.4: la proyección usa `core.projections.project_portfolio_by_asset`,
que compone CADA posición con su propio capital asignado y su propia
rentabilidad esperada, y suma los resultados — sustituye a la aproximación
anterior (una única tasa blended aplicada al capital total), que la Subfase
4.3 demostró matemática y empíricamente que subestima el capital proyectado
de forma creciente con el horizonte (hasta ~30% a 30 años en los datos
auditados). Ningún cálculo se duplica: el capital y la rentabilidad de cada
posición ya estaban calculados por `portfolio.allocation.build_portfolio_allocation`.

Supuesto financiero de esta proyección (documentado explícitamente, tal como
se acordó al aprobar la Subfase 4.3): cartera BUY & HOLD — cada posición
compone de forma independiente, SIN rebalanceo periódico a los pesos
iniciales. Un modelo con rebalanceo periódico daría un resultado distinto
y queda fuera del alcance de esta subfase.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.models import InvestorInputs
from core.projections import project_portfolio_by_asset
from portfolio.allocation import PortfolioAllocation
from ui.components import format_decimal, format_percentage


def render(investor: InvestorInputs, allocation: PortfolioAllocation) -> None:
    """Renderiza la proyección de capital y el resumen de la cartera optimizada."""
    st.header("HOJA 5: VISUALIZACIÓN DE RESULTADOS")

    anios = list(range(int(investor.plazo) + 1))
    posiciones = [(entry.allocated_capital, entry.expected_return) for entry in allocation.entries]
    proyeccion = project_portfolio_by_asset(posiciones, investor.plazo)
    df_proyeccion = pd.DataFrame({"Año": anios, "Cartera optimizada": proyeccion})

    col_tabla_proy, col_indicadores = st.columns([1.3, 1.7])

    with col_tabla_proy:
        st.subheader("Proyección de Capital (€)")
        st.dataframe(
            df_proyeccion.style.format({"Cartera optimizada": "{:,.2f} €"}),
            hide_index=True,
        )
        st.caption(
            "Proyección *buy & hold*: cada posición compone de forma independiente a su "
            "propia rentabilidad esperada, sin rebalanceo periódico a los pesos iniciales."
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
