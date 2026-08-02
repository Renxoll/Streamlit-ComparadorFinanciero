# Imagen para ejecutar el Sistema de Recomendacion y Optimizacion de Inversion (Streamlit).
#
# Base: python:3.11-slim-bookworm. Se elige 3.11 porque es la version que ya
# usa el proyecto en .devcontainer/devcontainer.json (mcr.microsoft.com/devcontainers/python:1-3.11-bookworm).
# "slim" (Debian, no Alpine) porque numpy/pandas/scipy publican wheels
# manylinux precompilados para glibc: en Debian se instalan directamente via
# pip, sin compilar nada y sin necesitar build-essential/gfortran/openblas.
# Alpine (musl libc) normalmente NO tiene esos wheels y obligaria a compilar
# estas librerias desde el codigo fuente, con una imagen final mas lenta de
# construir y, pese al nombre, no necesariamente mas pequena.
FROM python:3.11-slim-bookworm

WORKDIR /app

# PYTHONDONTWRITEBYTECODE: no generar .pyc (no aportan nada en un contenedor de un solo uso).
# PYTHONUNBUFFERED: logs de core/logger.py (StreamHandler a stdout) visibles al instante con `docker logs`.
# PIP_NO_CACHE_DIR: no dejar la cache de pip dentro de la imagen (reduce tamano final).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Copiar solo requirements.txt primero: aprovecha la cache de capas de Docker
# para no reinstalar dependencias en cada rebuild si solo cambia el codigo.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# El resto del codigo de la app (filtrado por .dockerignore: no incluye
# tests/, docs/, .git/, entornos virtuales, cachés ni configuracion de IDE).
COPY . .

EXPOSE 8501

# Streamlit expone un endpoint de salud propio; se usa python (ya presente en
# la imagen) en vez de instalar curl solo para esto.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# --server.address=0.0.0.0: imprescindible en Docker (por defecto Streamlit
#   escucha solo en localhost DENTRO del contenedor, inalcanzable desde fuera).
# --server.headless=true: no intentar abrir un navegador dentro del contenedor.
# --server.enableCORS=false / --server.enableXsrfProtection=false: mismos
#   flags que ya usa .devcontainer/devcontainer.json (postAttachCommand) para
#   este proyecto, mantenidos aqui por coherencia con el entorno de desarrollo existente.
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false"]
