"""Hoja 2: cuestionario de perfil inversor (modelo de 7 dimensiones ponderadas).

Cada pregunta se presenta en lenguaje natural (sin escalas numéricas
visibles) y se traduce internamente a la escala 1-5 mediante
`core.profile_model_config.PROFILE_DIMENSIONS`. El cálculo, la ponderación y
la trazabilidad completa se delegan a `core.risk_profile.calculate_investor_profile`.
"""
from __future__ import annotations

import streamlit as st

from core.profile_model_config import MAX_TOTAL_SCORE, NEUTRAL_DIMENSION_SCORE, PROFILE_DIMENSIONS
from core.risk_profile import calculate_investor_profile

_DEFAULT_OPTION_INDEX = 2  # opción central (puntuación 3) de las 5 disponibles en cada dimensión


def render() -> None:
    """Renderiza el cuestionario, calcula el perfil y muestra el resultado estructurado."""
    st.header("HOJA 2: CUESTIONARIO DE PERFIL INVERSOR")
    st.write(
        "Responda a las siguientes preguntas. Cada una evalúa una dimensión distinta de su "
        "perfil como inversor; sus respuestas se combinan mediante un modelo ponderado y "
        "transparente (puede consultar el desglose completo al final)."
    )

    selected_labels: dict[str, str] = {}
    for dimension in PROFILE_DIMENSIONS:
        option_labels = [option.label for option in dimension.options]
        selected_labels[dimension.key] = st.radio(
            f"**{dimension.name}** — {dimension.question}",
            options=option_labels,
            index=_DEFAULT_OPTION_INDEX,
            key=f"perfil_{dimension.key}",
        )

    result = calculate_investor_profile(selected_labels)
    st.session_state.puntuacion_test = result.total_score
    st.session_state.perfil_calc = result.profile

    st.divider()
    col_res1, col_res2 = st.columns(2)
    col_res1.metric("Puntuación ponderada", f"{result.total_score:.2f} / {MAX_TOTAL_SCORE:.2f}")
    col_res2.success(f"Perfil asignado: **{result.profile.upper()}**")
    st.info(result.explanation)

    if result.strengths:
        st.write("**Fortalezas detectadas:**")
        for strength in result.strengths:
            st.write(f"- {strength}")

    col_risk_up, col_risk_down = st.columns(2)
    with col_risk_up:
        st.write("**Factores que aumentan el riesgo recomendado:**")
        if result.risk_increasing_factors:
            for factor in result.risk_increasing_factors:
                st.write(f"- {factor}")
        else:
            st.caption("Ninguno detectado.")
    with col_risk_down:
        st.write("**Factores que reducen el riesgo recomendado:**")
        if result.risk_decreasing_factors:
            for factor in result.risk_decreasing_factors:
                st.write(f"- {factor}")
        else:
            st.caption("Ninguno detectado.")

    with st.expander("Ver desglose completo del cálculo (trazabilidad por dimensión)"):
        st.dataframe(
            {
                "Dimensión": [c.dimension_name for c in result.dimension_contributions],
                "Respuesta seleccionada": [c.selected_label for c in result.dimension_contributions],
                "Puntuación interna (1-5)": [c.internal_score for c in result.dimension_contributions],
                "Peso": [f"{c.weight:.0%}" for c in result.dimension_contributions],
                "Aporte a la puntuación": [f"{c.weighted_contribution:.3f}" for c in result.dimension_contributions],
            },
            hide_index=True,
            use_container_width=True,
        )
        st.caption(
            f"Puntuación neutra de referencia: {NEUTRAL_DIMENSION_SCORE:.2f}. "
            f"Rango posible de la puntuación ponderada: 1.00 - {MAX_TOTAL_SCORE:.2f}."
        )
