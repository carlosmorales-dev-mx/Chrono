from sqlalchemy import func
from sqlalchemy.orm import Session

import config
import db_models
import dominio


def _previos(db: Session, servicio_id: int, cantidad: int):
    """Los últimos `cantidad` chequeos YA guardados del servicio, el más nuevo primero: [(estado, creado_en)]."""
    if cantidad <= 0:
        return []
    filas = (
        db.query(db_models.Chequeo.estado, db_models.Chequeo.creado_en)
        .filter(db_models.Chequeo.servicio_id == servicio_id)
        .order_by(db_models.Chequeo.creado_en.desc(), db_models.Chequeo.id.desc())
        .limit(cantidad)
        .all()
    )
    return [(f[0], f[1]) for f in filas]


def procesar_transicion_estado(db: Session, servicio_id: int, estado_nuevo: str):
    """
    Se llama con cada chequeo nuevo, ANTES de guardarlo. Compara los chequeos recientes (más el nuevo)
    contra el incidente abierto y decide si abrir, escalar o cerrar. La decisión en sí vive en
    dominio.decidir_incidente (con histéresis: un solo chequeo malo/bueno no abre ni cierra nada).
    """
    abrir_tras = config.INCIDENTE_ABRIR_TRAS
    cerrar_tras = config.INCIDENTE_CERRAR_TRAS
    previos = _previos(db, servicio_id, max(abrir_tras, cerrar_tras) - 1)
    ultimos = [estado_nuevo] + [p[0] for p in previos]

    abierto = (
        db.query(db_models.Incidente)
        .filter(db_models.Incidente.servicio_id == servicio_id, db_models.Incidente.fin.is_(None))
        .first()
    )
    accion = dominio.decidir_incidente(ultimos, abierto.estado if abierto else None, abrir_tras, cerrar_tras)

    if accion.tipo == "abrir" and not abierto:
        nuevo = db_models.Incidente(servicio_id=servicio_id, estado=accion.severidad)
        # El incidente empezó en el PRIMER chequeo malo de la racha, no en el que lo confirmó.
        if abrir_tras >= 2 and len(previos) >= abrir_tras - 1:
            nuevo.inicio = previos[abrir_tras - 2][1]
        db.add(nuevo)
    elif accion.tipo == "cerrar" and abierto:
        abierto.fin = func.now()
    elif accion.tipo == "escalar" and abierto:
        abierto.estado = accion.severidad
