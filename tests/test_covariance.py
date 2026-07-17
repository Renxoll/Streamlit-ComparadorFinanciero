"""Pruebas unitarias de portfolio/covariance.py: funciones puras, sin red ni Streamlit.

Verifica consistencia cruzada con `core.capm` (mismo resultado par-a-par que
`annualized_covariance`/`annualized_volatility`) además del comportamiento
propiamente matricial (simetría, alineación de fechas, diagonal = varianza).
"""
from __future__ import annotations

import pandas as pd
import pytest

from core import capm
from portfolio import covariance


def _returns(values: list[float], start: str = "2024-01-01") -> pd.Series:
    index = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=index)


class _FakeService:
    """Doble de prueba de MarketDataService: devuelve series fijas sin red."""

    def __init__(self, returns_by_ticker: dict[str, pd.Series]) -> None:
        self._returns_by_ticker = returns_by_ticker

    def get_returns(self, ticker: str, period: str) -> pd.Series:
        return self._returns_by_ticker[ticker]


_SERIES_A = _returns([0.01, 0.02, -0.01, 0.03, 0.00, 0.01, -0.02])
_SERIES_B = _returns([0.02, 0.01, 0.00, 0.02, -0.01, 0.015, -0.01])
_SERIES_C = _returns([-0.01, 0.00, 0.01, -0.02, 0.03, 0.00, 0.01])


def test_build_aligned_returns_matrix_has_one_column_per_ticker() -> None:
    service = _FakeService({"A": _SERIES_A, "B": _SERIES_B, "C": _SERIES_C})
    matrix = covariance.build_aligned_returns_matrix(service, ["A", "B", "C"], period="5y")
    assert list(matrix.columns) == ["A", "B", "C"]
    assert len(matrix) == len(_SERIES_A)  # las 3 series ya comparten fechas


def test_build_aligned_returns_matrix_keeps_only_common_dates() -> None:
    short_series = pd.Series([0.01, 0.02], index=pd.date_range("2024-01-01", periods=2, freq="D"))
    service = _FakeService({"A": _SERIES_A, "SHORT": short_series})
    matrix = covariance.build_aligned_returns_matrix(service, ["A", "SHORT"], period="5y")
    assert len(matrix) == 2


def test_annualized_covariance_matrix_is_symmetric() -> None:
    service = _FakeService({"A": _SERIES_A, "B": _SERIES_B, "C": _SERIES_C})
    matrix = covariance.build_annualized_covariance_matrix(service, ["A", "B", "C"], period="5y")
    pd.testing.assert_frame_equal(matrix, matrix.T, check_exact=False)


def test_annualized_covariance_matrix_diagonal_equals_variance() -> None:
    service = _FakeService({"A": _SERIES_A, "B": _SERIES_B})
    matrix = covariance.build_annualized_covariance_matrix(service, ["A", "B"], period="5y")

    expected_variance_a = capm.annualized_volatility(_SERIES_A) ** 2
    expected_variance_b = capm.annualized_volatility(_SERIES_B) ** 2

    assert matrix.loc["A", "A"] == pytest.approx(expected_variance_a)
    assert matrix.loc["B", "B"] == pytest.approx(expected_variance_b)


def test_annualized_covariance_matrix_matches_pairwise_capm_calculation() -> None:
    """Consistencia cruzada: el off-diagonal debe coincidir con core.capm.annualized_covariance."""
    service = _FakeService({"A": _SERIES_A, "B": _SERIES_B})
    matrix = covariance.build_annualized_covariance_matrix(service, ["A", "B"], period="5y")

    expected_covariance_ab = capm.annualized_covariance(_SERIES_A, _SERIES_B)

    assert matrix.loc["A", "B"] == pytest.approx(expected_covariance_ab)
    assert matrix.loc["B", "A"] == pytest.approx(expected_covariance_ab)


def test_annualized_covariance_matrix_shape_matches_number_of_tickers() -> None:
    service = _FakeService({"A": _SERIES_A, "B": _SERIES_B, "C": _SERIES_C})
    matrix = covariance.build_annualized_covariance_matrix(service, ["A", "B", "C"], period="5y")
    assert matrix.shape == (3, 3)
