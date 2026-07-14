"""Hoja 2: cuestionario de perfil inversor (MiFID II).

Fase 1: se mantienen los sliders 1-5 sin cambios (el rediseño a lenguaje
natural es la observacion 2 del tutor, prevista para la Fase 2). Lo unico que
cambia es que el calculo del perfil ahora se delega a
`core.risk_profile.calculate_investor_profile`, ya cubierto por tests.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.risk_profile import calculate_investor_profile


def render() -> None:
    """Renderiza el cuestionario y actualiza `st.session_state` con el perfil calculado."""
    st.header("HOJA 2: CUESTIONARIO DE PERFIL INVERSOR")
    st.write("Seleccione el nivel (1 al 5) para cada criterio normativo:")

    c1 = st.slider("1. ¿Cuál es su horizonte temporal? (1: ≤1 año | 3: 2-5 años | 5: >8 años)", 1, 5, 3)
    c2 = st.slider("2. ¿Cómo reaccionaría ante una caída del 10%? (1: Vendería | 3: Mantendría | 5: Compraría más)", 1, 5, 3)
    c3 = st.slider("3. % de pérdida temporal aceptada (1: 0-2% | 3: 5-10% | 5: >20%)", 1, 5, 3)
    c4 = st.slider("4. Experiencia en mercados financieros (1: Nula | 3: Media | 5: Muy alta)", 1, 5, 3)
    c5 = st.slider("5. Prioridad para usted de la liquidez (1: Muy alta | 3: Media | 5: Muy baja)", 1, 5, 3)
    c6 = st.slider("6. Objetivo que busca (1: Preservar capital | 3: Equilibrio | 5: Máximo crecimiento)", 1, 5, 3)

    result = calculate_investor_profile([c1, c2, c3, c4, c5, c6])
    st.session_state.puntuacion_test = result.total_score
    st.session_state.perfil_calc = result.profile

    st.divider()
    col_res1, col_res2 = st.columns(2)
    col_res1.metric("Puntuación Total Cuestionario", f"{result.total_score} / 30")
    col_res2.success(f"Perfil Asignado según baremo: **{result.profile.upper()}**")

    with st.expander("Ver baremo de puntuación MiFID II"):
        st.table(pd.DataFrame({
            "Intervalo": ["6 a 13 puntos", "14 a 22 puntos", "23 a 30 puntos"],
            "Perfil Normativo": ["Perfil Conservador", "Perfil Moderado", "Perfil Agresivo"],
        }))
