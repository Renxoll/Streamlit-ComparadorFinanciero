"""Calculo del perfil inversor mediante un modelo de 7 dimensiones ponderadas.

Sustituye el baremo original (suma simple de 6 sliders 1-5, con umbrales que
casi nunca se cruzaban) por un modelo de scoring transparente: cada dimension
del cuestionario tiene un peso explicito y documentado en
`core/profile_model_config.py`, y el resultado incluye trazabilidad completa
(que respondio el usuario, como se transformo internamente, que peso
recibio, cuanto aporto a la puntuacion final) ademas de la etiqueta de
perfil.

Ver `docs/perfil_inversor_metodologia.md` para la explicacion metodologica
completa, con ejemplos de calculo.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import config
from core.profile_model_config import (
    CAPACITY_CATEGORY,
    CONSERVADOR_MAX_SCORE,
    EXPERIENCE_DIMENSION_KEY,
    MIN_EXPERIENCE_SCORE_FOR_AGGRESSIVE,
    MODERADO_MAX_SCORE,
    NEUTRAL_DIMENSION_SCORE,
    PROFILE_DIMENSIONS,
    AnswerOption,
    ProfileDimension,
)

# A partir de esta puntuacion interna (1-5), una respuesta se considera favorable al riesgo.
_HIGH_SCORE_THRESHOLD = 4
# A partir de esta puntuacion interna (1-5), una respuesta se considera conservadora.
_LOW_SCORE_THRESHOLD = 2
# Decimales a los que se redondea la puntuacion ponderada antes de clasificar, para eliminar
# ruido de coma flotante (ej. 0.15 + 0.20 no es exactamente representable en binario) sin
# perder precision real: los pesos y puntuaciones del modelo no distinguen mas de 3 decimales.
_SCORE_ROUNDING_DECIMALS = 6


@dataclass(frozen=True)
class DimensionContribution:
    """Trazabilidad completa de una dimension: respuesta, transformacion, peso y aporte."""

    dimension_key: str
    dimension_name: str
    selected_label: str
    internal_score: int
    weight: float
    weighted_contribution: float


@dataclass(frozen=True)
class InvestorProfileResult:
    """Resultado estructurado del cuestionario de perfil inversor."""

    total_score: float
    profile: str
    dimension_contributions: tuple[DimensionContribution, ...]
    explanation: str
    strengths: tuple[str, ...]
    risk_increasing_factors: tuple[str, ...]
    risk_decreasing_factors: tuple[str, ...]
    capped_by_experience: bool


def _find_selected_option(dimension: ProfileDimension, label: str) -> AnswerOption:
    """Devuelve la `AnswerOption` de `dimension` cuyo texto coincide con `label`."""
    for option in dimension.options:
        if option.label == label:
            return option
    valid_labels = [option.label for option in dimension.options]
    raise ValueError(
        f"'{label}' no es una respuesta válida para la dimensión '{dimension.key}'. "
        f"Opciones válidas: {valid_labels}."
    )


def _classify_by_score(total_score: float) -> str:
    """Aplica los umbrales de `core.profile_model_config` sobre la puntuación ponderada."""
    if total_score < CONSERVADOR_MAX_SCORE:
        return config.PERFIL_CONSERVADOR
    if total_score <= MODERADO_MAX_SCORE:
        return config.PERFIL_MODERADO
    return config.PERFIL_AGRESIVO


def _build_explanation(
    total_score: float,
    profile: str,
    contributions: tuple[DimensionContribution, ...],
    capped: bool,
) -> str:
    """Genera una explicación en lenguaje natural, citando las dimensiones más influyentes."""
    most_influential = sorted(
        contributions,
        key=lambda c: abs(c.weighted_contribution - NEUTRAL_DIMENSION_SCORE * c.weight),
        reverse=True,
    )[:2]
    influential_text = " y ".join(f"{c.dimension_name} (peso {c.weight:.0%})" for c in most_influential)

    text = (
        f"Con una puntuación ponderada de {total_score:.2f} sobre 5.00, el perfil resultante "
        f"es {profile}. Las dimensiones con mayor influencia en este resultado fueron: "
        f"{influential_text}."
    )
    if capped:
        text += (
            " El resultado bruto del modelo correspondía a un perfil Agresivo, pero se ha "
            "limitado a Moderado porque la experiencia inversora declarada es insuficiente "
            "para ese nivel de riesgo."
        )
    return text


def _detect_strengths(contributions: tuple[DimensionContribution, ...]) -> tuple[str, ...]:
    """Fortalezas: circunstancias OBJETIVAS (categoría 'capacidad') favorables detectadas."""
    dimension_by_key = {dimension.key: dimension for dimension in PROFILE_DIMENSIONS}
    strengths = []
    for contribution in contributions:
        dimension = dimension_by_key[contribution.dimension_key]
        if dimension.category == CAPACITY_CATEGORY and contribution.internal_score >= _HIGH_SCORE_THRESHOLD:
            strengths.append(f'{contribution.dimension_name}: "{contribution.selected_label}"')
    return tuple(strengths)


def _detect_risk_factors(
    contributions: tuple[DimensionContribution, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Factores que aumentan (score alto) o reducen (score bajo) el riesgo recomendado."""
    increasing = []
    decreasing = []
    for contribution in contributions:
        descriptor = f'{contribution.dimension_name} (peso {contribution.weight:.0%}): "{contribution.selected_label}"'
        if contribution.internal_score >= _HIGH_SCORE_THRESHOLD:
            increasing.append(descriptor)
        elif contribution.internal_score <= _LOW_SCORE_THRESHOLD:
            decreasing.append(descriptor)
    return tuple(increasing), tuple(decreasing)


def calculate_investor_profile(selected_labels: Mapping[str, str]) -> InvestorProfileResult:
    """Calcula el perfil inversor a partir de las respuestas en lenguaje natural.

    Args:
        selected_labels: diccionario `dimension.key -> etiqueta elegida por el usuario`,
            con una entrada por cada dimensión de `PROFILE_DIMENSIONS`.

    Returns:
        `InvestorProfileResult` con la puntuación, el perfil, la trazabilidad completa por
        dimensión, una explicación en lenguaje natural, fortalezas y factores de riesgo.

    Raises:
        KeyError: si falta la respuesta de alguna dimensión.
        ValueError: si una respuesta no coincide con ninguna opción válida de su dimensión.
    """
    contributions = []
    for dimension in PROFILE_DIMENSIONS:
        selected_label = selected_labels[dimension.key]
        option = _find_selected_option(dimension, selected_label)
        weighted_contribution = option.score * dimension.weight
        contributions.append(
            DimensionContribution(
                dimension_key=dimension.key,
                dimension_name=dimension.name,
                selected_label=selected_label,
                internal_score=option.score,
                weight=dimension.weight,
                weighted_contribution=weighted_contribution,
            )
        )
    contributions_tuple = tuple(contributions)

    total_score = round(sum(c.weighted_contribution for c in contributions_tuple), _SCORE_ROUNDING_DECIMALS)
    profile = _classify_by_score(total_score)

    experience_contribution = next(c for c in contributions_tuple if c.dimension_key == EXPERIENCE_DIMENSION_KEY)
    capped = False
    if profile == config.PERFIL_AGRESIVO and experience_contribution.internal_score < MIN_EXPERIENCE_SCORE_FOR_AGGRESSIVE:
        profile = config.PERFIL_MODERADO
        capped = True

    strengths = _detect_strengths(contributions_tuple)
    risk_increasing_factors, risk_decreasing_factors = _detect_risk_factors(contributions_tuple)
    if capped:
        risk_decreasing_factors = risk_decreasing_factors + (
            "Experiencia inversora insuficiente para sostener un perfil Agresivo "
            "(el resultado se limita a Moderado).",
        )

    explanation = _build_explanation(total_score, profile, contributions_tuple, capped)

    return InvestorProfileResult(
        total_score=total_score,
        profile=profile,
        dimension_contributions=contributions_tuple,
        explanation=explanation,
        strengths=strengths,
        risk_increasing_factors=risk_increasing_factors,
        risk_decreasing_factors=risk_decreasing_factors,
        capped_by_experience=capped,
    )
