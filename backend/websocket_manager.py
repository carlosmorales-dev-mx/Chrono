import asyncio

from fastapi import WebSocket


class ConnectionManager:
    """Lleva la lista de navegadores conectados por WebSocket ahora mismo,
    y sabe transmitirles un mensaje a todos a la vez."""

    TIMEOUT_ENVIO_S = 3.0

    def __init__(self):
        self.conexiones_activas: list[WebSocket] = []

    async def conectar(self, websocket: WebSocket):
        await websocket.accept()
        self.conexiones_activas.append(websocket)

    def desconectar(self, websocket: WebSocket):
        if websocket in self.conexiones_activas:
            self.conexiones_activas.remove(websocket)

    async def _enviar(self, conexion: WebSocket, mensaje: dict) -> bool:
        try:
            await asyncio.wait_for(conexion.send_json(mensaje), timeout=self.TIMEOUT_ENVIO_S)
            return True
        except Exception:
            return False

    async def transmitir(self, mensaje: dict):
        """Envía el mensaje a todos los conectados A LA VEZ: un navegador lento no retrasa a los demás.
        Si alguno ya se desconectó sin avisar (cerró la pestaña, perdió internet) o no responde a tiempo,
        se quita de la lista en vez de dejar que tumbe el envío."""
        if not self.conexiones_activas:
            return
        conexiones = list(self.conexiones_activas)
        resultados = await asyncio.gather(*(self._enviar(c, mensaje) for c in conexiones))
        for conexion, ok in zip(conexiones, resultados):
            if not ok:
                self.desconectar(conexion)


manager = ConnectionManager()
