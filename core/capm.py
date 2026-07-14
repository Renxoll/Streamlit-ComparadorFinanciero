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
    covariance_asset_market = covariance_matrix.loc["asset", "market"]
    market_variance = covariance_matrix.loc["market", "market"]
    if market_variance == 0:
        return 1.0
    return float(covariance_asset_market / market_variance)


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


def score_moderate_profile(beta: float, volatility: float) -> float:
    """Heuristica de seleccion para perfil moderado: penaliza distancia a beta=1 y volatilidad."""
    return abs(beta - 1.0) + volatility


def is_eligible_moderate_profile(
    beta: float,
    lower_bound: float = config.MODERADO_BETA_MIN,
    upper_bound: float = config.MODERADO_BETA_MAX,
) -> bool:
    """Indica si un activo entra en el rango de beta aceptado para perfil moderado."""
    return lower_bound <= beta <= upper_bound


def annualized_covariance(returns_a: pd.Series, returns_b: pd.Series) -> float:
    """Covarianza anualizada entre dos series de retornos diarios ya alineables."""
    aligned = pd.concat([returns_a, returns_b], axis=1).dropna()
    aligned.columns = ["a", "b"]
    return float(aligned.cov().loc["a", "b"] * TRADING_DAYS_PER_YEAR)


def combined_portfolio_volatility(
    vol_a: float, weight_a: float, vol_b: float, weight_b: float, covariance_ab: float
) -> float:
    """Volatilidad de una cartera de 2 activos (formula clasica de varianza de cartera)."""
    variance = (
        (weight_a**2 * vol_a**2)
        + (weight_b**2 * vol_b**2)
        + (2 * weight_a * weight_b * covariance_ab)
    )
    return float(np.sqrt(variance))


def build_universe_metrics(
    service: MarketDataService,
    universe: list[dict[str, str]],
    benchmark_ticker: str,
    risk_free_rate: float,
    market_premium: float,
    period: str = config.HISTORY_PERIOD,
) -> pd.DataFrame:
    """Orquesta la descarga y el calculo CAPM completo para cada activo del universo.

    Reemplaza a `procesar_universo` del `app.py` original, manteniendo
    exactamente los mismos calculos y nombres de columna.
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
            config.COL_PERFIL_OBJETIVO: "Moderado",
            config.COL_SECTOR: asset["Sector"],
            config.COL_EMPRESA: asset["Empresa"],
            config.COL_TICKER: ticker,
            config.COL_PRODUCTO: asset["Producto"],
            config.COL_BETA: beta,
            config.COL_DISTANCIA_BETA: abs(beta - 1.0),
            config.COL_VOL_DIARIA: daily_volatility,
            config.COL_VOL_ANUAL: annual_volatility,
            config.COL_CAPM: expected_return,
            config.COL_SHARPE: sharpe_ratio(expected_return, risk_free_rate, annual_volatility),
            config.COL_SCORE_MODERADO: score_moderate_profile(beta, annual_volatility),
            config.COL_ELEGIBLE_MODERADO: "Sí" if is_eligible_moderate_profile(beta) else "No",
        })

    return pd.DataFrame(rows)
