"""Hoja 3: productos elegibles por perfil."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from ui.components import format_decimal, format_percentage


def render(universe_metrics: pd.DataFrame, plazo: int, investor_profile: str) -> None:
    """Muestra la tabla de metricas CAPM de todo el universo de activos."""
    st.header("HOJA 3: OPCIONES DE EMPRESAS Y PRODUCTOS - BANCOS Y SEGUROS UE")
    st.caption(
        f"Todos los activos del universo de inversión, con su comportamiento histórico frente al "
        f"mercado (últimos {config.HISTORY_PERIOD.replace('y', ' años')}) y su rentabilidad esperada. "
        f"Perfil actual: {investor_profile}, horizonte de {plazo} años."
    )

    display_df = universe_metrics.copy()
    decimal_columns = [
        config.COL_BETA, config.COL_DISTANCIA_BETA, config.COL_VOL_DIARIA,
        config.COL_VOL_ANUAL, config.COL_SHARPE, config.COL_SCORE_PERFIL,
    ]
    for column in decimal_columns:
        display_df[column] = display_df[column].map(format_decimal)
    display_df[config.COL_CAPM] = display_df[config.COL_CAPM].map(format_percentage)

    st.dataframe(
        display_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            config.COL_BETA: st.column_config.Column(
                help="Sensibilidad histórica del activo frente al mercado europeo. Beta = 1 significa "
                "que se mueve igual que el mercado; por encima, más brusco; por debajo, más suave."
            ),
            config.COL_DISTANCIA_BETA: st.column_config.Column(
                help="Diferencia entre la Beta del activo y 1 (el comportamiento del mercado). Cuanto "
                "más baja, más se parece este activo al mercado en su conjunto."
            ),
            config.COL_VOL_DIARIA: st.column_config.Column(
                help="Variación típica del precio de un día para otro, en los últimos 5 años."
            ),
            config.COL_VOL_ANUAL: st.column_config.Column(
                help="La misma variación típica, expresada en términos anuales (más fácil de comparar "
                "con la rentabilidad esperada)."
            ),
            config.COL_CAPM: st.column_config.Column(
                help="Rentabilidad anual que cabría esperar de este activo según su Beta (modelo CAPM)."
            ),
            config.COL_SHARPE: st.column_config.Column(
                help="Rentabilidad esperada por encima de la tasa libre de riesgo, por cada unidad de "
                "volatilidad asumida. Más alto es mejor."
            ),
            config.COL_SCORE_PERFIL: st.column_config.Column(
                help="Puntuación interna usada solo para ordenar los activos según tu perfil; no "
                "determina por sí sola qué entra en tu cartera final (eso lo decide la Hoja 4)."
            ),
            config.COL_PERFIL_RIESGO_BETA: st.column_config.Column(
                help="Clasificación de riesgo del activo según su Beta (Conservador / Moderado / "
                "Agresivo). Es solo informativa: no incluye ni excluye activos de tu cartera."
            ),
        },
    )
