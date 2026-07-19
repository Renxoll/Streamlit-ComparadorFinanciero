# Metodología del motor de optimización de carteras (Markowitz)

Este documento describe el motor que construye la cartera final recomendada al inversor, implementado en el paquete `portfolio/`. Complementa a `docs/perfil_inversor_metodologia.md` (que describe cómo se calcula el perfil de riesgo): este documento describe qué se hace con ese perfil una vez calculado.

## 1. Objetivo

### Qué problema resolvía el diseño original

El sistema original (y su primera refactorización, Fases 1-2) seleccionaba la cartera mediante una heurística: de un universo de 7 acciones (bancos y aseguradoras de la UE), elegía "el mejor banco" y "la mejor aseguradora" por un score `|β − 1| + σ` calculado siempre con la fórmula del perfil Moderado, y mezclaba ambos activos con un peso que el usuario ajustaba manualmente con un slider.

### Qué limitaciones tenía

- **No era una optimización.** El nombre de la pestaña ("Cartera Markowitz") prometía la Teoría Moderna de Carteras, pero `scipy.optimize.minimize` estaba importado y nunca se invocaba.
- **Solo 2 activos, elegidos por sector, no por criterio de cartera.** No existía ninguna combinación real de N activos, ni frontera eficiente, ni maximización de ningún ratio.
- **El score usaba siempre la fórmula de "Moderado"**, con independencia del perfil real calculado por el cuestionario — el perfil no tenía ningún efecto matemático sobre la cartera resultante.
- **Sin control de concentración.** Nada impedía, en teoría, que una futura optimización real concentrase el 100% en un único activo (de hecho, así ocurrió la primera vez que se ejecutó un optimizador real sin restricciones — ver sección 5 y el hallazgo de la Subfase 3.2).
- **Universo sin diversificación de clase de activo.** Solo acciones de un mismo sector económico (banca y seguros europeos), sin renta fija ni monetario.

### Por qué fue sustituido

Porque una recomendación de cartera que no está optimizada, que ignora el perfil de riesgo real del usuario y que no puede diversificar entre clases de activo no es defendible ni como producto ni como metodología de TFM. La Fase 3 sustituye la heurística por un optimizador de Markowitz real, con restricciones dependientes del perfil y un universo que permite diversificación genuina.

## 2. Arquitectura

La lógica de cartera se separa en dos paquetes con responsabilidades distintas:

```
core/            → información de MERCADO y de UN activo frente al mercado
  market_data.py    - acceso a Yahoo Finance (vía MarketDataService/MarketDataProvider)
  capm.py           - Beta, volatilidad, CAPM, Sharpe individual (univariante)
  risk_profile.py   - cálculo del perfil inversor (7 dimensiones ponderadas)
  profile_model_config.py - configuración del modelo de perfil

portfolio/       → información MULTIVARIANTE y construcción de la CARTERA
  covariance.py     - matriz de covarianzas anualizada del universo (N x N)
  metrics.py        - métricas de cartera dado un vector de pesos (retorno, varianza, Sharpe, Beta)
  optimizer.py       - el problema de optimización en sí (scipy.optimize.minimize)
  constraints.py       - bandas de asignación por perfil + validación de factibilidad
  allocation.py          - traduce pesos óptimos + capital del inversor a euros por activo
```

La distinción es deliberada: `core/` no sabe nada sobre carteras (solo conoce un activo a la vez, frente a un benchmark); `portfolio/` no sabe nada sobre el mercado (recibe retornos y covarianzas ya calculados, nunca descarga nada directamente salvo a través de `core.market_data`). Ningún módulo de `portfolio/` importa Streamlit — todo es testeable sin la aplicación.

### Diagrama de flujo

```
Perfil inversor (Conservador / Moderado / Agresivo)
        │
        ▼
Universo de mercado (13 activos: acciones, ETFs de renta variable,
                      renta fija y monetario)
        │
        ▼
CAPM (retorno esperado y Beta por activo, core/capm.py)
        │
        ▼
Covarianza (matriz N x N anualizada, portfolio/covariance.py)
        │
        ▼
Restricciones del perfil (bandas de composición, portfolio/constraints.py)
        │
        ▼
Optimización (máximo Sharpe sujeto a restricciones, portfolio/optimizer.py)
        │
        ▼
Asignación de capital (pesos → euros por activo, portfolio/allocation.py)
        │
        ▼
UI (ui/sections/markowitz_portfolio.py — solo presentación)
```

Cada flecha es una frontera de responsabilidad: la UI solo consume el resultado final (`PortfolioAllocation`), no recalcula nada.

## 3. Universo de inversión

### Activos originales (7, sin cambios desde el modelo pre-refactorización)

7 acciones ordinarias de bancos y aseguradoras de la Unión Europea: Banco Santander, BNP Paribas, ING Groep (banca); Allianz, AXA, Mapfre, Assicurazioni Generali (seguros).

### ETFs añadidos (6, Subfases 3.1 y 3.4)

| Ticker | Instrumento | Clase de activo | Motivo |
|---|---|---|---|
| `EUNL.DE` | iShares Core MSCI World UCITS ETF | Renta Variable | Diversificación global, reduce el sesgo sectorial/geográfico de las 7 acciones. |
| `EXW1.DE` | iShares Core EURO STOXX 50 UCITS ETF | Renta Variable | Exposición amplia a renta variable de la zona euro, sin concentración sectorial banca/seguros. |
| `AGGH.MI` | iShares Core Global Aggregate Bond UCITS ETF (EUR Hedged) | Renta Fija | Renta fija global agregada, cubierta a EUR. |
| `IBGS.AS` | iShares Euro Government Bond 1-3yr UCITS ETF | Renta Fija | Deuda pública euro de corto plazo (baja duración, vol. anual ≈1.6%): añadido en la Subfase 3.4 para resolver la infactibilidad de Conservador (ver sección 8). |
| `IEAC.AS` | iShares Core EUR Corporate Bond UCITS ETF | Renta Fija | Renta fija corporativa investment grade en euros (riesgo de crédito, no solo de tipos): añadido junto con `IBGS.AS`. |
| `XEON.DE` | Xtrackers II EUR Overnight Rate Swap UCITS ETF | Monetario | Instrumento monetario EUR (tipo a un día), volatilidad prácticamente nula (≈0.25% anual). |

### Por qué ETFs UCITS

UCITS ("Undertakings for Collective Investment in Transferable Securities") es el marco regulatorio europeo de fondos armonizados: exige diversificación mínima dentro del propio fondo, límites de concentración, liquidez y transparencia de costes. Son productos aptos para un inversor minorista europeo, cotizados y con histórico verificable en Yahoo Finance — condición necesaria para poder aplicar el mismo motor CAPM/Markowitz que al resto del universo. Se excluyó explícitamente cualquier ETF apalancado, sintético especulativo o de derivados.

### Por qué no se añadieron productos redundantes

Antes de incorporar cada ETF se verificó su correlación y volatilidad frente a los activos ya presentes en el universo, para evitar diversificación aparente sin diversificación real:

- No se añadió un ETF de S&P 500 junto al de MSCI World: se solaparía en más del 60% de su composición (EE.UU. domina el índice MSCI World), añadiendo ruido de correlación sin aportar una fuente de riesgo distinta.
- `IBGS.AS` e `IEAC.AS` se verificaron frente a `AGGH.MI` antes de añadirse: correlación 0.65-0.74 (no >0.90, que habría indicado redundancia) y volatilidades claramente distintas (1.6% / 4.5% / 4.7%), confirmando que aportan fuentes de riesgo diferenciadas (duración corta vs. riesgo de crédito vs. agregado global).

## 4. Modelo matemático

Notación: `w` = vector de pesos de la cartera (uno por activo), `μ` = vector de retornos esperados, `Σ` = matriz de covarianzas anualizada, `Rf` = tasa libre de riesgo, `β` = vector de betas individuales.

**Retorno esperado de un activo (CAPM)**
```
E[R_i] = Rf + β_i · (Rm − Rf)
```
Implementado en `core/capm.py::capm_expected_return`, sin ninguna aproximación adicional: la función recibe `Rf` y `(Rm − Rf)` ya calculados y aplica la fórmula tal cual.

Desde la Subfase 5.1, `Rf` y `Rm` son **constantes fijas**, no un input manual del usuario (antes, un `st.number_input` en la Hoja 1 permitía cambiarlos en cada ejecución, lo que impedía reproducir exactamente el mismo resultado entre evaluaciones distintas):

| Parámetro | Valor | Constante |
|---|---|---|
| `Rf` (tasa libre de riesgo anual) | 2,3% | `config.RISK_FREE_RATE` |
| `Rm` (rentabilidad de mercado anual) | 8,0% | `config.MARKET_RETURN` |
| `Rm − Rf` (prima de riesgo, la que consume `capm_expected_return`) | 5,7% | `config.MARKET_RISK_PREMIUM` (derivada de las dos anteriores, no un tercer número suelto) |

Son referencias representativas del mercado europeo en la fecha de elaboración del proyecto, no datos de mercado en vivo — el mismo disclaimer se muestra en la Hoja 1 (`config.CAPM_ASSUMPTIONS_DISCLAIMER`).

**Beta de un activo**
```
β_i = Cov(R_i, R_m) / Var(R_m)
```
Estimada empíricamente con datos históricos: series de retornos diarios de 5 años, alineadas por fecha con el benchmark (Euro Stoxx 50). Es el único componente de `E[R_i]` que varía por activo — `Rf` y `Rm` son los mismos para todos. Implementado en `core/capm.py::compute_beta`.

**Importante — separación entre CAPM y la optimización:** `E[R_i]` se calcula por completo ANTES de optimizar, en `core/capm.py::build_universe_metrics` (capa `core/`, sin ningún conocimiento de carteras). El optimizador de Markowitz (`portfolio/optimizer.py`) recibe el vector `μ` de retornos esperados ya calculado como uno de sus 3 argumentos de entrada (junto con `Σ` y `Rf`) y lo usa tal cual en su función objetivo — **no vuelve a calcular ningún retorno por su cuenta**. Esta separación es la misma que describe la sección 2 (Arquitectura): `core/` calcula "cuánto se espera que rinda cada activo"; `portfolio/` decide "cuánto peso poner en cada uno", sin mezclar ambas responsabilidades en el mismo módulo.

**Retorno esperado de la cartera**
```
E[R_p] = w' μ = Σ_i w_i · E[R_i]
```
Implementado en `portfolio/metrics.py::portfolio_expected_return`.

**Varianza y volatilidad de la cartera**
```
σ_p² = w' Σ w
σ_p  = √(w' Σ w)
```
Esta es la forma cuadrática clásica de Markowitz: a diferencia de una media ponderada de volatilidades individuales, `w'Σw` incorpora las covarianzas cruzadas entre todos los pares de activos, capturando el beneficio real de la diversificación. Implementado en `portfolio/metrics.py::portfolio_variance` / `portfolio_volatility`.

**Beta de la cartera**
```
β_p = w' β = Σ_i w_i · β_i
```
Implementado en `portfolio/metrics.py::portfolio_beta`.

**Ratio de Sharpe**
```
Sharpe = (E[R_p] − Rf) / σ_p
```
Aplicado tanto a activos individuales (`core/capm.py::sharpe_ratio`) como a la cartera completa (`portfolio/metrics.py::portfolio_sharpe_ratio`, que delega en la misma fórmula para no duplicarla).

**Matriz de covarianzas**
```
Σ_ij = Cov(R_i, R_j) anualizada = Cov_diaria(R_i, R_j) × 252
```
construida a partir de retornos diarios alineados por fecha entre TODOS los activos del universo simultáneamente (no solo pares), en `portfolio/covariance.py::build_annualized_covariance_matrix`.

## 5. Optimización

**Función objetivo**: maximizar el Ratio de Sharpe de la cartera, formulado como minimización de su negativo (scipy solo minimiza):
```
minimizar_w   −(w'μ − Rf) / √(w'Σw)
```

**Algoritmo**: `scipy.optimize.minimize(method="SLSQP")` — Sequential Least Squares Programming, el método estándar de scipy para problemas no lineales con restricciones de igualdad y desigualdad simultáneas (como este). El punto de partida es la cartera de pesos iguales (`1/n` cada uno): un punto neutro, ya factible, que no sesga la solución hacia ningún activo concreto.

**Restricciones estructurales (siempre activas)**:
```
Σ w_i = 1          (la cartera invierte el 100% del capital, ni más ni menos)
w_i ≥ 0             (no se permite venta en corto — no aplicable a un inversor minorista)
```

**Restricciones por perfil (opcionales, añadidas desde la Subfase 3.3)**:
```
w_i ≤ peso_máx(perfil)                        — vía `bounds` de scipy (restricción de caja, exacta)
Σ w_i∈{RF,Monetario} ≥ mín_RF(perfil)          — restricción lineal de desigualdad
Σ w_i∈RV ≤ máx_RV(perfil)                       — restricción lineal de desigualdad
```

El peso máximo por activo se implementa como `bounds` (no como una restricción de desigualdad adicional) porque scipy resuelve las cotas de caja de forma más robusta y exacta que N restricciones individuales `w_i ≤ máx`.

**Por qué el peso máximo por activo es necesario, no opcional**: sin él, la optimización de Markowitz es célebremente inestable ante error de estimación en los retornos esperados (Michaud, 1989, "maximización de errores"): pequeñas diferencias en μ empujan al optimizador hacia soluciones de esquina. Se comprobó empíricamente en la Subfase 3.2: sin restricción de peso máximo, el optimizador concentró el 97% de la cartera en 2 activos de los 11 disponibles en ese momento.

## 6. Restricciones por perfil

| Perfil | Peso máx. por activo | Piso renta fija + monetario | Techo renta variable | Objetivo financiero |
|---|---|---|---|---|
| Conservador | 25% | 60% | 40% | Protección del capital: la mayoría de la cartera en instrumentos de bajo riesgo, sin concentración excesiva en ningún activo individual. |
| Moderado | 35% | 30% | 70% | Equilibrio entre crecimiento y seguridad. |
| Agresivo | 45% | 10% | 90% | Crecimiento: se permite mayor concentración y mayor exposición a renta variable, manteniendo un piso mínimo de liquidez/seguridad. |

Justificación financiera: el piso de renta fija/monetario y el techo de renta variable son complementarios por diseño (suman exactamente 100% en los 3 perfiles), de modo que ambas restricciones codifican la misma política de asignación de capital vista desde dos ángulos — no son reglas independientes que puedan entrar en conflicto entre sí. El peso máximo por activo crece con el apetito de riesgo del perfil: un Conservador nunca debería depender en exceso de un único emisor o instrumento, mientras que un Agresivo, que ya asume más riesgo de mercado por diseño, puede razonablemente concentrar más en las mejores oportunidades identificadas por el modelo.

### Por qué 25% / 35% / 45%, específicamente

Los tres topes están directamente relacionados con el problema que describe **Michaud (1989, "The Markowitz Optimization Enigma: Is 'Optimized' Optimal?")**: la optimización de media-varianza sin restricciones es extremadamente sensible a errores de estimación en los retornos esperados — pequeñas diferencias en `μ` (que siempre existen, al venir de una estimación histórica, no de un valor cierto) empujan al optimizador hacia soluciones de esquina, concentrando el resultado en muy pocos activos aunque la diferencia real de calidad entre ellos y el resto sea mínima. Michaud lo llama la "maximización de errores": el optimizador no distingue entre una diferencia de retorno esperado genuina y el ruido de la propia estimación, y trata ambas como si fueran igual de fiables.

Los tres objetivos que persigue limitar el peso máximo por activo, en línea con ese problema:

- **Evitar concentración excesiva**: ningún perfil permite que un único activo supere el 45% de la cartera (Agresivo), ni el 25% en Conservador. Es una cota dura, no una preferencia: el optimizador no puede violarla aunque matemáticamente "quisiera" concentrar más (se implementa como `bounds` de scipy, sección 5).
- **Reducir la sensibilidad a errores de estimación**: cuanto más conservador el perfil, más bajo el tope (25% frente a 45%) — precisamente porque un inversor conservador es el que menos margen tiene para absorber el efecto de un error de estimación en el activo que el modelo cree, erróneamente, que es el mejor.
- **Mejorar la diversificación**: con un tope de 25%, la cartera de Conservador necesita, por aritmética, al menos 4 posiciones distintas para completar el 100%; con 45% (Agresivo), basta con 3 — es decir, el tope no solo limita el riesgo de un único activo, también fuerza un número mínimo de posiciones independientes, coherente con el principio de diversificación de Markowitz (1952) que fundamenta todo el modelo.

Se comprobó empíricamente en la Subfase 3.2 (antes de introducir estos topes) que, sin ninguna restricción de concentración, el optimizador llegó a poner el 97% de la cartera en 2 activos de los 11 disponibles en ese momento — la manifestación exacta del problema de Michaud sobre datos reales de este proyecto, no solo una advertencia teórica.

Los valores concretos (25/35/45) no proceden de una fórmula cerrada de la literatura — Michaud no prescribe un número exacto, solo demuestra la necesidad de acotar — sino de una escala creciente y proporcional al apetito de riesgo de cada perfil, con Moderado como punto intermedio razonable entre los dos extremos.

Estas bandas, y no un filtro de elegibilidad individual por Beta, son las que realmente diferencian las 3 carteras resultantes (ver limitación conocida en la sección 8).

## 7. Validaciones implementadas

| Validación | Dónde | Qué comprueba |
|---|---|---|
| Suma de pesos = 1 | `portfolio/metrics.py::validate_weights_sum_to_one` | Con tolerancia numérica (1e-6); el optimizador renormaliza sus pesos tras resolver para garantizarlo. |
| No venta en corto | `portfolio/metrics.py::validate_no_short_selling` | Ningún peso negativo. |
| Matriz cuadrada / dimensiones compatibles | `portfolio/metrics.py::validate_square_matrix`, `validate_dimensions_match` | El número de activos coincide entre pesos, retornos esperados y la matriz de covarianzas. |
| Matriz semidefinida positiva (PSD) | `portfolio/metrics.py::validate_positive_semidefinite_covariance` | Condición matemática necesaria para que la matriz represente una covarianza real; se comprueba una única vez al inicio de la optimización (no en cada iteración, por coste computacional). |
| Factibilidad de las restricciones del perfil | `portfolio/constraints.py::validate_constraint_feasibility` | Antes de invocar a scipy: ¿hay suficiente renta fija disponible para el piso exigido?, ¿el tope por activo permite completar el 100%?, ¿las bandas no son contradictorias? Lanza `InfeasibleConstraintsError` con un mensaje explícito si no. |
| Capital exacto al céntimo | `portfolio/allocation.py::_allocate_capital_across_entries` | La asignación se calcula en céntimos enteros (no en euros con decimales) para que la suma de los importes asignados coincida exactamente con el capital del inversor, sin pérdida por redondeo. |

## 8. Limitaciones conocidas

- **La proyección de capital (Hoja 5) sigue aplicando una única tasa de rentabilidad esperada (la de la cartera completa) al capital total**, en vez de proyectar cada posición con su capital asignado y sumar los resultados año a año. Para horizontes de varios años, ambos cálculos divergen matemáticamente (promediar tasas y componer no es lo mismo que componer cada activo y sumar). Es una limitación heredada de fases anteriores, no introducida ni resuelta en la Fase 3; requiere una fase propia centrada en el modelo de proyección.
- **El filtro de elegibilidad individual por Beta (`portfolio.constraints.is_asset_eligible_for_profile`) no se usa para preseleccionar el universo que recibe el optimizador.** Se comprobó en la Subfase 3.5 que, con los datos reales actuales, ningún activo de renta variable alcanza el umbral Beta ≥ 1.25 exigido para el perfil Agresivo (el máximo real es 1.2475): aplicar ese filtro habría dejado a "Agresivo" sin ninguna renta variable disponible. El umbral (heredado sin cambios desde el modelo original, nunca contrastado contra la distribución real de Betas del universo) queda documentado como candidato a recalibración en una fase futura. Mientras tanto, toda la diferenciación de riesgo por perfil la hacen las bandas de composición (sección 6), ya validadas como suficientes.
- **El modelo de retorno esperado (CAPM de un solo factor) aplica el mismo benchmark (Euro Stoxx 50) a activos de naturaleza muy distinta** (acciones bancarias europeas, un ETF de renta variable global, un ETF monetario). Es una simplificación estándar de un modelo CAPM de libro de texto, documentada aquí como supuesto metodológico, no como error.
- **La tasa libre de riesgo y la prima de mercado son parámetros introducidos manualmente por el usuario**, no datos de mercado en tiempo real — razonable para fines pedagógicos, pero debe presentarse como "supuesto del usuario", no como "dato de mercado".

## 9. Referencias

- **Markowitz, H. (1952). "Portfolio Selection". *The Journal of Finance*.** Origen de la Teoría Moderna de Carteras: para un nivel de riesgo dado, existe una combinación de activos que maximiza el retorno esperado (la "frontera eficiente"), gracias a que la varianza de una cartera depende no solo de las varianzas individuales sino de las covarianzas entre activos. Es la base matemática de `portfolio/metrics.py` y `portfolio/optimizer.py`.
- **Sharpe, W. F. (1966). "Mutual Fund Performance". *The Journal of Business*.** Introduce el ratio que lleva su nombre, rentabilidad en exceso de la tasa libre de riesgo por unidad de volatilidad, usado aquí como función objetivo de la optimización (la cartera "tangente" de la frontera eficiente).
- **CAPM (Capital Asset Pricing Model)**, desarrollado por Sharpe, Lintner y Mossin a partir del trabajo de Markowitz: relaciona el retorno esperado de un activo con su Beta (sensibilidad al riesgo de mercado no diversificable) y la prima de riesgo de mercado. Es la base de `core/capm.py`.
