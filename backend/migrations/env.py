"""Entorno de Alembic: conecta las migraciones con la base de datos y los modelos de Chrono."""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# backend/ en el path, para poder importar config, database y db_models aunque se invoque desde otro sitio.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config as chrono_config  # noqa: E402
import db_models  # noqa: E402,F401  (registra los modelos en Base.metadata)
from database import Base  # noqa: E402

alembic_cfg = context.config

# Al correr desde la app (migrar.aplicar) no se toca la configuración de logging de la aplicación.
if alembic_cfg.config_file_name is not None and alembic_cfg.attributes.get("usar_logging_ini", True):
    fileConfig(alembic_cfg.config_file_name, disable_existing_loggers=False)

# La URL sale de DATABASE_URL (variable de entorno o backend/.env). El % se duplica porque ConfigParser interpola.
alembic_cfg.set_main_option("sqlalchemy.url", chrono_config.DATABASE_URL.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse (alembic upgrade head --sql)."""
    context.configure(
        url=alembic_cfg.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        alembic_cfg.get_section(alembic_cfg.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
