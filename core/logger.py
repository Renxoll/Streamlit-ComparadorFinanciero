"""Configuracion centralizada de logging para toda la aplicacion.

Sustituye la dependencia exclusiva de `st.error` para reportar fallos: los
eventos relevantes (timeouts, simbolos invalidos, cache hits/miss, errores de
Yahoo Finance) quedan registrados aqui independientemente de si Streamlit
llega a mostrar o no un mensaje al usuario.
"""
from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_ROOT_LOGGER_NAME = "comparador_financiero"
_configured = False


def _configure_root_logger() -> None:
    """Configura el logger raiz de la aplicacion una unica vez por proceso."""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    root_logger = logging.getLogger(_ROOT_LOGGER_NAME)
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    root_logger.propagate = False

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger hijo del logger raiz de la aplicacion, ya configurado.

    Args:
        name: normalmente `__name__` del modulo que solicita el logger.
    """
    _configure_root_logger()
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")
