"""Generacion del PDF de resumen ejecutivo."""
from __future__ import annotations

import pandas as pd
from fpdf import FPDF


def build_summary_pdf(summary_df: pd.DataFrame) -> bytes:
    """Construye el PDF de la ficha de recomendacion a partir de la tabla resumen.

    Nota: el contenido textual (branding "Universidad de Leon - MUCAF") se
    mantiene sin cambios en esta fase; se retira en la Fase 5 junto con el
    resto de referencias al TFM (observacion 1 del tutor).
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, "UNIVERSIDAD DE LEON - MUCAF", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Ficha de Recomendacion - Trabajo Fin de Master", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 10)
    for _, row in summary_df.iterrows():
        concepto = str(row["Concepto Metodológico"]).encode("latin-1", "replace").decode("latin-1")
        valor = str(row["Valor Asignado"]).encode("latin-1", "replace").decode("latin-1")
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(75, 8, concepto, border=1)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(115, 8, valor, border=1, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
