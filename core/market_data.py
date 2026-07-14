"""Capa de acceso a datos de mercado, desacoplada de cualquier proveedor concreto.

Aplica el Principio de Inversion de Dependencias (SOLID): el resto del dominio
(`core/capm.py`, `ui/sections/*.py`) depende unicamente de `MarketDataService`
y de la abstraccion `MarketDataProvider`, nunca de `yfinance` directamente.
Sustituir Yahoo Finance por otro proveedor en el futuro solo requiere escribir
una nueva clase que implemente `MarketDataProvider`.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod

import pandas as pd
import yfinance as yf

from core.logger import get_logger

logger = get_logger(__name__)


class MarketDataError(Exception):
    """Error de dominio: los datos de mercado no pudieron obtenerse o son invalidos."""


class MarketDataProvider(ABC):
    """Abstraccion de cualquier fuente de precios historicos."""

    @abstractmethod
    def get_close_prices(self, ticker: str, period: str) -> pd.Series:
        """Devuelve la serie de precios de cierre de `ticker` para el periodo dado.

        Debe lanzar `MarketDataError` si el simbolo es invalido, no hay datos
        disponibles, o la fuente de datos falla de forma irrecuperable.
        """
        raise NotImplementedError


class YahooFinanceProvider(MarketDataProvider):
    """`MarketDataProvider` respaldado por Yahoo Finance (libreria `yfinance`).

    Incluye reintentos con backoff progresivo y validacion de datos vacios,
    ya que `yfinance` no expone excepciones tipadas propias y puede fallar de
    forma intermitente (rate limiting, timeouts, simbolos deslistados).
    """

    def __init__(self, max_retries: int = 3, retry_backoff_seconds: float = 1.5) -> None:
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds

    def get_close_prices(self, ticker: str, period: str) -> pd.Series:
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                history = yf.Ticker(ticker).history(period=period)
                if history.empty or "Close" not in history.columns:
                    raise MarketDataError(
                        f"Yahoo Finance no devolvio datos para el simbolo '{ticker}'."
                    )
                logger.info(
                    "Descarga OK: ticker=%s periodo=%s intento=%s/%s filas=%s",
                    ticker, period, attempt, self._max_retries, len(history),
                )
                return history["Close"]
            except Exception as exc:  # yfinance no expone jerarquia de excepciones propia
                last_error = exc
                logger.warning(
                    "Fallo al descargar ticker=%s (intento %s/%s): %s",
                    ticker, attempt, self._max_retries, exc,
                )
                if attempt < self._max_retries:
                    time.sleep(self._retry_backoff_seconds * attempt)

        logger.error(
            "Descarga definitivamente fallida para ticker=%s tras %s intentos.",
            ticker, self._max_retries,
        )
        raise MarketDataError(
            f"No se pudo obtener el historico de '{ticker}' tras {self._max_retries} intentos."
        ) from last_error


class MarketDataService:
    """Fachada de dominio sobre un `MarketDataProvider`.

    No depende de Streamlit ni de `yfinance`: recibe el proveedor por
    inyeccion de dependencias (con `YahooFinanceProvider` como valor por
    defecto para no obligar a los llamadores a construirlo explicitamente).
    """

    def __init__(self, provider: MarketDataProvider | None = None) -> None:
        self._provider = provider or YahooFinanceProvider()

    @property
    def provider(self) -> MarketDataProvider:
        return self._provider

    def get_price_history(self, ticker: str, period: str) -> pd.Series:
        """Serie de precios de cierre para `ticker` en el `period` indicado."""
        return self._provider.get_close_prices(ticker, period)

    def get_returns(self, ticker: str, period: str) -> pd.Series:
        """Serie de rentabilidades diarias (variacion porcentual) de `ticker`."""
        prices = self.get_price_history(ticker, period)
        return prices.pct_change().dropna()
