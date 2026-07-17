"""Construcción de la matriz de covarianzas del universo de activos.

Generaliza a N activos el cálculo par-a-par de `core.capm.annualized_covariance`
(pensado para 2 activos). Es el insumo directo de `portfolio.optimizer`: el
problema de Markowitz necesita la matriz de covarianzas completa del universo
filtrado, no solo pares aislados.
"""
from __future__ import annotations

import pandas as pd

import config
from core.market_data import MarketDataService

TRADING_DAYS_PER_YEAR = config.TRADING_DAYS_PER_YEAR


def build_aligned_returns_matrix(
    service: MarketDataService, tickers: list[str], period: str = config.HISTORY_PERIOD
) -> pd.DataFrame:
    """Descarga y alinea (inner join) los retornos diarios de todos los `tickers`.

    Cada columna es un ticker; se conservan únicamente las fechas en las que
    TODOS los activos tienen cotización (mismo criterio que
    `core.capm.align_returns`, pero para N series en vez de 2).
    """
    returns_by_ticker = {ticker: service.get_returns(ticker, period) for ticker in tickers}
    return pd.DataFrame(returns_by_ticker).dropna()


def annualized_covariance_matrix(returns_matrix: pd.DataFrame) -> pd.DataFrame:
    """Matriz de covarianzas anualizada (N x N) a partir de una matriz de retornos alineados."""
    return returns_matrix.cov() * TRADING_DAYS_PER_YEAR


def build_annualized_covariance_matrix(
    service: MarketDataService, tickers: list[str], period: str = config.HISTORY_PERIOD
) -> pd.DataFrame:
    """Orquesta la descarga y el cálculo de la matriz de covarianzas anualizada."""
    returns_matrix = build_aligned_returns_matrix(service, tickers, period)
    return annualized_covariance_matrix(returns_matrix)
