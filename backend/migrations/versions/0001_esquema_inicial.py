"""esquema inicial: servicios, chequeos e incidentes

Revision ID: 0001
Revises:
Create Date: 2026-10-05

Esta migración describe el esquema tal como existía antes de adoptar Alembic. Es IDEMPOTENTE a propósito:
  · en una base VACÍA (CI, contenedores, una instalación nueva) crea las tablas y los índices;
  · en una base que YA tenía el esquema (creada con create_all) no toca las tablas y solo se asegura de que
    existan los índices. Por eso no hace falta «alembic stamp»: `upgrade head` sirve en los dos casos.
El DDL está escrito a mano (no se genera desde los modelos) para que esta migración no cambie cuando los
modelos evolucionen: los cambios futuros van en migraciones nuevas.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

INDICES = [
    "CREATE INDEX IF NOT EXISTS ix_servicios_id ON servicios (id)",
    "CREATE INDEX IF NOT EXISTS ix_chequeos_id ON chequeos (id)",
    "CREATE INDEX IF NOT EXISTS ix_chequeos_servicio_id ON chequeos (servicio_id)",
    "CREATE INDEX IF NOT EXISTS ix_chequeos_creado_en ON chequeos (creado_en)",
    "CREATE INDEX IF NOT EXISTS ix_incidentes_id ON incidentes (id)",
    "CREATE INDEX IF NOT EXISTS ix_incidentes_servicio_id ON incidentes (servicio_id)",
]


def upgrade() -> None:
    existentes = sa.inspect(op.get_bind())

    if not existentes.has_table("servicios"):
        op.create_table(
            "servicios",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("nombre", sa.String(), nullable=False),
            sa.Column("url", sa.String(), nullable=False),
            sa.Column("anclado", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not existentes.has_table("chequeos"):
        op.create_table(
            "chequeos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("servicio_id", sa.Integer(), sa.ForeignKey("servicios.id"), nullable=False),
            sa.Column("estado", sa.String(), nullable=False),
            sa.Column("codigo_http", sa.Integer(), nullable=True),
            sa.Column("latencia_ms", sa.Integer(), nullable=True),
            sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not existentes.has_table("incidentes"):
        op.create_table(
            "incidentes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("servicio_id", sa.Integer(), sa.ForeignKey("servicios.id"), nullable=False),
            sa.Column("estado", sa.String(), nullable=False),
            sa.Column("inicio", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("fin", sa.DateTime(timezone=True), nullable=True),
        )

    for sentencia in INDICES:
        op.execute(sentencia)


def downgrade() -> None:
    # DESTRUCTIVO: borra todos los datos. Solo para desarrollo.
    op.drop_table("incidentes")
    op.drop_table("chequeos")
    op.drop_table("servicios")
