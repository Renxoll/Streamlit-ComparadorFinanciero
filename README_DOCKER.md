# Ejecutar la aplicación con Docker

Esta guía permite ejecutar el Sistema de Recomendación y Optimización de Inversión sin instalar Python, crear entornos virtuales ni instalar dependencias manualmente.

## Requisitos

- **Docker Desktop** (Windows, macOS o Linux). Nada más — ni Python, ni pip, ni las librerías del `requirements.txt` se instalan en tu máquina: todo vive dentro del contenedor.

## Construir la imagen

```bash
docker compose build
```

Descarga la imagen base (`python:3.11-slim-bookworm`) e instala las dependencias del `requirements.txt` (`streamlit`, `yfinance`, `pandas`, `numpy`, `scipy`, `fpdf2`, `certifi`). Solo hace falta repetir este paso si cambias `requirements.txt` o el propio `Dockerfile`.

## Ejecutar la aplicación

```bash
docker compose up
```

Si aún no habías construido la imagen, `docker compose up` la construye automáticamente antes de arrancar.

Para ejecutarla en segundo plano (sin bloquear la terminal):

```bash
docker compose up -d
```

## Acceder a la aplicación

Abre en el navegador:

```
http://localhost:8501
```

## Detener la aplicación

```bash
docker compose down
```

## Reconstruir después de cambios en el código

```bash
docker compose up --build
```

Fuerza una reconstrucción de la imagen (recoge cambios en `app.py`, `core/`, `portfolio/`, `ui/`, `reports/`, `config.py`, etc.) y vuelve a levantar el contenedor.

## Variables de entorno (opcional)

La aplicación **no necesita ninguna variable de entorno** para funcionar: no usa claves de API ni configuración sensible (`yfinance` no requiere autenticación). Si en el futuro hiciera falta alguna (por ejemplo, `TZ` para la zona horaria de los logs), copia `.env.example` a `.env`:

```bash
cp .env.example .env
```

`docker-compose.yml` carga ese archivo automáticamente si existe; si no existe, la aplicación arranca igual con sus valores por defecto.

## Notas

- El contenedor se reinicia automáticamente si se cae (`restart: unless-stopped`), salvo que lo pares tú explícitamente con `docker compose down`.
- Los datos de mercado se descargan de Yahoo Finance en cada ejecución (no hay ninguna base de datos ni volumen persistente que mantener); el contenedor no guarda ningún estado entre reinicios.
- El "Perfil calculado", el cuestionario y el resto de datos introducidos viven en la sesión del navegador (`st.session_state` de Streamlit), no en el contenedor — cerrar el contenedor no es lo mismo que reiniciar tu sesión en la app (usa el botón "🔄 Nueva simulación" dentro de la propia aplicación para eso).
