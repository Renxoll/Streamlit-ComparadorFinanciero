"""Hoja 1: datos del inversor."""
from __future__ import annotations

import streamlit as st

import config
from core.models import InvestorInputs
from ui.components import format_percentage


def render() -> InvestorInputs:
    """Renderiza el formulario de datos del inversor y devuelve los valores capturados."""
    st.header("HOJA 1: DATOS DEL INVERSOR")
    col1, col_space, col2 = st.columns([1.2, 0.2, 1.6])

    with col1:
        st.subheader("Parámetros de Entrada")
        nombre = st.text_input(
            "Nombre:", value="",
            help="Se usa para identificarte en el resumen final (Hoja 6) y en el PDF exportable.",
        )
        edad = st.number_input(
            "Edad:", min_value=18, max_value=100, value=None,
            help="Dato informativo: no interviene en el cálculo de tu perfil de riesgo ni en la cartera.",
        )
        importe = st.number_input(
            "Importe a invertir (€):", min_value=1000, value=10000, step=500,
            help="Capital que se repartirá entre los activos de la cartera que se calcule para ti.",
        )
        plazo = st.number_input(
            "Plazo (años):", min_value=1, max_value=30, value=5,
            help="Horizonte temporal de tu inversión; se usa para proyectar la evolución del capital (Hoja 5).",
        )

        st.subheader("Parámetros de mercado (fijos)")
        col_rf, col_rm = st.columns(2)
        col_rf.metric(
            "Tasa libre de riesgo anual (Rf)", format_percentage(config.RISK_FREE_RATE, decimals=1),
            help="Rentabilidad de referencia de un activo sin riesgo; punto de partida del cálculo de rentabilidad esperada de cada activo.",
        )
        col_rm.metric(
            "Rentabilidad de mercado anual (Rm)", format_percentage(config.MARKET_RETURN, decimals=1),
            help="Rentabilidad histórica de referencia del mercado europeo; junto con Rf determina la prima de riesgo de mercado.",
        )
        st.caption(config.CAPM_ASSUMPTIONS_DISCLAIMER)

    with col2:
        st.subheader("¿Cómo funciona esta herramienta?")
        st.caption(
            "Tu recomendación de inversión se construye en varios pasos, cada uno en su propia "
            "pestaña. El perfil de riesgo y la cartera resultante se calculan y se muestran una "
            "única vez, en el paso correspondiente."
        )
        st.markdown(
            "1. **Datos del inversor** (aquí) — tu capital y tu horizonte temporal.\n"
            "2. **Cuestionario** — tus respuestas determinan tu perfil de riesgo.\n"
            "3. **Productos por perfil** — activos disponibles y su comportamiento frente al mercado.\n"
            "4. **Cartera Markowitz** — optimización y pesos de la cartera para tu perfil.\n"
            "5. **Gráficos** — proyección del capital invertido a lo largo del plazo elegido.\n"
            "6. **Resumen** — ficha final descargable en PDF."
        )

    return InvestorInputs(
        nombre=nombre,
        edad=edad,
        importe=importe,
        plazo=plazo,
        risk_free_rate=config.RISK_FREE_RATE,
        market_premium=config.MARKET_RISK_PREMIUM,
    )
