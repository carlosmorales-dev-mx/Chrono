"""Pruebas del flujo del worker con un cliente HTTP FALSO (no hace ninguna petición real)."""
import asyncio
import os
import sys
import time as tiempo_real
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["INGEST_TOKEN"] = "token-de-prueba"
os.environ["BACKEND_URL"] = "http://backend.test"

try:
    import httpx  # noqa: F401  (en tu entorno está instalado)
except ImportError:  # permite correr esta prueba en un entorno sin httpx
    httpx = types.ModuleType("httpx")

    class RequestError(Exception):
        pass

    class HTTPStatusError(Exception):
        def __init__(self, mensaje="", *, request=None, response=None):  # misma firma que httpx real
            super().__init__(mensaje)
            self.request, self.response = request, response

    class InvalidURL(Exception):
        pass

    httpx.RequestError, httpx.HTTPStatusError, httpx.InvalidURL = RequestError, HTTPStatusError, InvalidURL
    httpx.TimeoutException = type("TimeoutException", (RequestError,), {})
    httpx.AsyncClient = object
    sys.modules["httpx"] = httpx

import check_servicios as w  # noqa: E402


class Resp:
    def __init__(self, status=200, datos=None, texto=""):
        self.status_code, self._datos, self.text = status, datos or {}, texto

    def json(self):
        return self._datos

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)


class Cliente:
    """Cliente falso: `guion` es una lista de respuestas (o excepciones) que se van entregando en orden."""
    def __init__(self, get=None, post=None):
        self._get, self._post = list(get or []), list(post or [])
        self.llamadas = []

    async def get(self, url, **kw):
        self.llamadas.append(("get", url, kw))
        r = self._get.pop(0) if len(self._get) > 1 else self._get[0]
        if isinstance(r, BaseException):
            raise r
        return r

    async def post(self, url, **kw):
        self.llamadas.append(("post", url, kw))
        r = self._post.pop(0) if len(self._post) > 1 else self._post[0]
        if isinstance(r, BaseException):
            raise r
        return r


def correr(coro):
    return asyncio.run(coro)


def reloj(*valores):
    it = iter(valores)
    return lambda: next(it)


def con_reloj(perf_counter):
    """El módulo `time` que ve el worker, con un perf_counter controlado (el `time` global queda intacto)."""
    return types.SimpleNamespace(perf_counter=perf_counter, monotonic=tiempo_real.monotonic)


class Flujo(unittest.TestCase):
    def setUp(self):
        self.svc = {"id": 1, "nombre": "Mi API", "url": "https://api.example.com"}
        self._resolver, self._sleep, self._time = w._resolver, asyncio.sleep, w.time
        w._resolver = lambda host, puerto: ["93.184.216.34"]
        w.PERMITIR_OBJETIVOS_PRIVADOS = False
        w.UMBRAL_DEGRADADO_MS = 1200

        async def sin_espera(_):
            return None
        w.asyncio.sleep = sin_espera

    def tearDown(self):
        w._resolver = self._resolver
        w.asyncio.sleep = self._sleep
        w.time = self._time

    def medir(self, ms):
        w.time = con_reloj(reloj(0.0, ms / 1000))

    def test_respuesta_rapida_es_up(self):
        self.medir(120)
        r = correr(w.chequear_servicio(Cliente(get=[Resp(200)]), self.svc))
        self.assertEqual((r["estado"], r["codigo"], r["latencia_ms"], r["servicio_id"]), ("up", 200, 120, 1))

    def test_respuesta_lenta_es_degraded(self):
        self.medir(2400)
        self.assertEqual(correr(w.chequear_servicio(Cliente(get=[Resp(200)]), self.svc))["estado"], "degraded")

    def test_5xx_es_down_y_4xx_degraded(self):
        self.medir(50)
        self.assertEqual(correr(w.chequear_servicio(Cliente(get=[Resp(503)]), self.svc))["estado"], "down")
        self.medir(50)
        self.assertEqual(correr(w.chequear_servicio(Cliente(get=[Resp(404)]), self.svc))["estado"], "degraded")

    def test_error_de_red_es_down_sin_latencia(self):
        r = correr(w.chequear_servicio(Cliente(get=[httpx.RequestError("timeout")]), self.svc))
        self.assertEqual((r["estado"], r["codigo"], r["latencia_ms"]), ("down", None, None))

    def test_destino_interno_se_omite_sin_hacer_la_peticion(self):
        w._resolver = lambda host, puerto: ["10.0.0.5"]
        cliente = Cliente(get=[Resp(200)])
        self.assertIsNone(correr(w.chequear_servicio(cliente, self.svc)))
        self.assertEqual(cliente.llamadas, [])  # ni siquiera intentó conectarse

    def test_un_fallo_inesperado_no_tumba_a_los_demas(self):
        self.medir(10)
        malo = {"id": 2, "nombre": "Malo", "url": "https://malo.example.com"}
        cliente = Cliente(get=[Resp(200), httpx.InvalidURL("url rara")])
        w.time = con_reloj(lambda: 0.01)
        resultados = correr(w.chequear_todos(cliente, [self.svc, malo]))
        self.assertEqual([r["nombre"] for r in resultados], ["Mi API"])  # antes, una excepción tumbaba toda la vuelta

    def test_envio_lleva_el_token_y_solo_los_campos_esperados(self):
        cliente = Cliente(post=[Resp(201, {"guardados": 1, "ignorados": 0})])
        ok = correr(w.enviar_al_backend(cliente, [{"servicio_id": 1, "nombre": "x", "estado": "up", "codigo": 200, "latencia_ms": 50}]))
        self.assertTrue(ok)
        _, url, kw = cliente.llamadas[0]
        self.assertEqual(url, "http://backend.test/internal/ingest")
        self.assertEqual(kw["headers"], {"X-Ingest-Token": "token-de-prueba"})
        self.assertEqual(kw["json"], {"resultados": [{"servicio_id": 1, "estado": "up", "codigo": 200, "latencia_ms": 50}]})

    def test_token_rechazado_no_se_reintenta(self):
        cliente = Cliente(post=[Resp(401)])
        self.assertFalse(correr(w.enviar_al_backend(cliente, [{"servicio_id": 1, "nombre": "x", "estado": "up", "codigo": 200, "latencia_ms": 5}])))
        self.assertEqual(len(cliente.llamadas), 1)

    def test_reintenta_una_vez_si_el_backend_falla(self):
        cliente = Cliente(post=[Resp(500), Resp(201, {"guardados": 1})])
        self.assertTrue(correr(w.enviar_al_backend(cliente, [{"servicio_id": 1, "nombre": "x", "estado": "up", "codigo": 200, "latencia_ms": 5}])))
        self.assertEqual(len(cliente.llamadas), 2)

    def test_si_el_backend_no_responde_devuelve_false_tras_dos_intentos(self):
        cliente = Cliente(post=[httpx.RequestError("sin conexión")])
        self.assertFalse(correr(w.enviar_al_backend(cliente, [{"servicio_id": 1, "nombre": "x", "estado": "up", "codigo": 200, "latencia_ms": 5}])))
        self.assertEqual(len(cliente.llamadas), 2)

    def test_error_4xx_de_validacion_no_se_reintenta(self):
        cliente = Cliente(post=[Resp(422, texto="detalle")])
        self.assertFalse(correr(w.enviar_al_backend(cliente, [{"servicio_id": 1, "nombre": "x", "estado": "up", "codigo": 200, "latencia_ms": 5}])))
        self.assertEqual(len(cliente.llamadas), 1)

    def test_una_vuelta_completa(self):
        w.time = con_reloj(reloj(0.0, 0.1, 0.0, 0.1))
        cliente = Cliente(get=[Resp(200, [self.svc, {"id": 2, "nombre": "B", "url": "https://b.example.com"}]), Resp(200), Resp(200)], post=[Resp(201, {"guardados": 2})])
        self.assertEqual(correr(w.una_vuelta(cliente)), 2)
        self.assertEqual(sum(1 for c in cliente.llamadas if c[0] == "post"), 1)

    def test_sin_servicios_no_envia_nada(self):
        cliente = Cliente(get=[Resp(200, [])])
        self.assertEqual(correr(w.una_vuelta(cliente)), 0)
        self.assertEqual([c for c in cliente.llamadas if c[0] == "post"], [])

    def test_backend_caido_al_pedir_servicios(self):
        cliente = Cliente(get=[httpx.RequestError("sin conexión")])
        self.assertEqual(correr(w.obtener_servicios(cliente)), [])

    def test_apagado_limpio_del_bucle(self):
        llamadas = []
        estado = {}

        async def una(_):
            llamadas.append(1)
            estado["parar"].set()  # simula Ctrl+C / podman stop después de la primera vuelta
            return 0

        class Cm:
            async def __aenter__(self_):
                return Cliente()

            async def __aexit__(self_, *a):
                return False

        async def principal():
            estado["parar"] = asyncio.Event()
            await asyncio.wait_for(w.bucle_principal(estado["parar"]), timeout=5)

        original, original_cliente = w.una_vuelta, w.httpx.AsyncClient
        w.una_vuelta, w.httpx.AsyncClient = una, lambda **kw: Cm()
        try:
            correr(principal())
        finally:
            w.una_vuelta, w.httpx.AsyncClient = original, original_cliente
        self.assertEqual(llamadas, [1])  # hizo una vuelta y salió en cuanto se pidió parar


if __name__ == "__main__":
    unittest.main()
