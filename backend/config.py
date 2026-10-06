"""Configuración del backend, leída de variables de entorno (y de backend/.env).

Todo tiene un valor por defecto razonable salvo DATABASE_URL. Ver backend/.env.example.
"""
import logging
import os

from dotenv import load_dotenv

load_dotenv()


def _texto(nombre: str, defecto: str = "") -> str:
    return os.getenv(nombre, defecto).strip()


def _booleano(nombre: str, defecto: bool = False) -> bool:
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return defecto
    return valor.strip().lower() in {"1", "true", "yes", "y", "si", "sí", "on"}


def _entero(nombre: str, defecto: int, minimo: int = 0) -> int:
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return defecto
    try:
        return max(minimo, int(valor.strip()))
    except ValueError:
        logging.getLogger("chrono").warning("%s=%r no es un número válido; se usa %s", nombre, valor, defecto)
        return defecto


def normalizar_url_bd(url):
    """Pide el driver de PostgreSQL de forma EXPLÍCITA: «postgresql://» pasa a «postgresql+psycopg2://».

    SQLAlchemy 2.1 cambió el driver por defecto de «postgresql://» de psycopg2 a psycopg 3. Este proyecto instala
    psycopg2-binary, así que sin esto un entorno nuevo (contenedores, CI, una instalación limpia) falla con
    «No module named 'psycopg'» mientras que uno viejo sigue funcionando. Pidiéndolo explícito se comporta igual
    en SQLAlchemy 2.0 y 2.1. Si la URL ya trae un driver («postgresql+psycopg://…»), se respeta tal cual.
    """
    if not url:
        return url
    for prefijo in ("postgresql://", "postgres://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg2://" + url[len(prefijo):]
    return url


# --- base de datos ---
DATABASE_URL = normalizar_url_bd(_texto("DATABASE_URL")) or None

# --- seguridad ---
# Token compartido con el worker (cabecera X-Ingest-Token). Si está vacío, el ingest queda abierto (solo para desarrollo).
INGEST_TOKEN = _texto("INGEST_TOKEN") or None
# Modo de solo lectura: bloquea crear, editar, anclar y borrar servicios (útil para una demo pública).
SOLO_LECTURA = _booleano("CHRONO_SOLO_LECTURA", False)
# Orígenes extra permitidos por CORS, separados por comas. localhost/127.0.0.1 siempre se permiten.
CORS_ORIGINS = [o.strip() for o in _texto("CORS_ORIGINS").split(",") if o.strip()]
# Si es false (por defecto) no se aceptan servicios que apunten a direcciones internas (localhost, 192.168.x.x…).
PERMITIR_OBJETIVOS_PRIVADOS = _booleano("PERMITIR_OBJETIVOS_PRIVADOS", False)

# --- incidentes: cuántos chequeos seguidos hacen falta para abrir/cerrar uno (evita rachas por un solo mal chequeo) ---
INCIDENTE_ABRIR_TRAS = _entero("INCIDENTE_ABRIR_TRAS", 2, minimo=1)
INCIDENTE_CERRAR_TRAS = _entero("INCIDENTE_CERRAR_TRAS", 3, minimo=1)

# --- datos ---
# Días que se conservan los chequeos crudos (0 = no borrar nunca). Los incidentes se conservan siempre.
RETENCION_DIAS = _entero("RETENCION_DIAS", 30, minimo=0)

LOG_LEVEL = _texto("LOG_LEVEL", "INFO").upper()
