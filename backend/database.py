from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

import config

if not config.DATABASE_URL:
    raise RuntimeError(
        "Falta DATABASE_URL. Copia backend/.env.example a backend/.env y ajusta la conexión "
        "(por ejemplo: postgresql://usuario:clave@localhost:5433/base)."
    )

# pool_pre_ping: detecta conexiones que la base ya cerró (reinicio del contenedor) en vez de fallar una vez.
engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
