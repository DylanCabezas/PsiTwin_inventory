from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EstadoOrdenReposicion(str, Enum):
    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    ENVIADA = "ENVIADA"
    PARCIAL = "PARCIAL"
    RECIBIDA = "RECIBIDA"
    CANCELADA = "CANCELADA"


class OrigenOrden(str, Enum):
    MANUAL = "MANUAL"
    RECOMENDACION_IA = "RECOMENDACION_IA"


class OrdenReposicionCreate(BaseModel):
    id_recomendacion: Optional[str] = None
    id_empresa: str
    id_almacen: str
    id_proveedor: str

    fecha_estimada_recepcion: Optional[datetime] = None

    origen: OrigenOrden = OrigenOrden.MANUAL

    observacion: Optional[str] = Field(
        default=None,
        max_length=500
    )


class OrdenReposicionUpdate(BaseModel):
    fecha_estimada_recepcion: Optional[datetime] = None
    observacion: Optional[str] = Field(
        default=None,
        max_length=500
    )


class OrdenReposicionResponse(BaseModel):
    id_orden_reposicion: str
    id_recomendacion: Optional[str] = None

    id_empresa: str
    id_almacen: str
    id_proveedor: str

    origen: OrigenOrden
    estado: EstadoOrdenReposicion

    fecha_orden: datetime
    fecha_estimada_recepcion: Optional[datetime] = None

    observacion: Optional[str] = None

    fecha_creacion: datetime
    fecha_actualizacion: datetime