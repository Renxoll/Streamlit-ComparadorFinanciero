"""Pruebas unitarias de core/market_data.py, usando dobles de prueba (sin red)."""
from __future__ import annotations

import pandas as pd
import pytest

import core.market_data as market_data_module
from core.market_data import MarketDataError, MarketDataProvider, MarketDataService, YahooFinanceProvider


class _FakeProvider(MarketDataProvider):
    """Proveedor de prueba que nunca toca la red."""

    def __init__(self, prices_by_ticker: dict[str, pd.Series], raise_for: set[str] | None = None) -> None:
        self._prices_by_ticker = prices_by_ticker
        self._raise_for = raise_for or set()

    def get_close_prices(self, ticker: str, period: str) -> pd.Series:
        if ticker in self._raise_for:
            raise MarketDataError(f"Símbolo inválido de prueba: {ticker}")
        return self._prices_by_ticker[ticker]


def _price_series(values: list[float]) -> pd.Series:
    index = pd.date_range("2024-01-01", periods=len(values), freq="D")
    return pd.Series(values, index=index)


def test_service_delegates_price_history_to_injected_provider() -> None:
    prices = _price_series([100.0, 101.0, 102.0])
    service = MarketDataService(provider=_FakeProvider({"AAA.MC": prices}))
    result = service.get_price_history("AAA.MC", period="5y")
    pd.testing.assert_series_equal(result, prices)


def test_service_computes_percentage_returns() -> None:
    prices = _price_series([100.0, 110.0, 99.0])
    service = MarketDataService(provider=_FakeProvider({"AAA.MC": prices}))
    returns = service.get_returns("AAA.MC", period="5y")
    assert returns.tolist() == pytest.approx([0.10, -0.10])


def test_invalid_symbol_raises_market_data_error() -> None:
    service = MarketDataService(provider=_FakeProvider({}, raise_for={"INVALID"}))
    with pytest.raises(MarketDataError):
        service.get_price_history("INVALID", period="5y")


def test_default_provider_is_yahoo_finance() -> None:
    service = MarketDataService()
    assert isinstance(service.provider, YahooFinanceProvider)


def test_yahoo_finance_provider_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = {"n": 0}

    class _FailTwiceThenSucceedTicker:
        def __init__(self, ticker: str) -> None:
            self._ticker = ticker

        def history(self, period: str) -> pd.DataFrame:
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise RuntimeError("Fallo simulado de red")
            return pd.DataFrame(
                {"Close": [10.0, 11.0]}, index=pd.date_range("2024-01-01", periods=2, freq="D")
            )

    monkeypatch.setattr(market_data_module.yf, "Ticker", _FailTwiceThenSucceedTicker)
    provider = YahooFinanceProvider(max_retries=3, retry_backoff_seconds=0.0)

    prices = provider.get_close_prices("FAKE.MC", period="5y")

    assert call_count["n"] == 3
    assert prices.tolist() == [10.0, 11.0]


def test_yahoo_finance_provider_raises_after_exhausting_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    class _AlwaysFailTicker:
        def __init__(self, ticker: str) -> None:
            pass

        def history(self, period: str) -> pd.DataFrame:
            raise RuntimeError("Fallo simulado de red")

    monkeypatch.setattr(market_data_module.yf, "Ticker", _AlwaysFailTicker)
    provider = YahooFinanceProvider(max_retries=2, retry_backoff_seconds=0.0)

    with pytest.raises(MarketDataError):
        provider.get_close_prices("FAKE.MC", period="5y")


def test_yahoo_finance_provider_raises_on_empty_history(monkeypatch: pytest.MonkeyPatch) -> None:
    class _EmptyTicker:
        def __init__(self, ticker: str) -> None:
            pass

        def history(self, period: str) -> pd.DataFrame:
            return pd.DataFrame()

    monkeypatch.setattr(market_data_module.yf, "Ticker", _EmptyTicker)
    provider = YahooFinanceProvider(max_retries=1, retry_backoff_seconds=0.0)

    with pytest.raises(MarketDataError):
        provider.get_close_prices("FAKE.MC", period="5y")
