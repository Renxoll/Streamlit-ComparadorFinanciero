# 📊 Comparador y Optimizador de Inversión Financiera (TFM)

Una aplicación web interactiva desarrollada en Python orientada al análisis financiero, evaluación del riesgo sistemático y optimización de carteras de inversión. Este proyecto aplica normativas de idoneidad (MiFID II) y teorías fundamentales de finanzas cuantitativas para el sector bancario y asegurador europeo.

## 🚀 Características Principales

La aplicación integra análisis en tiempo real y modelos matemáticos avanzados a través de una interfaz gráfica intuitiva:

1. **Análisis Fundamental Automatizado:**
   - Extracción de datos en tiempo real de Yahoo Finance.
   - Cálculo y comparación comparativa de ratios clave: ROE, ROA, Margen Operativo, Utilidad Neta e Ingresos Totales.
   - Conversión de divisas dinámica (EUR/USD) obteniendo el tipo de cambio del mercado al instante.

2. **Evaluación de Riesgo Sistemático (Beta) y Modelo CAPM:**
   - Filtrado estricto de activos basado en la Beta ($\beta$) para ajustarse al perfil del inversor (enfocado en el Perfil Moderado, buscando $\beta \approx 1$).
   - Cálculo automático de la **Rentabilidad Esperada** de cada activo utilizando el Modelo de Valoración de Activos de Capital (CAPM), integrando una tasa libre de riesgo y una prima de mercado parametrizadas.

3. **Optimización de Carteras (Teoría de Markowitz):**
   - Descarga de históricos de precios de los últimos 5 años para construir la matriz de varianzas-covarianzas de los activos seleccionados.
   - Algoritmo de optimización (`scipy.optimize`) para calcular la **Frontera Eficiente**.
   - Asignación porcentual óptima del capital para **maximizar el Ratio de Sharpe**, mostrando la rentabilidad esperada conjunta y el nivel de riesgo (volatilidad anualizada).

4. **Visualización y Generación de Reportes:**
   - Gráficas interactivas mostrando la evolución del precio de las acciones en los últimos 6 meses.
   - Resaltado visual condicional (verde/rojo) que indica automáticamente el activo "ganador" en cada métrica financiera.
   - **Exportación a PDF:** Generación dinámica de un reporte profesional descargable que incluye la comparativa, la asignación óptima de Markowitz y notas legales.

## 🛠️ Stack Tecnológico

El proyecto está construido íntegramente en Python utilizando las siguientes librerías:

* **[Streamlit](https://streamlit.io/):** Creación de la interfaz gráfica y despliegue web interactivo.
* **[yfinance](https://pypi.org/project/yfinance/):** Conexión con la API de Yahoo Finance para la descarga de cotizaciones, ratios financieros y metadatos bursátiles.
* **[Pandas](https://pandas.pydata.org/) & [NumPy](https://numpy.org/):** Estructuración, limpieza y cálculos matriciales sobre los dataframes financieros.
* **[SciPy](https://scipy.org/):** Resolución algorítmica para la minimización numérica de funciones (optimización de Markowitz).
* **[FPDF2](https://pyfpdf.github.io/fpdf2/):** Construcción estructurada y exportación del reporte ejecutivo en formato `.pdf`.
* **[Certifi](https://pypi.org/project/certifi/):** Gestión de certificados SSL para garantizar conexiones seguras en las peticiones a la API.

## 💻 Instalación y Ejecución Local

Sigue estos pasos para levantar la aplicación en tu entorno de desarrollo:

**1. Clonar o descargar el proyecto**
Asegúrate de tener el archivo `app.py` guardado en tu directorio de trabajo.

**2. Instalar dependencias**
Abre tu terminal y ejecuta el siguiente comando para instalar todas las librerías necesarias:
```bash
pip install streamlit yfinance pandas numpy scipy fpdf2 certifi