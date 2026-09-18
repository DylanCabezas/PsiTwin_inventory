from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    Field,
    model_validator
)


class DetalleRecepcionCreate(BaseModel):
    id_detalle_reposicion: str
    id_inventario: str

    cantidad_recibida: int = Field(
        ...,
        gt=0
    )

    cantidad_rechazada: int = Field(
        default=0,
        ge=0
    )

    motivo_rechazo: Optional[str] = Field(
        default=None,
        max_length=500
    )

    @model_validator(mode="after")
    def validar_cantidades(self):

        if (
            self.cantidad_rechazada
            > self.cantidad_recibida
        ):
            raise ValueError(
                "La cantidad rechazada no puede "
                "ser mayor que la recibida"
            )

        if (
            self.cantidad_rechazada > 0
            and not self.motivo_rechazo
        ):
            raise ValueError(
                "Debe indicar el motivo del rechazo"
            )

        return self


class DetalleRecepcionResponse(BaseModel):
    id_detalle_recepcion: str
    id_recepcion: str
    id_detalle_reposicion: str
    id_inventario: str

    cantidad_recibida: int
    cantidad_rechazada: int
    cantidad_aceptada: int

    motivo_rechazo: Optional[str] = None

    id_movimiento: Optional[str] = None

    fecha_creacion: datetime