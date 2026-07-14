"""Pruebas de la configuración del modelo: valida que el modelo esté bien formado.

Estas pruebas son la garantía de "no hay umbrales mágicos": si alguien edita
`core/profile_model_config.py` y rompe una invariante (pesos que no suman 1,
una dimensión sin 5 opciones, umbrales desordenados), estas pruebas fallan
inmediatamente en vez de producir un perfil incorrecto en producción.
"""
from __future__ import annotations

import pytest

import config
from core.profile_model_config import (
    CONSERVADOR_MAX_SCORE,
    EXPERIENCE_DIMENSION_KEY,
    MAX_DIMENSION_SCORE,
    MAX_TOTAL_SCORE,
    MIN_DIMENSION_SCORE,
    MIN_TOTAL_SCORE,
    MODERADO_MAX_SCORE,
    PROFILE_DIMENSIONS,
)


def test_dimension_weights_sum_to_one() -> None:
    total_weight = sum(dimension.weight for dimension in PROFILE_DIMENSIONS)
    assert total_weight == pytest.approx(1.0)


def test_there_are_seven_dimensions() -> None:
    assert len(PROFILE_DIMENSIONS) == 7


def test_dimension_keys_are_unique() -> None:
    keys = [dimension.key for dimension in PROFILE_DIMENSIONS]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize("dimension", PROFILE_DIMENSIONS, ids=lambda d: d.key)
def test_each_dimension_has_five_options_scored_one_to_five(dimension) -> None:  # type: ignore[no-untyped-def]
    assert len(dimension.options) == 5
    scores = sorted(option.score for option in dimension.options)
    assert scores == [1, 2, 3, 4, 5]


@pytest.mark.parametrize("dimension", PROFILE_DIMENSIONS, ids=lambda d: d.key)
def test_each_dimension_has_positive_weight_and_non_empty_text(dimension) -> None:  # type: ignore[no-untyped-def]
    assert dimension.weight > 0
    assert dimension.name.strip() != ""
    assert dimension.question.strip() != ""
    assert dimension.rationale.strip() != ""


@pytest.mark.parametrize("dimension", PROFILE_DIMENSIONS, ids=lambda d: d.key)
def test_option_labels_within_a_dimension_are_unique(dimension) -> None:  # type: ignore[no-untyped-def]
    labels = [option.label for option in dimension.options]
    assert len(labels) == len(set(labels))


def test_thresholds_are_ordered_and_within_range() -> None:
    assert MIN_TOTAL_SCORE < CONSERVADOR_MAX_SCORE < MODERADO_MAX_SCORE < MAX_TOTAL_SCORE


def test_total_score_range_matches_dimension_score_range() -> None:
    assert MIN_TOTAL_SCORE == float(MIN_DIMENSION_SCORE)
    assert MAX_TOTAL_SCORE == float(MAX_DIMENSION_SCORE)


def test_experience_dimension_key_exists_in_dimensions() -> None:
    keys = {dimension.key for dimension in PROFILE_DIMENSIONS}
    assert EXPERIENCE_DIMENSION_KEY in keys


def test_profile_labels_are_defined_in_config() -> None:
    assert config.PERFIL_CONSERVADOR == "Conservador"
    assert config.PERFIL_MODERADO == "Moderado"
    assert config.PERFIL_AGRESIVO == "Agresivo"
