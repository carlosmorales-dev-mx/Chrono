"""índice compuesto de chequeos y un solo incidente abierto por servicio

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-05

Son las mismas sentencias que ya aplicaba migrar.py antes de Alembic, así que en una base que pasó por ahí
esta migración no cambia nada (todo es IF NOT EXISTS).
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

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


def upgrade() -> None:
    for sentencia in SENTENCIAS:
        op.execute(sentencia)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chequeos_servicio_creado")
    op.execute("DROP INDEX IF EXISTS uq_incidentes_abierto_por_servicio")
