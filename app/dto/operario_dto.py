from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OperarioCreate(BaseModel):
    id_empresa: str

    nombre: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    apellido: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    cargo: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    turno: str = Field(
        ...,
        min_length=2,
        max_length=50
    )

    estado: str = Field(
        default="ACTIVO",
        min_length=2,
        max_length=50
    )


class OperarioUpdate(BaseModel):
    nombre: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    apellido: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    cargo: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    turno: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=50
    )

    estado: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=50
    )


class OperarioResponse(BaseModel):
    id_operario: str
    id_empresa: str

    nombre: str
    apellido: str
    cargo: str
    turno: str
    estado: str
    id_almacen: Optional[str] = None

    fecha_creacion: datetime
    fecha_actualizacion: datetime