"""Hoja 1: datos del inversor."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.models import InvestorInputs


def render() -> InvestorInputs:
    """Renderiza el formulario de datos del inversor y devuelve los valores capturados."""
    st.header("HOJA 1: DATOS DEL INVERSOR")
    col1, col_space, col2 = st.columns([1.2, 0.2, 1.6])

    with col1:
        st.subheader("Parámetros de Entrada")
        nombre = st.text_input("Nombre:", value="Jimena Triguero")
        edad = st.number_input("Edad:", min_value=18, max_value=100, value=34)
        importe = st.number_input("Importe a invertir (€):", min_value=1000, value=10000, step=500)
        plazo = st.number_input("Plazo (años):", min_value=1, max_value=30, value=5)
        risk_free_rate = st.number_input("Tasa libre de riesgo anual (Rf):", value=0.0200, format="%.4f")
        market_premium = st.number_input("Prima de riesgo de mercado (Rm - Rf):", value=0.0550, format="%.4f")

        st.info(f"**Perfil calculado actual:** {st.session_state.perfil_calc}")

    with col2:
        st.subheader("Diccionario Metodológico (TFM)")
        df_dicc = pd.DataFrame({
            "Campo": ["Nombre", "Edad", "Importe", "Plazo", "Rf", "Perfil"],
            "Uso en la interfaz": [
                "Identificación del usuario", "Apoyo al perfil inversor", "Capital inicial",
                "Horizonte temporal", "Activo libre de riesgo", "Resultado cuestionario",
            ],
            "Relación con el TFM": [
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
        risk_free_rate=risk_free_rate,
        market_premium=market_premium,
    )
