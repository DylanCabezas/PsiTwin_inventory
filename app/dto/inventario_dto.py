from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    Field,
    model_validator
)


# ============================================================
# CREAR INVENTARIO
# ============================================================

class InventarioCreate(BaseModel):

    id_producto: str

    id_rack: str

    stock_actual: int = Field(
        ...,
        ge=0
    )

    stock_minimo: int = Field(
        default=0,
        ge=0
    )

    stock_maximo: int = Field(
        ...,
        ge=0
    )

    @model_validator(mode="after")
    def validar_stocks(self):

        if self.stock_minimo > self.stock_maximo:

            raise ValueError(
                "El stock mínimo no puede ser mayor "
                "que el stock máximo"
            )

        return self


# ============================================================
# ACTUALIZAR INVENTARIO
# ============================================================

class InventarioUpdate(BaseModel):

    # Solo límites: el stock cambia únicamente por
    # movimientos y recepciones; el rack no se cambia.

    stock_minimo: Optional[int] = Field(
        default=None,
        ge=0
    )

    stock_maximo: Optional[int] = Field(
        default=None,
        ge=0
    )


# ============================================================
# RESPONSE
# ============================================================

class InventarioResponse(BaseModel):

    id_inventario: str

    id_producto: str

    id_rack: str

    stock_actual: int

    stock_minimo: int

    stock_maximo: int

    fecha_creacion: datetime

    fecha_actualizacion: datetime


# ============================================================
# HISTORIAL DE CAMBIOS
#
# GET /inventarios/{id}/historial
# ============================================================

class InventarioHistorialResponse(BaseModel):

    fecha: datetime

    id_operario: Optional[str] = None

    operario_nombre: Optional[str] = None

    # CREAR | EDITAR_LIMITES
    accion: str

    antes: Optional[dict] = None

    despues: Optional[dict] = None
