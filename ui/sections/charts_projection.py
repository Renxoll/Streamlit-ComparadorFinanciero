"""Hoja 5: proyeccion y graficos.

Fase 1: se mantiene la formula de proyeccion original, que aplica el capital
COMPLETO a cada escenario (banco solo / seguro solo / cartera combinada). La
correccion para proyectar el capital efectivamente asignado a cada activo
(observacion 7 del tutor) se implementa en la Fase 4.

Nota de auditoria (se corrige tambien en la Fase 4, no aqui): la fila
"Referencia conjunta" de la tabla comparativa combina una rentabilidad
calculada siempre a pesos 50/50 con una volatilidad conjunta calculada con
los pesos reales del slider de la Hoja 4 — esa inconsistencia ya existia en
el `app.py` original y se preserva intencionadamente en esta fase para no
alterar el comportamiento visible.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from core.models import InvestorInputs, MarkowitzSelection
from core.projections import blended_annual_rate, project_compound_growth

_PESO_REFERENCIA_50_50 = 0.5


def render(investor: InvestorInputs, selection: MarkowitzSelection) -> None:
    """Renderiza las proyecciones de capital y la tabla comparativa de indicadores."""
    st.header("HOJA 5: VISUALIZACIÓN DE RESULTADOS")

    anios = list(range(int(investor.plazo) + 1))
    proy_banco = project_compound_growth(
        investor.importe, selection.mejor_banco[config.COL_CAPM], investor.plazo
    )
    proy_seguro = project_compound_growth(
        investor.importe, selection.mejor_seguro[config.COL_CAPM], investor.plazo
    )

    rentabilidad_50_50 = blended_annual_rate(
        selection.mejor_banco[config.COL_CAPM], _PESO_REFERENCIA_50_50,
        selection.mejor_seguro[config.COL_CAPM], _PESO_REFERENCIA_50_50,
    )
    proy_cartera = project_compound_growth(investor.importe, rentabilidad_50_50, investor.plazo)

    df_proyeccion = pd.DataFrame({
        "Año": anios,
        f"{selection.mejor_banco[config.COL_EMPRESA]}": proy_banco,
        f"{selection.mejor_seguro[config.COL_EMPRESA]}": proy_seguro,
        "Cartera Referencial (50% / 50%)": proy_cartera,
    })

    col_tabla_proy, col_indicadores = st.columns([1.3, 1.7])

    with col_tabla_proy:
        st.subheader("Proyección de Capital (€)")
        st.dataframe(
            df_proyeccion.style.format({col: "{:,.2f} €" for col in df_proyeccion.columns if col != "Año"}),
            hide_index=True,
        )

    with col_indicadores:
        st.subheader("Tabla de Resumen Comparativo")
        sharpe_referencia = (
            (rentabilidad_50_50 - investor.risk_free_rate) / selection.volatilidad_conjunta
            if selection.volatilidad_conjunta
            else 0.0
        )
        df_ind = pd.DataFrame({
            "Indicador": ["Empresa / producto", "Sector", "Beta", "Volatilidad anual", "Rentabilidad CAPM", "Sharpe individual"],
            "Banco seleccionado": [
                selection.mejor_banco[config.COL_EMPRESA], "Banco",
                f"{selection.mejor_banco[config.COL_BETA]:.4f}",
                f"{selection.mejor_banco[config.COL_VOL_ANUAL]:.4f}",
                f"{selection.mejor_banco[config.COL_CAPM] * 100:.2f}%",
                f"{selection.mejor_banco[config.COL_SHARPE]:.4f}",
            ],
            "Aseguradora seleccionada": [
                selection.mejor_seguro[config.COL_EMPRESA], "Seguros",
                f"{selection.mejor_seguro[config.COL_BETA]:.4f}",
                f"{selection.mejor_seguro[config.COL_VOL_ANUAL]:.4f}",
                f"{selection.mejor_seguro[config.COL_CAPM] * 100:.2f}%",
                f"{selection.mejor_seguro[config.COL_SHARPE]:.4f}",
            ],
            "Referencia conjunta (50/50)": [
                f"{selection.mejor_banco[config.COL_EMPRESA]} + {selection.mejor_seguro[config.COL_EMPRESA]}",
                "Banco + Seguros",
                f"{(selection.mejor_banco[config.COL_BETA] + selection.mejor_seguro[config.COL_BETA]) / 2:.4f}",
                f"{selection.volatilidad_conjunta:.4f}",
                f"{rentabilidad_50_50 * 100:.2f}%",
                f"{sharpe_referencia:.4f}",
            ],
            "Observación": ["Selección final por sector", "Universo UE (bancos y aseguradoras)", "Según criterio del perfil actual", "Riesgo diversificado", "Modelo CAPM", "Rentabilidad-Riesgo"],
        })
        st.dataframe(df_ind, hide_index=True, use_container_width=True)

    st.subheader("Evolución temporal del capital invertido")
    st.line_chart(df_proyeccion.set_index("Año"))
