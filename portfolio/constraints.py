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


class InfeasibleConstraintsError(Exception):
    """Las bandas de `ProfileConstraints` son matemáticamente imposibles de satisfacer
    con el universo de activos disponible, independientemente de lo que haga el
    optimizador (no es un problema de convergencia numérica).
    """


# Margen de tolerancia para comparaciones de punto flotante en las comprobaciones de
# factibilidad (evita falsos positivos/negativos por redondeo binario de los porcentajes).
_FEASIBILITY_TOLERANCE = 1e-9


def validate_constraint_feasibility(asset_classes: np.ndarray, profile_constraints: ProfileConstraints) -> None:
    """Verifica, ANTES de invocar al optimizador, si las bandas de `profile_constraints`
    tienen alguna solución posible dado el universo de `asset_classes`.

    Comprueba las 3 condiciones necesarias y suficientes para que exista al menos un
    vector de pesos `w` que cumpla simultáneamente `sum(w)=1`, `0 <= w_i <= max_weight_per_asset`
    y las bandas de composición renta fija/renta variable:

    1. Capacidad de renta fija: ¿hay suficientes activos de renta fija/monetario para
       alcanzar, entre todos y con el tope por activo, el mínimo exigido?
    2. Capacidad total: ¿el tope por activo, multiplicado por el número de activos del
       universo, permite siquiera completar el 100% de la cartera?
    3. Bandas no contradictorias: ¿el mínimo de renta fija más el máximo de renta
       variable suman, como mínimo, el 100% de la cartera?

    Args:
        asset_classes: vector (n_activos,) con la clase de cada activo del universo
            considerado (antes de optimizar).
        profile_constraints: bandas del perfil a validar.

    Raises:
        InfeasibleConstraintsError: con un mensaje que explica exactamente qué
            condición falla, si no existe ninguna solución posible.
    """
    n_total_assets = len(asset_classes)
    n_fixed_income_assets = int(np.sum(build_fixed_income_mask(asset_classes)))
    cap = profile_constraints.max_weight_per_asset
    min_fixed_income = profile_constraints.min_fixed_income_weight
    max_equity = profile_constraints.max_equity_weight
    profile = profile_constraints.profile

    max_achievable_fixed_income = n_fixed_income_assets * cap
    if max_achievable_fixed_income < min_fixed_income - _FEASIBILITY_TOLERANCE:
        raise InfeasibleConstraintsError(
            f"El perfil {profile} requiere al menos {min_fixed_income:.0%} en renta fija, "
            f"pero el universo actual solo permite un máximo del {max_achievable_fixed_income:.0%} "
            f"({n_fixed_income_assets} activo(s) de renta fija/monetario x {cap:.0%} de peso "
            f"máximo por activo)."
        )

    max_total_capacity = n_total_assets * cap
    if max_total_capacity < 1.0 - _FEASIBILITY_TOLERANCE:
        raise InfeasibleConstraintsError(
            f"El perfil {profile} tiene un peso máximo de {cap:.0%} por activo, pero el "
            f"universo solo tiene {n_total_assets} activo(s): la capacidad máxima combinada "
            f"es {max_total_capacity:.0%}, insuficiente para completar el 100% de la cartera."
        )

    if min_fixed_income + max_equity < 1.0 - _FEASIBILITY_TOLERANCE:
        raise InfeasibleConstraintsError(
            f"Las bandas del perfil {profile} son contradictorias: el mínimo de renta fija "
            f"({min_fixed_income:.0%}) más el máximo de renta variable ({max_equity:.0%}) "
            f"suman {min_fixed_income + max_equity:.0%}, menos del 100% necesario para "
            f"completar la cartera."
        )
