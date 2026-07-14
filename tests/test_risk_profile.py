"""Pruebas exhaustivas de core/risk_profile.py.

Cubre: escenarios claramente conservadores y agresivos, perfiles intermedios,
casos límite exactamente en los umbrales, respuestas inconsistentes (para
verificar la regla de tope por experiencia), valores extremos, trazabilidad
completa y validación de entradas inválidas.
"""
from __future__ import annotations

import pytest

import config
from core.profile_model_config import (
    EXPERIENCE_DIMENSION_KEY,
    MAX_TOTAL_SCORE,
    MIN_EXPERIENCE_SCORE_FOR_AGGRESSIVE,
    MIN_TOTAL_SCORE,
    PROFILE_DIMENSIONS,
)
from core.risk_profile import calculate_investor_profile

_DIMENSION_BY_KEY = {dimension.key: dimension for dimension in PROFILE_DIMENSIONS}


def _labels_for_scores(scores_by_key: dict[str, int]) -> dict[str, str]:
    """Traduce puntuaciones internas deseadas (1-5) a las etiquetas en lenguaje natural."""
    return {
        key: next(option.label for option in _DIMENSION_BY_KEY[key].options if option.score == score)
        for key, score in scores_by_key.items()
    }


def _all_dimensions_at(score: int, **overrides: int) -> dict[str, str]:
    """Respuestas para las 7 dimensiones a `score`, con overrides puntuales por clave."""
    scores = {dimension.key: score for dimension in PROFILE_DIMENSIONS}
    scores.update(overrides)
    return _labels_for_scores(scores)


# --- Escenarios claros ---


def test_clearly_conservative_investor() -> None:
    answers = _all_dimensions_at(1)
    result = calculate_investor_profile(answers)
    assert result.total_score == pytest.approx(MIN_TOTAL_SCORE)
    assert result.profile == config.PERFIL_CONSERVADOR
    assert result.capped_by_experience is False


def test_clearly_aggressive_investor() -> None:
    # experiencia tambien en 5 para que la regla de tope no interfiera con este escenario.
    answers = _all_dimensions_at(5)
    result = calculate_investor_profile(answers)
    assert result.total_score == pytest.approx(MAX_TOTAL_SCORE)
    assert result.profile == config.PERFIL_AGRESIVO
    assert result.capped_by_experience is False


def test_neutral_answers_produce_moderado() -> None:
    answers = _all_dimensions_at(3)
    result = calculate_investor_profile(answers)
    assert result.total_score == pytest.approx(3.0)
    assert result.profile == config.PERFIL_MODERADO


# --- Perfil intermedio (no neutro, no extremo) ---


def test_intermediate_profile_lands_in_moderado() -> None:
    answers = _all_dimensions_at(3, tolerancia_riesgo=4, capacidad_perdidas=3, horizonte_temporal=4)
    result = calculate_investor_profile(answers)
    assert result.total_score == pytest.approx(3.35)
    assert result.profile == config.PERFIL_MODERADO


# --- Casos límite exactamente en los umbrales (combinaciones calculadas a mano) ---


def test_boundary_exactly_at_conservador_moderado_threshold() -> None:
    # tolerancia_riesgo=5 (peso 0.20), resto=2 -> 5*0.20 + 2*0.80 = 2.60 (umbral exacto)
    answers = _all_dimensions_at(2, tolerancia_riesgo=5)
    result = calculate_investor_profile(answers)
    assert result.total_score == pytest.approx(2.60)
    assert result.profile == config.PERFIL_MODERADO  # el umbral es inclusivo hacia Moderado


def test_just_below_conservador_moderado_threshold() -> None:
    # horizonte_temporal=5 (peso 0.15), resto=2 -> 5*0.15 + 2*0.85 = 2.45 (< 2.60)
    answers = _all_dimensions_at(2, horizonte_temporal=5)
    result = calculate_investor_profile(answers)
    assert result.total_score == pytest.approx(2.45)
    assert result.profile == config.PERFIL_CONSERVADOR


def test_boundary_exactly_at_moderado_agresivo_threshold() -> None:
    # tolerancia_riesgo=5 (peso 0.20), resto=3 -> 5*0.20 + 3*0.80 = 3.40 (umbral exacto)
    answers = _all_dimensions_at(3, tolerancia_riesgo=5)
    result = calculate_investor_profile(answers)
    assert result.total_score == pytest.approx(3.40)
    assert result.profile == config.PERFIL_MODERADO  # el umbral es inclusivo hacia Moderado


def test_just_above_moderado_agresivo_threshold() -> None:
    # tolerancia_riesgo=5, capacidad_perdidas=4, resto=3 -> 3.40 + (1 * 0.20) = 3.60 (> 3.40)
    answers = _all_dimensions_at(3, tolerancia_riesgo=5, capacidad_perdidas=4)
    result = calculate_investor_profile(answers)
    assert result.total_score == pytest.approx(3.60)
    assert result.profile == config.PERFIL_AGRESIVO


# --- Respuestas inconsistentes: regla de tope por experiencia ---


def test_inconsistent_answers_are_capped_by_low_experience() -> None:
    """Un inversor que declara alto riesgo en todo salvo experiencia (=1) no puede
    terminar en Agresivo: la puntuacion bruta lo sugeriria, pero MiFID II exige
    comprender los riesgos antes de asumirlos."""
    answers = _all_dimensions_at(5, experiencia_inversora=1)
    result = calculate_investor_profile(answers)

    assert result.total_score > 3.40  # el modelo bruto sugeriria Agresivo
    assert result.profile == config.PERFIL_MODERADO  # pero se limita por falta de experiencia
    assert result.capped_by_experience is True
    assert any("experiencia" in factor.lower() for factor in result.risk_decreasing_factors)
    assert "limitado a Moderado" in result.explanation


def test_high_experience_does_not_trigger_cap() -> None:
    answers = _all_dimensions_at(5, experiencia_inversora=MIN_EXPERIENCE_SCORE_FOR_AGGRESSIVE)
    result = calculate_investor_profile(answers)
    assert result.profile == config.PERFIL_AGRESIVO
    assert result.capped_by_experience is False


# --- Valores extremos ---


@pytest.mark.parametrize("score", [1, 2, 3, 4, 5])
def test_total_score_always_within_valid_range(score: int) -> None:
    answers = _all_dimensions_at(score)
    result = calculate_investor_profile(answers)
    assert MIN_TOTAL_SCORE <= result.total_score <= MAX_TOTAL_SCORE


# --- Validacion de entradas ---


def test_missing_dimension_raises_key_error() -> None:
    answers = _all_dimensions_at(3)
    del answers[EXPERIENCE_DIMENSION_KEY]
    with pytest.raises(KeyError):
        calculate_investor_profile(answers)


def test_invalid_label_raises_value_error() -> None:
    answers = _all_dimensions_at(3)
    answers["tolerancia_riesgo"] = "Esta no es una opción válida"
    with pytest.raises(ValueError, match="no es una respuesta válida"):
        calculate_investor_profile(answers)


# --- Trazabilidad ---


def test_dimension_contributions_have_full_traceability() -> None:
    answers = _all_dimensions_at(3, tolerancia_riesgo=5)
    result = calculate_investor_profile(answers)

    assert len(result.dimension_contributions) == len(PROFILE_DIMENSIONS)
    for contribution in result.dimension_contributions:
        dimension = _DIMENSION_BY_KEY[contribution.dimension_key]
        assert contribution.selected_label == answers[contribution.dimension_key]
        assert contribution.weight == pytest.approx(dimension.weight)
        assert contribution.weighted_contribution == pytest.approx(contribution.internal_score * contribution.weight)

    tolerancia_contribution = next(c for c in result.dimension_contributions if c.dimension_key == "tolerancia_riesgo")
    assert tolerancia_contribution.internal_score == 5
    assert tolerancia_contribution.weighted_contribution == pytest.approx(1.0)


def test_result_is_deterministic() -> None:
    answers = _all_dimensions_at(3, tolerancia_riesgo=4, experiencia_inversora=2)
    assert calculate_investor_profile(answers) == calculate_investor_profile(answers)


# --- Fortalezas vs. factores de riesgo (categorías distintas, no redundantes) ---


def test_strengths_only_include_capacity_dimensions() -> None:
    # tolerancia_riesgo (actitud) y horizonte_temporal (capacidad) ambas en 5.
    answers = _all_dimensions_at(3, tolerancia_riesgo=5, horizonte_temporal=5)
    result = calculate_investor_profile(answers)

    assert any("Horizonte temporal" in strength for strength in result.strengths)
    assert not any("Tolerancia al riesgo" in strength for strength in result.strengths)
    # Pero SI debe aparecer como factor de riesgo (esa lista no distingue categoria).
    assert any("Tolerancia al riesgo" in factor for factor in result.risk_increasing_factors)


def test_risk_factors_are_symmetric_and_neutral_scores_are_excluded() -> None:
    answers = _all_dimensions_at(3, tolerancia_riesgo=5, capacidad_perdidas=1)
    result = calculate_investor_profile(answers)

    assert any("Tolerancia al riesgo" in factor for factor in result.risk_increasing_factors)
    assert any("Capacidad para asumir pérdidas" in factor for factor in result.risk_decreasing_factors)
    # Las dimensiones que quedaron en el valor neutro (3) no deben aparecer en ninguna lista.
    assert not any("Objetivo de inversión" in factor for factor in result.risk_increasing_factors)
    assert not any("Objetivo de inversión" in factor for factor in result.risk_decreasing_factors)
