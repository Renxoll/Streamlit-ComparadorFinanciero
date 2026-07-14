"""Hoja 6: resumen final y exportacion a PDF."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.models import InvestorInputs, MarkowitzSelection
from reports.pdf_export import build_summary_pdf


def render(investor: InvestorInputs, selection: MarkowitzSelection) -> None:
    """Renderiza la tarjeta resumen y el boton de descarga del PDF ejecutivo."""
    st.header("HOJA 6: RESUMEN FINAL DEL SISTEMA DE RECOMENDACIÓN")

    df_resumen_card = pd.DataFrame({
        "Concepto Metodológico": [
            "Usuario", "Perfil inversor", "Universo analizado",
            "Número de empresas candidatas", "Criterio de beta",
            "Mejor banco", "Mejor aseguradora", "Modelo de rentabilidad",
            "Criterio de selección", "Observación",
        ],
        "Valor Asignado": [
            investor.nombre, st.session_state.perfil_calc, "Bancos y aseguradoras de la Unión Europea",
            "7", "Beta cercana a 1 (Moderado)",
            selection.mejor_banco["Empresa"], selection.mejor_seguro["Empresa"], "CAPM",
            "Menor score moderado por sector", "M1-M7 representan empresas candidatas, no combinaciones de pesos",
        ],
    })

    col_card, col_pdf = st.columns([2, 1])
    with col_card:
        st.table(df_resumen_card)

    with col_pdf:
        st.write("### Exportación Documental")
        st.write("Genera el acta oficial de resultados para incorporar como anexo en la memoria del TFM.")
        st.download_button(
            label="📥 Descargar Ficha de Resultados (PDF)",
            data=build_summary_pdf(df_resumen_card),
            file_name="Resumen_Ejecutivo_TFM.pdf",
            mime="application/pdf",
        )
