from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from websocket_manager import manager

app = FastAPI(title="Pulse API")

app.add_middleware(
    CORSMiddleware,
    # Regex en vez de lista exacta: Vite salta de puerto automático
    # cuando 5173 ya está ocupado (p.ej. por otro proyecto corriendo a
    # la vez), y una lista fija de orígenes se rompe silenciosamente
    # cada vez que eso pasa -- exactamente lo que causó este bug.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def raiz():
    return {"status": "Pulse API corriendo"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.conectar(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.desconectar(websocket)