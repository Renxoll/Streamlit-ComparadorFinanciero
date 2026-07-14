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
        f"Filtrado metodológico para el perfil {investor_profile}, horizonte de {plazo} años, "
        "bajo modelo CAPM con datos reales de mercado."
    )

    display_df = universe_metrics.copy()
    decimal_columns = [
        config.COL_BETA, config.COL_DISTANCIA_BETA, config.COL_VOL_DIARIA,
        config.COL_VOL_ANUAL, config.COL_SHARPE, config.COL_SCORE_PERFIL,
    ]
    for column in decimal_columns:
        display_df[column] = display_df[column].map(format_decimal)
    display_df[config.COL_CAPM] = display_df[config.COL_CAPM].map(format_percentage)

    st.dataframe(display_df, hide_index=True, use_container_width=True)
