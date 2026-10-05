import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

import config
import migrar
import retencion
from api.routes import router
from database import engine
from websocket_manager import manager

logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("chrono")

INTERVALO_RETENCION_S = 6 * 3600


async def _ciclo_retencion():
    """Cada 6 horas borra los chequeos crudos más viejos que RETENCION_DIAS."""
    while True:
        try:
            await run_in_threadpool(retencion.purgar_chequeos_antiguos)
        except Exception:
            log.exception("falló la purga de chequeos antiguos")
        await asyncio.sleep(INTERVALO_RETENCION_S)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await run_in_threadpool(migrar.aplicar)
    except Exception:
        # No tumbar el servidor si la base aún no responde: /health lo reportará y las consultas fallarán claro.
        log.exception("No se pudieron aplicar las migraciones al arrancar (¿la base de datos está encendida?)")
    if not config.INGEST_TOKEN:
        log.warning("INGEST_TOKEN no está definido: cualquiera que alcance /internal/ingest puede inyectar chequeos.")
    if config.SOLO_LECTURA:
        log.info("Modo de solo lectura activado: no se pueden crear, editar ni borrar servicios.")
    tarea = asyncio.create_task(_ciclo_retencion()) if config.RETENCION_DIAS > 0 else None
    yield
    if tarea:
        tarea.cancel()


app = FastAPI(title="Chrono API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Regex en vez de lista exacta: Vite salta de puerto automático cuando 5173 ya está ocupado, y una lista
    # fija de orígenes se rompe en silencio cada vez que eso pasa. Para un despliegue real, CORS_ORIGINS
    # agrega los orígenes de producción (separados por comas).
    allow_origins=config.CORS_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

app.include_router(router)


@app.get("/")
def raiz():
    return {"status": "Chrono API corriendo"}


def _verificar_base():
    with engine.connect() as conexion:
        conexion.execute(text("SELECT 1"))


@app.get("/health")
async def salud():
    """Para monitores y contenedores: 200 si el servidor y la base responden, 503 si no."""
    try:
        await run_in_threadpool(_verificar_base)
    except Exception:
        return JSONResponse(status_code=503, content={"status": "error", "db": "no responde"})
    return {"status": "ok", "db": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.conectar(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.desconectar(websocket)
