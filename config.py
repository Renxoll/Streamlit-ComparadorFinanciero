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

# --- Perfiles de riesgo normativos (unica fuente de verdad para las 3 etiquetas) ---
PERFIL_CONSERVADOR = "Conservador"
PERFIL_MODERADO = "Moderado"
PERFIL_AGRESIVO = "Agresivo"

# --- Fronteras de elegibilidad de activos por Beta.
#     Particion continua y sin solapes del eje de Beta en 3 bandas (Fase 2):
#       Conservador: beta <= BETA_ELIGIBILITY_LOWER_BOUND
#       Moderado:    BETA_ELIGIBILITY_LOWER_BOUND <= beta <= BETA_ELIGIBILITY_UPPER_BOUND
#       Agresivo:    beta >= BETA_ELIGIBILITY_UPPER_BOUND
#     Los valores se heredan sin cambios del modelo original (que solo definia la banda
#     Moderado); ver core/capm.py::is_eligible_for_profile. ---
BETA_ELIGIBILITY_LOWER_BOUND = 0.75
BETA_ELIGIBILITY_UPPER_BOUND = 1.25

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
# Antes "Score moderado" / "Elegible perfil moderado": se generalizan en la Fase 2 porque
# ahora reflejan el perfil REAL calculado, no siempre "Moderado" (bug corregido).
COL_SCORE_PERFIL = "Score perfil"
COL_ELEGIBLE_PERFIL = "Elegible perfil actual"
