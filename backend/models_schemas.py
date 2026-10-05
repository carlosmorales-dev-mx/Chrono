from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

import config
import dominio


class ServicioCreate(BaseModel):
    nombre: str
    url: str

    @field_validator("nombre")
    @classmethod
    def _validar_nombre(cls, valor):
        return dominio.validar_nombre(valor)

    @field_validator("url")
    @classmethod
    def _validar_url(cls, valor):
        return dominio.validar_url(valor, permitir_privados=config.PERMITIR_OBJETIVOS_PRIVADOS)


class ResultadoChequeo(BaseModel):
    servicio_id: int = Field(ge=1)
    estado: Literal["up", "degraded", "down"]
    codigo: Optional[int] = Field(default=None, ge=100, le=599)
    latencia_ms: Optional[int] = Field(default=None, ge=0, le=600000)


class LoteChequeos(BaseModel):
    resultados: list[ResultadoChequeo] = Field(min_length=1, max_length=500)
