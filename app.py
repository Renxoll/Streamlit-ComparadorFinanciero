import os
import certifi

# Configurar certificados de seguridad ANTES de importar yfinance
os.environ["CURL_CA_BUNDLE"] = certifi.where()
os.environ["SSL_CERT_FILE"] = certifi.where()

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from fpdf import FPDF
from scipy.optimize import minimize

st.set_page_config(page_title="TFM - Carteras e Interfaz Inversor", layout="wide")

st.title("Sistema de Recomendación y Optimización de Inversión (TFM)")
st.caption("Máster Universitario en Ciencias Actuariales y Financieras (MUCAF) - Universidad de León")

# --- 1. UNIVERSO CERRADO DEL TFM (Solo Nombres y Tickers) ---
UNIVERSO_TFM = [
    {"Sector": "Banco", "Empresa": "Banco Santander", "Ticker": "SAN.MC", "Producto": "Acción ordinaria - entidad bancaria"},
    {"Sector": "Banco", "Empresa": "BNP Paribas", "Ticker": "BNP.PA", "Producto": "Acción ordinaria - entidad bancaria"},
    {"Sector": "Banco", "Empresa": "ING Groep", "Ticker": "INGA.AS", "Producto": "Acción ordinaria - entidad bancaria"},
    {"Sector": "Seguros", "Empresa": "Allianz SE", "Ticker": "ALV.DE", "Producto": "Acción ordinaria - entidad aseguradora"},
    {"Sector": "Seguros", "Empresa": "AXA SA", "Ticker": "CS.PA", "Producto": "Acción ordinaria - entidad aseguradora"},
    {"Sector": "Seguros", "Empresa": "Mapfre SA", "Ticker": "MAP.MC", "Producto": "Acción ordinaria - entidad aseguradora"},
    {"Sector": "Seguros", "Empresa": "Assicurazioni Generali", "Ticker": "G.MI", "Producto": "Acción ordinaria - entidad aseguradora"}
]

# Inicialización de memoria de sesión
if 'perfil_calc' not in st.session_state: st.session_state.perfil_calc = "Moderado"
if 'puntuacion_test' not in st.session_state: st.session_state.puntuacion_test = 18

# --- MOTOR DE EXTRACCIÓN Y CÁLCULO DINÁMICO (YAHOO FINANCE) ---
@st.cache_data(ttl=3600, show_spinner="Descargando datos históricos y procesando matrices de covarianza...")
def procesar_universo(rf, prima_mercado):
    filas = []
    
    # 1. Descargar el Benchmark (Euro Stoxx 50) para el cálculo de la Beta
    df_bench = yf.Ticker("^STOXX50E").history(period="5y")['Close']
    ret_bench = df_bench.pct_change().dropna()
    
    for item in UNIVERSO_TFM:
        ticker = item["Ticker"]
        
        # 2. Descargar activo individual
        df_asset = yf.Ticker(ticker).history(period="5y")['Close']
        ret_asset = df_asset.pct_change().dropna()
        
        # 3. Alinear fechas (Inner Join temporal)
        df_aligned = pd.concat([ret_asset, ret_bench], axis=1).dropna()
        df_aligned.columns = ['Asset', 'Bench']
        
        # 4. Cálculos Actuariales Reales
        vol_diaria = df_aligned['Asset'].std()
        vol_anual = vol_diaria * np.sqrt(252)
        
        # Matriz de covarianzas para hallar la Beta matemática
        cov_matrix = df_aligned.cov()
        cov_i_m = cov_matrix.iloc[0, 1]
        var_m = cov_matrix.iloc[1, 1]
        
        beta = cov_i_m / var_m if var_m != 0 else 1.0
        
        # 5. Cálculos derivados
        dist_beta = abs(beta - 1.0)
        capm = rf + (beta * prima_mercado)
        sharpe = (capm - rf) / vol_anual
        score_mod = dist_beta + vol_anual

        filas.append({
            "Perfil objetivo": "Moderado",
            "Sector": item["Sector"],
            "Empresa": item["Empresa"],
            "Ticker Yahoo": ticker,
            "Producto financiero": item["Producto"],
            "Beta": beta,
            "Distancia a β=1": dist_beta,
            "Volatilidad diaria 5 años": vol_diaria,
            "Volatilidad anual 5 años": vol_anual,
            "Rentabilidad CAPM": capm,
            "Sharpe individual CAPM": sharpe,
            "Score moderado": score_mod,
            "Elegible perfil moderado": "Sí" if (beta >= 0.75 and beta <= 1.25) else "No"
        })
    return pd.DataFrame(filas)

# --- LAS 6 PESTAÑAS EXACTAS DEL EXCEL ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1. Datos Inversor", 
    "2. Cuestionario", 
    "3. Productos Perfil", 
    "4. Cartera Markowitz", 
    "5. Gráficos", 
    "6. Resumen Interfaz"
])

# ==========================================
# HOJA 1: DATOS DEL INVERSOR
# ==========================================
with tab1:
    st.header("HOJA 1: DATOS DEL INVERSOR")
    col1, col_space, col2 = st.columns([1.2, 0.2, 1.6])
    
    with col1:
        st.subheader("Parámetros de Entrada")
        nombre = st.text_input("Nombre:", value="Jimena Triguero")
        edad = st.number_input("Edad:", min_value=18, max_value=100, value=34)
        importe = st.number_input("Importe a invertir (€):", min_value=1000, value=10000, step=500)
        plazo = st.number_input("Plazo (años):", min_value=1, max_value=30, value=5)
        rf = st.number_input("Tasa libre de riesgo anual (Rf):", value=0.0200, format="%.4f")
        prima = st.number_input("Prima de riesgo de mercado (Rm - Rf):", value=0.0550, format="%.4f")
        
        st.info(f"**Perfil calculado actual:** {st.session_state.perfil_calc}")
        
    with col2:
        st.subheader("Diccionario Metodológico (TFM)")
        df_dicc = pd.DataFrame({
            "Campo": ["Nombre", "Edad", "Importe", "Plazo", "Rf", "Perfil"],
            "Uso en la interfaz": ["Identificación del usuario", "Apoyo al perfil inversor", "Capital inicial", "Horizonte temporal", "Activo libre de riesgo", "Resultado cuestionario"],
            "Relación con el TFM": ["Pantalla inicial", "MiFID II / idoneidad", "Proyección de valor futuro", "Selección de activos", "Ratio de Sharpe", "Recomendación de cartera"]
        })
        st.dataframe(df_dicc, hide_index=True, use_container_width=True)

# Ejecutar el motor de cálculo y guardar en variable
df_universo = procesar_universo(rf, prima)

# ==========================================
# HOJA 2: CUESTIONARIO MiFID II
# ==========================================
with tab2:
    st.header("HOJA 2: CUESTIONARIO DE PERFIL INVERSOR")
    st.write("Seleccione el nivel (1 al 5) para cada criterio normativo:")
    
    c1 = st.slider("1. ¿Cuál es su horizonte temporal? (1: ≤1 año | 3: 2-5 años | 5: >8 años)", 1, 5, 3)
    c2 = st.slider("2. ¿Cómo reaccionaría ante una caída del 10%? (1: Vendería | 3: Mantendría | 5: Compraría más)", 1, 5, 3)
    c3 = st.slider("3. % de pérdida temporal aceptada (1: 0-2% | 3: 5-10% | 5: >20%)", 1, 5, 3)
    c4 = st.slider("4. Experiencia en mercados financieros (1: Nula | 3: Media | 5: Muy alta)", 1, 5, 3)
    c5 = st.slider("5. Prioridad para usted de la liquidez (1: Muy alta | 3: Media | 5: Muy baja)", 1, 5, 3)
    c6 = st.slider("6. Objetivo que busca (1: Preservar capital | 3: Equilibrio | 5: Máximo crecimiento)", 1, 5, 3)
    
    total_puntos = c1 + c2 + c3 + c4 + c5 + c6
    st.session_state.puntuacion_test = total_puntos
    
    if total_puntos <= 13: p_calc = "Conservador"
    elif total_puntos <= 22: p_calc = "Moderado"
    else: p_calc = "Agresivo"
    
    st.session_state.perfil_calc = p_calc
    
    st.divider()
    col_res1, col_res2 = st.columns(2)
    col_res1.metric("Puntuación Total Cuestionario", f"{total_puntos} / 30")
    col_res2.success(f"Perfil Asignado según baremo: **{p_calc.upper()}**")
    
    with st.expander("Ver baremo de puntuación MiFID II"):
        st.table(pd.DataFrame({
            "Intervalo": ["6 a 13 puntos", "14 a 22 puntos", "23 a 30 puntos"],
            "Perfil Normativo": ["Perfil Conservador", "Perfil Moderado", "Perfil Agresivo"]
        }))

# ==========================================
# HOJA 3: PRODUCTOS POR PERFIL
# ==========================================
with tab3:
    st.header("HOJA 3: OPCIONES DE EMPRESAS Y PRODUCTOS - BANCOS Y SEGUROS UE")
    st.caption(f"Filtrado metodológico para horizonte de {plazo} años bajo modelo CAPM con datos reales de mercado.")
    
    df_h3 = df_universo.copy()
    # Formateo visual
    df_mostrar_h3 = df_h3.copy()
    for col in ["Beta", "Distancia a β=1"]: df_mostrar_h3[col] = df_mostrar_h3[col].map("{:.4f}".format)
    for col in ["Volatilidad diaria 5 años", "Volatilidad anual 5 años", "Sharpe individual CAPM", "Score moderado"]: df_mostrar_h3[col] = df_mostrar_h3[col].map("{:.4f}".format)
    df_mostrar_h3["Rentabilidad CAPM"] = (df_mostrar_h3["Rentabilidad CAPM"] * 100).map("{:.2f}%".format)
    
    st.dataframe(df_mostrar_h3, hide_index=True, use_container_width=True)

# ==========================================
# HOJA 4: CARTERA MARKOWITZ (M1 - M7)
# ==========================================
with tab4:
    st.header("HOJA 4: ANÁLISIS M1-M7 DE EMPRESAS CANDIDATAS")
    
    # Selección matemática del ganador
    bancos_df = df_universo[df_universo["Sector"] == "Banco"]
    seguros_df = df_universo[df_universo["Sector"] == "Seguros"]
    
    mejor_banco = bancos_df.loc[bancos_df["Score moderado"].idxmin()]
    mejor_seguro = seguros_df.loc[seguros_df["Score moderado"].idxmin()]
    
    df_m1_m7 = df_universo.copy()
    df_m1_m7.insert(0, "Combinación Markowitz", ["M1", "M2", "M3", "M4", "M5", "M6", "M7"])
    
    resultados_col = []
    for idx, row in df_m1_m7.iterrows():
        if row["Ticker Yahoo"] == mejor_banco["Ticker Yahoo"]: resultados_col.append("Mejor banco")
        elif row["Ticker Yahoo"] == mejor_seguro["Ticker Yahoo"]: resultados_col.append("Mejor aseguradora")
        else: resultados_col.append("Candidato moderado")
    df_m1_m7["Resultado"] = resultados_col
    
    df_v4 = df_m1_m7[["Combinación Markowitz", "Perfil objetivo", "Sector", "Empresa", "Ticker Yahoo", "Producto financiero", "Beta", "Volatilidad anual 5 años", "Rentabilidad CAPM", "Sharpe individual CAPM", "Distancia a β=1", "Score moderado", "Resultado"]]
    st.dataframe(df_v4, hide_index=True, use_container_width=True)
    
    st.divider()
    st.subheader("Simulación de Cruce entre Ganadores Sectoriales")
    col_gb, col_gs = st.columns(2)
    col_gb.success(f"🏆 **Mejor Banco:** {mejor_banco['Empresa']} ({mejor_banco['Ticker Yahoo']})")
    col_gs.success(f"🏆 **Mejor Aseguradora:** {mejor_seguro['Empresa']} ({mejor_seguro['Ticker Yahoo']})")
    
    w_b = st.slider("Peso asignado al Banco (%)", 0, 100, 50, step=5) / 100.0
    w_s = 1.0 - w_b
    
    # Descargar serie para cruce dinámico de covarianza de la cartera óptima
    with st.spinner("Calculando covarianza histórica exacta del cruce seleccionado..."):
        serie_banco = yf.Ticker(mejor_banco["Ticker Yahoo"]).history(period="5y")['Close'].pct_change().dropna()
        serie_seguro = yf.Ticker(mejor_seguro["Ticker Yahoo"]).history(period="5y")['Close'].pct_change().dropna()
        
        df_cruce = pd.concat([serie_banco, serie_seguro], axis=1).dropna()
        cov_bs = df_cruce.cov().iloc[0, 1] * 252 # Covarianza anualizada
    
    beta_comb = (w_b * mejor_banco["Beta"]) + (w_s * mejor_seguro["Beta"])
    ret_comb = (w_b * mejor_banco["Rentabilidad CAPM"]) + (w_s * mejor_seguro["Rentabilidad CAPM"])
    
    vol_comb = np.sqrt((w_b**2 * mejor_banco["Volatilidad anual 5 años"]**2) + (w_s**2 * mejor_seguro["Volatilidad anual 5 años"]**2) + (2 * w_b * w_s * cov_bs))
    sharpe_comb = (ret_comb - rf) / vol_comb
    
    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    c_m1.metric("Distribución", f"{int(w_b*100)}% / {int(w_s*100)}%")
    c_m2.metric("Beta Conjunta", f"{beta_comb:.4f}")
    c_m3.metric("Rentabilidad CAPM", f"{ret_comb*100:.2f}%")
    c_m4.metric("Sharpe Conjunto", f"{sharpe_comb:.4f}")

# ==========================================
# HOJA 5: GRÁFICOS Y PROYECCIÓN
# ==========================================
with tab5:
    st.header("HOJA 5: VISUALIZACIÓN DE RESULTADOS")
    
    anios = list(range(int(plazo) + 1))
    proy_b = [importe * ((1 + mejor_banco["Rentabilidad CAPM"])**t) for t in anios]
    proy_s = [importe * ((1 + mejor_seguro["Rentabilidad CAPM"])**t) for t in anios]
    
    ret_50_50 = (0.5 * mejor_banco["Rentabilidad CAPM"]) + (0.5 * mejor_seguro["Rentabilidad CAPM"])
    proy_c = [importe * ((1 + ret_50_50)**t) for t in anios]
    
    df_proyeccion = pd.DataFrame({
        "Año": anios,
        f"{mejor_banco['Empresa']}": proy_b,
        f"{mejor_seguro['Empresa']}": proy_s,
        "Cartera Referencial (50% / 50%)": proy_c
    })
    
    col_tabla_proy, col_indicadores = st.columns([1.3, 1.7])
    
    with col_tabla_proy:
        st.subheader("Proyección de Capital (€)")
        st.dataframe(df_proyeccion.style.format({col: "{:,.2f} €" for col in df_proyeccion.columns if col != "Año"}), hide_index=True)
        
    with col_indicadores:
        st.subheader("Tabla de Resumen Comparativo")
        df_ind = pd.DataFrame({
            "Indicador": ["Empresa / producto", "Sector", "Beta", "Volatilidad anual", "Rentabilidad CAPM", "Sharpe individual"],
            "Banco seleccionado": [mejor_banco["Empresa"], "Banco", f"{mejor_banco['Beta']:.4f}", f"{mejor_banco['Volatilidad anual 5 años']:.4f}", f"{mejor_banco['Rentabilidad CAPM']*100:.2f}%", f"{mejor_banco['Sharpe individual CAPM']:.4f}"],
            "Aseguradora seleccionada": [mejor_seguro["Empresa"], "Seguros", f"{mejor_seguro['Beta']:.4f}", f"{mejor_seguro['Volatilidad anual 5 años']:.4f}", f"{mejor_seguro['Rentabilidad CAPM']*100:.2f}%", f"{mejor_seguro['Sharpe individual CAPM']:.4f}"],
            "Referencia conjunta (50/50)": [f"{mejor_banco['Empresa']} + {mejor_seguro['Empresa']}", "Banco + Seguros", f"{(mejor_banco['Beta']+mejor_seguro['Beta'])/2:.4f}", f"{vol_comb:.4f}", f"{ret_50_50*100:.2f}%", f"{(ret_50_50-rf)/vol_comb:.4f}"],
            "Observación": ["Selección final por sector", "Universo moderado UE", "Cercana a 1", "Riesgo diversificado", "Modelo CAPM", "Rentabilidad-Riesgo"]
        })
        st.dataframe(df_ind, hide_index=True, use_container_width=True)

    st.subheader("Evolución temporal del capital invertido")
    st.line_chart(df_proyeccion.set_index("Año"))

# ==========================================
# HOJA 6: RESUMEN FINAL INTERFAZ
# ==========================================
with tab6:
    st.header("HOJA 6: RESUMEN FINAL DEL SISTEMA DE RECOMENDACIÓN")
    
    df_resumen_card = pd.DataFrame({
        "Concepto Metodológico": [
            "Usuario", "Perfil inversor", "Universo analizado", 
            "Número de empresas candidatas", "Criterio de beta", 
            "Mejor banco", "Mejor aseguradora", "Modelo de rentabilidad", 
            "Criterio de selección", "Observación"
        ],
        "Valor Asignado": [
            nombre, st.session_state.perfil_calc, "Bancos y aseguradoras de la Unión Europea",
            "7", "Beta cercana a 1 (Moderado)",
            mejor_banco["Empresa"], mejor_seguro["Empresa"], "CAPM",
            "Menor score moderado por sector", "M1-M7 representan empresas candidatas, no combinaciones de pesos"
        ]
    })
    
    col_card, col_pdf = st.columns([2, 1])
    with col_card:
        st.table(df_resumen_card)
        
    with col_pdf:
        st.write("### Exportación Documental")
        st.write("Genera el acta oficial de resultados para incorporar como anexo en la memoria del TFM.")
        
        def construir_pdf_tfm():
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 15)
            pdf.cell(0, 10, "UNIVERSIDAD DE LEON - MUCAF", align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Ficha de Recomendacion - Trabajo Fin de Master", align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)
            
            pdf.set_font("Helvetica", "", 10)
            for idx, r in df_resumen_card.iterrows():
                c_texto = str(r['Concepto Metodológico']).encode('latin-1', 'replace').decode('latin-1')
                v_texto = str(r['Valor Asignado']).encode('latin-1', 'replace').decode('latin-1')
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(75, 8, c_texto, border=1)
                pdf.set_font("Helvetica", "", 10)
                pdf.cell(115, 8, v_texto, border=1, new_x="LMARGIN", new_y="NEXT")
            
            return bytes(pdf.output())

        st.download_button(
            label="📥 Descargar Ficha de Resultados (PDF)",
            data=construir_pdf_tfm(),
            file_name="Resumen_Ejecutivo_TFM.pdf",
            mime="application/pdf"
        )