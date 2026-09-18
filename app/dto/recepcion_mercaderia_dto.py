from datetime import datetime
from enum import Enum

from pydantic import (
    BaseModel,
    Field,
    model_validator
)


class EstadoRecepcion(str, Enum):
    CONFORME = "CONFORME"
    RECHAZADO = "RECHAZADO"
    EN_EVALUACION = "EN_EVALUACION"


class DetalleRecepcionCreate(BaseModel):

    id_detalle_reposicion: str

    cantidad_recibida: int = Field(
        gt=0
    )

    lote: str = Field(
        min_length=1,
        max_length=100
    )

    fecha_vencimiento: datetime | None = None

    temperatura_recepcion: float | None = None

    estado_recepcion: EstadoRecepcion

    comentario_recepcion: str | None = Field(
        default=None,
        max_length=1000
    )

    @model_validator(mode="after")
    def validar(self):

        self.lote = self.lote.strip()

        if self.comentario_recepcion is not None:
            self.comentario_recepcion = (
                self.comentario_recepcion.strip()
            )

        if (
            self.estado_recepcion
            in {
                EstadoRecepcion.RECHAZADO,
                EstadoRecepcion.EN_EVALUACION
            }
            and
            not self.comentario_recepcion
        ):
            raise ValueError(
                "Debe indicar el motivo cuando "
                "la mercadería es RECHAZADA "
                "o queda EN_EVALUACION"
            )

        return self


class RecepcionMercaderiaCreate(BaseModel):

    id_orden_reposicion: str

    id_operario: str

    fecha_recepcion: datetime | None = None

    observaciones_generales: str | None = Field(
        default=None,
        max_length=1000
    )

    detalles: list[
        DetalleRecepcionCreate
    ] = Field(
        min_length=1
    )


class DetalleRecepcionResponse(BaseModel):

    id_detalle_recepcion: str

    id_recepcion: str

    id_detalle_reposicion: str

    cantidad_recibida: int

    lote: str

    fecha_vencimiento: datetime | None

    temperatura_recepcion: float | None

    estado_recepcion: EstadoRecepcion

    comentario_recepcion: str | None

    ubicado: bool

    id_inventario: str | None

    fecha_resolucion: datetime | None = None

    id_operario_resolucion: str | None = None

    comentario_resolucion: str | None = None


class RecepcionMercaderiaResponse(BaseModel):

    id_recepcion: str

    id_orden_reposicion: str

    id_operario: str

    fecha_recepcion: datetime

    observaciones_generales: str | None

    fecha_creacion: datetime

    detalles: list[
        DetalleRecepcionResponse
    ]


class UbicarDetalleRecepcion(BaseModel):

    id_rack: str


class ResolverEvaluacion(BaseModel):

    id_operario: str

    estado_recepcion: EstadoRecepcion

    comentario_resolucion: str = Field(
        min_length=1,
        max_length=1000
    )

    @model_validator(mode="after")
    def validar_estado(self):

        if self.estado_recepcion not in {
            EstadoRecepcion.CONFORME,
            EstadoRecepcion.RECHAZADO
        }:
            raise ValueError(
                "Una evaluación solo puede "
                "resolverse como CONFORME "
                "o RECHAZADO"
            )

        self.comentario_resolucion = (
            self.comentario_resolucion.strip()
        )

        return self