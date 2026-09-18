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

    id_rack: Optional[str] = None

    stock_actual: Optional[int] = Field(
        default=None,
        ge=0
    )

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