from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import relationship

from database import Base


class Servicio(Base):
    __tablename__ = "servicios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    url = Column(String, nullable=False)
    anclado = Column(Boolean, default=False, nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    chequeos = relationship("Chequeo", back_populates="servicio", cascade="all, delete-orphan")
    incidentes = relationship("Incidente", back_populates="servicio", cascade="all, delete-orphan")


class Chequeo(Base):
    __tablename__ = "chequeos"
    # Las consultas son siempre "los chequeos de UN servicio en un rango de tiempo": un índice compuesto las cubre.
    # (migrar.py crea el mismo índice, con el mismo nombre, en bases que ya existían.)
    __table_args__ = (Index("ix_chequeos_servicio_creado", "servicio_id", "creado_en"),)

    id = Column(Integer, primary_key=True, index=True)
    servicio_id = Column(Integer, ForeignKey("servicios.id"), nullable=False, index=True)
    estado = Column(String, nullable=False)
    codigo_http = Column(Integer, nullable=True)
    latencia_ms = Column(Integer, nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    servicio = relationship("Servicio", back_populates="chequeos")


class Incidente(Base):
    """
    Un registro por cada periodo continuo en que un servicio estuvo degradado o caido.
    Se abre solo cuando varios chequeos seguidos salen mal y se cierra solo cuando varios
    seguidos vuelven a 'up' (ver dominio.decidir_incidente) -- sin que nadie lo cree a mano.
    """
    __tablename__ = "incidentes"
    # Como máximo UN incidente abierto por servicio: lo garantiza la base de datos, no solo el código.
    __table_args__ = (
        Index("uq_incidentes_abierto_por_servicio", "servicio_id", unique=True, postgresql_where=text("fin IS NULL")),
    )

    id = Column(Integer, primary_key=True, index=True)
    servicio_id = Column(Integer, ForeignKey("servicios.id"), nullable=False, index=True)
    estado = Column(String, nullable=False)  # "degraded" | "down" -- el peor estado visto
    inicio = Column(DateTime(timezone=True), server_default=func.now())
    fin = Column(DateTime(timezone=True), nullable=True)  # NULL = sigue activo

    servicio = relationship("Servicio", back_populates="incidentes")
