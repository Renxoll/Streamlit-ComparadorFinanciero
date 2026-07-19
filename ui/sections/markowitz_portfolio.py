"""Hoja 4: cartera óptima (Markowitz real).

Reescrita por completo en la Subfase 3.5: sustituye a la heurística "mejor
banco + mejor aseguradora" de las Fases 1-2 por una integración real con
`portfolio/{covariance,optimizer,constraints,allocation}.py`. Este módulo es
EXCLUSIVAMENTE una capa de presentación: no calcula pesos, Sharpe, volatilidad
ni retornos — solo orquesta las llamadas a `portfolio/` y muestra el resultado.

Nota de diseño importante (hallazgo de esta subfase, ver informe): el universo
NO se filtra por elegibilidad individual de Beta
(`portfolio.constraints.is_asset_eligible_for_profile`) antes de optimizar.
Con los datos reales actuales, ningún activo de renta variable alcanza el
umbral de Beta >= 1.25 exigido para "Agresivo" (el máximo real es 1.2475), por
lo que filtrar dejaría a ese perfil sin ninguna renta variable disponible —
el resultado opuesto al que un perfil Agresivo necesita. En su lugar, se
optimiza sobre el universo COMPLETO y son las bandas de composición de
`ProfileConstraints` (piso de renta fija, techo de renta variable, peso
máximo por activo) las que diferencian los 3 perfiles — enfoque ya validado
en las Subfases 3.3/3.4 y verificado de nuevo aquí con datos reales.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

import config
from core.market_data import MarketDataService
from core.models import InvestorInputs
from portfolio import covariance as covariance_module
from portfolio.allocation import PortfolioAllocation, build_portfolio_allocation
from portfolio.constraints import InfeasibleConstraintsError, get_constraints_for_profile
from portfolio.optimizer import optimize_max_sharpe
from ui.components import format_decimal, format_percentage


@st.cache_data(ttl=3600, show_spinner="Calculando matriz de covarianzas del universo...")
def _cached_covariance_matrix(tickers: tuple[str, ...], period: str) -> np.ndarray:
    """Envoltorio cacheado de `portfolio.covariance.build_annualized_covariance_matrix`."""
    service = MarketDataService()
    return covariance_module.build_annualized_covariance_matrix(service, list(tickers), period).to_numpy()


def render(
    universe_metrics: pd.DataFrame, investor: InvestorInputs, investor_profile: str
) -> PortfolioAllocation | None:
    """Ejecuta la optimización de Markowitz para `investor_profile` y muestra la cartera resultante.

    Devuelve `None` si las restricciones del perfil no son matemáticamente
    factibles con el universo actual (`InfeasibleConstraintsError`), en cuyo
    caso se muestra un mensaje de error explicativo en vez de romper la app.
    """
    st.header("HOJA 4: CARTERA ÓPTIMA (MODELO DE MARKOWITZ)")
    st.caption(
        f"Optimización de máximo Ratio de Sharpe para el perfil {investor_profile}, sujeta a las "
        "restricciones de asignación de ese perfil (ver Hoja 3 para las métricas CAPM de cada activo)."
    )

    profile_constraints = get_constraints_for_profile(investor_profile)
    tickers = tuple(universe_metrics[config.COL_TICKER])
    covariance_matrix = _cached_covariance_matrix(tickers, config.HISTORY_PERIOD)
    expected_returns = universe_metrics[config.COL_CAPM].to_numpy()
    asset_classes = universe_metrics[config.COL_CLASE_ACTIVO].to_numpy()

    try:
        optimization_result = optimize_max_sharpe(
            expected_returns,
            covariance_matrix,
            investor.risk_free_rate,
            asset_classes=asset_classes,
            profile_constraints=profile_constraints,
        )
    except InfeasibleConstraintsError as exc:
        st.error(
            f"No es posible construir una cartera para el perfil {investor_profile} con el "
            f"universo de activos actual: {exc}"
        )
        return None

    if not optimization_result.converged:
        st.warning(
            "El optimizador no garantiza haber alcanzado el óptimo exacto "
            f"(mensaje del solver: {optimization_result.message}). Los resultados mostrados "
            "son la mejor aproximación encontrada."
        )

    allocation = build_portfolio_allocation(universe_metrics, optimization_result, investor.importe)

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Rentabilidad esperada", format_percentage(allocation.expected_return))
    col_m2.metric("Volatilidad", format_percentage(allocation.volatility))
    col_m3.metric("Beta de cartera", format_decimal(allocation.beta))
    col_m4.metric("Sharpe de cartera", format_decimal(allocation.sharpe_ratio))

    col_c1, col_c2, col_c3 = st.columns(3)
    col_c1.metric("Renta Variable", format_percentage(allocation.equity_percentage, decimals=1))
    col_c2.metric("Renta Fija", format_percentage(allocation.fixed_income_percentage, decimals=1))
    col_c3.metric("Monetario", format_percentage(allocation.money_market_percentage, decimals=1))

    st.divider()
    st.subheader("Composición de la cartera")

    positions = [entry for entry in allocation.entries if entry.weight > 0]
    df_positions = pd.DataFrame({
        "Ticker": [entry.ticker for entry in positions],
        "Activo": [entry.name for entry in positions],
        "Clase de activo": [entry.asset_class for entry in positions],
        "Peso": [format_percentage(entry.weight) for entry in positions],
        "Capital asignado": [f"{entry.allocated_capital:,.2f} €" for entry in positions],
        "Rentabilidad esperada": [format_percentage(entry.expected_return) for entry in positions],
        "Beta": [format_decimal(entry.beta) for entry in positions],
    })
    st.dataframe(df_positions, hide_index=True, use_container_width=True)

    st.subheader("Distribución de la cartera")
    chart_data = pd.DataFrame(
        {"Peso": [entry.weight for entry in positions]},
        index=[entry.ticker for entry in positions],
    )
    st.bar_chart(chart_data)

    return allocation
