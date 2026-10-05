"""Aplica las migraciones de la base de datos. Seguro de correr tantas veces como quieras.

Usa Alembic (backend/migrations/). Si Alembic no está instalado cae al modo simple de antes
(create_all + los mismos índices), para que un entorno sin actualizar siga funcionando.
"""
import logging
from pathlib import Path

from sqlalchemy import text

import db_models  # noqa: F401  (registra los modelos en Base.metadata)
from database import Base, engine

log = logging.getLogger("chrono")
RAIZ = Path(__file__).resolve().parent

# Modo simple (sin Alembic). Debe coincidir con migrations/versions/0002 (una prueba lo vigila).
SENTENCIAS = [
    # Si por una carrera antigua quedó más de un incidente abierto por servicio, se cierran los sobrantes
    # (se conserva el más antiguo) para poder crear el índice único de abajo.
    """
    UPDATE incidentes SET fin = now()
    WHERE fin IS NULL
      AND id NOT IN (SELECT MIN(id) FROM incidentes WHERE fin IS NULL GROUP BY servicio_id)
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_incidentes_abierto_por_servicio ON incidentes (servicio_id) WHERE fin IS NULL",
    "CREATE INDEX IF NOT EXISTS ix_chequeos_servicio_creado ON chequeos (servicio_id, creado_en)",
]


def _aplicar_sin_alembic():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conexion:
        for sentencia in SENTENCIAS:
            conexion.execute(text(sentencia))
    log.info("migraciones aplicadas (modo simple, sin Alembic)")


def aplicar():
    try:
        from alembic import command
        from alembic.config import Config
    except ImportError:
        log.warning("Alembic no está instalado: se usa el modo simple. Instálalo con «make install-backend».")
        return _aplicar_sin_alembic()

    configuracion = Config(str(RAIZ / "alembic.ini"))
    configuracion.set_main_option("script_location", str(RAIZ / "migrations"))
    configuracion.attributes["usar_logging_ini"] = False  # no pisar el logging de la aplicación
    command.upgrade(configuracion, "head")
    log.info("migraciones aplicadas (Alembic)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    aplicar()
    print("Migraciones aplicadas")
