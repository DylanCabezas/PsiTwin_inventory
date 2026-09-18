from typing import List

from fastapi import APIRouter, status

from app.dto.orden_reposicion_dto import (
    OrdenReposicionCreate,
    OrdenReposicionUpdate,
    OrdenReposicionResponse,
    EstadoOrdenReposicion
)

from app.services.orden_reposicion_service import (
    OrdenReposicionService
)


router = APIRouter(
    prefix="/ordenes-reposicion",
    tags=["Ordenes de Reposicion"]
)

service = OrdenReposicionService()


@router.post(
    "",
    response_model=OrdenReposicionResponse,
    status_code=status.HTTP_201_CREATED
)
async def crear(data: OrdenReposicionCreate):
    return await service.crear(data)


@router.get(
    "",
    response_model=List[OrdenReposicionResponse]
)
async def obtener_todos():
    return await service.obtener_todos()


@router.get(
    "/empresa/{id_empresa}",
    response_model=List[OrdenReposicionResponse]
)
async def obtener_por_empresa(id_empresa: str):
    return await service.obtener_por_empresa(id_empresa)


@router.get(
    "/almacen/{id_almacen}",
    response_model=List[OrdenReposicionResponse]
)
async def obtener_por_almacen(id_almacen: str):
    return await service.obtener_por_almacen(id_almacen)


@router.get(
    "/proveedor/{id_proveedor}",
    response_model=List[OrdenReposicionResponse]
)
async def obtener_por_proveedor(id_proveedor: str):
    return await service.obtener_por_proveedor(id_proveedor)


@router.get(
    "/estado/{estado}",
    response_model=List[OrdenReposicionResponse]
)
async def obtener_por_estado(
    estado: EstadoOrdenReposicion
):
    return await service.obtener_por_estado(
        estado.value
    )


@router.patch(
    "/{id_orden}/aprobar",
    response_model=OrdenReposicionResponse
)
async def aprobar(id_orden: str):
    return await service.aprobar(id_orden)


@router.patch(
    "/{id_orden}/enviar",
    response_model=OrdenReposicionResponse
)
async def enviar(id_orden: str):
    return await service.enviar(id_orden)


@router.patch(
    "/{id_orden}/cancelar",
    response_model=OrdenReposicionResponse
)
async def cancelar(id_orden: str):
    return await service.cancelar(id_orden)


@router.get(
    "/{id_orden}",
    response_model=OrdenReposicionResponse
)
async def obtener_por_id(id_orden: str):
    return await service.obtener_por_id(id_orden)


@router.put(
    "/{id_orden}",
    response_model=OrdenReposicionResponse
)
async def actualizar(
    id_orden: str,
    data: OrdenReposicionUpdate
):
    return await service.actualizar(id_orden, data)


@router.delete("/{id_orden}")
async def eliminar(id_orden: str):
    return await service.eliminar(id_orden)