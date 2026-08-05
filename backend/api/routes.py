from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

import db_models
from database import get_db
from models_schemas import LoteChequeos, ServicioCreate
from websocket_manager import manager
from incident_detector import procesar_transicion_estado

router = APIRouter()


# ---------- Gestión de servicios ----------

@router.get("/servicios")
def listar_servicios(db: Session = Depends(get_db)):
    servicios = db.query(db_models.Servicio).order_by(db_models.Servicio.id).all()
    return [{"id": s.id, "nombre": s.nombre, "url": s.url} for s in servicios]


@router.post("/servicios", status_code=201)
def crear_servicio(datos: ServicioCreate, db: Session = Depends(get_db)):
    nuevo = db_models.Servicio(nombre=datos.nombre.strip(), url=datos.url.strip())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return {"id": nuevo.id, "nombre": nuevo.nombre, "url": nuevo.url}


@router.put("/servicios/{servicio_id}")
def actualizar_servicio(servicio_id: int, datos: ServicioCreate, db: Session = Depends(get_db)):
    """
    Renombrar o cambiar la URL de un servicio ya existente -- antes solo
    se podia crear/eliminar, nunca editar uno que ya estaba monitoreando.
    """
    servicio = db.query(db_models.Servicio).filter(db_models.Servicio.id == servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    servicio.nombre = datos.nombre.strip()
    servicio.url = datos.url.strip()
    db.commit()
    db.refresh(servicio)
    return {"id": servicio.id, "nombre": servicio.nombre, "url": servicio.url}


@router.put("/servicios/{servicio_id}")
def actualizar_servicio(servicio_id: int, datos: ServicioCreate, db: Session = Depends(get_db)):
    """
    Renombrar o cambiar la URL de un servicio ya existente -- antes solo
    se podia crear/eliminar, nunca editar uno que ya estaba monitoreando.
    """
    servicio = db.query(db_models.Servicio).filter(db_models.Servicio.id == servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    servicio.nombre = datos.nombre.strip()
    servicio.url = datos.url.strip()
    db.commit()
    db.refresh(servicio)
    return {"id": servicio.id, "nombre": servicio.nombre, "url": servicio.url}


@router.patch("/servicios/{servicio_id}/anclar")
def alternar_anclado(servicio_id: int, db: Session = Depends(get_db)):
    """Fija o desfija un servicio -- los anclados se muestran siempre
    primero en el frontend, sin importar su estado actual."""
    servicio = db.query(db_models.Servicio).filter(db_models.Servicio.id == servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    servicio.anclado = not servicio.anclado
    db.commit()
    db.refresh(servicio)
    return {"id": servicio.id, "anclado": servicio.anclado}


@router.delete("/servicios/{servicio_id}", status_code=204)
def eliminar_servicio(servicio_id: int, db: Session = Depends(get_db)):
    servicio = db.query(db_models.Servicio).filter(db_models.Servicio.id == servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    db.delete(servicio)
    db.commit()


# ---------- Ingesta (usada por el worker) ----------

@router.post("/internal/ingest", status_code=201)
async def ingerir_chequeos(lote: LoteChequeos, db: Session = Depends(get_db)):
    nombres_por_id = {s.id: s.nombre for s in db.query(db_models.Servicio).all()}

    guardados = []
    for r in lote.resultados:
        db.add(db_models.Chequeo(
            servicio_id=r.servicio_id, estado=r.estado,
            codigo_http=r.codigo, latencia_ms=r.latencia_ms,
        ))
        procesar_transicion_estado(db, r.servicio_id, r.estado)
        guardados.append(r)
    db.commit()

    for r in guardados:
        await manager.transmitir({
            "tipo": "chequeo", "servicio_id": r.servicio_id,
            "nombre": nombres_por_id.get(r.servicio_id, "desconocido"),
            "estado": r.estado, "codigo_http": r.codigo, "latencia_ms": r.latencia_ms,
        })

    return {"guardados": len(lote.resultados)}


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
def historial_servicio(servicio_id: int, db: Session = Depends(get_db)):
    """
    Downsampling ADAPTATIVO, no una agregacion fija por hora.

    Problema que tenia la version anterior: agrupar por hora de reloj
    significa que un servicio recien agregado (o la base de datos
    recien recreada) no tiene ni un solo punto para dibujar hasta que
    pase una hora natural -- la grafica se queda vacia por diseño
    durante minutos u horas, algo inaceptable en una demo en vivo.

    La solucion correcta: traer los chequeos crudos de las ultimas
    24h, y SOLO si hay demasiados (mas de TARGET_PUNTOS) agruparlos en
    bloques de tamaño IGUAL EN CANTIDAD DE FILAS (no en tiempo fijo).
    Con pocos datos, se ven todos los puntos reales de inmediato. Con
    miles acumulados con el tiempo, se resumen a un numero legible sin
    perder la forma general de la curva.
    """
    TARGET_PUNTOS = 30

    filas = db.execute(text("""
        SELECT latencia_ms, estado, creado_en
        FROM chequeos
        WHERE servicio_id = :sid
          AND creado_en > now() - interval '24 hours'
          AND latencia_ms IS NOT NULL
        ORDER BY creado_en ASC
    """), {"sid": servicio_id}).mappings().all()

    if not filas:
        return []

    if len(filas) <= TARGET_PUNTOS:
        return [
            {"latencia_ms": f["latencia_ms"], "estado": f["estado"], "creado_en": f["creado_en"].isoformat()}
            for f in filas
        ]

    tamano_bloque = -(-len(filas) // TARGET_PUNTOS)  # division hacia arriba
    resultado = []
    for i in range(0, len(filas), tamano_bloque):
        bloque = filas[i:i + tamano_bloque]
        promedio = round(sum(f["latencia_ms"] for f in bloque) / len(bloque))
        estados = [f["estado"] for f in bloque]
        estado_predominante = max(set(estados), key=estados.count)
        resultado.append({
            "latencia_ms": promedio,
            "estado": estado_predominante,
            "creado_en": bloque[-1]["creado_en"].isoformat(),
        })
    return resultado


@router.get("/chequeos/{servicio_id}/percentiles")
def percentiles_servicio(servicio_id: int, db: Session = Depends(get_db)):
    fila = db.execute(text("""
        SELECT
            percentile_cont(0.5) WITHIN GROUP (ORDER BY latencia_ms) AS p50,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY latencia_ms) AS p95,
            percentile_cont(0.99) WITHIN GROUP (ORDER BY latencia_ms) AS p99
        FROM chequeos
        WHERE servicio_id = :sid AND creado_en > now() - interval '24 hours' AND latencia_ms IS NOT NULL
    """), {"sid": servicio_id}).mappings().first()

    return {
        "p50": round(fila["p50"]) if fila["p50"] is not None else None,
        "p95": round(fila["p95"]) if fila["p95"] is not None else None,
        "p99": round(fila["p99"]) if fila["p99"] is not None else None,
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

    colores = {"up": "#1A6E5C", "degraded": "#6B4A18", "down": "#6B1E2E", None: "#4A3468"}
    textos = {"up": "operativo", "degraded": "degradado", "down": "caido", None: "sin datos"}
    color = colores.get(fila["estado"])
    texto_estado = textos.get(fila["estado"])
    nombre = fila["nombre"]

    ancho_nombre = 12 * len(nombre) + 20
    ancho_estado = 12 * len(texto_estado) + 20
    ancho_total = ancho_nombre + ancho_estado

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{ancho_total}" height="24">
  <rect width="{ancho_nombre}" height="24" fill="#0D0714" rx="4"/>
  <rect x="{ancho_nombre}" width="{ancho_estado}" height="24" fill="{color}" rx="4"/>
  <rect x="{ancho_nombre-4}" width="4" height="24" fill="{color}"/>
  <text x="{ancho_nombre/2}" y="16" font-family="Verdana,sans-serif" font-size="11" fill="#F5EAD3" text-anchor="middle">{nombre}</text>
  <text x="{ancho_nombre + ancho_estado/2}" y="16" font-family="Verdana,sans-serif" font-size="11" fill="#F5EAD3" text-anchor="middle">{texto_estado}</text>
</svg>'''
    from fastapi.responses import Response
    return Response(content=svg, media_type="image/svg+xml")


# ---------- Fase 5.5: Línea de tiempo de incidentes ----------

@router.get("/incidentes")
def listar_incidentes(db: Session = Depends(get_db)):
    """Los ultimos 20 incidentes de TODOS los servicios, mas reciente
    primero -- para la seccion de historial global del dashboard."""
    filas = db.execute(text("""
        SELECT i.id, s.nombre AS servicio, i.estado, i.inicio, i.fin,
               EXTRACT(EPOCH FROM (COALESCE(i.fin, now()) - i.inicio))::int AS duracion_seg
        FROM incidentes i
        JOIN servicios s ON s.id = i.servicio_id
        ORDER BY i.inicio DESC
        LIMIT 20
    """)).mappings().all()

    return [
        {
            "id": f["id"],
            "servicio": f["servicio"],
            "estado": f["estado"],
            "inicio": f["inicio"].isoformat(),
            "fin": f["fin"].isoformat() if f["fin"] else None,
            "activo": f["fin"] is None,
            "duracion_seg": f["duracion_seg"],
        }
        for f in filas
    ]
