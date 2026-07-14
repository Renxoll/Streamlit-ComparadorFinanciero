# Metodología del modelo de perfil inversor

Este documento describe el algoritmo que clasifica a un inversor como **Conservador**, **Moderado** o **Agresivo** a partir de un cuestionario de idoneidad. Está escrito para poder incorporarse directamente como anexo metodológico.

La implementación de referencia vive en dos archivos:

- `core/profile_model_config.py`: **todas** las decisiones del modelo (dimensiones, preguntas, ponderaciones, escala, umbrales). Es la única fuente de verdad; ningún número del algoritmo aparece fuera de este archivo.
- `core/risk_profile.py`: el algoritmo en sí (funciones puras, sin dependencia de la interfaz), que consume la configuración anterior.

## 1. Objetivo del modelo

Evaluar la idoneidad de un inversor combinando tres elementos que exige la normativa de protección al inversor (MiFID II):

1. **Voluntad de asumir riesgo** (actitud/preferencia subjetiva).
2. **Capacidad de asumir riesgo** (circunstancias objetivas: horizonte, patrimonio, necesidad de liquidez).
3. **Conocimiento y experiencia** para comprender los riesgos de los productos.

El modelo anterior (una suma simple de 6 preguntas en escala 1-5, con un baremo de 6-13 / 14-22 / 23-30 puntos) no distinguía estos tres elementos, no documentaba por qué cada pregunta pesaba lo mismo, y en la práctica el perfil casi nunca cambiaba: al sumar 6 variables independientes centradas en el valor medio, el resultado se concentraba estadísticamente en la banda central, que además era la más ancha (37,5 % del rango posible). Este modelo corrige ambos problemas.

## 2. Dimensiones evaluadas

El cuestionario mide **7 dimensiones**, cada una con una pregunta en lenguaje natural (nunca se muestra al usuario una escala numérica) y 5 opciones de respuesta, internamente equivalentes a una puntuación de 1 (más conservadora) a 5 (más arriesgada).

| Dimensión | Categoría | Peso | Justificación del peso |
|---|---|---|---|
| Tolerancia al riesgo | Actitud | **20 %** | Junto con la capacidad de pérdidas, es el pilar central de cualquier evaluación de idoneidad ("willingness to take risk"). |
| Capacidad para asumir pérdidas | Capacidad | **20 %** | Mide la capacidad objetiva ("ability to take risk"), no la actitud. Mismo peso que la tolerancia porque MiFID II trata ambas como los dos pilares de la idoneidad. |
| Horizonte temporal | Capacidad | **15 %** | Un horizonte más largo aumenta estructuralmente la capacidad de asumir riesgo (más tiempo para recuperarse de caídas). |
| Situación financiera | Capacidad | **15 %** | Ingresos estables y colchón de ahorro aumentan la capacidad real de asumir riesgo. **Dimensión nueva**: el modelo original no la evaluaba, pese a ser un requisito explícito de MiFID II. |
| Objetivo de inversión | Actitud | **15 %** | El objetivo declarado condiciona el equilibrio rentabilidad-riesgo que conviene perseguir. |
| Experiencia inversora | Conocimiento | **10 %** | Determina si el inversor comprende los riesgos de productos complejos. Peso moderado en la puntuación, pero además actúa como **límite** (ver sección 5). |
| Liquidez necesaria | Capacidad | **5 %** | Afecta sobre todo al *tipo* de producto adecuado (necesidad de deshacer la posición rápido), no tanto al riesgo de mercado en sí, por lo que recibe el peso más bajo. |

Los 7 pesos suman exactamente **1.00** (verificado por una aserción en tiempo de carga del módulo y por un test dedicado, `test_dimension_weights_sum_to_one`).

Cada dimensión se etiqueta además con una **categoría**: `capacidad` (circunstancia objetiva) o `actitud_conocimiento` (subjetiva o de conocimiento). Esta distinción se usa en la sección 6 para separar "fortalezas" de "factores de riesgo".

## 3. Escala interna y transformación

El usuario nunca ve números. Por ejemplo, para "Horizonte temporal":

| Opción mostrada al usuario | Puntuación interna |
|---|---|
| Menos de 1 año | 1 |
| Entre 1 y 3 años | 2 |
| Entre 3 y 5 años | 3 |
| Entre 5 y 10 años | 4 |
| Más de 10 años | 5 |

Cada una de las 7 dimensiones sigue la misma convención: **1 = respuesta más conservadora, 5 = respuesta más arriesgada**, consistente en todas las dimensiones para que la agregación posterior sea coherente.

## 4. Fórmula de puntuación

La puntuación ponderada total es la suma de cada puntuación interna multiplicada por el peso de su dimensión:

```
puntuación_total = Σ (puntuación_dimensión_i × peso_i)
```

Como los pesos suman 1 y cada puntuación individual está en el rango [1, 5], la puntuación total **siempre** está en el rango **[1.0, 5.0]**, con 3.0 como valor neutro (todas las respuestas centrales).

La suma se redondea a 6 decimales antes de clasificar, para eliminar el ruido de coma flotante binaria inherente a sumar pesos como 0.15 o 0.20 (que no son exactamente representables en binario) sin perder ninguna precisión real: ni los pesos ni las puntuaciones distinguen más de 3 decimales.

## 5. Umbrales de clasificación

| Puntuación ponderada | Perfil |
|---|---|
| < 2.60 | Conservador |
| 2.60 – 3.40 (ambos inclusive) | Moderado |
| > 3.40 | Agresivo |

**Por qué estos valores y no otros:** la banda "Moderado" se definió simétrica alrededor del valor neutro (3.0 ± 0.4), ocupando el 20 % del rango total (1.0-5.0) — frente al 37,5 % de la banda central del modelo original. Esta anchura se eligió deliberadamente para que el perfil **sí cambie** ante combinaciones realistas de respuestas: mover una única dimensión de peso 20 % desde el centro hasta un extremo (por ejemplo, tolerancia al riesgo de 3 a 5) desplaza la puntuación en 0.40 puntos, exactamente el ancho del semi-intervalo Moderado. Es decir, **una respuesta claramente marcada en una dimensión de peso alto, combinada con una segunda respuesta moderadamente marcada, ya es suficiente para cambiar de perfil** — sin llegar a ser tan sensible que una única respuesta extremosa (bien podría ser un error de un clic) reclasifique por sí sola a todo el inversor.

### Regla de límite por experiencia (gating)

Un inversor cuya puntuación en "Experiencia inversora" sea la mínima (1 = "Ninguna experiencia") **nunca puede alcanzar el perfil Agresivo**, aunque el resto de sus respuestas lo sugiera. Si el modelo bruto clasificaría como Agresivo a un inversor sin experiencia, el resultado se limita a Moderado y queda registrado explícitamente en el resultado (`capped_by_experience = True`).

Justificación: MiFID II exige que el cliente comprenda los riesgos de un producto antes de ser dirigido a él ("test de conveniencia"). Una puntuación de riesgo alta combinada con nula experiencia es el caso típico de una respuesta inconsistente que un modelo de idoneidad debe detectar y corregir, no trasladar literalmente a la recomendación.

Los umbrales, el ancho de la banda y el valor de la regla de límite están definidos como constantes con nombre en `core/profile_model_config.py` (`CONSERVADOR_MAX_SCORE`, `MODERADO_MAX_SCORE`, `MIN_EXPERIENCE_SCORE_FOR_AGGRESSIVE`) — no existe ningún número mágico suelto en el código del algoritmo.

## 6. Fortalezas y factores de riesgo

Además de la etiqueta de perfil, el resultado incluye tres listas derivadas de forma determinista de las respuestas:

- **Fortalezas**: dimensiones de categoría `capacidad` (circunstancia objetiva, no actitud) cuya puntuación es ≥ 4. Representan condiciones objetivamente favorables para invertir (por ejemplo, un horizonte largo o un buen colchón de ahorro), con independencia de si el inversor es o no arriesgado por temperamento.
- **Factores que aumentan el riesgo recomendado**: cualquier dimensión (de cualquier categoría) con puntuación ≥ 4.
- **Factores que reducen el riesgo recomendado**: cualquier dimensión con puntuación ≤ 2. Si además se activó la regla de límite por experiencia, se añade una entrada explícita indicándolo.

Nótese que "fortalezas" y "factores que aumentan el riesgo" no son la misma lista: una tolerancia al riesgo alta (actitud) es un factor que aumenta el riesgo recomendado, pero no se cuenta como "fortaleza" en el sentido de capacidad objetiva.

## 7. Trazabilidad completa

El resultado (`InvestorProfileResult`) incluye, por cada una de las 7 dimensiones, un objeto `DimensionContribution` con:

- `selected_label`: la respuesta exacta (en lenguaje natural) elegida por el usuario.
- `internal_score`: a qué puntuación (1-5) se transformó esa respuesta.
- `weight`: el peso de la dimensión.
- `weighted_contribution`: `internal_score × weight`, es decir, cuánto aportó esa dimensión concreta a la puntuación final.

Esto permite reconstruir, para cualquier resultado, exactamente cómo se llegó a él — imprescindible tanto para depurar el modelo como para justificar la recomendación ante el usuario o ante un tribunal de TFM.

## 8. Ejemplos completos de cálculo

Los siguientes 4 ejemplos son salida real del sistema (no valores calculados a mano), obtenidos ejecutando `core.risk_profile.calculate_investor_profile` directamente.

### Ejemplo 1 — Inversor conservador típico

| Dimensión | Respuesta | Puntuación | Peso | Aporte |
|---|---|---|---|---|
| Tolerancia al riesgo | Vendería toda la posición de inmediato... | 1 | 0.20 | 0.200 |
| Capacidad para asumir pérdidas | 2% - 5% | 2 | 0.20 | 0.400 |
| Horizonte temporal | Entre 1 y 3 años | 2 | 0.15 | 0.300 |
| Situación financiera | Ingresos estables, ahorro limitado | 2 | 0.15 | 0.300 |
| Objetivo de inversión | Preservar el capital, evitando pérdidas | 1 | 0.15 | 0.150 |
| Experiencia inversora | Experiencia básica | 2 | 0.10 | 0.200 |
| Liquidez necesaria | Alta | 2 | 0.05 | 0.100 |

**Puntuación total = 1.650 → Perfil = Conservador** (sin límite por experiencia aplicado)

> Explicación generada: *"Con una puntuación ponderada de 1.65 sobre 5.00, el perfil resultante es Conservador. Las dimensiones con mayor influencia en este resultado fueron: Tolerancia al riesgo (peso 20%) y Objetivo de inversión (peso 15%)."*

### Ejemplo 2 — Inversor moderado con matices

| Dimensión | Respuesta | Puntuación | Peso | Aporte |
|---|---|---|---|---|
| Tolerancia al riesgo | Mantendría la inversión sin hacer cambios | 3 | 0.20 | 0.600 |
| Capacidad para asumir pérdidas | 10% - 20% | 4 | 0.20 | 0.800 |
| Horizonte temporal | Entre 5 y 10 años | 4 | 0.15 | 0.600 |
| Situación financiera | Ingresos estables y colchón de varios meses | 3 | 0.15 | 0.450 |
| Objetivo de inversión | Equilibrio entre crecimiento y seguridad | 3 | 0.15 | 0.450 |
| Experiencia inversora | Experiencia media | 3 | 0.10 | 0.300 |
| Liquidez necesaria | Alta | 2 | 0.05 | 0.100 |

**Puntuación total = 3.300 → Perfil = Moderado**

- Fortalezas detectadas: *Capacidad para asumir pérdidas: "10% - 20%"*; *Horizonte temporal: "Entre 5 y 10 años"*
- Factor que reduce el riesgo: *Liquidez necesaria (peso 5%): "Alta"*

Este ejemplo ilustra el diseño: dos dimensiones de peso alto/medio (capacidad de pérdidas 20 %, horizonte 15 %) desplazan la puntuación desde el neutro (3.0) hasta 3.3, sin necesidad de que las 7 dimensiones se muevan a la vez — el problema central del modelo original.

### Ejemplo 3 — Inversor agresivo experimentado

| Dimensión | Respuesta | Puntuación | Peso | Aporte |
|---|---|---|---|---|
| Tolerancia al riesgo | Invertiría una cantidad adicional significativa | 5 | 0.20 | 1.000 |
| Capacidad para asumir pérdidas | 10% - 20% | 4 | 0.20 | 0.800 |
| Horizonte temporal | Más de 10 años | 5 | 0.15 | 0.750 |
| Situación financiera | Ingresos altos y estables, con patrimonio adicional | 4 | 0.15 | 0.600 |
| Objetivo de inversión | Maximizar crecimiento a largo plazo | 5 | 0.15 | 0.750 |
| Experiencia inversora | Experiencia muy alta | 5 | 0.10 | 0.500 |
| Liquidez necesaria | Baja | 4 | 0.05 | 0.200 |

**Puntuación total = 4.600 → Perfil = Agresivo** (experiencia = 5, no se activa el límite)

### Ejemplo 4 — Respuestas inconsistentes: la regla de límite por experiencia en acción

Idéntico al ejemplo 3 en todas las dimensiones salvo que "Experiencia inversora" = 1 ("Ninguna experiencia") y el resto se lleva a su máximo (5):

**Puntuación bruta = 4.600** (idéntica al ejemplo 3, ya que la experiencia solo pesa 10 % y su aporte de 0.100 vs 0.500 no altera lo suficiente la suma para cruzar por sí sola un umbral)

- Perfil bruto sugerido por la puntuación: **Agresivo**
- **Perfil final: Moderado** (`capped_by_experience = True`)
- Factor añadido: *"Experiencia inversora insuficiente para sostener un perfil Agresivo (el resultado se limita a Moderado)."*
- Explicación generada: *"...El resultado bruto del modelo correspondía a un perfil Agresivo, pero se ha limitado a Moderado porque la experiencia inversora declarada es insuficiente para ese nivel de riesgo."*

Este es exactamente el escenario que motiva la regla del apartado 5: un inversor que dice estar dispuesto a asumir el máximo riesgo en todas las dimensiones pero declara no tener ninguna experiencia previa recibe una recomendación más prudente, con la incoherencia explicada de forma transparente en vez de ignorada.

## 9. Efecto sobre la selección de activos

A partir de esta fase, el perfil calculado deja de ser una etiqueta informativa: determina directamente, para cada activo del universo, su elegibilidad (`core.capm.is_eligible_for_profile`) y su score de selección (`core.capm.score_for_profile`):

- **Conservador**: elegible si Beta ≤ 0.75; se prioriza minimizar Beta + volatilidad (protección de capital).
- **Moderado**: elegible si 0.75 ≤ Beta ≤ 1.25; se prioriza minimizar la distancia a Beta = 1 más la volatilidad (activos "de mercado").
- **Agresivo**: elegible si Beta ≥ 1.25; se prioriza maximizar la Beta, sin penalizar la volatilidad (busca amplificar retornos).

Verificado end-to-end (ver informe de Fase 2): con los mismos datos de mercado, el mismo escenario produce Beta conjunta de cartera de 0.86 (Conservador), 0.95 (Moderado) y 1.02 (Agresivo) — la recomendación final cambia de forma coherente con el perfil.

## 10. Limitaciones conocidas y líneas futuras

- Los campos `edad`, `importe` y `plazo` de la Hoja 1 ("Datos del inversor") siguen sin integrarse en el cálculo del perfil; el horizonte temporal se pregunta también en el cuestionario (Hoja 2) de forma independiente. Unificar ambas fuentes es una mejora pendiente, fuera del alcance de esta fase.
- El modelo de selección de activos por perfil (sección 9) sigue siendo una heurística de score mínimo por sector, no una optimización de cartera real. La Fase 3 sustituye este mecanismo por una optimización de Markowitz completa (`scipy.optimize.minimize`) sobre un universo ampliado con ETFs, que consumirá el mismo resultado de perfil descrito en este documento sin cambios en `core/risk_profile.py`.
