from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class OperarioCreate(BaseModel):
    id_empresa: str
    id_almacen: Optional[str] = None

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

    correo: EmailStr

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

    correo: Optional[EmailStr] = None

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
    correo: Optional[EmailStr] = None
    cargo: str
    turno: str
    estado: str
    id_almacen: Optional[str] = None
    correo_verificado: bool = False
    fecha_verificacion_correo: Optional[datetime] = None

    fecha_creacion: datetime
    fecha_actualizacion: datetime