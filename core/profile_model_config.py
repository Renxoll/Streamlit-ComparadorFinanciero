"""Configuracion del modelo de perfil inversor (cuestionario de idoneidad).

Centraliza TODAS las decisiones del algoritmo de perfilado: dimensiones
evaluadas, preguntas en lenguaje natural, ponderacion de cada dimension,
escala interna y umbrales de clasificacion. Ninguna de estas decisiones debe
aparecer como un numero suelto en `core/risk_profile.py`: si se quiere
auditar, justificar o modificar el modelo, este es el unico archivo a revisar.

Ver `docs/perfil_inversor_metodologia.md` para la explicacion metodologica
completa, con ejemplos de calculo.
"""
from __future__ import annotations

from dataclasses import dataclass

import config

# --- Escala interna de cada dimension ---
MIN_DIMENSION_SCORE = 1
MAX_DIMENSION_SCORE = 5
NEUTRAL_DIMENSION_SCORE = 3

MIN_TOTAL_SCORE = float(MIN_DIMENSION_SCORE)
MAX_TOTAL_SCORE = float(MAX_DIMENSION_SCORE)

# --- Categorias de dimension: distinguen circunstancias OBJETIVAS ("capacidad") de
#     actitud/conocimiento SUBJETIVO ("actitud_conocimiento"). Se usa para separar
#     "fortalezas" (capacidad objetiva favorable) de "factores de riesgo" (cualquier
#     dimension, objetiva o subjetiva, que empuje la puntuacion hacia un extremo). ---
CAPACITY_CATEGORY = "capacidad"
ATTITUDE_KNOWLEDGE_CATEGORY = "actitud_conocimiento"


@dataclass(frozen=True)
class AnswerOption:
    """Una opcion de respuesta en lenguaje natural y su equivalencia en la escala interna."""

    label: str
    score: int


@dataclass(frozen=True)
class ProfileDimension:
    """Una dimension del cuestionario de perfil inversor, con su pregunta y ponderacion."""

    key: str
    name: str
    question: str
    weight: float
    category: str
    rationale: str
    options: tuple[AnswerOption, ...]


PROFILE_DIMENSIONS: tuple[ProfileDimension, ...] = (
    ProfileDimension(
        key="tolerancia_riesgo",
        name="Tolerancia al riesgo",
        question="Si el valor de su inversión cayera un 10% en poco tiempo, ¿cómo reaccionaría?",
        weight=0.20,
        category=ATTITUDE_KNOWLEDGE_CATEGORY,
        rationale=(
            "Mide la disposición subjetiva a soportar pérdidas temporales. Junto con la "
            "capacidad de asumir pérdidas, es el componente central de cualquier evaluación "
            "de idoneidad MiFID II, por lo que recibe el peso más alto del modelo."
        ),
        options=(
            AnswerOption("Vendería toda la posición de inmediato para evitar más pérdidas", 1),
            AnswerOption("Vendería una parte para reducir el riesgo", 2),
            AnswerOption("Mantendría la inversión sin hacer cambios", 3),
            AnswerOption("Aprovecharía para invertir algo más", 4),
            AnswerOption("Invertiría una cantidad adicional significativa", 5),
        ),
    ),
    ProfileDimension(
        key="capacidad_perdidas",
        name="Capacidad para asumir pérdidas",
        question="¿Qué porcentaje de pérdida temporal podría asumir sin que afecte a su situación financiera?",
        weight=0.20,
        category=CAPACITY_CATEGORY,
        rationale=(
            "Mide la capacidad OBJETIVA (no la actitud) de absorber pérdidas sin comprometer "
            "el resto de la situación financiera. Recibe el mismo peso que la tolerancia al "
            "riesgo porque, según MiFID II, ambas son los dos pilares de la idoneidad: "
            "'willingness' y 'ability' to take risk."
        ),
        options=(
            AnswerOption("0% - 2%: no puedo permitirme pérdidas", 1),
            AnswerOption("2% - 5%", 2),
            AnswerOption("5% - 10%", 3),
            AnswerOption("10% - 20%", 4),
            AnswerOption("Más del 20%", 5),
        ),
    ),
    ProfileDimension(
        key="horizonte_temporal",
        name="Horizonte temporal",
        question="¿Cuál es su horizonte temporal previsto para esta inversión?",
        weight=0.15,
        category=CAPACITY_CATEGORY,
        rationale=(
            "Un horizonte más largo aumenta estructuralmente la capacidad de asumir riesgo, "
            "al permitir recuperarse de caídas temporales del mercado antes de necesitar el "
            "capital."
        ),
        options=(
            AnswerOption("Menos de 1 año", 1),
            AnswerOption("Entre 1 y 3 años", 2),
            AnswerOption("Entre 3 y 5 años", 3),
            AnswerOption("Entre 5 y 10 años", 4),
            AnswerOption("Más de 10 años", 5),
        ),
    ),
    ProfileDimension(
        key="situacion_financiera",
        name="Situación financiera",
        question="¿Cómo describiría su situación financiera actual (ingresos, ahorros y estabilidad)?",
        weight=0.15,
        category=CAPACITY_CATEGORY,
        rationale=(
            "Un colchón de ahorro e ingresos estables aumentan la capacidad real de asumir "
            "riesgo, con independencia de la actitud declarada por el inversor. Dimensión "
            "ausente en el modelo original pese a ser un requisito explícito de MiFID II "
            "('situación financiera, incluida la capacidad para soportar pérdidas')."
        ),
        options=(
            AnswerOption("Ingresos ajustados, sin ahorro adicional al invertido", 1),
            AnswerOption("Ingresos estables, ahorro limitado", 2),
            AnswerOption("Ingresos estables y un colchón de ahorro de varios meses", 3),
            AnswerOption("Ingresos altos y estables, con patrimonio adicional", 4),
            AnswerOption("Situación financiera muy sólida, con excedente significativo", 5),
        ),
    ),
    ProfileDimension(
        key="objetivo_inversion",
        name="Objetivo de inversión",
        question="¿Cuál es el objetivo principal de esta inversión?",
        weight=0.15,
        category=ATTITUDE_KNOWLEDGE_CATEGORY,
        rationale=(
            "El objetivo declarado (preservar capital frente a maximizar crecimiento) "
            "condiciona directamente el equilibrio rentabilidad-riesgo que conviene perseguir."
        ),
        options=(
            AnswerOption("Preservar el capital, evitando pérdidas", 1),
            AnswerOption("Obtener una rentabilidad algo superior a la inflación, con bajo riesgo", 2),
            AnswerOption("Buscar un equilibrio entre crecimiento y seguridad", 3),
            AnswerOption("Priorizar el crecimiento, asumiendo riesgo moderado-alto", 4),
            AnswerOption("Maximizar el crecimiento a largo plazo, asumiendo alta volatilidad", 5),
        ),
    ),
    ProfileDimension(
        key="experiencia_inversora",
        name="Experiencia inversora",
        question="¿Cuál es su experiencia previa invirtiendo en productos financieros?",
        weight=0.10,
        category=ATTITUDE_KNOWLEDGE_CATEGORY,
        rationale=(
            "La experiencia y el conocimiento determinan si el inversor comprende los riesgos "
            "de los productos más complejos. Recibe un peso moderado en la puntuación, pero "
            "además actúa como límite (ver `MIN_EXPERIENCE_SCORE_FOR_AGGRESSIVE`): un "
            "inversor sin experiencia nunca se clasifica como Agresivo, aunque el resto de "
            "respuestas lo sugieran."
        ),
        options=(
            AnswerOption("Ninguna experiencia", 1),
            AnswerOption("Experiencia básica (depósitos, fondos garantizados)", 2),
            AnswerOption("Experiencia media (fondos de inversión, alguna acción)", 3),
            AnswerOption("Experiencia alta (acciones, ETFs, derivados ocasionalmente)", 4),
            AnswerOption("Experiencia muy alta: inversor activo y habitual en varios mercados", 5),
        ),
    ),
    ProfileDimension(
        key="liquidez_necesaria",
        name="Liquidez necesaria",
        question="¿Qué prioridad tiene para usted poder disponer de este dinero en cualquier momento?",
        weight=0.05,
        category=CAPACITY_CATEGORY,
        rationale=(
            "Afecta sobre todo al TIPO de producto adecuado (necesidad de poder deshacer la "
            "posición rápidamente) más que al riesgo de mercado en sí mismo, por lo que "
            "recibe el peso más bajo del modelo."
        ),
        options=(
            AnswerOption("Muy alta: podría necesitarlo en cualquier momento", 1),
            AnswerOption("Alta", 2),
            AnswerOption("Media", 3),
            AnswerOption("Baja", 4),
            AnswerOption("Muy baja: no lo necesitaré en el corto/medio plazo", 5),
        ),
    ),
)

_WEIGHT_SUM_TOLERANCE = 1e-9
_total_weight = sum(dimension.weight for dimension in PROFILE_DIMENSIONS)
assert abs(_total_weight - 1.0) < _WEIGHT_SUM_TOLERANCE, (
    f"Los pesos de PROFILE_DIMENSIONS deben sumar 1.0 (suman {_total_weight})."
)

# --- Umbrales de clasificacion sobre la puntuacion ponderada (escala 1.0 - 5.0) ---
# Banda "Moderado" centrada en el valor neutro (3.0) y simetrica (+/- 0.4 puntos),
# deliberadamente mas estrecha que la banda del modelo original (que ocupaba el 37.5%
# del rango posible): con estos umbrales, la combinacion de 2-3 respuestas claramente
# marcadas en las dimensiones de mayor peso ya desplaza el perfil, sin que haga falta
# mover las 7 dimensiones a la vez. Justificacion numerica completa en
# docs/perfil_inversor_metodologia.md.
CONSERVADOR_MAX_SCORE = 2.6
MODERADO_MAX_SCORE = 3.4

# --- Regla de limitacion por experiencia (gating, no solo ponderacion) ---
# Un inversor sin experiencia (puntuacion minima en "experiencia_inversora") nunca puede
# alcanzar el perfil Agresivo aunque su puntuacion ponderada lo sugiera: MiFID II exige que
# el cliente comprenda los riesgos de un producto antes de ser dirigido a el.
EXPERIENCE_DIMENSION_KEY = "experiencia_inversora"
MIN_EXPERIENCE_SCORE_FOR_AGGRESSIVE = 2

assert any(dimension.key == EXPERIENCE_DIMENSION_KEY for dimension in PROFILE_DIMENSIONS), (
    f"EXPERIENCE_DIMENSION_KEY='{EXPERIENCE_DIMENSION_KEY}' no existe en PROFILE_DIMENSIONS."
)
assert config.PERFIL_CONSERVADOR and config.PERFIL_MODERADO and config.PERFIL_AGRESIVO, (
    "config.py debe definir las 3 etiquetas de perfil normativo."
)
