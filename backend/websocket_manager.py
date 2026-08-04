from fastapi import WebSocket


class ConnectionManager:
    """Lleva la lista de navegadores conectados por WebSocket ahora
    mismo, y sabe transmitirles un mensaje a todos a la vez."""

    def __init__(self):
        self.conexiones_activas: list[WebSocket] = []

    async def conectar(self, websocket: WebSocket):
        await websocket.accept()
        self.conexiones_activas.append(websocket)

    def desconectar(self, websocket: WebSocket):
        if websocket in self.conexiones_activas:
            self.conexiones_activas.remove(websocket)

    async def transmitir(self, mensaje: dict):
        """Envia el mensaje a todos los conectados. Si alguno ya se
        desconecto sin avisar (cerro la pestaña, perdio internet), lo
        quitamos de la lista en vez de dejar que tumbe el broadcast."""
        muertas = []
        for conexion in self.conexiones_activas:
            try:
                await conexion.send_json(mensaje)
            except Exception:
                muertas.append(conexion)
        for conexion in muertas:
            self.desconectar(conexion)


manager = ConnectionManager()
