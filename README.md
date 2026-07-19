# 📊 Sistema de Recomendación y Optimización de Inversión
**Máster Universitario en Ciencias Actuariales y Financieras (MUCAF) - Universidad de León**

Una aplicación web interactiva desarrollada en Python que replica, automatiza y mejora el modelo actuarial diseñado para el Trabajo Fin de Máster. Orientada a la perfilación de riesgo (MiFID II), evaluación del riesgo sistemático y optimización de carteras de inversión centradas en el sector bancario y asegurador de la Unión Europea.

## 🧠 Arquitectura Lógica del Sistema (Perfilado y Scoring)

El motor de recomendación se fundamenta en un proceso secuencial de dos fases que conecta la normativa europea con la teoría financiera de carteras:

**1. Evaluación de Idoneidad (Perfil del Inversor)**
Se aplica un cuestionario interactivo de 6 variables clave (horizonte, liquidez, experiencia, objetivos, tolerancia y capacidad de pérdida) valoradas en una escala del 1 al 5. El algoritmo procesa la sumatoria total (máximo de 30 puntos):
- **6 - 13 Puntos:** Perfil **Conservador**
- **14 - 22 Puntos:** Perfil **Moderado**
- **23 - 30 Puntos:** Perfil **Agresivo**

**2. Asignación Financiera Dinámica (Filtro por Beta $\beta$)**
El modelo extrae la sensibilidad histórica del activo frente al Euro Stoxx 50 y aplica reglas estrictas de filtrado y puntuación según el perfil obtenido:
- **Inversor Conservador:** Selecciona activos refugio ($\beta < 0.95$). El "Score" interno penaliza la suma de Beta y Volatilidad para priorizar la protección del capital.
- **Inversor Moderado:** Exige activos con un nivel de riesgo similar al mercado ($0.80 \le \beta \le 1.20$). El "Score" matemático minimiza la distancia del activo respecto al mercado: $|\beta - 1| + \sigma$.
- **Inversor Agresivo:** Filtra activos procíclicos ($\beta > 1.05$). El "Score" recompensa la alta sensibilidad para amplificar retornos en fases expansivas, asumiendo mayor volatilidad.

## 🚀 Características Principales y Flujo de la Interfaz

La aplicación está estructurada exactamente en **6 fases (pestañas)** secuenciales que guían al usuario y automatizan los cálculos matemáticos:

1. **Datos del Inversor:** Recopilación de parámetros de entrada críticos para el modelo (Capital a invertir, Plazo temporal, Tasa libre de riesgo $R_f$ y Prima de mercado). Incluye un diccionario metodológico de las variables.
2. **Cuestionario MiFID II:** Test de idoneidad y conveniencia mediante *sliders* de puntuación. Clasifica algorítmicamente al inversor.
3. **Productos por Perfil (Motor Actuarial Dinámico):**
   - **Extracción de datos en tiempo real:** Conexión con Yahoo Finance para descargar series históricas de precios (últimos 5 años).
   - **Benchmark de Mercado:** Utilización del Euro Stoxx 50 (`^STOXX50E`) para la obtención empírica de la matriz de covarianzas.
   - **Cálculo en vivo:** Procesamiento matemático de la Volatilidad Anualizada ($\sigma$), la Beta ($\beta$) real, la rentabilidad exigida (**CAPM**) y el Ratio de Sharpe.
4. **Análisis M1-M7 y Cartera Conjunta:** Selección automatizada del activo ganador por sector (Banco y Aseguradora) según el Score. Permite simular el cruce de pesos porcentuales y calcular la rentabilidad, el riesgo y el Ratio de Sharpe de la cartera combinada.
5. **Gráficos y Proyección:** Cálculo de capitalización compuesta del capital invertido desde $t=0$ hasta el año límite del horizonte temporal. Visualización gráfica del desempeño de la cartera híbrida frente a los activos individuales.
6. **Resumen de Interfaz y Exportación:** Dashboard ejecutivo con las resoluciones metodológicas del algoritmo.
   - **Exportación a PDF:** Generación dinámica de la Ficha de Recomendación Oficial, lista para anexar a la memoria del TFM.

🛡️ **Blindaje Anti-Fallos (Fallback System):** Sistema de seguridad programado para la defensa del máster. Si el ordenador carece de conexión a internet o la API de Yahoo Finance deniega la petición durante la presentación, el sistema adopta instantáneamente los valores actuariales estáticos pre-calculados en el modelo original, asegurando un funcionamiento ininterrumpido.

## 🛠️ Stack Tecnológico

El proyecto está construido íntegramente en Python utilizando las siguientes librerías:

* **[Streamlit](https://streamlit.io/):** Creación de la interfaz gráfica de usuario y gestión del estado de la sesión (`session_state`).
* **[yfinance](https://pypi.org/project/yfinance/):** Petición de cotizaciones históricas y metadatos bursátiles al mercado de valores.
* **[Pandas](https://pandas.pydata.org/) & [NumPy](https://numpy.org/):** Limpieza de series de tiempo, alineación de fechas, retornos logarítmicos y cálculos algebraicos de matrices de covarianza.
* **[SciPy](https://scipy.org/):** Resolución algorítmica para la optimización de pesos.
* **[FPDF2](https://pyfpdf.github.io/fpdf2/):** Construcción estructurada y exportación del reporte ejecutivo en formato `.pdf`.
* **[Certifi](https://pypi.org/project/certifi/):** Gestión de certificados SSL para garantizar la resolución y autorización de peticiones web hacia la API financiera.

## 💻 Instalación y Ejecución Local

Sigue estos pasos para levantar la aplicación en tu entorno de desarrollo:

**1. Clonar o descargar el proyecto**
Asegúrate de tener el archivo `app.py` (o `main.py`) guardado en tu directorio de trabajo.

**2. Instalar dependencias**
Abre tu terminal y ejecuta el siguiente comando para instalar todas las librerías necesarias:
```bash
pip install -r requirements.txt
