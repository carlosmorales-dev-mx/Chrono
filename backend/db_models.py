from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
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

    id = Column(Integer, primary_key=True, index=True)
    servicio_id = Column(Integer, ForeignKey("servicios.id"), nullable=False, index=True)
    estado = Column(String, nullable=False)
    codigo_http = Column(Integer, nullable=True)
    latencia_ms = Column(Integer, nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    servicio = relationship("Servicio", back_populates="chequeos")


class Incidente(Base):
    """
    Un registro por cada periodo continuo en que un servicio estuvo
    degradado o caido. Se abre automaticamente cuando un chequeo
    detecta la transicion de 'up' a algo peor, y se cierra solo cuando
    vuelve a 'up' -- sin que nadie tenga que crearlo a mano.
    """
    __tablename__ = "incidentes"

    id = Column(Integer, primary_key=True, index=True)
    servicio_id = Column(Integer, ForeignKey("servicios.id"), nullable=False, index=True)
    estado = Column(String, nullable=False)  # "degraded" | "down" -- el peor estado visto
    inicio = Column(DateTime(timezone=True), server_default=func.now())
    fin = Column(DateTime(timezone=True), nullable=True)  # NULL = sigue activo

    servicio = relationship("Servicio", back_populates="incidentes")
