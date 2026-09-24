from typing import List

from fastapi import APIRouter

from app.dto.recomendacion_dto import (
    RecomendacionCreate,
    RecomendacionResponse,
    RecomendacionEstadoUpdate
)

from app.services.recomendacion_service import (
    RecomendacionService
)


router = APIRouter(
    prefix="/recomendaciones",
    tags=["Recomendaciones"]
)

service = RecomendacionService()


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


@router.get(
    "",
    response_model=List[
        RecomendacionResponse
    ]
)
async def listar_recomendaciones():
    return await service.listar()


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