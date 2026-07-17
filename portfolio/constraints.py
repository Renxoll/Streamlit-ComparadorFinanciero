"""Restricciones de cartera por perfil inversor (Subfase 3.3).

Centraliza TODAS las bandas de asignación por perfil (peso máximo por
activo, piso de renta fija+monetario, techo de renta variable) en una
estructura declarativa (`ProfileConstraints`): cambiar un porcentaje es
editar una línea de este archivo, sin tocar `portfolio/optimizer.py`.

Las bandas se aplican por CLASE DE ACTIVO ("Renta Variable" / "Renta Fija" /
"Monetario"), no por Beta: la Beta frente a un índice bursátil no es un
criterio válido para incluir o excluir ETFs de renta fija o monetarios (ver
`is_asset_eligible_for_profile`).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import config
from core.capm import is_eligible_for_profile as _is_equity_eligible_for_profile

_FIXED_INCOME_CLASSES = (config.CLASE_RENTA_FIJA, config.CLASE_MONETARIO)


@dataclass(frozen=True)
class ProfileConstraints:
    """Bandas de asignación de cartera para un perfil inversor concreto.

    Todos los porcentajes se expresan como fracción (0.25 = 25 %).
    """

    profile: str
    max_weight_per_asset: float
    min_fixed_income_weight: float
    max_equity_weight: float


# Fuente única de verdad de las bandas por perfil. Para cambiar un
# porcentaje, editar únicamente estos valores; nada más en el código depende
# de ellos por copia.
_CONSTRAINTS_BY_PROFILE: dict[str, ProfileConstraints] = {
    config.PERFIL_CONSERVADOR: ProfileConstraints(
        profile=config.PERFIL_CONSERVADOR,
        max_weight_per_asset=0.25,
        min_fixed_income_weight=0.60,
        max_equity_weight=0.40,
    ),
    config.PERFIL_MODERADO: ProfileConstraints(
        profile=config.PERFIL_MODERADO,
        max_weight_per_asset=0.35,
        min_fixed_income_weight=0.30,
        max_equity_weight=0.70,
    ),
    config.PERFIL_AGRESIVO: ProfileConstraints(
        profile=config.PERFIL_AGRESIVO,
        max_weight_per_asset=0.45,
        min_fixed_income_weight=0.10,
        max_equity_weight=0.90,
    ),
}


def get_constraints_for_profile(profile: str) -> ProfileConstraints:
    """Devuelve las bandas de asignación definidas para `profile`.

    Raises:
        ValueError: si `profile` no es uno de los 3 perfiles normativos.
    """
    try:
        return _CONSTRAINTS_BY_PROFILE[profile]
    except KeyError:
        valid_profiles = list(_CONSTRAINTS_BY_PROFILE)
        raise ValueError(
            f"No hay restricciones definidas para el perfil '{profile}'. Perfiles válidos: {valid_profiles}."
        ) from None


def is_asset_eligible_for_profile(beta: float, asset_class: str, profile: str) -> bool:
    """Determina si un activo entra en el universo invertible de `profile`.

    Renta fija y monetario son SIEMPRE elegibles, independientemente de su
    Beta: la Beta frente a un índice bursátil no mide el riesgo relevante de
    estos instrumentos (puede ser cercana a cero o incluso levemente
    negativa sin que eso los haga inadecuados para ningún perfil), y el
    control de cuánto pesan en la cartera ya lo hacen las bandas de
    composición (`min_fixed_income_weight`) en el optimizador, no un filtro
    binario de entrada.

    Para renta variable (acciones y ETFs de renta variable) se mantiene SIN
    CAMBIOS el criterio de Beta original de `core.capm.is_eligible_for_profile`.
    """
    if asset_class in _FIXED_INCOME_CLASSES:
        return True
    return _is_equity_eligible_for_profile(beta, profile)


def build_fixed_income_mask(asset_classes: np.ndarray) -> np.ndarray:
    """Vector (0.0/1.0) que marca con 1.0 los activos de renta fija o monetario."""
    return np.array([1.0 if asset_class in _FIXED_INCOME_CLASSES else 0.0 for asset_class in asset_classes])


def build_equity_mask(asset_classes: np.ndarray) -> np.ndarray:
    """Vector (0.0/1.0) que marca con 1.0 los activos de renta variable."""
    return np.array(
        [1.0 if asset_class == config.CLASE_RENTA_VARIABLE else 0.0 for asset_class in asset_classes]
    )
