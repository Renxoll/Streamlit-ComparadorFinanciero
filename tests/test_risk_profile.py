"""Pruebas unitarias de core/risk_profile.py.

Documentan el comportamiento ACTUAL del baremo (heredado del app.py
original) para poder demostrar objetivamente, en la Fase 2, que la
correccion del sesgo hacia "Moderado" cambia estos resultados de forma
controlada y no accidental.
"""
from __future__ import annotations

import pytest

from core.risk_profile import calculate_investor_profile


@pytest.mark.parametrize(
    "scores,expected_profile",
    [
        ([1, 1, 1, 1, 1, 1], "Conservador"),  # 6 puntos: minimo posible
        ([2, 2, 2, 2, 2, 3], "Conservador"),  # 13 puntos: limite superior Conservador
        ([2, 2, 2, 2, 3, 3], "Moderado"),     # 14 puntos: limite inferior Moderado
        ([3, 3, 3, 3, 3, 3], "Moderado"),     # 18 puntos: centro de la banda (valor por defecto de los sliders)
        ([4, 4, 4, 4, 3, 3], "Moderado"),     # 22 puntos: limite superior Moderado
        ([4, 4, 4, 4, 4, 3], "Agresivo"),     # 23 puntos: limite inferior Agresivo
        ([5, 5, 5, 5, 5, 5], "Agresivo"),     # 30 puntos: maximo posible
    ],
)
def test_calculate_investor_profile_thresholds(scores: list[int], expected_profile: str) -> None:
    result = calculate_investor_profile(scores)
    assert result.total_score == sum(scores)
    assert result.profile == expected_profile


def test_calculate_investor_profile_is_deterministic() -> None:
    scores = [1, 5, 2, 4, 3, 3]
    assert calculate_investor_profile(scores) == calculate_investor_profile(scores)


def test_single_slider_change_rarely_crosses_a_threshold() -> None:
    """Documenta el bug de fondo (observacion 3 del tutor): mover un unico
    slider desde el centro (3) no alcanza para cambiar de perfil, porque la
    banda "Moderado" (14-22) es la mas ancha y esta centrada en la suma por
    defecto (18). Este test debe empezar a FALLAR en la Fase 2, cuando se
    corrija la ponderacion — su objetivo es dejar constancia del problema.
    """
    baseline = calculate_investor_profile([3, 3, 3, 3, 3, 3])
    moved_one_slider_to_extreme = calculate_investor_profile([5, 3, 3, 3, 3, 3])
    assert baseline.profile == moved_one_slider_to_extreme.profile == "Moderado"
