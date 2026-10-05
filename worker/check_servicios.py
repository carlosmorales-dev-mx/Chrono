import asyncio
import logging
import os
import signal
import socket
import time

import httpx
from dotenv import load_dotenv

import logica

load_dotenv()


def _numero(nombre: str, defecto: float) -> float:
    try:
        return float(os.getenv(nombre, "").strip() or defecto)
    except ValueError:
        return defecto


def _booleano(nombre: str, defecto: bool = False) -> bool:
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return defecto
    return valor.strip().lower() in {"1", "true", "yes", "y", "si", "sí", "on"}


BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001").strip().rstrip("/")
INGEST_TOKEN = os.getenv("INGEST_TOKEN", "").strip() or None
INTERVALO_S = max(5.0, _numero("CHECK_INTERVAL", 30))
TIMEOUT_S = max(1.0, _numero("TIMEOUT_S", 5))
# Umbral de latencia: aunque el código HTTP sea exitoso, una respuesta demasiado lenta es un problema real.
UMBRAL_DEGRADADO_MS = int(_numero("UMBRAL_DEGRADADO_MS", 1200))
PERMITIR_OBJETIVOS_PRIVADOS = _booleano("PERMITIR_OBJETIVOS_PRIVADOS", False)
USER_AGENT = "ChronoMonitor/1.0 (+https://github.com/carlosmorales-dev-mx/Chrono)"

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("chrono.worker")


def _resolver(host: str, puerto: int) -> list:
    return [info[4][0] for info in socket.getaddrinfo(host, puerto, type=socket.SOCK_STREAM)]


async def obtener_servicios(cliente: httpx.AsyncClient) -> list:
    """Pide la lista de servicios a monitorear al backend: si agregas uno nuevo desde el frontend,
    el worker lo empieza a chequear en su siguiente vuelta, sin reiniciar nada."""
    try:
        respuesta = await cliente.get(f"{BACKEND_URL}/servicios", timeout=TIMEOUT_S)
        respuesta.raise_for_status()
        return respuesta.json()
    except httpx.RequestError as e:
        log.warning("no se pudo obtener la lista de servicios del backend: %s", e)
    except httpx.HTTPStatusError as e:
        log.warning("el backend respondió %s al pedir la lista de servicios", e.response.status_code)
    return []


async def chequear_servicio(cliente: httpx.AsyncClient, servicio: dict):
    """Devuelve el resultado del chequeo, o None si no se debe chequear (destino no permitido)."""
    url = servicio["url"]
    # Se comprueba justo antes de conectar (la resolución de DNS puede bloquear: va en un hilo aparte).
    permitido = await asyncio.to_thread(logica.objetivo_permitido, url, PERMITIR_OBJETIVOS_PRIVADOS, _resolver)
    if not permitido:
        log.warning("%s: destino no permitido (apunta a una red interna); se omite", servicio.get("nombre"))
        return None

    inicio = time.perf_counter()
    try:
        respuesta = await cliente.get(url, timeout=TIMEOUT_S)
    except httpx.RequestError:  # incluye timeouts y errores de conexión
        return {"servicio_id": servicio["id"], "nombre": servicio["nombre"], "estado": "down", "codigo": None, "latencia_ms": None}

    latencia_ms = round((time.perf_counter() - inicio) * 1000)
    return {
        "servicio_id": servicio["id"],
        "nombre": servicio["nombre"],
        "estado": logica.clasificar(respuesta.status_code, latencia_ms, UMBRAL_DEGRADADO_MS),
        "codigo": respuesta.status_code,
        "latencia_ms": latencia_ms,
    }


async def chequear_todos(cliente: httpx.AsyncClient, servicios: list) -> list:
    """Chequea todo en paralelo. Un fallo inesperado en UN servicio no tumba a los demás."""
    resultados = await asyncio.gather(*(chequear_servicio(cliente, s) for s in servicios), return_exceptions=True)
    salida = []
    for servicio, r in zip(servicios, resultados):
        if isinstance(r, BaseException):
            log.error("falló el chequeo de %s: %r", servicio.get("nombre"), r)
        elif r is not None:
            salida.append(r)
    return salida


async def enviar_al_backend(cliente: httpx.AsyncClient, resultados: list) -> bool:
    """Manda los resultados al backend (hasta 2 intentos). Devuelve True si se guardaron."""
    payload = [
        {"servicio_id": r["servicio_id"], "estado": r["estado"], "codigo": r["codigo"], "latencia_ms": r["latencia_ms"]}
        for r in resultados
    ]
    cabeceras = {"X-Ingest-Token": INGEST_TOKEN} if INGEST_TOKEN else {}
    for intento in (1, 2):
        try:
            respuesta = await cliente.post(f"{BACKEND_URL}/internal/ingest", json={"resultados": payload}, headers=cabeceras, timeout=TIMEOUT_S)
            if respuesta.status_code == 401:
                log.error("el backend rechazó el token: INGEST_TOKEN debe ser igual en backend/.env y worker/.env")
                return False  # reintentar no sirve de nada
            if 400 <= respuesta.status_code < 500:
                log.error("el backend rechazó los datos (%s): %s", respuesta.status_code, respuesta.text[:200])
                return False
            respuesta.raise_for_status()
            datos = respuesta.json()
            log.info("enviado al backend: %s guardados, %s ignorados", datos.get("guardados"), datos.get("ignorados", 0))
            return True
        except httpx.HTTPStatusError as e:
            log.warning("el backend respondió %s (intento %s)", e.response.status_code, intento)
        except httpx.RequestError as e:
            log.warning("no se pudo contactar al backend (intento %s): %s", intento, e)
        if intento == 1:
            await asyncio.sleep(1)
    return False


def imprimir_resultados(resultados: list):
    simbolos = {"up": "✓", "degraded": "⚠", "down": "✗"}
    for r in resultados:
        if r["latencia_ms"] is not None:
            log.info("%s %-16s %sms  (%s)", simbolos[r["estado"]], r["nombre"], r["latencia_ms"], r["codigo"])
        else:
            log.info("%s %-16s sin respuesta", simbolos[r["estado"]], r["nombre"])


async def una_vuelta(cliente: httpx.AsyncClient) -> int:
    """Una ronda completa: pide los servicios, los chequea y manda los resultados. Devuelve cuántos chequeó."""
    servicios = await obtener_servicios(cliente)
    if not servicios:
        log.info("(sin servicios registrados todavía)")
        return 0
    resultados = await chequear_todos(cliente, servicios)
    imprimir_resultados(resultados)
    if resultados:
        await enviar_al_backend(cliente, resultados)
    return len(resultados)


async def bucle_principal(parar=None):
    parar = parar or asyncio.Event()
    loop = asyncio.get_running_loop()
    for senal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(senal, parar.set)  # apagado limpio con Ctrl+C o con `podman stop`
        except (NotImplementedError, RuntimeError):
            pass
    if not INGEST_TOKEN:
        log.warning("INGEST_TOKEN no está definido: si el backend lo exige, rechazará los resultados.")
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as cliente:
        while not parar.is_set():
            inicio = time.monotonic()
            try:
                await una_vuelta(cliente)
            except Exception:
                log.exception("falló una vuelta de chequeos; se reintenta en la siguiente")
            espera = max(0.0, INTERVALO_S - (time.monotonic() - inicio))
            try:
                await asyncio.wait_for(parar.wait(), timeout=espera)
            except asyncio.TimeoutError:
                pass
    log.info("worker detenido")


if __name__ == "__main__":
    asyncio.run(bucle_principal())
