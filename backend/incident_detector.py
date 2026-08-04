from sqlalchemy.orm import Session
from sqlalchemy import func
import db_models


def procesar_transicion_estado(db: Session, servicio_id: int, estado_nuevo: str):
    """
    Se llama con cada chequeo nuevo que llega. Compara contra el
    incidente abierto (si existe) para decidir si hay que abrir uno
    nuevo, actualizar su severidad, o cerrarlo.
    """
    incidente_abierto = (
        db.query(db_models.Incidente)
        .filter(db_models.Incidente.servicio_id == servicio_id, db_models.Incidente.fin.is_(None))
        .first()
    )

    if estado_nuevo == "up":
        if incidente_abierto:
            incidente_abierto.fin = func.now()
        return

    # estado_nuevo es "degraded" o "down"
    if not incidente_abierto:
        db.add(db_models.Incidente(servicio_id=servicio_id, estado=estado_nuevo))
    elif estado_nuevo == "down" and incidente_abierto.estado == "degraded":
        # Empeoro durante el mismo incidente -- refleja la peor severidad vista
        incidente_abierto.estado = "down"
