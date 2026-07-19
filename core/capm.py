"""Calculos financieros del modelo CAPM: funciones puras, sin Streamlit ni red.

Toda funcion de este modulo recibe datos ya descargados (via `MarketDataService`)
y devuelve valores o DataFrames, lo que permite testearlas sin conexion a
internet ni levantar la aplicacion (observacion 3 y 9 del tutor).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config
from core.market_data import MarketDataService

TRADING_DAYS_PER_YEAR = config.TRADING_DAYS_PER_YEAR


def align_returns(asset_returns: pd.Series, market_returns: pd.Series) -> pd.DataFrame:
    """Alinea temporalmente (inner join) los retornos de un activo y su benchmark.

    Replica el comportamiento original: la volatilidad del activo se calcula
    sobre esta serie ya alineada con el benchmark, no sobre la serie cruda.
    """
    aligned = pd.concat([asset_returns, market_returns], axis=1).dropna()
    aligned.columns = ["asset", "market"]
    return aligned


def compute_beta(aligned_returns: pd.DataFrame) -> float:
    """Calcula la Beta (sensibilidad al mercado) a partir de retornos alineados."""
    covariance_matrix = aligned_returns.cov()
    # pandas-stubs tipa `DataFrame.loc[escalar, escalar]` como una union muy amplia
    # (no puede probar estaticamente que `.cov()` de columnas float devuelve float64).
    # En tiempo de ejecucion siempre es un numpy.float64, por lo que `float(...)` es seguro.
    covariance_asset_market = float(covariance_matrix.loc["asset", "market"])  # type: ignore[arg-type]
    market_variance = float(covariance_matrix.loc["market", "market"])  # type: ignore[arg-type]
    if market_variance == 0:
        return 1.0
    return covariance_asset_market / market_variance


def annualized_volatility(daily_returns: pd.Series) -> float:
    """Anualiza una volatilidad diaria asumiendo `TRADING_DAYS_PER_YEAR` sesiones/año."""
    return float(daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def capm_expected_return(beta: float, risk_free_rate: float, market_premium: float) -> float:
    """Rentabilidad esperada segun el modelo CAPM: Rf + beta * (Rm - Rf)."""
    return risk_free_rate + beta * market_premium


def sharpe_ratio(expected_return: float, risk_free_rate: float, volatility: float) -> float:
    """Ratio de exceso de rentabilidad sobre volatilidad total.

    Se protege la division por cero (no presente en el original, donde una
    volatilidad nula habria propagado `inf`/`nan` silenciosamente); en la
    practica esto no altera ningun resultado con los activos reales del
    universo, cuya volatilidad historica siempre es distinta de cero.
    """
    if volatility == 0:
        return 0.0
    return (expected_return - risk_free_rate) / volatility


def score_for_profile(beta: float, volatility: float, profile: str) -> float:
    """Heuristica de seleccion de activos: un score MAS BAJO es MEJOR para `profile`.

    - Conservador: penaliza beta y volatilidad por igual (prioriza proteccion de capital).
    - Moderado: penaliza la distancia a beta=1 y la volatilidad (activos "de mercado").
    - Agresivo: premia la beta alta, sin penalizar volatilidad (busca amplificar retornos).

    Fase 2: sustituye a `score_moderate_profile`, que aplicaba SIEMPRE la formula
    de "Moderado" sin importar el perfil realmente calculado por el cuestionario
    (bug critico identificado en la auditoria: la seleccion de activos no dependia
    del perfil del usuario). Reemplazada tras verificar con tests que, para
    `profile == config.PERFIL_MODERADO`, el resultado es identico al original.
    """
    if profile == config.PERFIL_CONSERVADOR:
        return beta + volatility
    if profile == config.PERFIL_AGRESIVO:
        return -beta
    return abs(beta - 1.0) + volatility


def is_eligible_for_profile(
    beta: float,
    profile: str,
    lower_bound: float = config.BETA_ELIGIBILITY_LOWER_BOUND,
    upper_bound: float = config.BETA_ELIGIBILITY_UPPER_BOUND,
) -> bool:
    """Indica si un activo entra en el rango de beta aceptado para `profile`.

    Particiona el eje de Beta en 3 bandas contiguas y sin solapes:
    Conservador (beta <= lower_bound), Moderado (lower_bound <= beta <= upper_bound),
    Agresivo (beta >= upper_bound). Sustituye a `is_eligible_moderate_profile`, que
    solo sabia evaluar la banda Moderado (ver nota en `score_for_profile`).
    """
    if profile == config.PERFIL_CONSERVADOR:
        return beta <= lower_bound
    if profile == config.PERFIL_AGRESIVO:
        return beta >= upper_bound
    return lower_bound <= beta <= upper_bound


def annualized_covariance(returns_a: pd.Series, returns_b: pd.Series) -> float:
    """Covarianza anualizada entre dos series de retornos diarios ya alineables.

    Nota (Subfase 3.5): ya no se usa en la UI (la construcción de cartera usa
    `portfolio.covariance.build_annualized_covariance_matrix` para N activos).
    Se conserva porque `tests/test_covariance.py` la usa como oráculo
    independiente para verificar, par a par, que la matriz de covarianzas
    coincide con este cálculo de referencia — no es código muerto, es una
    utilidad de verificación cruzada.
    """
    aligned = pd.concat([returns_a, returns_b], axis=1).dropna()
    aligned.columns = ["a", "b"]
    covariance_ab = float(aligned.cov().loc["a", "b"])  # type: ignore[arg-type]  # ver nota en compute_beta
    return covariance_ab * TRADING_DAYS_PER_YEAR


def build_universe_metrics(
    service: MarketDataService,
    universe: list[dict[str, str]],
    benchmark_ticker: str,
    risk_free_rate: float,
    market_premium: float,
    investor_profile: str,
    period: str = config.HISTORY_PERIOD,
) -> pd.DataFrame:
    """Orquesta la descarga y el calculo CAPM completo para cada activo del universo.

    Reemplaza a `procesar_universo` del `app.py` original. A partir de la Fase 2,
    `investor_profile` determina el score y la elegibilidad de cada activo
    (antes, ambos se calculaban SIEMPRE con la formula de "Moderado", sin importar
    el resultado real del cuestionario).
    """
    market_returns = service.get_returns(benchmark_ticker, period)

    rows: list[dict[str, object]] = []
    for asset in universe:
        ticker = asset["Ticker"]
        asset_returns = service.get_returns(ticker, period)
        aligned = align_returns(asset_returns, market_returns)

        beta = compute_beta(aligned)
        daily_volatility = float(aligned["asset"].std())
        annual_volatility = annualized_volatility(aligned["asset"])
        expected_return = capm_expected_return(beta, risk_free_rate, market_premium)

        rows.append({
            config.COL_PERFIL_OBJETIVO: investor_profile,
            config.COL_SECTOR: asset["Sector"],
            config.COL_EMPRESA: asset["Empresa"],
            config.COL_TICKER: ticker,
            config.COL_PRODUCTO: asset["Producto"],
            config.COL_CLASE_ACTIVO: asset["Clase de activo"],
            config.COL_BETA: beta,
            config.COL_DISTANCIA_BETA: abs(beta - 1.0),
            config.COL_VOL_DIARIA: daily_volatility,
            config.COL_VOL_ANUAL: annual_volatility,
            config.COL_CAPM: expected_return,
            config.COL_SHARPE: sharpe_ratio(expected_return, risk_free_rate, annual_volatility),
            config.COL_SCORE_PERFIL: score_for_profile(beta, annual_volatility, investor_profile),
            config.COL_ELEGIBLE_PERFIL: "Sí" if is_eligible_for_profile(beta, investor_profile) else "No",
        })

    return pd.DataFrame(rows)
