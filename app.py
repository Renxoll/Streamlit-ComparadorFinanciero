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

st.set_page_config(page_title="Comparador Financiero", layout="wide")

st.title("Comparador y Optimizador de Inversión")
st.write("Análisis de rentabilidad, evaluación de riesgo sistemático (Beta) y optimización de Markowitz.")

# --- BANCOS Y SEGUROS ---
bancos_europeos = {
    "Banco Santander (España)": "SAN.MC",
    "BBVA (España)": "BBVA.MC",
    "BNP Paribas (Francia)": "BNP.PA",
    "Société Générale (Francia)": "GLE.PA",
    "Deutsche Bank (Alemania)": "DBK.DE",
    "Commerzbank (Alemania)": "CBK.DE",
    "Intesa Sanpaolo (Italia)": "ISP.MI",
    "UniCredit (Italia)": "UCG.MI",
    "ING Group (Países Bajos)": "INGA.AS"
}

seguros_europeos = {
    "Allianz (Alemania)": "ALV.DE",
    "AXA (Francia)": "CS.PA",
    "Mapfre (España)": "MAP.MC",
    "Generali (Italia)": "G.MI"
}

# --- BARRA LATERAL Y TIPO DE CAMBIO ---
st.sidebar.header("Configuración de Búsqueda")
sector = st.sidebar.radio("Sectores disponibles:", ("Banca", "Seguros"))

st.sidebar.divider()
st.sidebar.subheader("💱 Divisa de Visualización")

try:
    eur_usd_rate = yf.Ticker("EURUSD=X").history(period="1d")['Close'].iloc[-1]
except:
    eur_usd_rate = 1.09

moneda = st.sidebar.radio("Mostrar montos en:", ("Euros (€)", "Dólares ($)"))
tasa_conversion = eur_usd_rate if moneda == "Dólares ($)" else 1.0
simbolo_moneda = "$" if moneda == "Dólares ($)" else "€"

# Parámetros macroeconómicos del entorno
TASA_LIBRE_RIESGO = 0.02  # 2% anual
PRIMA_RIESGO_MERCADO = 0.05  # 5% de prima de riesgo

st.sidebar.divider()
st.sidebar.subheader("Parámetros del Modelo")
st.sidebar.info(f"Tasa Libre de Riesgo (Rf): {TASA_LIBRE_RIESGO*100}%\n\nPrima de Mercado (Rm - Rf): {PRIMA_RIESGO_MERCADO*100}%")

if moneda == "Dólares ($)":
    st.sidebar.info(f"Tipo de cambio actual: 1€ = ${eur_usd_rate:.4f}")

empresas = bancos_europeos if sector == "Banca" else seguros_europeos

st.subheader("Seleccione dos entidades para comparar y optimizar")
col_sel1, col_sel2 = st.columns(2)

with col_sel1:
    empresa_1 = st.selectbox("Entidad 1:", list(empresas.keys()), index=0)

with col_sel2:
    empresa_2 = st.selectbox("Entidad 2:", list(empresas.keys()), index=1)

def obtener_metricas(ticker):
    info = yf.Ticker(ticker).info
    beta = info.get('beta', 'N/A')
    
    rentabilidad_capm = 'N/A'
    if isinstance(beta, (int, float)):
        rentabilidad_capm = TASA_LIBRE_RIESGO + (beta * PRIMA_RIESGO_MERCADO)
        
    return {
        "Beta (Riesgo Sistemático)": beta,
        "Rentabilidad Esperada (CAPM)": rentabilidad_capm,
        "ROE (Rentabilidad Financiera)": info.get('returnOnEquity', 'N/A'),
        "ROA (Rentabilidad Económica)": info.get('returnOnAssets', 'N/A'),
        "Margen Operativo": info.get('operatingMargins', 'N/A'),
        "Utilidad Neta": info.get('netIncomeToCommon', 'N/A'),
        "Ingresos Totales": info.get('totalRevenue', 'N/A')
    }

def optimizar_markowitz(ticker1, ticker2, ret_capm1, ret_capm2):
    # Descargar datos históricos de 5 años para covarianzas
    data1 = yf.Ticker(ticker1).history(period="5y")['Close']
    data2 = yf.Ticker(ticker2).history(period="5y")['Close']
    df_precios = pd.DataFrame({ticker1: data1, ticker2: data2}).dropna()
    
    if df_precios.empty:
        return None
        
    # Retornos logarítmicos diarios y covarianza anualizada
    retornos = np.log(df_precios / df_precios.shift(1)).dropna()
    cov_matrix = retornos.cov() * 252
    
    mu = np.array([ret_capm1, ret_capm2])
    
    # Función a minimizar: Ratio de Sharpe negativo
    def neg_sharpe(pesos):
        retorno_portafolio = np.sum(pesos * mu)
        volatilidad_portafolio = np.sqrt(np.dot(pesos.T, np.dot(cov_matrix, pesos)))
        return -(retorno_portafolio - TASA_LIBRE_RIESGO) / volatilidad_portafolio

    restricciones = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})
    limites = ((0, 1), (0, 1)) # Posiciones largas únicamente
    pesos_iniciales = [0.5, 0.5]
    
    resultado = minimize(neg_sharpe, pesos_iniciales, method='SLSQP', bounds=limites, constraints=restricciones)
    
    if resultado.success:
        w1, w2 = resultado.x
        retorno_opt = np.sum(resultado.x * mu)
        volatilidad_opt = np.sqrt(np.dot(resultado.x.T, np.dot(cov_matrix, resultado.x)))
        sharpe_opt = (retorno_opt - TASA_LIBRE_RIESGO) / volatilidad_opt
        return {"w1": w1, "w2": w2, "ret": retorno_opt, "vol": volatilidad_opt, "sharpe": sharpe_opt}
    return None

def formatear_porcentaje(valor):
    return f"{valor * 100:.2f}%" if isinstance(valor, (int, float)) else "N/A"

def formatear_beta(valor):
    return f"{valor:.2f}" if isinstance(valor, (int, float)) else "N/A"

def formatear_moneda(valor, tasa, simbolo):
    return f"{simbolo} {(valor * tasa):,.0f}".replace(',', '.') if isinstance(valor, (int, float)) else "N/A"

def aplicar_colores(row, col1, col2):
    estilos = [''] * len(row)
    val1_str = str(row[col1])
    val2_str = str(row[col2])
    
    if val1_str == 'N/A' or val2_str == 'N/A':
        return estilos
        
    try:
        v1 = float(val1_str.replace('%', '')) if '%' in val1_str else float(val1_str.replace('€', '').replace('$', '').replace('.', '').strip())
        v2 = float(val2_str.replace('%', '')) if '%' in val2_str else float(val2_str.replace('€', '').replace('$', '').replace('.', '').strip())
        
        # Para la Beta, el ganador no es el mayor, sino el más cercano a 1 (Perfil Moderado)
        if "Beta" in str(row["Indicador / Rubro"]):
            dist_v1 = abs(v1 - 1.0)
            dist_v2 = abs(v2 - 1.0)
            v1, v2 = dist_v2, dist_v1 # Invertimos para que la lógica de menor distancia gane
            
        color_ganador = 'background-color: rgba(39, 174, 96, 0.4); font-weight: bold; color: white;'
        color_perdedor = 'background-color: rgba(231, 76, 60, 0.4); color: white;'
        
        idx_1 = row.index.get_loc(col1)
        idx_2 = row.index.get_loc(col2)
        
        if v1 > v2:
            estilos[idx_1] = color_ganador
            estilos[idx_2] = color_perdedor
        elif v2 > v1:
            estilos[idx_1] = color_perdedor
            estilos[idx_2] = color_ganador
    except Exception:
        pass
    
    return estilos

def generar_pdf_bytes(empresa1, empresa2, df, markowitz=None):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Reporte Comparativo de Inversion", align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"Analisis: {empresa1} vs {empresa2}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 10)
    anchos = [65, 60, 60] 
    columnas = list(df.columns)
    
    for i in range(3):
        texto_col = str(columnas[i]).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(anchos[i], 10, texto_col, border=1, align="C")
    pdf.ln()
    
    pdf.set_font("Helvetica", "", 10)
    for index, row in df.iterrows():
        for i, item in enumerate(row):
            texto_celda = str(item).replace('€', 'EUR')
            texto_celda = texto_celda.encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(anchos[i], 10, texto_celda, border=1, align="C")
        pdf.ln()
        
    if markowitz:
        pdf.ln(10)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Optimizacion de Cartera (Frontera Eficiente Markowitz)", align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Asignacion Optima {empresa1}: {markowitz['w1']*100:.2f}%", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Asignacion Optima {empresa2}: {markowitz['w2']*100:.2f}%", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Rentabilidad Esperada Conjunta (CAPM): {markowitz['ret']*100:.2f}%", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Riesgo de Cartera (Volatilidad Anualizada): {markowitz['vol']*100:.2f}%", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Ratio de Sharpe Maximizado: {markowitz['sharpe']:.4f}", new_x="LMARGIN", new_y="NEXT")
        
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    disclaimer = "Nota Legal: Datos extraidos en tiempo real bajo normativa IFRS provenientes de fuentes oficiales e institucionales del mercado de valores europeo."
    pdf.multi_cell(0, 5, disclaimer, align="L")
    
    return bytes(pdf.output())

# --- BOTÓN PRINCIPAL ---
if st.button("📊 Comparar y Optimizar Cartera"):
    if empresa_1 == empresa_2:
        st.warning("⚠️ Por favor selecciona dos empresas distintas para comparar.")
    else:
        with st.spinner('Procesando datos financieros, CAPM y optimizando Markowitz...'):
            datos_e1 = obtener_metricas(empresas[empresa_1])
            datos_e2 = obtener_metricas(empresas[empresa_2])

            df_comparativo = pd.DataFrame({
                "Indicador / Rubro": list(datos_e1.keys()),
                empresa_1: [
                    formatear_beta(datos_e1["Beta (Riesgo Sistemático)"]),
                    formatear_porcentaje(datos_e1["Rentabilidad Esperada (CAPM)"]),
                    formatear_porcentaje(datos_e1["ROE (Rentabilidad Financiera)"]),
                    formatear_porcentaje(datos_e1["ROA (Rentabilidad Económica)"]),
                    formatear_porcentaje(datos_e1["Margen Operativo"]),
                    formatear_moneda(datos_e1["Utilidad Neta"], tasa_conversion, simbolo_moneda),
                    formatear_moneda(datos_e1["Ingresos Totales"], tasa_conversion, simbolo_moneda)
                ],
                empresa_2: [
                    formatear_beta(datos_e2["Beta (Riesgo Sistemático)"]),
                    formatear_porcentaje(datos_e2["Rentabilidad Esperada (CAPM)"]),
                    formatear_porcentaje(datos_e2["ROE (Rentabilidad Financiera)"]),
                    formatear_porcentaje(datos_e2["ROA (Rentabilidad Económica)"]),
                    formatear_porcentaje(datos_e2["Margen Operativo"]),
                    formatear_moneda(datos_e2["Utilidad Neta"], tasa_conversion, simbolo_moneda),
                    formatear_moneda(datos_e2["Ingresos Totales"], tasa_conversion, simbolo_moneda)
                ]
            })
            
            # Ejecutar Markowitz si hay datos CAPM válidos
            markowitz_res = None
            if isinstance(datos_e1["Rentabilidad Esperada (CAPM)"], float) and isinstance(datos_e2["Rentabilidad Esperada (CAPM)"], float):             
                ticker1 = empresas[empresa_1]
                ticker2 = empresas[empresa_2]
                markowitz_res = optimizar_markowitz(ticker1, ticker2, datos_e1["Rentabilidad Esperada (CAPM)"], datos_e2["Rentabilidad Esperada (CAPM)"])
            
            st.session_state.df_actual = df_comparativo
            st.session_state.empresa_1_actual = empresa_1
            st.session_state.empresa_2_actual = empresa_2
            st.session_state.markowitz_actual = markowitz_res

            hist_1 = yf.Ticker(empresas[empresa_1]).history(period="6mo")['Close']
            hist_2 = yf.Ticker(empresas[empresa_2]).history(period="6mo")['Close']
            
            st.session_state.df_hist = pd.DataFrame({
                empresa_1: hist_1 * tasa_conversion, 
                empresa_2: hist_2 * tasa_conversion
            })

if 'df_actual' in st.session_state:
    st.success("¡Análisis y optimización generados con éxito!")
    
    pdf_bytes = generar_pdf_bytes(st.session_state.empresa_1_actual, st.session_state.empresa_2_actual, st.session_state.df_actual, st.session_state.markowitz_actual)
    
    col_vacia, col_btn = st.columns([3, 1])
    with col_btn:
        st.download_button(
            label="Descargar Reporte en PDF",
            data=pdf_bytes,
            file_name=f"Reporte_{st.session_state.empresa_1_actual}_vs_{st.session_state.empresa_2_actual}.pdf",
            mime="application/pdf"
        )
    
    df_estilizado = st.session_state.df_actual.style.apply(
        lambda row: aplicar_colores(row, st.session_state.empresa_1_actual, st.session_state.empresa_2_actual), 
        axis=1
    )
    st.dataframe(df_estilizado, hide_index=True, use_container_width=True)
    
    if st.session_state.markowitz_actual:
        st.subheader("🎯 Optimización de Cartera (Markowitz)")
        mw = st.session_state.markowitz_actual
        col1, col2, col3 = st.columns(3)
        col1.metric(f"Peso Óptimo {st.session_state.empresa_1_actual}", f"{mw['w1']*100:.2f}%")
        col2.metric(f"Peso Óptimo {st.session_state.empresa_2_actual}", f"{mw['w2']*100:.2f}%")
        col3.metric("Ratio de Sharpe", f"{mw['sharpe']:.4f}")
        
        col4, col5 = st.columns(2)
        col4.info(f"**Rentabilidad Esperada Conjunta:** {mw['ret']*100:.2f}%")
        col5.warning(f"**Volatilidad (Riesgo Estimado):** {mw['vol']*100:.2f}%")
        
    st.subheader(f"Evolución del Precio de la Acción ({simbolo_moneda}) - Últimos 6 meses")
    st.line_chart(st.session_state.df_hist)