"""Métricas de cartera: funciones puras sobre pesos, retornos y covarianza.

Cada función opera sobre arrays de NumPy (pesos, retornos esperados, matriz
de covarianzas) sin conocer tickers ni ninguna estructura de `pandas` — la
correspondencia entre posiciones del array y activos concretos es
responsabilidad de quien llama (ver `portfolio.allocation`, Subfase 3.4).

Ningún módulo de `portfolio/` depende de Streamlit.
"""
from __future__ import annotations

import numpy as np

from core.capm import sharpe_ratio as _asset_sharpe_ratio

# --- Tolerancias de validación (ninguna vive fuera de este bloque: cero numeros magicos) ---
WEIGHT_SUM_TOLERANCE = 1e-6
NEGATIVE_WEIGHT_TOLERANCE = 1e-8
COVARIANCE_PSD_TOLERANCE = 1e-8


def validate_weights_sum_to_one(weights: np.ndarray, tolerance: float = WEIGHT_SUM_TOLERANCE) -> None:
    """Verifica que los pesos de la cartera sumen 1, dentro de una tolerancia numérica."""
    total = float(np.sum(weights))
    if abs(total - 1.0) > tolerance:
        raise ValueError(f"Los pesos de la cartera deben sumar 1.0 (suman {total:.8f}).")


def validate_no_short_selling(weights: np.ndarray, tolerance: float = NEGATIVE_WEIGHT_TOLERANCE) -> None:
    """Verifica que ningún peso sea negativo (no se permite venta en corto)."""
    minimum_weight = float(np.min(weights))
    if minimum_weight < -tolerance:
        raise ValueError(
            f"No se permiten pesos negativos (no short-selling); mínimo encontrado: {minimum_weight:.8f}."
        )


def validate_square_matrix(matrix: np.ndarray, name: str = "matriz") -> None:
    """Verifica que `matrix` sea cuadrada (2 dimensiones, mismo número de filas y columnas)."""
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"La {name} debe ser cuadrada; forma recibida: {matrix.shape}.")


def validate_dimensions_match(weights_or_returns: np.ndarray, covariance_matrix: np.ndarray) -> None:
    """Verifica que la longitud del vector coincida con la dimensión de la matriz de covarianzas."""
    validate_square_matrix(covariance_matrix, name="matriz de covarianzas")
    n_assets = len(weights_or_returns)
    if covariance_matrix.shape != (n_assets, n_assets):
        raise ValueError(
            f"Dimensiones incompatibles: {n_assets} elementos frente a una matriz de "
            f"covarianzas de forma {covariance_matrix.shape}."
        )


def validate_positive_semidefinite_covariance(
    covariance_matrix: np.ndarray, tolerance: float = COVARIANCE_PSD_TOLERANCE
) -> None:
    """Verifica que `covariance_matrix` sea semidefinida positiva.

    Es una condición matemática necesaria para que la matriz represente una
    covarianza real (autovalores negativos indicarían datos inconsistentes,
    p. ej. series de precios mal alineadas). Se exige semidefinida, no
    estrictamente definida positiva, porque activos perfecta o casi
    perfectamente correlacionados producen autovalores exactamente o casi
    cero, que son válidos.

    Nota de rendimiento: esta validación calcula los autovalores de la
    matriz (coste O(n^3)) y por eso NO se invoca dentro de `portfolio_variance`
    (que el optimizador llama en cada iteración); se invoca una única vez al
    inicio de `portfolio.optimizer.optimize_max_sharpe`.
    """
    validate_square_matrix(covariance_matrix, name="matriz de covarianzas")
    eigenvalues = np.linalg.eigvalsh(covariance_matrix)
    minimum_eigenvalue = float(np.min(eigenvalues))
    if minimum_eigenvalue < -tolerance:
        raise ValueError(
            f"La matriz de covarianzas no es semidefinida positiva "
            f"(autovalor mínimo={minimum_eigenvalue:.8e}); no es una matriz de covarianzas válida."
        )


def portfolio_expected_return(weights: np.ndarray, expected_returns: np.ndarray) -> float:
    """Retorno esperado de la cartera: combinación lineal ponderada `w' · μ`."""
    return float(np.dot(weights, expected_returns))


def portfolio_variance(weights: np.ndarray, covariance_matrix: np.ndarray) -> float:
    """Varianza de la cartera: forma cuadrática de Markowitz `w' · Σ · w`."""
    validate_dimensions_match(weights, covariance_matrix)
    return float(weights @ covariance_matrix @ weights)


def portfolio_volatility(weights: np.ndarray, covariance_matrix: np.ndarray) -> float:
    """Volatilidad (desviación típica) de la cartera: raíz cuadrada de la varianza."""
    variance = portfolio_variance(weights, covariance_matrix)
    # max(...,0.0) protege de ruido de coma flotante (una covarianza PSD nunca
    # produce varianza negativa en teoria, pero el redondeo binario si puede
    # arrastrar valores como -1e-18 en la practica).
    return float(np.sqrt(max(variance, 0.0)))


def portfolio_beta(weights: np.ndarray, betas: np.ndarray) -> float:
    """Beta de la cartera: promedio ponderado de las betas individuales `w' · β`."""
    return float(np.dot(weights, betas))


def portfolio_sharpe_ratio(expected_return: float, risk_free_rate: float, volatility: float) -> float:
    """Ratio de Sharpe de la cartera.

    Delega en `core.capm.sharpe_ratio`: la fórmula es idéntica a la de un
    activo individual una vez se dispone del retorno esperado y la
    volatilidad ya agregados a nivel de cartera; no se duplica aquí.
    """
    return _asset_sharpe_ratio(expected_return, risk_free_rate, volatility)
