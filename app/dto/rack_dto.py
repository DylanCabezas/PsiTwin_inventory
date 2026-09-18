from datetime import datetime
from enum import Enum

from pydantic import (
    BaseModel,
    Field
)


class EstadoRack(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    LLENO = "LLENO"
    MANTENIMIENTO = "MANTENIMIENTO"


class RackCreate(BaseModel):
    id_zona: str

    codigo: str = Field(
        min_length=1,
        max_length=50
    )

    nivel: int = Field(
        ge=0
    )

    capacidad: float = Field(
        gt=0
    )

    estado: EstadoRack = EstadoRack.DISPONIBLE


class RackUpdate(BaseModel):
    codigo: str | None = Field(
        default=None,
        min_length=1,
        max_length=50
    )

    nivel: int | None = Field(
        default=None,
        ge=0
    )

    capacidad: float | None = Field(
        default=None,
        gt=0
    )

    estado: EstadoRack | None = None


class RackResponse(BaseModel):
    id_rack: str
    id_zona: str

    codigo: str

    nivel: int

    capacidad: float

    estado: EstadoRack

    fecha_creacion: datetime

    fecha_actualizacion: datetime