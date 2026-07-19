"""Hoja 1: datos del inversor."""
from __future__ import annotations

import pandas as pd
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
        nombre = st.text_input("Nombre:", value="")
        edad = st.number_input("Edad:", min_value=18, max_value=100, value=None)
        importe = st.number_input("Importe a invertir (€):", min_value=1000, value=10000, step=500)
        plazo = st.number_input("Plazo (años):", min_value=1, max_value=30, value=5)

        st.subheader("Parámetros de mercado (fijos)")
        col_rf, col_rm = st.columns(2)
        col_rf.metric("Tasa libre de riesgo anual (Rf)", format_percentage(config.RISK_FREE_RATE, decimals=1))
        col_rm.metric("Rentabilidad de mercado anual (Rm)", format_percentage(config.MARKET_RETURN, decimals=1))
        st.caption(config.CAPM_ASSUMPTIONS_DISCLAIMER)

        st.info(f"**Perfil calculado actual:** {st.session_state.perfil_calc}")

    with col2:
        st.subheader("Diccionario Metodológico")
        df_dicc = pd.DataFrame({
            "Campo": ["Nombre", "Edad", "Importe", "Plazo", "Rf", "Perfil"],
            "Uso en la interfaz": [
                "Identificación del usuario", "Apoyo al perfil inversor", "Capital inicial",
                "Horizonte temporal", "Activo libre de riesgo", "Resultado cuestionario",
            ],
            "Relación con la metodología": [
                "Pantalla inicial", "MiFID II / idoneidad", "Proyección de valor futuro",
                "Selección de activos", "Ratio de Sharpe", "Recomendación de cartera",
            ],
        })
        st.dataframe(df_dicc, hide_index=True, use_container_width=True)

    return InvestorInputs(
        nombre=nombre,
        edad=edad,
        importe=importe,
        plazo=plazo,
        risk_free_rate=config.RISK_FREE_RATE,
        market_premium=config.MARKET_RISK_PREMIUM,
    )
