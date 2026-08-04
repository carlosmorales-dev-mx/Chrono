from database import engine, Base
import db_models  # noqa: F401

Base.metadata.create_all(bind=engine)
print("Tabla 'chequeos' creada correctamente")
