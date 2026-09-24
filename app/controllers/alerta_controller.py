from typing import List

from fastapi import APIRouter

from app.dto.alerta_dto import (
    AlertaCreate,
    AlertaResponse,
    AlertaEstadoUpdate
)

from app.services.alerta_service import (
    AlertaService
)


router = APIRouter(
    prefix="/alertas",
    tags=["Alertas"]
)

service = AlertaService()


@router.post(
    "",
    response_model=AlertaResponse,
    status_code=201
)
async def crear_alerta(
    data: AlertaCreate
):
    return await service.crear(
        data
    )


@router.get(
    "",
    response_model=List[
        AlertaResponse
    ]
)
async def listar_alertas():
    return await service.listar()


@router.get(
    "/activas",
    response_model=List[
        AlertaResponse
    ]
)
async def listar_alertas_activas():
    return await service.listar_activas()


@router.get(
    "/empresa/{id_empresa}",
    response_model=List[
        AlertaResponse
    ]
)
async def listar_alertas_empresa(
    id_empresa: str
):
    return await service.listar_por_empresa(
        id_empresa
    )


@router.get(
    "/almacen/{id_almacen}",
    response_model=List[
        AlertaResponse
    ]
)
async def listar_alertas_almacen(
    id_almacen: str
):
    return await service.listar_por_almacen(
        id_almacen
    )


@router.get(
    "/producto/{id_producto}",
    response_model=List[
        AlertaResponse
    ]
)
async def listar_alertas_producto(
    id_producto: str
):
    return await service.listar_por_producto(
        id_producto
    )


@router.get(
    "/inventario/{id_inventario}",
    response_model=List[
        AlertaResponse
    ]
)
async def listar_alertas_inventario(
    id_inventario: str
):
    return await service.listar_por_inventario(
        id_inventario
    )


@router.get(
    "/nivel/{nivel_riesgo}",
    response_model=List[
        AlertaResponse
    ]
)
async def listar_alertas_nivel(
    nivel_riesgo: str
):
    return await service.listar_por_nivel(
        nivel_riesgo
    )


@router.get(
    "/{id_alerta}",
    response_model=AlertaResponse
)
async def obtener_alerta(
    id_alerta: str
):
    return await service.obtener(
        id_alerta
    )


@router.patch(
    "/{id_alerta}/estado",
    response_model=AlertaResponse
)
async def cambiar_estado_alerta(
    id_alerta: str,
    data: AlertaEstadoUpdate
):
    return await service.cambiar_estado(
        id_alerta,
        data
    )