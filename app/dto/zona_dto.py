from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    Field,
    AliasChoices
)


# ============================================================
# CREAR ZONA
# ============================================================

class ZonaCreate(BaseModel):

    id_almacen: str

    nombre: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    tipo_zona: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    temperatura_min: Optional[float] = None

    temperatura_max: Optional[float] = None

    capacidad: int = Field(
        ...,
        ge=0
    )


# ============================================================
# ACTUALIZAR ZONA
# ============================================================

class ZonaUpdate(BaseModel):

    nombre: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    tipo_zona: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    temperatura_min: Optional[float] = None

    temperatura_max: Optional[float] = None

    capacidad: Optional[int] = Field(
        default=None,
        ge=0
    )


# ============================================================
# RESPONSE
#
# Acepta:
#
# id
# id_zona
#
# pero siempre responde como:
#
# id
# ============================================================

class ZonaResponse(BaseModel):

    id: str = Field(
        validation_alias=AliasChoices(
            "id",
            "id_zona"
        )
    )

    id_almacen: str

    id_empresa: str

    nombre: str

    tipo_zona: str

    temperatura_min: Optional[float] = None

    temperatura_max: Optional[float] = None

    capacidad: int

    fecha_creacion: datetime

    fecha_actualizacion: datetime