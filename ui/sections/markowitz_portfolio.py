"""Hoja 4: analisis M1-M7 y cruce de ganadores sectoriales.

Fase 1: se mantiene la heuristica original de seleccion ("mejor banco + mejor
aseguradora" por `Score moderado` minimo) con mezcla manual de pesos mediante
un slider. La optimizacion real de Markowitz sobre N activos con
`scipy.optimize.minimize` es la observacion 6/9 del tutor y se implementa en
el paquete `portfolio/` en la Fase 3.

La unica correccion funcional de esta fase es que la descarga de las series
para el calculo de covarianza del cruce ahora esta cacheada: en el original
no lo estaba, y cualquier interaccion en CUALQUIER pestaña de la app volvia a
disparar 2 llamadas de red sincronas a Yahoo Finance en cada rerun de
Streamlit (causa mas probable de las "interacciones que hacen fallar la app"
reportadas por el tutor, observacion 4/8).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from core import capm
from core.market_data import MarketDataService
from core.models import MarkowitzSelection

_COMBINACIONES_MARKOWITZ = ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]


@st.cache_data(ttl=3600, show_spinner="Calculando covarianza histórica exacta del cruce seleccionado...")
def _fetch_annualized_covariance(ticker_a: str, ticker_b: str, period: str = config.HISTORY_PERIOD) -> float:
    """Descarga (cacheada) las series de dos activos y calcula su covarianza anualizada."""
    service = MarketDataService()
    returns_a = service.get_returns(ticker_a, period)
    returns_b = service.get_returns(ticker_b, period)
    return capm.annualized_covariance(returns_a, returns_b)


def render(universe_metrics: pd.DataFrame, risk_free_rate: float) -> MarkowitzSelection:
    """Renderiza el analisis M1-M7 y el cruce sectorial; devuelve la seleccion resultante."""
    st.header("HOJA 4: ANÁLISIS M1-M7 DE EMPRESAS CANDIDATAS")

    bancos_df = universe_metrics[universe_metrics[config.COL_SECTOR] == "Banco"]
    seguros_df = universe_metrics[universe_metrics[config.COL_SECTOR] == "Seguros"]

    mejor_banco = bancos_df.loc[bancos_df[config.COL_SCORE_MODERADO].idxmin()]
    mejor_seguro = seguros_df.loc[seguros_df[config.COL_SCORE_MODERADO].idxmin()]

    df_m1_m7 = universe_metrics.copy()
    df_m1_m7.insert(0, "Combinación Markowitz", _COMBINACIONES_MARKOWITZ)

    resultados_col = []
    for _, row in df_m1_m7.iterrows():
        if row[config.COL_TICKER] == mejor_banco[config.COL_TICKER]:
            resultados_col.append("Mejor banco")
        elif row[config.COL_TICKER] == mejor_seguro[config.COL_TICKER]:
            resultados_col.append("Mejor aseguradora")
        else:
            resultados_col.append("Candidato moderado")
    df_m1_m7["Resultado"] = resultados_col

    columnas_vista = [
        "Combinación Markowitz", config.COL_PERFIL_OBJETIVO, config.COL_SECTOR, config.COL_EMPRESA,
        config.COL_TICKER, config.COL_PRODUCTO, config.COL_BETA, config.COL_VOL_ANUAL,
        config.COL_CAPM, config.COL_SHARPE, config.COL_DISTANCIA_BETA, config.COL_SCORE_MODERADO, "Resultado",
    ]
    st.dataframe(df_m1_m7[columnas_vista], hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Simulación de Cruce entre Ganadores Sectoriales")
    col_gb, col_gs = st.columns(2)
    col_gb.success(f"🏆 **Mejor Banco:** {mejor_banco[config.COL_EMPRESA]} ({mejor_banco[config.COL_TICKER]})")
    col_gs.success(f"🏆 **Mejor Aseguradora:** {mejor_seguro[config.COL_EMPRESA]} ({mejor_seguro[config.COL_TICKER]})")

    peso_banco = st.slider("Peso asignado al Banco (%)", 0, 100, 50, step=5) / 100.0
    peso_seguro = 1.0 - peso_banco

    with st.spinner("Calculando covarianza histórica exacta del cruce seleccionado..."):
        covarianza_anualizada = _fetch_annualized_covariance(
            mejor_banco[config.COL_TICKER], mejor_seguro[config.COL_TICKER]
        )

    beta_conjunta = (peso_banco * mejor_banco[config.COL_BETA]) + (peso_seguro * mejor_seguro[config.COL_BETA])
    rentabilidad_conjunta = (peso_banco * mejor_banco[config.COL_CAPM]) + (peso_seguro * mejor_seguro[config.COL_CAPM])
    volatilidad_conjunta = capm.combined_portfolio_volatility(
        mejor_banco[config.COL_VOL_ANUAL], peso_banco,
        mejor_seguro[config.COL_VOL_ANUAL], peso_seguro,
        covarianza_anualizada,
    )
    sharpe_conjunto = capm.sharpe_ratio(rentabilidad_conjunta, risk_free_rate, volatilidad_conjunta)

    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    c_m1.metric("Distribución", f"{int(peso_banco * 100)}% / {int(peso_seguro * 100)}%")
    c_m2.metric("Beta Conjunta", f"{beta_conjunta:.4f}")
    c_m3.metric("Rentabilidad CAPM", f"{rentabilidad_conjunta * 100:.2f}%")
    c_m4.metric("Sharpe Conjunto", f"{sharpe_conjunto:.4f}")

    return MarkowitzSelection(
        mejor_banco=mejor_banco,
        mejor_seguro=mejor_seguro,
        peso_banco=peso_banco,
        peso_seguro=peso_seguro,
        beta_conjunta=beta_conjunta,
        rentabilidad_conjunta=rentabilidad_conjunta,
        volatilidad_conjunta=volatilidad_conjunta,
        sharpe_conjunto=sharpe_conjunto,
        covarianza_anualizada=covarianza_anualizada,
    )
