"""Datos reales congelados del universo completo (13 activos, Subfase 3.4).

No es un archivo de test (pytest lo ignora por no empezar con `test_`): es un
módulo de constantes compartido por `test_constraints.py`, `test_optimizer.py`
y `test_allocation.py`, para no repetir la descarga real de Yahoo Finance en
cada archivo ni depender de la red al ejecutar la suite.

Generado una única vez a partir de `core.capm.build_universe_metrics` +
`portfolio.covariance.build_annualized_covariance_matrix` sobre
`config.UNIVERSO_TFM` (Rf=0.02, prima=0.055, período=5y).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config

TICKERS = [
    "SAN.MC", "BNP.PA", "INGA.AS", "ALV.DE", "CS.PA", "MAP.MC", "G.MI",
    "EUNL.DE", "EXW1.DE", "AGGH.MI", "IBGS.AS", "IEAC.AS", "XEON.DE",
]

EMPRESAS = [
    "Banco Santander", "BNP Paribas", "ING Groep", "Allianz SE", "AXA SA", "Mapfre SA",
    "Assicurazioni Generali", "iShares Core MSCI World UCITS ETF",
    "iShares Core EURO STOXX 50 UCITS ETF",
    "iShares Core Global Aggregate Bond UCITS ETF (EUR Hedged)",
    "iShares Euro Government Bond 1-3yr UCITS ETF", "iShares Core EUR Corporate Bond UCITS ETF",
    "Xtrackers II EUR Overnight Rate Swap UCITS ETF",
]

ASSET_CLASSES = np.array(
    [config.CLASE_RENTA_VARIABLE] * 9 + [config.CLASE_RENTA_FIJA] * 3 + [config.CLASE_MONETARIO]
)

RISK_FREE_RATE = 0.02

EXPECTED_RETURNS = np.array([
    0.08861395, 0.08246624, 0.08002630, 0.06297696, 0.06410116, 0.05429769,
    0.05695852, 0.05381961, 0.07354125, 0.02151863, 0.02043627, 0.02482329,
    0.02003973,
])

BETAS = np.array([
    1.24752637e+00, 1.13574998e+00, 1.09138705e+00, 7.81399296e-01,
    8.01839134e-01, 6.23594858e-01, 6.71972805e-01, 6.14902047e-01,
    9.73477119e-01, 2.76114792e-02, 7.93239535e-03, 8.76956671e-02,
    7.22328137e-04,
])

VOLATILITIES = np.array([
    0.30788141, 0.2842396, 0.2783024, 0.1956971, 0.20929424, 0.21051165,
    0.19359016, 0.14135808, 0.17302507, 0.04680632, 0.01603434, 0.0451662,
    0.00252984,
])

SHARPE_RATIOS = np.array([
    0.22285837, 0.21976618, 0.21568728, 0.2196096, 0.21071364, 0.16292551,
    0.19091107, 0.23924782, 0.30944211, 0.03244501, 0.02720922, 0.10678919,
    0.01570375,
])

COVARIANCE_MATRIX = np.array([
    [9.54906107e-02, 6.39565352e-02, 6.11361220e-02, 3.83306446e-02, 3.99974585e-02, 3.75851045e-02, 3.27814231e-02, 2.13985399e-02, 3.84580706e-02, -1.75829437e-04, -1.86896594e-04, 1.96757200e-03, 2.71051776e-05],
    [6.39565352e-02, 8.11780144e-02, 6.25284920e-02, 3.55799813e-02, 4.05214272e-02, 3.16082313e-02, 3.14798098e-02, 1.86546407e-02, 3.50859166e-02, -4.21240000e-04, -2.14120583e-04, 1.78561600e-03, 2.27286258e-05],
    [6.11361220e-02, 6.25284920e-02, 7.78262852e-02, 3.41968784e-02, 3.82306995e-02, 3.06502491e-02, 2.89114878e-02, 1.84823655e-02, 3.36691578e-02, -1.39920489e-03, -4.01214231e-04, 1.33244818e-03, 2.13232894e-05],
    [3.83306446e-02, 3.55799813e-02, 3.41968784e-02, 3.85072934e-02, 3.14533670e-02, 2.41965645e-02, 2.57353916e-02, 1.37090209e-02, 2.42584254e-02, 1.18453035e-04, 1.05438875e-04, 1.83164730e-03, 2.62632651e-05],
    [3.99974585e-02, 4.05214272e-02, 3.82306995e-02, 3.14533670e-02, 4.48879613e-02, 2.61190736e-02, 2.71537723e-02, 1.41465636e-02, 2.51260203e-02, -1.54428826e-04, 1.73210092e-05, 1.67503470e-03, 2.70961728e-05],
    [3.75851045e-02, 3.16082313e-02, 3.06502491e-02, 2.41965645e-02, 2.61190736e-02, 4.42119480e-02, 2.22394712e-02, 1.11839064e-02, 1.90725877e-02, -1.20506586e-04, -6.27032650e-05, 9.82016077e-04, 7.93471487e-06],
    [3.27814231e-02, 3.14798098e-02, 2.89114878e-02, 2.57353916e-02, 2.71537723e-02, 2.22394712e-02, 3.75620511e-02, 1.25135713e-02, 2.07545959e-02, 6.37634453e-05, 1.27532822e-04, 1.83935463e-03, 1.80093425e-05],
    [2.13985399e-02, 1.86546407e-02, 1.84823655e-02, 1.37090209e-02, 1.41465636e-02, 1.11839064e-02, 1.25135713e-02, 2.01689812e-02, 1.88648787e-02, 5.05558268e-04, 2.06209321e-04, 2.16446038e-03, -2.15655587e-06],
    [3.84580706e-02, 3.50859166e-02, 3.36691578e-02, 2.42584254e-02, 2.51260203e-02, 1.90725877e-02, 2.07545959e-02, 1.88648787e-02, 3.01360837e-02, 8.47171408e-04, 2.64223289e-04, 2.71178217e-03, 1.87202657e-05],
    [-1.75829437e-04, -4.21240000e-04, -1.39920489e-03, 1.18453035e-04, -1.54428826e-04, -1.20506586e-04, 6.37634453e-05, 5.05558268e-04, 8.47171408e-04, 2.19689766e-03, 4.86405338e-04, 1.48560287e-03, 1.85355043e-06],
    [-1.86896594e-04, -2.14120583e-04, -4.01214231e-04, 1.05438875e-04, 1.73210092e-05, -6.27032650e-05, 1.27532822e-04, 2.06209321e-04, 2.64223289e-04, 4.86405338e-04, 2.55545529e-04, 5.35673320e-04, 1.23025125e-06],
    [1.96757200e-03, 1.78561600e-03, 1.33244818e-03, 1.83164730e-03, 1.67503470e-03, 9.82016077e-04, 1.83935463e-03, 2.16446038e-03, 2.71178217e-03, 1.48560287e-03, 5.35673320e-04, 2.03996532e-03, 3.33381883e-06],
    [2.71051776e-05, 2.27286258e-05, 2.13232894e-05, 2.62632651e-05, 2.70961728e-05, 7.93471487e-06, 1.80093425e-05, -2.15655587e-06, 1.87202657e-05, 1.85355043e-06, 1.23025125e-06, 3.33381883e-06, 6.47910600e-06],
])


def build_universe_metrics(investor_profile: str = config.PERFIL_MODERADO) -> pd.DataFrame:
    """Reconstruye el DataFrame equivalente a `core.capm.build_universe_metrics` a partir
    de los datos congelados de este módulo, sin red. Usado por `test_allocation.py` para
    probar `portfolio.allocation.build_portfolio_allocation` con datos reales."""
    return pd.DataFrame({
        config.COL_PERFIL_OBJETIVO: [investor_profile] * len(TICKERS),
        config.COL_TICKER: TICKERS,
        config.COL_EMPRESA: EMPRESAS,
        config.COL_CLASE_ACTIVO: ASSET_CLASSES,
        config.COL_BETA: BETAS,
        config.COL_CAPM: EXPECTED_RETURNS,
        config.COL_SHARPE: SHARPE_RATIOS,
        config.COL_VOL_ANUAL: VOLATILITIES,
    })
