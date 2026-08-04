import asyncio
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")


async def obtener_servicios(cliente: httpx.AsyncClient) -> list[dict]:
    """Pide la lista de servicios a monitorear al backend -- ya no vive
    hardcodeada aqui, asi que si agregas uno nuevo desde el frontend,
    el worker lo empieza a chequear en su siguiente vuelta, sin
    reiniciar nada."""
    try:
        respuesta = await cliente.get(f"{BACKEND_URL}/servicios", timeout=5.0)
        respuesta.raise_for_status()
        return respuesta.json()
    except httpx.RequestError:
        print("(no se pudo obtener la lista de servicios del backend)")
        return []


# Umbral de latencia: aunque el codigo HTTP sea exitoso, una
# respuesta demasiado lenta es un problema real en cualquier sistema
# de monitoreo serio -- no solo "arriba/abajo" segun el codigo.
UMBRAL_DEGRADADO_MS = 1200


async def chequear_servicio(cliente: httpx.AsyncClient, servicio: dict) -> dict:
    inicio = time.perf_counter()
    try:
        respuesta = await cliente.get(servicio["url"], timeout=5.0)
        latencia_ms = round((time.perf_counter() - inicio) * 1000)

        if respuesta.status_code >= 400:
            estado = "degraded"
        elif latencia_ms > UMBRAL_DEGRADADO_MS:
            estado = "degraded"
        else:
            estado = "up"

        return {
            "servicio_id": servicio["id"],
            "nombre": servicio["nombre"],
            "estado": estado,
            "codigo": respuesta.status_code,
            "latencia_ms": latencia_ms,
        }
    except httpx.RequestError:
        return {
            "servicio_id": servicio["id"],
            "nombre": servicio["nombre"],
            "estado": "down",
            "codigo": None,
            "latencia_ms": None,
        }


async def chequear_todos(cliente: httpx.AsyncClient, servicios: list[dict]) -> list[dict]:
    tareas = [chequear_servicio(cliente, s) for s in servicios]
    return await asyncio.gather(*tareas)


async def enviar_al_backend(cliente: httpx.AsyncClient, resultados: list[dict]):
    payload = [
        {
            "servicio_id": r["servicio_id"],
            "estado": r["estado"],
            "codigo": r["codigo"],
            "latencia_ms": r["latencia_ms"],
        }
        for r in resultados
    ]
    try:
        respuesta = await cliente.post(
            f"{BACKEND_URL}/internal/ingest",
            json={"resultados": payload},
            timeout=5.0,
        )
        respuesta.raise_for_status()
        print(f"(enviado al backend: {respuesta.json()['guardados']} guardados)")
    except httpx.RequestError as e:
        print(f"(no se pudo contactar al backend: {e})")
    except httpx.HTTPStatusError as e:
        print(f"(el backend rechazo los datos: {e.response.status_code})")


def imprimir_resultados(resultados: list[dict]):
    simbolos = {"up": "✓", "degraded": "⚠", "down": "✗"}
    for r in resultados:
        simbolo = simbolos[r["estado"]]
        if r["latencia_ms"] is not None:
            print(f"{simbolo} {r['nombre']:<16} {r['latencia_ms']}ms  ({r['codigo']})")
        else:
            print(f"{simbolo} {r['nombre']:<16} sin respuesta")


async def bucle_principal():
    async with httpx.AsyncClient() as cliente:
        while True:
            print("\n--- Chequeo:", time.strftime("%H:%M:%S"), "---")
            servicios = await obtener_servicios(cliente)
            if not servicios:
                print("(sin servicios registrados todavia)")
            else:
                resultados = await chequear_todos(cliente, servicios)
                imprimir_resultados(resultados)
                await enviar_al_backend(cliente, resultados)
            await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(bucle_principal())
