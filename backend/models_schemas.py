from pydantic import BaseModel
from typing import Literal, Optional


class ServicioCreate(BaseModel):
    nombre: str
    url: str


class ResultadoChequeo(BaseModel):
    servicio_id: int
    estado: Literal["up", "degraded", "down"]
    codigo: Optional[int] = None
    latencia_ms: Optional[int] = None


class LoteChequeos(BaseModel):
    resultados: list[ResultadoChequeo]
