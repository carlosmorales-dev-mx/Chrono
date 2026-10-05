"""Ajustes de esquema idempotentes (seguros de correr tantas veces como quieras).

Hasta que el proyecto adopte Alembic, las bases que ya existían se actualizan aquí:
create_all crea las tablas que falten y las sentencias de abajo agregan lo demás.
"""
import logging

from sqlalchemy import text

import db_models  # noqa: F401  (registra los modelos en Base.metadata)
from database import Base, engine

log = logging.getLogger("chrono")

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


def aplicar():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conexion:
        for sentencia in SENTENCIAS:
            conexion.execute(text(sentencia))
    log.info("migraciones aplicadas")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    aplicar()
    print("Migraciones aplicadas")
