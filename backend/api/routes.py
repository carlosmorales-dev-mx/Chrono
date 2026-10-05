import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

import config
import db_models
import dominio
from database import get_db
from incident_detector import procesar_transicion_estado
from models_schemas import LoteChequeos, ServicioCreate
from websocket_manager import manager

router = APIRouter()


def exigir_escritura():
    """Bloquea las rutas que modifican servicios cuando el servidor está en modo de solo lectura (demo pública)."""
    if config.SOLO_LECTURA:
        raise HTTPException(status_code=403, detail="El servidor está en modo de solo lectura")


escritura = [Depends(exigir_escritura)]


def _servicio_o_404(db: Session, servicio_id: int):
    servicio = db.query(db_models.Servicio).filter(db_models.Servicio.id == servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return servicio


def _serializar(servicio) -> dict:
    return {"id": servicio.id, "nombre": servicio.nombre, "url": servicio.url, "anclado": servicio.anclado}


def _url_ya_monitoreada(db: Session, url: str, excepto_id: Optional[int] = None) -> bool:
    consulta = db.query(db_models.Servicio.id).filter(func.lower(db_models.Servicio.url) == url.lower())
    if excepto_id is not None:
        consulta = consulta.filter(db_models.Servicio.id != excepto_id)
    return consulta.first() is not None


# ---------- Gestión de servicios ----------

@router.get("/servicios")
def listar_servicios(db: Session = Depends(get_db)):
    servicios = db.query(db_models.Servicio).order_by(db_models.Servicio.id).all()
    return [_serializar(s) for s in servicios]


@router.post("/servicios", status_code=201, dependencies=escritura)
def crear_servicio(datos: ServicioCreate, db: Session = Depends(get_db)):
    if _url_ya_monitoreada(db, datos.url):
        raise HTTPException(status_code=409, detail="Ya existe un servicio con esa URL")
    nuevo = db_models.Servicio(nombre=datos.nombre, url=datos.url)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return _serializar(nuevo)


@router.put("/servicios/{servicio_id}", dependencies=escritura)
def actualizar_servicio(servicio_id: int, datos: ServicioCreate, db: Session = Depends(get_db)):
    """Renombrar o cambiar la URL de un servicio que ya se está monitoreando."""
    servicio = _servicio_o_404(db, servicio_id)
    if _url_ya_monitoreada(db, datos.url, excepto_id=servicio_id):
        raise HTTPException(status_code=409, detail="Ya existe un servicio con esa URL")
    servicio.nombre = datos.nombre
    servicio.url = datos.url
    db.commit()
    db.refresh(servicio)
    return _serializar(servicio)


@router.patch("/servicios/{servicio_id}/anclar", dependencies=escritura)
def alternar_anclado(servicio_id: int, db: Session = Depends(get_db)):
    """Fija o desfija un servicio -- los anclados se muestran siempre primero en el frontend."""
    servicio = _servicio_o_404(db, servicio_id)
    servicio.anclado = not servicio.anclado
    db.commit()
    db.refresh(servicio)
    return {"id": servicio.id, "anclado": servicio.anclado}


@router.delete("/servicios/{servicio_id}", status_code=204, dependencies=escritura)
def eliminar_servicio(servicio_id: int, db: Session = Depends(get_db)):
    servicio = _servicio_o_404(db, servicio_id)
    db.delete(servicio)
    db.commit()


# ---------- Ingesta (usada por el worker) ----------

def _verificar_token(recibido: Optional[str]):
    esperado = config.INGEST_TOKEN
    if not esperado:
        return  # sin token configurado el ingest queda abierto (solo desarrollo local)
    if not recibido or not hmac.compare_digest(recibido.encode(), esperado.encode()):
        raise HTTPException(status_code=401, detail="Token de ingesta inválido")


def _guardar_lote(db: Session, lote: LoteChequeos):
    """Guarda los chequeos y actualiza los incidentes. Es código de base de datos BLOQUEANTE, por eso se
    ejecuta fuera del bucle de eventos (ver ingerir_chequeos). Devuelve (mensajes_para_el_websocket, ignorados)."""
    nombres = {fila[0]: fila[1] for fila in db.query(db_models.Servicio.id, db_models.Servicio.nombre).all()}
    mensajes = []
    ignorados = 0
    for r in lote.resultados:
        if r.servicio_id not in nombres:
            # El servicio se borró mientras el worker medía: se descarta ese resultado, no todo el lote.
            ignorados += 1
            continue
        procesar_transicion_estado(db, r.servicio_id, r.estado)  # antes de guardar el actual
        db.add(db_models.Chequeo(
            servicio_id=r.servicio_id, estado=r.estado,
            codigo_http=r.codigo, latencia_ms=r.latencia_ms,
        ))
        db.flush()  # que el siguiente resultado del mismo servicio (si lo hay) vea este chequeo
        mensajes.append({
            "tipo": "chequeo", "servicio_id": r.servicio_id, "nombre": nombres[r.servicio_id],
            "estado": r.estado, "codigo_http": r.codigo, "latencia_ms": r.latencia_ms,
        })
    db.commit()
    return mensajes, ignorados


@router.post("/internal/ingest", status_code=201)
async def ingerir_chequeos(
    lote: LoteChequeos,
    db: Session = Depends(get_db),
    x_ingest_token: Optional[str] = Header(default=None),
):
    _verificar_token(x_ingest_token)
    mensajes, ignorados = await run_in_threadpool(_guardar_lote, db, lote)
    for mensaje in mensajes:
        await manager.transmitir(mensaje)
    return {"guardados": len(mensajes), "ignorados": ignorados}


# ---------- Consultas de estado ----------

@router.get("/chequeos/recientes")
def listar_recientes(db: Session = Depends(get_db)):
    filas = (
        db.query(db_models.Chequeo, db_models.Servicio.nombre)
        .join(db_models.Servicio)
        .order_by(db_models.Chequeo.creado_en.desc())
        .limit(50)
        .all()
    )
    return [
        {"servicio": nombre, "estado": c.estado, "codigo_http": c.codigo_http,
         "latencia_ms": c.latencia_ms, "creado_en": c.creado_en.isoformat()}
        for c, nombre in filas
    ]


@router.get("/chequeos/estado-actual")
def estado_actual(db: Session = Depends(get_db)):
    resultado = db.execute(text("""
        SELECT s.id, s.nombre, s.url, s.anclado, c.estado, c.codigo_http, c.latencia_ms, c.creado_en
        FROM servicios s
        LEFT JOIN LATERAL (
            SELECT estado, codigo_http, latencia_ms, creado_en
            FROM chequeos WHERE chequeos.servicio_id = s.id
            ORDER BY creado_en DESC LIMIT 1
        ) c ON true
        ORDER BY s.id
    """)).mappings().all()

    return [
        {"id": r["id"], "nombre": r["nombre"], "url": r["url"], "anclado": r["anclado"], "estado": r["estado"],
         "codigo_http": r["codigo_http"], "latencia_ms": r["latencia_ms"],
         "creado_en": r["creado_en"].isoformat() if r["creado_en"] else None}
        for r in resultado
    ]


@router.get("/chequeos/{servicio_id}/historial")
def historial_servicio(
    servicio_id: int,
    horas: int = Query(24, ge=1, le=168),
    puntos: int = Query(96, ge=10, le=288),
    db: Session = Depends(get_db),
):
    """
    Historial en tramos de TIEMPO iguales (ver dominio.agrupar_historial). Cada punto trae el peor estado
    del tramo y la latencia media de los chequeos que respondieron (null si todos fallaron), así las caídas
    SIEMPRE se ven. El ancho del tramo se adapta a los datos: un servicio recién agregado muestra enseguida
    sus puntos reales, sin esperar a que pase una hora.
    """
    ahora = datetime.now(timezone.utc)
    desde = ahora - timedelta(hours=horas)
    filas = (
        db.query(db_models.Chequeo.creado_en, db_models.Chequeo.estado, db_models.Chequeo.latencia_ms)
        .filter(db_models.Chequeo.servicio_id == servicio_id, db_models.Chequeo.creado_en > desde)
        .order_by(db_models.Chequeo.creado_en.asc())
        .all()
    )
    return dominio.agrupar_historial([(f[0], f[1], f[2]) for f in filas], ahora, horas=horas, puntos_max=puntos)


@router.get("/chequeos/{servicio_id}/percentiles")
def percentiles_servicio(servicio_id: int, db: Session = Depends(get_db)):
    desde = datetime.now(timezone.utc) - timedelta(hours=24)
    filas = (
        db.query(db_models.Chequeo.latencia_ms)
        .filter(
            db_models.Chequeo.servicio_id == servicio_id,
            db_models.Chequeo.creado_en > desde,
            db_models.Chequeo.latencia_ms.is_not(None),
        )
        .all()
    )
    valores = [f[0] for f in filas]
    return {
        "p50": dominio.percentil(valores, 0.5),
        "p95": dominio.percentil(valores, 0.95),
        "p99": dominio.percentil(valores, 0.99),
    }


@router.get("/badge/{servicio_id}.svg")
def badge_servicio(servicio_id: int, db: Session = Depends(get_db)):
    fila = db.execute(text("""
        SELECT s.nombre, c.estado FROM servicios s
        LEFT JOIN LATERAL (
            SELECT estado FROM chequeos WHERE chequeos.servicio_id = s.id
            ORDER BY creado_en DESC LIMIT 1
        ) c ON true WHERE s.id = :sid
    """), {"sid": servicio_id}).mappings().first()

    if not fila:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    return Response(
        content=dominio.construir_badge(fila["nombre"], fila["estado"]),
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=30",
            "X-Content-Type-Options": "nosniff",
            # Defensa en profundidad: aunque algo se colara, el navegador no ejecuta scripts en este SVG.
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
        },
    )


# ---------- Línea de tiempo de incidentes ----------

@router.get("/incidentes")
def listar_incidentes(
    response: Response,
    dias: int = Query(30, ge=1, le=365),
    limite: int = Query(500, ge=1, le=2000),
    servicio_id: Optional[int] = None,
    estado: Optional[str] = None,
    activos: bool = False,
    db: Session = Depends(get_db),
):
    """
    Incidentes de los últimos `dias` días (y SIEMPRE los que siguen abiertos), del más reciente al más antiguo.
    Filtros opcionales: servicio_id, estado (degraded|down) y activos. La cabecera X-Total-Count dice cuántos
    coinciden en total, por si `limite` los recortó.
    """
    if estado not in (None, "degraded", "down"):
        raise HTTPException(status_code=422, detail="estado debe ser 'degraded' o 'down'")

    ahora = datetime.now(timezone.utc)
    desde = ahora - timedelta(days=dias)
    consulta = (
        db.query(db_models.Incidente, db_models.Servicio.nombre)
        .join(db_models.Servicio, db_models.Servicio.id == db_models.Incidente.servicio_id)
        .filter(or_(db_models.Incidente.fin.is_(None), db_models.Incidente.inicio >= desde))
    )
    if servicio_id is not None:
        consulta = consulta.filter(db_models.Incidente.servicio_id == servicio_id)
    if estado is not None:
        consulta = consulta.filter(db_models.Incidente.estado == estado)
    if activos:
        consulta = consulta.filter(db_models.Incidente.fin.is_(None))

    response.headers["X-Total-Count"] = str(consulta.count())
    filas = consulta.order_by(db_models.Incidente.inicio.desc()).limit(limite).all()

    return [
        {
            "id": i.id,
            "servicio_id": i.servicio_id,
            "servicio": nombre,
            "estado": i.estado,
            "inicio": i.inicio.isoformat(),
            "fin": i.fin.isoformat() if i.fin else None,
            "activo": i.fin is None,
            "duracion_seg": max(0, int(((i.fin or ahora) - i.inicio).total_seconds())),
        }
        for i, nombre in filas
    ]
