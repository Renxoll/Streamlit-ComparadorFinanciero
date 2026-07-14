"""Constantes y parametros de configuracion de la aplicacion.

Este modulo no debe importar Streamlit ni ningun cliente de datos externo:
solo contiene valores estaticos reutilizados por el resto de capas.
"""
from __future__ import annotations

# --- Metadatos de la aplicacion ---
# Nota: el branding TFM se mantiene en esta fase por instruccion explicita de no
# introducir cambios visibles. Se retira en la Fase 5 (observacion 1 del tutor).
APP_TITLE = "TFM - Carteras e Interfaz Inversor"

# --- Parametros de mercado ---
BENCHMARK_TICKER = "^STOXX50E"
HISTORY_PERIOD = "5y"
TRADING_DAYS_PER_YEAR = 252

# --- Universo cerrado de activos (Fase 1: sin cambios; se amplia con ETFs en la Fase 3) ---
UNIVERSO_TFM: list[dict[str, str]] = [
    {"Sector": "Banco", "Empresa": "Banco Santander", "Ticker": "SAN.MC", "Producto": "Accion ordinaria - entidad bancaria"},
    {"Sector": "Banco", "Empresa": "BNP Paribas", "Ticker": "BNP.PA", "Producto": "Accion ordinaria - entidad bancaria"},
    {"Sector": "Banco", "Empresa": "ING Groep", "Ticker": "INGA.AS", "Producto": "Accion ordinaria - entidad bancaria"},
    {"Sector": "Seguros", "Empresa": "Allianz SE", "Ticker": "ALV.DE", "Producto": "Accion ordinaria - entidad aseguradora"},
    {"Sector": "Seguros", "Empresa": "AXA SA", "Ticker": "CS.PA", "Producto": "Accion ordinaria - entidad aseguradora"},
    {"Sector": "Seguros", "Empresa": "Mapfre SA", "Ticker": "MAP.MC", "Producto": "Accion ordinaria - entidad aseguradora"},
    {"Sector": "Seguros", "Empresa": "Assicurazioni Generali", "Ticker": "G.MI", "Producto": "Accion ordinaria - entidad aseguradora"},
]

# --- Umbrales de elegibilidad por perfil moderado (Beta cercana a 1) ---
MODERADO_BETA_MIN = 0.75
MODERADO_BETA_MAX = 1.25

# --- Nombres de columnas del DataFrame de universo, centralizados para evitar
#     errores de tipeo al compartirse entre core/capm.py y ui/sections/*.py ---
COL_PERFIL_OBJETIVO = "Perfil objetivo"
COL_SECTOR = "Sector"
COL_EMPRESA = "Empresa"
COL_TICKER = "Ticker Yahoo"
COL_PRODUCTO = "Producto financiero"
COL_BETA = "Beta"
COL_DISTANCIA_BETA = "Distancia a β=1"
COL_VOL_DIARIA = "Volatilidad diaria 5 años"
COL_VOL_ANUAL = "Volatilidad anual 5 años"
COL_CAPM = "Rentabilidad CAPM"
COL_SHARPE = "Sharpe individual CAPM"
COL_SCORE_MODERADO = "Score moderado"
COL_ELEGIBLE_MODERADO = "Elegible perfil moderado"
