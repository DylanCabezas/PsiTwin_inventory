from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TipoAlerta(str, Enum):
    RIESGO_STOCKOUT = "RIESGO_STOCKOUT"
    STOCK_BAJO = "STOCK_BAJO"
    SOBRESTOCK = "SOBRESTOCK"
    CONSUMO_ANOMALO = "CONSUMO_ANOMALO"
    PROXIMO_VENCIMIENTO = "PROXIMO_VENCIMIENTO"


class NivelRiesgo(str, Enum):
    BAJO = "BAJO"
    MEDIO = "MEDIO"
    ALTO = "ALTO"
    CRITICO = "CRITICO"


class EstadoAlerta(str, Enum):
    ACTIVA = "ACTIVA"
    VISTA = "VISTA"
    RESUELTA = "RESUELTA"
    IGNORADA = "IGNORADA"


class AlertaCreate(BaseModel):
    # Se ignora: se toma del token.
    id_empresa: Optional[str] = None
    id_almacen: str
    id_inventario: str
    id_detalle_inventario: str | None = None
    id_producto: str

    tipo_alerta: TipoAlerta
    nivel_riesgo: NivelRiesgo

    titulo: str = Field(
        min_length=3,
        max_length=150
    )

    mensaje: str = Field(
        min_length=3,
        max_length=1000
    )

    stock_actual: float = Field(ge=0)

    dias_cobertura: Optional[float] = Field(
        default=None,
        ge=0
    )

    stock_seguridad: Optional[float] = Field(
        default=None,
        ge=0
    )

    punto_reposicion: Optional[float] = Field(
        default=None,
        ge=0
    )

    forecast_7d: Optional[float] = Field(
        default=None,
        ge=0
    )


class AlertaResponse(BaseModel):
    id_alerta: str

    id_empresa: str
    id_almacen: str
    id_inventario: str
    id_detalle_inventario: str | None = None
    id_producto: str

    tipo_alerta: TipoAlerta
    nivel_riesgo: NivelRiesgo

    titulo: str
    mensaje: str

    stock_actual: float
    dias_cobertura: Optional[float] = None
    stock_seguridad: Optional[float] = None
    punto_reposicion: Optional[float] = None
    forecast_7d: Optional[float] = None

    estado: EstadoAlerta

    fecha_creacion: datetime
    fecha_actualizacion: datetime
    fecha_resolucion: Optional[datetime] = None


class AlertaEstadoUpdate(BaseModel):
    estado: EstadoAlerta