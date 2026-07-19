# Validación financiera del sistema (Fase 4)

Este documento consolida la auditoría financiera realizada en la Fase 4 (Subfases 4.1-4.4): qué se auditó, cómo se validó con evidencia (matemática y empírica, con datos reales) y qué conclusiones y decisiones se adoptaron. Complementa a `docs/markowitz_metodologia.md` (que describe el motor de optimización construido en la Fase 3) y a `docs/perfil_inversor_metodologia.md` (modelo de perfil, Fase 2).

## 1. Objetivo de la validación financiera

La Fase 3 resolvió la **arquitectura y la optimización**: sustituyó la heurística de 2 activos por un optimizador de Markowitz real (`portfolio/`), con restricciones dependientes del perfil, sobre un universo de 13 activos diversificado por clase. Al cerrar la Fase 3 el sistema ya optimizaba carteras correctamente desde el punto de vista *algorítmico*.

Quedaba una pregunta distinta, no resuelta por la Fase 3: **¿son financieramente correctos y coherentes los modelos que alimentan ese optimizador?** Un optimizador puede ejecutarse sin errores y aun así partir de un Beta mal calibrado, un benchmark inapropiado, o una proyección de resultados que contradice matemáticamente los propios retornos que el optimizador calculó. La Fase 4 audita exactamente eso: la consistencia financiera de cada pieza del modelo (criterio Beta, CAPM, proyección) contrastada contra teoría y datos reales, sin tocar la arquitectura salvo donde la evidencia demostrara un error real.

## 2. Validación del criterio Beta (Subfase 4.1)

**Distribución real de Betas** (9 activos de renta variable del universo, datos verificados directamente contra Yahoo Finance): media 0,88, mediana 0,80, desviación estándar 0,24, mínimo 0,61 (`EUNL.DE`), máximo 1,25 (`SAN.MC`, 1,2472 exacto).

**Problema del umbral 1,25:** bajo los umbrales `BETA_ELIGIBILITY_LOWER_BOUND=0,75` / `BETA_ELIGIBILITY_UPPER_BOUND=1,25` (heredados sin cambios desde antes de la Fase 2), la clasificación de los 9 activos de renta variable resulta **Conservador 3/9, Moderado 6/9, Agresivo 0/9**. Ningún activo alcanza el umbral superior — el máximo real queda a un 0,22% de distancia, un margen demasiado pequeño para atribuirlo a ruido de mercado.

**Alternativas consideradas** (evidencia cuantitativa completa en el informe original de la Subfase 4.1): terciles empíricos (reparto 3/3/3), umbral fijo recalibrado a ~1,05-1,10 (reparto 3/3/3 o 3/4/2), ampliar el universo con instrumentos de mayor Beta, o no hacer nada.

**Decisión adoptada:** **ninguna implementación todavía**. Se documentó el hallazgo con 4 alternativas justificadas, recomendando recalibrar el umbral fijo (opción de mayor estabilidad e interpretabilidad), pero la decisión de implementar queda pendiente de aprobación explícita, fuera del alcance de la Fase 4 tal como se acotó.

**Punto importante de coherencia arquitectónica:** el optimizador (`portfolio/optimizer.py`, desde la Subfase 3.5) **no depende de este filtro** — recibe el universo completo de 13 activos para los 3 perfiles, y toda la diferenciación de riesgo la hacen las bandas de composición de `ProfileConstraints` (verificado y validado en las Subfases 3.3-3.5). El criterio de Beta que se auditó en la 4.1 solo afecta a una columna **informativa** de la Hoja 3 (`core.capm.is_eligible_for_profile`), no a la construcción real de la cartera. La auditoría demuestra que ese criterio informativo necesita revisión igualmente, porque mostrar "0 activos elegibles para Agresivo" en una tabla que el usuario puede leer es engañoso, aunque no tenga efecto sobre el resultado final.

## 3. Validación del modelo CAPM (Subfase 4.2)

**Fórmulas verificadas contra la teoría, término a término:**
- Beta: `Cov(Ri,Rm)/Var(Rm)` — coincide con Sharpe (1964)/Lintner (1965).
- CAPM: `Rf + β(Rm−Rf)` — signos y estructura correctos; `market_premium` se recibe ya como `(Rm−Rf)`.
- Sharpe: `(E[R]−Rf)/σ` — es el Sharpe Ratio (1966) clásico (volatilidad total), no el Treynor Ratio.

**Benchmark:** `^STOXX50E` — apropiado para las acciones y ETFs de renta variable europea del universo; aplicado también (por diseño, con la misma fórmula CAPM) a renta fija y monetario, donde CAPM no es el modelo teóricamente correcto, aunque los resultados numéricos son plausibles por construcción (β≈0 ⟹ retorno≈Rf).

**Precios ajustados:** verificado empíricamente (no asumido) que `yf.Ticker(t).history(period=p)` devuelve precios ajustados por dividendos y splits — coincide exactamente con `Adj Close`, con una diferencia media del 8,25% frente al precio sin ajustar sobre `SAN.MC` en la ventana de 5 años. Confirmación positiva, no un hallazgo negativo.

**Unidades anuales:** Rf y prima de mercado se introducen como tasas anuales (Hoja 1); la volatilidad se anualiza con `√252`; Beta no se anualiza (correcto: es un coeficiente adimensional). No se detectó ninguna mezcla de unidades diaria/anual en ningún cálculo.

**Limitaciones detectadas:**
- **Benchmark de precio, no de rentabilidad total:** `^STOXX50E` excluye dividendos. Razonado matemáticamente (`Cov(X,Y+c)=Cov(X,Y)` para una constante `c`) que el impacto sobre Beta es previsiblemente pequeño, dado que los ~50 componentes del índice reparten sus fechas ex-dividendo a lo largo del año. Además, la app no deriva la prima de mercado del benchmark — es un input manual del usuario, lo que limita el alcance práctico del hallazgo.
- **Ausencia de ajuste Blume/Vasicek:** la Beta bruta no se contrae hacia 1, a diferencia de la convención de Bloomberg (`β_adj=0,67·β_raw+0,33·1`). Es un refinamiento de nivel práctico/CFA III, no parte del CAPM de libro de texto que este proyecto implementa deliberadamente en su forma clásica.
- **CAPM aplicado a renta fija/monetario:** simplificación metodológica aceptable para el alcance del proyecto, no un modelo específico de esa clase de activo (que en la práctica se valoraría por curva de tipos/duración, no por Beta bursátil).
- **Propagación silenciosa de `NaN`:** `compute_beta` no distingue `market_variance = NaN` de `market_variance = 0` (`NaN == 0` es `False`). Reproducido directamente invocando las funciones reales con series degeneradas (sin fechas comunes, o con una única fecha común): el resultado es `NaN` sin excepción ni log de error, propagado silenciosamente hasta el DataFrame mostrado en Hoja 3. No se manifiesta con el universo actual (los 13 tickers tienen 1250-1281 filas de histórico, ninguno degenerado), pero el código lo permitiría sin aviso ante un activo futuro con historial insuficiente.

## 4. Validación del modelo de proyección (Subfase 4.3)

**Por qué la proyección blended era incorrecta:** aplicaba una única tasa (la rentabilidad esperada agregada de la cartera en `t=0`) al capital total, en vez de proyectar cada posición con su propio capital y su propia tasa.

**Demostración matemática (desigualdad de Jensen):** para `t≥1`, `x→x^t` es convexa, por lo que `Σwᵢ(1+rᵢ)^t ≥ (1+r_blended)^t`, con igualdad únicamente si `t=1` o si todos los `rᵢ` son idénticos. La dirección del sesgo (el método blended siempre subestima) queda demostrada antes de examinar ningún dato concreto.

**Cuantificación empírica (cartera real, capital 10.000€):** a 1 año, ambos métodos coinciden exactamente (0,000%) en los 3 perfiles, confirmando la identidad matemática. La divergencia crece de forma acelerada: +0,6% a 5 años, +2,8% a 10 años, +12,7% a 20 años, **+29,1% a 31,0% a 30 años** según el perfil.

**Mecanismo (crecimiento diferencial, buy & hold):** en la cartera Moderado, `EXW1.DE` (7,35% de retorno esperado, con el 35% del capital inicial) pasa de representar el 36,1% del valor total en el año 1 al 68,0% en el año 30, mientras `XEON.DE`+`IBGS.AS` (≈2%, ≈61% inicial) se diluyen al 25,6%. La CAGR real implícita sube de 4,07% a 5,01% — el modelo blended, al fijar una tasa estática, nunca captura esta redistribución de peso hacia el activo de mayor rendimiento, que es precisamente lo que ocurre en una cartera **buy & hold** (sin rebalanceo periódico a los pesos iniciales).

## 5. Implementación de la corrección (Subfase 4.4)

**Función nueva:** `core.projections.project_portfolio_by_asset(entries, years)`, que compone cada posición por separado y suma los resultados año a año. `project_compound_growth` se mantuvo sin ninguna modificación (verificado por `git diff` sin cambios en esa función), preservando retrocompatibilidad.

**Por qué recibe pares `(capital, retorno)` y no `PortfolioAllocation.entries` directamente:** decisión arquitectónica deliberada. `core/` no debe depender de `portfolio/` — es `portfolio/` quien depende de `core/` en todo el proyecto desde la Fase 3, nunca al revés. Importar `AllocationEntry` desde `core/projections.py` invertiría esa dirección de dependencia. La extracción `[(entry.allocated_capital, entry.expected_return) for entry in allocation.entries]` se hace en `ui/sections/charts_projection.py`, que ya depende de ambos paquetes y es el lugar correcto para ese puente.

**Antes / Después (cartera Moderado, 10.000€, 30 años, verificado en la app real vía `AppTest`):**

| Año | Antes (blended) | Después (por activo) |
|---|---|---|
| 1 | 10.406,52€ | 10.406,52€ (idéntico) |
| 10 | 14.895,54€ | 15.319,15€ |
| 20 | 22.187,72€ | 25.001,06€ |
| 30 | 33.049,82€ | 43.300,50€ (+31,0%) |

## 6. Validaciones realizadas durante la Fase 4

- **pytest**: ejecutado tras cada subfase con cambios de código (4.4) y tras cada subfase de auditoría (4.1-4.3, para confirmar ausencia de regresión); 195/195 en las subfases de auditoría, 208/208 tras la Subfase 4.4 (+13 tests nuevos de `project_portfolio_by_asset`).
- **mypy**: 0 errores en 27 archivos de producción, en las 4 subfases.
- **AppTest**: ejecutado para los 3 perfiles (Conservador, Moderado, Agresivo) en cada subfase con cambio de código, y al menos una vez por subfase de auditoría; 0 excepciones en todos los casos.
- **Datos reales**: toda cifra citada en este documento proviene de una descarga real de Yahoo Finance en el momento de cada subfase (no de datos simulados ni supuestos), incluyendo la verificación empírica del ajuste por dividendos y la reproducción directa del caso `NaN`.
- **Comparación matemática**: la desigualdad de Jensen (Subfase 4.3) y la invarianza de la covarianza a desplazamientos constantes (Subfase 4.2, benchmark de precio) se demostraron analíticamente antes de medir ningún dato, para que la conclusión no dependiera de la muestra concreta.
- **Comparación empírica**: cada predicción matemática se contrastó después contra datos reales del propio universo de 13 activos (distribución de Beta, deviación de la proyección, discrepancia de volatilidad por método de alineación).

## 7. Limitaciones conocidas (reales, no especuladas)

- El benchmark (`^STOXX50E`) es la variante de precio del Euro Stoxx 50, no de rentabilidad total (Subfase 4.2).
- No se aplica ajuste de Blume/Vasicek a la Beta bruta (Subfase 4.2).
- La proyección de Hoja 5 asume **buy & hold** (sin rebalanceo periódico), un supuesto explícito y documentado, no el único modelo posible (Subfase 4.3/4.4).
- CAPM se aplica a renta fija y monetario como simplificación metodológica, no como modelo específico de esa clase de activo (Subfase 4.2).
- `compute_beta` no distingue `NaN` de `0` en la varianza de mercado; no se manifiesta con el universo actual pero es un riesgo de código real ante un activo con historial insuficiente (Subfase 4.2).
- El criterio de elegibilidad por Beta (Hoja 3, informativo) deja el perfil Agresivo sin renta variable elegible bajo el umbral actual; no afecta a la cartera construida por el optimizador, pero sí a lo que se muestra al usuario (Subfase 4.1).

## 8. Trabajo futuro

**Mejoras metodológicas** (requieren nueva evidencia/aprobación antes de implementarse):
- Recalibrar `BETA_ELIGIBILITY_UPPER_BOUND` (candidato: ~1,05-1,10, ver Subfase 4.1) o sustituir el criterio informativo de Hoja 3 por uno basado en clase de activo.
- Evaluar un modelo de expected return específico para renta fija/monetario (yield to maturity o duración) en vez de CAPM.
- Añadir validación explícita de `NaN`/`Inf` en `compute_beta`, `annualized_volatility` y `capm_expected_return`.
- Documentar formalmente el supuesto de benchmark de precio (ya reflejado en este documento; posible nota adicional en `docs/markowitz_metodologia.md`).

**Mejoras funcionales:**
- Ofrecer, como alternativa opcional a buy & hold, un modelo de proyección con rebalanceo periódico a los pesos iniciales (produciría un tercer resultado, distinto de ambos ya implementados).

**Mejoras de UX:** ninguna identificada durante la Fase 4 — esta fase se mantuvo deliberadamente enfocada en consistencia financiera, no en interfaz.

## 9. Conclusiones

Antes de la Fase 4, el sistema optimizaba carteras correctamente (Fase 3) pero sin haber verificado que los modelos financieros subyacentes fueran coherentes entre sí ni con la teoría. La Fase 4 demuestra que la cadena **CAPM → Optimización → Asignación → Proyección** es ahora matemáticamente consistente de principio a fin: los retornos esperados que CAPM calcula por activo son los mismos que el optimizador usa para maximizar Sharpe, los mismos que `PortfolioAllocation` reparte en euros, y ahora también los mismos que la proyección de Hoja 5 compone — sin la desviación sistemática de hasta el 31% que introducía el modelo blended. Esta consistencia interna **no existía antes de la Fase 4**: la proyección estaba desconectada del resto de la cadena de cálculo, usando una aproximación que ningún otro módulo del sistema compartía ni validaba.

Las limitaciones que persisten (benchmark de precio, ausencia de Blume, CAPM sobre renta fija, buy & hold) están documentadas, cuantificadas donde ha sido posible, y clasificadas explícitamente como supuestos metodológicos conocidos — no como errores sin resolver.
