import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Comparador Financiero", layout="wide")

# --- MEMORIA DE LA SESIÓN ---
# Inicializamos una lista vacía para guardar las comparaciones favoritas
if 'favoritos' not in st.session_state:
    st.session_state.favoritos = []

st.title("Comparador de Opciones de Inversión")
st.write("Análisis de rentabilidad entre entidades. Las métricas superiores se resaltan en verde.")

# Diccionarios con los tickers
bancos_europeos = {
    "Banco Santander (España)": "SAN.MC",
    "BNP Paribas (Francia)": "BNP.PA",
    "Deutsche Bank (Alemania)": "DBK.DE",
    "Intesa Sanpaolo (Italia)": "ISP.MI"
}

seguros_europeos = {
    "Allianz (Alemania)": "ALV.DE",
    "AXA (Francia)": "CS.PA",
    "Mapfre (España)": "MAP.MC",
    "Generali (Italia)": "G.MI"
}

st.sidebar.header("Configuración de Búsqueda")
sector = st.sidebar.radio("Sectores disponibles:", ("Banca", "Seguros"))

empresas = bancos_europeos if sector == "Banca" else seguros_europeos

st.subheader("Seleccione dos entidades para comparar")
col_sel1, col_sel2 = st.columns(2)

with col_sel1:
    empresa_1 = st.selectbox("Entidad 1:", list(empresas.keys()), index=0)

with col_sel2:
    empresa_2 = st.selectbox("Entidad 2:", list(empresas.keys()), index=1)

def obtener_metricas(ticker):
    info = yf.Ticker(ticker).info
    return {
        "ROE (Rentabilidad Financiera)": info.get('returnOnEquity', 'N/A'),
        "ROA (Rentabilidad Económica)": info.get('returnOnAssets', 'N/A'),
        "Margen Operativo": info.get('operatingMargins', 'N/A'),
        "Utilidad Neta (Euros)": info.get('netIncomeToCommon', 'N/A'),
        "Ingresos Totales (Euros)": info.get('totalRevenue', 'N/A')
    }

def formatear_porcentaje(valor):
    return f"{valor * 100:.2f}%" if isinstance(valor, (int, float)) else "N/A"

def formatear_moneda(valor):
    return f"€ {valor:,.0f}".replace(',', '.') if isinstance(valor, (int, float)) else "N/A"

# --- LÓGICA DE COLORES ---
def aplicar_colores(row, col1, col2):
    """Compara dos columnas y pinta de verde el valor mayor y rojo el menor."""
    estilos = [''] * len(row)
    val1_str = str(row[col1])
    val2_str = str(row[col2])
    
    if val1_str == 'N/A' or val2_str == 'N/A':
        return estilos
        
    try:
        # Extraemos los números puros ignorando los símbolos de Euro y Porcentaje
        v1 = float(val1_str.replace('%', '')) if '%' in val1_str else float(val1_str.replace('€', '').replace('.', '').strip())
        v2 = float(val2_str.replace('%', '')) if '%' in val2_str else float(val2_str.replace('€', '').replace('.', '').strip())
        
        color_ganador = 'background-color: rgba(39, 174, 96, 0.4); font-weight: bold; color: white;'
        color_perdedor = 'background-color: rgba(231, 76, 60, 0.4); color: white;'
        
        idx_1 = row.index.get_loc(col1)
        idx_2 = row.index.get_loc(col2)
        
        # Asumimos que un número mayor siempre es mejor (ideal para rentabilidad e ingresos)
        if v1 > v2:
            estilos[idx_1] = color_ganador
            estilos[idx_2] = color_perdedor
        elif v2 > v1:
            estilos[idx_1] = color_perdedor
            estilos[idx_2] = color_ganador
    except Exception:
        pass
    
    return estilos

# --- BOTÓN PRINCIPAL ---
if st.button("Comparar Entidades en Tiempo Real"):
    if empresa_1 == empresa_2:
        st.warning("⚠️ Por favor selecciona dos empresas distintas para comparar.")
    else:
        with st.spinner('Extrayendo datos de la bolsa de valores...'):
            datos_e1 = obtener_metricas(empresas[empresa_1])
            datos_e2 = obtener_metricas(empresas[empresa_2])

            df_comparativo = pd.DataFrame({
                "Indicador / Rubro": list(datos_e1.keys()),
                empresa_1: [
                    formatear_porcentaje(datos_e1["ROE (Rentabilidad Financiera)"]),
                    formatear_porcentaje(datos_e1["ROA (Rentabilidad Económica)"]),
                    formatear_porcentaje(datos_e1["Margen Operativo"]),
                    formatear_moneda(datos_e1["Utilidad Neta (Euros)"]),
                    formatear_moneda(datos_e1["Ingresos Totales (Euros)"])
                ],
                empresa_2: [
                    formatear_porcentaje(datos_e2["ROE (Rentabilidad Financiera)"]),
                    formatear_porcentaje(datos_e2["ROA (Rentabilidad Económica)"]),
                    formatear_porcentaje(datos_e2["Margen Operativo"]),
                    formatear_moneda(datos_e2["Utilidad Neta (Euros)"]),
                    formatear_moneda(datos_e2["Ingresos Totales (Euros)"])
                ]
            })
            
            # Guardamos el DataFrame crudo en la sesión temporal para usarlo si el usuario quiere guardarlo
            st.session_state.df_actual = df_comparativo
            st.session_state.empresa_1_actual = empresa_1
            st.session_state.empresa_2_actual = empresa_2

# --- RENDERIZADO DE LA TABLA ACTUAL Y BOTÓN DE GUARDAR ---
if 'df_actual' in st.session_state:
    st.success("¡Análisis comparativo generado con éxito!")
    
    # Aplicar los estilos de color
    df_estilizado = st.session_state.df_actual.style.apply(
        lambda row: aplicar_colores(row, st.session_state.empresa_1_actual, st.session_state.empresa_2_actual), 
        axis=1
    )
    st.dataframe(df_estilizado, hide_index=True, use_container_width=True)
    
    col_vacia, col_btn = st.columns([3, 1])
    with col_btn:
        if st.button("Guardar esta comparación"):
            st.session_state.favoritos.append({
                "e1": st.session_state.empresa_1_actual,
                "e2": st.session_state.empresa_2_actual,
                "df": st.session_state.df_actual
            })
            st.toast('¡Guardado en favoritos!', icon='✅')

# --- SECCIÓN DE FAVORITOS GUARDADOS ---
if st.session_state.favoritos:
    st.divider()
    st.subheader("Comparaciones Guardadas")
    st.write("Revisa aquí las empresas que has analizado previamente:")
    
    for i, fav in enumerate(reversed(st.session_state.favoritos)):
        # Reversed para que la última guardada aparezca arriba
        with st.expander(f"Resultado #{len(st.session_state.favoritos) - i}: {fav['e1']} vs {fav['e2']}"):
            df_fav_estilizado = fav["df"].style.apply(
                lambda row: aplicar_colores(row, fav['e1'], fav['e2']), 
                axis=1
            )
            st.dataframe(df_fav_estilizado, hide_index=True, use_container_width=True)