"""Hoja 4: analisis M1-M7 y cruce de ganadores sectoriales.

Se mantiene la heuristica de seleccion ("mejor banco + mejor aseguradora" por
`Score perfil` minimo, ver `core.capm.score_for_profile`) con mezcla manual
de pesos mediante un slider. La optimizacion real de Markowitz sobre N
activos con `scipy.optimize.minimize` es la observacion 6/9 del tutor y se
implementa en el paquete `portfolio/` en la Fase 3.

Desde la Fase 2, `universe_metrics` ya trae el score y la elegibilidad
calculados para el perfil REAL del inversor (antes, siempre se usaba la
formula de "Moderado"): esta seccion no necesita saber cual es el perfil,
simplemente selecciona el minimo de `Score perfil` por sector.

Correccion funcional de la Fase 1 (se mantiene): la descarga de las series
para el calculo de covarianza del cruce esta cacheada; en el original no lo
estaba, y cualquier interaccion en CUALQUIER pestaña de la app volvia a
disparar 2 llamadas de red sincronas a Yahoo Finance en cada rerun de
Streamlit (causa mas probable de las "interacciones que hacen fallar la app"
reportadas por el tutor, observacion 4/8).
"""
from __future__ import annotations

from typing import cast

import pandas as pd
import streamlit as st

import config
from core import capm
from core.market_data import MarketDataService
from core.models import MarkowitzSelection

# Nota (Subfase 3.1): esta pestaña completa se reescribe en la Subfase 3.5 para usar
# la optimizacion real de Markowitz sobre el universo ampliado. Mientras tanto, la
# etiqueta "M1..MN" se genera dinamicamente (antes era una lista fija de 7 elementos,
# que rompia al ampliar el universo con ETFs: longitud fija != numero real de activos).


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

    # `.loc[idxmin()]` selecciona una única fila por una etiqueta escalar, por lo que
    # en tiempo de ejecución siempre devuelve una Series; se declara explícitamente
    # porque el stub de pandas no puede probarlo de forma estática.
    mejor_banco = cast(pd.Series, bancos_df.loc[bancos_df[config.COL_SCORE_PERFIL].idxmin()])
    mejor_seguro = cast(pd.Series, seguros_df.loc[seguros_df[config.COL_SCORE_PERFIL].idxmin()])

    df_m1_m7 = universe_metrics.copy()
    combinaciones = [f"M{i + 1}" for i in range(len(df_m1_m7))]
    df_m1_m7.insert(0, "Combinación Markowitz", combinaciones)

    resultados_col = []
    for _, row in df_m1_m7.iterrows():
        if row[config.COL_TICKER] == mejor_banco[config.COL_TICKER]:
            resultados_col.append("Mejor banco")
        elif row[config.COL_TICKER] == mejor_seguro[config.COL_TICKER]:
            resultados_col.append("Mejor aseguradora")
        else:
            resultados_col.append("Otro candidato")
    df_m1_m7["Resultado"] = resultados_col

    columnas_vista = [
        "Combinación Markowitz", config.COL_PERFIL_OBJETIVO, config.COL_SECTOR, config.COL_EMPRESA,
        config.COL_TICKER, config.COL_PRODUCTO, config.COL_BETA, config.COL_VOL_ANUAL,
        config.COL_CAPM, config.COL_SHARPE, config.COL_DISTANCIA_BETA, config.COL_SCORE_PERFIL, "Resultado",
    ]
    st.dataframe(df_m1_m7[columnas_vista], hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Simulación de Cruce entre Ganadores Sectoriales")
    col_gb, col_gs = st.columns(2)
    col_gb.success(f"🏆 **Mejor Banco:** {mejor_banco[config.COL_EMPRESA]} ({mejor_banco[config.COL_TICKER]})")
    col_gs.success(f"🏆 **Mejor Aseguradora:** {mejor_seguro[config.COL_EMPRESA]} ({mejor_seguro[config.COL_TICKER]})")

    peso_banco = st.slider("Peso asignado al Banco (%)", 0, 100, 50, step=5) / 100.0
    peso_seguro = 1.0 - peso_banco

    ticker_banco = str(mejor_banco[config.COL_TICKER])
    ticker_seguro = str(mejor_seguro[config.COL_TICKER])
    beta_banco = float(mejor_banco[config.COL_BETA])
    beta_seguro = float(mejor_seguro[config.COL_BETA])
    capm_banco = float(mejor_banco[config.COL_CAPM])
    capm_seguro = float(mejor_seguro[config.COL_CAPM])
    vol_banco = float(mejor_banco[config.COL_VOL_ANUAL])
    vol_seguro = float(mejor_seguro[config.COL_VOL_ANUAL])

    with st.spinner("Calculando covarianza histórica exacta del cruce seleccionado..."):
        covarianza_anualizada = _fetch_annualized_covariance(ticker_banco, ticker_seguro)

    beta_conjunta = (peso_banco * beta_banco) + (peso_seguro * beta_seguro)
    rentabilidad_conjunta = (peso_banco * capm_banco) + (peso_seguro * capm_seguro)
    volatilidad_conjunta = capm.combined_portfolio_volatility(
        vol_banco, peso_banco, vol_seguro, peso_seguro, covarianza_anualizada,
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
