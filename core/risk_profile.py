"""Calculo del perfil inversor a partir del cuestionario MiFID II.

Fase 1: se extrae el algoritmo original tal cual, como funcion pura y
testeable, sin modificar el baremo ni la ponderacion. La correccion del sesgo
hacia "Moderado" y la incorporacion de nuevas variables (observacion 3 del
tutor) se implementan en la Fase 2, ya con esta funcion cubierta por tests
que documentan el comportamiento de partida.
"""
from __future__ import annotations

from dataclasses import dataclass

CONSERVADOR_MAX_SCORE = 13
MODERADO_MAX_SCORE = 22
MIN_POSSIBLE_SCORE = 6
MAX_POSSIBLE_SCORE = 30

PERFIL_CONSERVADOR = "Conservador"
PERFIL_MODERADO = "Moderado"
PERFIL_AGRESIVO = "Agresivo"


@dataclass(frozen=True)
class InvestorProfileResult:
    """Resultado del cuestionario: puntuacion total y perfil normativo asignado."""

    total_score: int
    profile: str


def calculate_investor_profile(scores: list[int]) -> InvestorProfileResult:
    """Calcula el perfil inversor sumando las 6 puntuaciones del cuestionario (escala 1-5).

    Args:
        scores: lista con las 6 puntuaciones del cuestionario, cada una entre 1 y 5.

    Returns:
        `InvestorProfileResult` con la puntuacion total (6-30) y el perfil
        normativo resultante (Conservador / Moderado / Agresivo).
    """
    total_score = sum(scores)

    if total_score <= CONSERVADOR_MAX_SCORE:
        profile = PERFIL_CONSERVADOR
    elif total_score <= MODERADO_MAX_SCORE:
        profile = PERFIL_MODERADO
    else:
        profile = PERFIL_AGRESIVO

    return InvestorProfileResult(total_score=total_score, profile=profile)
