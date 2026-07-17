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

# --- Clases de activo (Fase 3): usadas por portfolio/constraints.py para las bandas
#     minimas/maximas por perfil (ej. Conservador exige un piso de Renta Fija + Monetario).
#     Sustituyen a la Beta como criterio UNICO de elegibilidad, que no tiene sentido
#     aplicado por igual a acciones y a ETFs de renta fija o monetarios. ---
CLASE_RENTA_VARIABLE = "Renta Variable"
CLASE_RENTA_FIJA = "Renta Fija"
CLASE_MONETARIO = "Monetario"

# --- Universo de activos. Bancos y aseguradoras UE (sin cambios desde el modelo original)
#     ampliado en la Fase 3 con 4 ETFs UCITS diversificados, sin apalancamiento ni derivados,
#     verificados contra Yahoo Finance (5 años de historico completo a fecha de esta fase). ---
UNIVERSO_TFM: list[dict[str, str]] = [
    {"Sector": "Banco", "Empresa": "Banco Santander", "Ticker": "SAN.MC", "Producto": "Accion ordinaria - entidad bancaria", "Clase de activo": CLASE_RENTA_VARIABLE},
    {"Sector": "Banco", "Empresa": "BNP Paribas", "Ticker": "BNP.PA", "Producto": "Accion ordinaria - entidad bancaria", "Clase de activo": CLASE_RENTA_VARIABLE},
    {"Sector": "Banco", "Empresa": "ING Groep", "Ticker": "INGA.AS", "Producto": "Accion ordinaria - entidad bancaria", "Clase de activo": CLASE_RENTA_VARIABLE},
    {"Sector": "Seguros", "Empresa": "Allianz SE", "Ticker": "ALV.DE", "Producto": "Accion ordinaria - entidad aseguradora", "Clase de activo": CLASE_RENTA_VARIABLE},
    {"Sector": "Seguros", "Empresa": "AXA SA", "Ticker": "CS.PA", "Producto": "Accion ordinaria - entidad aseguradora", "Clase de activo": CLASE_RENTA_VARIABLE},
    {"Sector": "Seguros", "Empresa": "Mapfre SA", "Ticker": "MAP.MC", "Producto": "Accion ordinaria - entidad aseguradora", "Clase de activo": CLASE_RENTA_VARIABLE},
    {"Sector": "Seguros", "Empresa": "Assicurazioni Generali", "Ticker": "G.MI", "Producto": "Accion ordinaria - entidad aseguradora", "Clase de activo": CLASE_RENTA_VARIABLE},
    {"Sector": "ETF Renta Variable Global", "Empresa": "iShares Core MSCI World UCITS ETF", "Ticker": "EUNL.DE", "Producto": "ETF UCITS - renta variable global diversificada", "Clase de activo": CLASE_RENTA_VARIABLE},
    {"Sector": "ETF Renta Variable Europa", "Empresa": "iShares Core EURO STOXX 50 UCITS ETF", "Ticker": "EXW1.DE", "Producto": "ETF UCITS - renta variable zona euro", "Clase de activo": CLASE_RENTA_VARIABLE},
    {"Sector": "ETF Renta Fija", "Empresa": "iShares Core Global Aggregate Bond UCITS ETF (EUR Hedged)", "Ticker": "AGGH.MI", "Producto": "ETF UCITS - renta fija agregada global, cubierta a EUR", "Clase de activo": CLASE_RENTA_FIJA},
    {"Sector": "ETF Monetario", "Empresa": "Xtrackers II EUR Overnight Rate Swap UCITS ETF", "Ticker": "XEON.DE", "Producto": "ETF UCITS - monetario EUR (tipo a un dia)", "Clase de activo": CLASE_MONETARIO},
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
COL_CLASE_ACTIVO = "Clase de activo"
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
