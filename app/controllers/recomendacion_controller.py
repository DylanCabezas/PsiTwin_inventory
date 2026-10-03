from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter

from pydantic import (
    BaseModel,
    Field
)

from app.dto.recomendacion_dto import (
    RecomendacionCreate,
    RecomendacionResponse,
    RecomendacionEstadoUpdate,
        EstadoRecomendacion,
        EmpresaAprobacionRequest,
        EmpresaCambiosRequest,
        EmpresaRechazoRequest,
        PropuestaRecomendacionUpdate,
)

from app.services.recomendacion_service import (
    RecomendacionService
)


# ============================================================
# REQUEST PARA CONVERTIR RECOMENDACION EN ORDEN
# ============================================================

class CrearOrdenDesdeRecomendacionRequest(
    BaseModel
):

    id_proveedor: str

    costo_unitario: float = Field(
        ge=0
    )

    fecha_estimada_recepcion: Optional[
        datetime
    ] = None


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/recomendaciones",
    tags=["Recomendaciones"]
)

service = RecomendacionService()


# ============================================================
# CREAR RECOMENDACION
# ============================================================

@router.post(
    "",
    response_model=RecomendacionResponse,
    status_code=201
)
async def crear_recomendacion(
    data: RecomendacionCreate
):

    return await service.crear(
        data
    )


# ============================================================
# LISTAR
# ============================================================

@router.get(
    "",
    response_model=List[
        RecomendacionResponse
    ]
)
async def listar_recomendaciones():

    return await service.listar()


# ============================================================
# POR EMPRESA
# ============================================================

@router.get(
    "/empresa/{id_empresa}",
    response_model=List[
        RecomendacionResponse
    ]
)
async def listar_recomendaciones_empresa(
    id_empresa: str
):

    return await service.listar_por_empresa(
        id_empresa
    )


# ============================================================
# POR ALMACEN
# ============================================================

@router.get(
    "/almacen/{id_almacen}",
    response_model=List[
        RecomendacionResponse
    ]
)
async def listar_recomendaciones_almacen(
    id_almacen: str
):

    return await service.listar_por_almacen(
        id_almacen
    )


# ============================================================
# POR PRODUCTO
# ============================================================

@router.get(
    "/producto/{id_producto}",
    response_model=List[
        RecomendacionResponse
    ]
)
async def listar_recomendaciones_producto(
    id_producto: str
):

    return await service.listar_por_producto(
        id_producto
    )


# ============================================================
# POR INVENTARIO
# ============================================================

@router.get(
    "/inventario/{id_inventario}",
    response_model=List[
        RecomendacionResponse
    ]
)
async def listar_recomendaciones_inventario(
    id_inventario: str
):

    return await service.listar_por_inventario(
        id_inventario
    )


# ============================================================
# CREAR ORDEN DESDE RECOMENDACION
#
# IMPORTANTE:
# Debe estar antes de /{id_recomendacion}
# ============================================================

@router.post(
    "/{id_recomendacion}/crear-orden",
    status_code=201
)
async def crear_orden_desde_recomendacion(
    id_recomendacion: str,
    data: CrearOrdenDesdeRecomendacionRequest
):

    return (
        await service
        .crear_orden_desde_recomendacion(

            id_recomendacion=
                id_recomendacion,

            id_proveedor=
                data.id_proveedor,

            costo_unitario=
                data.costo_unitario,

            fecha_estimada_recepcion=
                data.fecha_estimada_recepcion
        )
    )


# ============================================================
# OBTENER RECOMENDACION
# ============================================================

@router.get(
    "/{id_recomendacion}",
    response_model=RecomendacionResponse
)
async def obtener_recomendacion(
    id_recomendacion: str
):

    return await service.obtener(
        id_recomendacion
    )


# ============================================================
# CAMBIAR ESTADO
# ============================================================

@router.patch(
    "/{id_recomendacion}/estado",
    response_model=RecomendacionResponse
)
async def cambiar_estado_recomendacion(
    id_recomendacion: str,
    data: RecomendacionEstadoUpdate
):

    return await service.cambiar_estado(
        id_recomendacion,
        data
    )


@router.patch(
    "/{id_recomendacion}/validar-operario",
    response_model=RecomendacionResponse
)
async def validar_por_operario(
    id_recomendacion: str,
    id_operario: str | None = None
):
    return await service.cambiar_estado(
        id_recomendacion,
        RecomendacionEstadoUpdate(
            estado=EstadoRecomendacion.VALIDADA_OPERARIO
        ),
        id_operario
    )


@router.patch(
    "/{id_recomendacion}/aprobar-empresa",
)
async def aprobar_por_empresa(
    id_recomendacion: str,
    data: EmpresaAprobacionRequest,
):
    return await service.aprobar_por_empresa(
        id_recomendacion,
        data,
    )


@router.patch(
    "/{id_recomendacion}/solicitar-cambios",
    response_model=RecomendacionResponse,
)
async def solicitar_cambios(
    id_recomendacion: str,
    data: EmpresaCambiosRequest,
):
    return await service.solicitar_cambios(id_recomendacion, data)


@router.patch(
    "/{id_recomendacion}/rechazar-empresa",
    response_model=RecomendacionResponse,
)
async def rechazar_por_empresa(
    id_recomendacion: str,
    data: EmpresaRechazoRequest,
):
    return await service.rechazar_por_empresa(id_recomendacion, data)


@router.patch(
    "/{id_recomendacion}/actualizar-propuesta",
    response_model=RecomendacionResponse,
)
async def actualizar_propuesta(
    id_recomendacion: str,
    data: PropuestaRecomendacionUpdate,
    id_operario: str | None = None,
):
    return await service.actualizar_propuesta(
        id_recomendacion,
        data,
        id_operario,
    )