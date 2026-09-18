from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    Field,
    model_validator
)


class ProductoCreate(BaseModel):

    id_empresa: str
    id_rack: str

    nombre: str = Field(
        ...,
        min_length=2,
        max_length=150
    )

    categoria: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    familia: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    marca: Optional[str] = None

    peso: Optional[float] = Field(
        default=None,
        gt=0
    )

    volumen: Optional[float] = Field(
        default=None,
        gt=0
    )

    stock: int = Field(
        default=0,
        ge=0
    )

    requiere_refrigeracion: bool = False

    temperatura_min_almacenamiento: Optional[float] = None
    temperatura_max_almacenamiento: Optional[float] = None

    lead_time_dias: int = Field(
        ...,
        ge=0
    )

    vida_util_dias: int = Field(
        ...,
        ge=1
    )

    @model_validator(mode="after")
    def validar_refrigeracion(self):

        if self.requiere_refrigeracion:

            if (
                self.temperatura_min_almacenamiento is None
                or
                self.temperatura_max_almacenamiento is None
            ):

                raise ValueError(
                    "Si el producto requiere refrigeración, "
                    "debe indicar temperatura mínima y máxima"
                )

            if (
                self.temperatura_min_almacenamiento
                >
                self.temperatura_max_almacenamiento
            ):

                raise ValueError(
                    "La temperatura mínima no puede ser "
                    "mayor que la máxima"
                )

        return self


class ProductoUpdate(BaseModel):

    id_rack: Optional[str] = None

    nombre: Optional[str] = None
    categoria: Optional[str] = None
    familia: Optional[str] = None
    marca: Optional[str] = None

    peso: Optional[float] = None
    volumen: Optional[float] = None

    stock: Optional[int] = Field(
        default=None,
        ge=0
    )

    requiere_refrigeracion: Optional[bool] = None

    temperatura_min_almacenamiento: Optional[float] = None
    temperatura_max_almacenamiento: Optional[float] = None

    lead_time_dias: Optional[int] = Field(
        default=None,
        ge=0
    )

    vida_util_dias: Optional[int] = Field(
        default=None,
        ge=1
    )


class ProductoResponse(BaseModel):

    id_producto: str

    id_empresa: str

    # Para compatibilidad con registros antiguos
    id_rack: Optional[str] = None

    nombre: str

    categoria: str

    familia: str

    marca: Optional[str] = None

    peso: Optional[float] = None

    volumen: Optional[float] = None

    # Para compatibilidad con registros antiguos
    stock: int = 0

    requiere_refrigeracion: bool = False

    temperatura_min_almacenamiento: Optional[float] = None

    temperatura_max_almacenamiento: Optional[float] = None

    lead_time_dias: int

    vida_util_dias: int

    fecha_creacion: datetime

    fecha_actualizacion: datetime