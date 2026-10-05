"""Borra los chequeos crudos más viejos que RETENCION_DIAS para que la tabla no crezca sin límite.

Los incidentes NO se borran (son el historial valioso). Uso manual:   python retencion.py [días]
"""
import logging
import sys
from datetime import datetime, timedelta, timezone

import config
import db_models
from database import SessionLocal

log = logging.getLogger("chrono")


def purgar_chequeos_antiguos(dias=None) -> int:
    dias = config.RETENCION_DIAS if dias is None else dias
    if dias <= 0:
        return 0
    limite = datetime.now(timezone.utc) - timedelta(days=dias)
    db = SessionLocal()
    try:
        borrados = db.query(db_models.Chequeo).filter(db_models.Chequeo.creado_en < limite).delete(synchronize_session=False)
        db.commit()
        if borrados:
            log.info("retención: %s chequeos de más de %s días eliminados", borrados, dias)
        return borrados
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    argumento = int(sys.argv[1]) if len(sys.argv) > 1 else None
    print(f"{purgar_chequeos_antiguos(argumento)} chequeos eliminados")
