"""Punto de entrada de la aplicacion.

Orquesta la carga de datos y el renderizado de cada seccion. No contiene
logica financiera propia: todos los calculos viven en `core/`, y toda la
presentacion vive en `ui/sections/`.
"""
from __future__ import annotations

import os

import certifi

# Configurar certificados de seguridad ANTES de importar yfinance
os.environ["CURL_CA_BUNDLE"] = certifi.where()
os.environ["SSL_CERT_FILE"] = certifi.where()

import pandas as pd
import streamlit as st

import config
from core import capm
from core.market_data import MarketDataService
from ui.sections import (
    charts_projection,
    investor_data,
    markowitz_portfolio,
    products_by_profile,
    questionnaire,
    summary_export,
)

st.set_page_config(page_title=config.APP_TITLE, layout="wide")

st.title("Sistema de Recomendación y Optimización de Inversión (TFM)")
st.caption("Máster Universitario en Ciencias Actuariales y Financieras (MUCAF) - Universidad de León")

# --- Inicialización de memoria de sesión ---
if "perfil_calc" not in st.session_state:
    st.session_state.perfil_calc = config.PERFIL_MODERADO
if "puntuacion_test" not in st.session_state:
    st.session_state.puntuacion_test = 3.0  # puntuacion neutra en la escala 1.0-5.0 (antes: 18 sobre 30)


@st.cache_data(ttl=3600, show_spinner="Descargando datos históricos y procesando matrices de covarianza...")
def _cached_universe_metrics(risk_free_rate: float, market_premium: float, investor_profile: str) -> pd.DataFrame:
    """Envoltorio cacheado de `capm.build_universe_metrics`.

    Desde la Fase 2, `investor_profile` forma parte de la clave de cache: el
    score y la elegibilidad de cada activo dependen del perfil calculado, no
    solo de Rf y la prima de mercado.
    """
    service = MarketDataService()
    return capm.build_universe_metrics(
        service=service,
        universe=config.UNIVERSO_TFM,
        benchmark_ticker=config.BENCHMARK_TICKER,
        risk_free_rate=risk_free_rate,
        market_premium=market_premium,
        investor_profile=investor_profile,
    )


tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1. Datos Inversor",
    "2. Cuestionario",
    "3. Productos Perfil",
    "4. Cartera Markowitz",
    "5. Gráficos",
    "6. Resumen Interfaz",
])

with tab1:
    investor = investor_data.render()

with tab2:
    questionnaire.render()

# Se calcula DESPUES del cuestionario: el universo depende del perfil real
# calculado en la Hoja 2 (st.session_state.perfil_calc), no de un valor fijo.
universe_metrics = _cached_universe_metrics(
    investor.risk_free_rate, investor.market_premium, st.session_state.perfil_calc
)

with tab3:
    products_by_profile.render(universe_metrics, investor.plazo, st.session_state.perfil_calc)

with tab4:
    allocation = markowitz_portfolio.render(universe_metrics, investor, st.session_state.perfil_calc)

# `allocation` es None solo si las restricciones del perfil no son factibles con el
# universo actual (ver InfeasibleConstraintsError en Hoja 4); en ese caso no hay
# cartera que proyectar ni resumir.
with tab5:
    if allocation is not None:
        charts_projection.render(investor, allocation)
    else:
        st.info("No hay una cartera optimizada disponible para este perfil (ver Hoja 4).")

with tab6:
    if allocation is not None:
        summary_export.render(investor, allocation)
    else:
        st.info("No hay una cartera optimizada disponible para este perfil (ver Hoja 4).")
