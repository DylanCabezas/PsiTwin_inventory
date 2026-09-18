from typing import List

from fastapi import APIRouter, status

from app.dto.detalle_reposicion_dto import (
    DetalleReposicionCreate,
    DetalleReposicionUpdate,
    DetalleReposicionResponse
)

from app.services.detalle_reposicion_service import (
    DetalleReposicionService
)


router = APIRouter(
    tags=["Detalles de Reposicion"]
)

service = DetalleReposicionService()


@router.post(
    "/ordenes-reposicion/{id_orden}/detalles",
    response_model=DetalleReposicionResponse,
    status_code=status.HTTP_201_CREATED
)
async def crear(
    id_orden: str,
    data: DetalleReposicionCreate
):
    return await service.crear(id_orden, data)


@router.get(
    "/ordenes-reposicion/{id_orden}/detalles",
    response_model=List[DetalleReposicionResponse]
)
async def obtener_por_orden(id_orden: str):
    return await service.obtener_por_orden(id_orden)


@router.get(
    "/detalles-reposicion/{id_detalle}",
    response_model=DetalleReposicionResponse
)
async def obtener_por_id(id_detalle: str):
    return await service.obtener_por_id(id_detalle)


@router.put(
    "/detalles-reposicion/{id_detalle}",
    response_model=DetalleReposicionResponse
)
async def actualizar(
    id_detalle: str,
    data: DetalleReposicionUpdate
):
    return await service.actualizar(
        id_detalle,
        data
    )


@router.delete(
    "/detalles-reposicion/{id_detalle}"
)
async def eliminar(id_detalle: str):
    return await service.eliminar(id_detalle)