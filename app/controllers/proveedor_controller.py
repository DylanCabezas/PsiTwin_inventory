from typing import List

from fastapi import APIRouter, status

from app.dto.proveedor_dto import (
    ProveedorCreate,
    ProveedorUpdate,
    ProveedorResponse,
    EstadoProveedor
)

from app.services.proveedor_service import (
    ProveedorService
)


router = APIRouter(
    prefix="/proveedores",
    tags=["Proveedores"]
)

service = ProveedorService()


@router.post(
    "",
    response_model=ProveedorResponse,
    status_code=status.HTTP_201_CREATED
)
async def crear(data: ProveedorCreate):
    return await service.crear(data)


@router.get(
    "",
    response_model=List[ProveedorResponse]
)
async def obtener_todos():
    return await service.obtener_todos()


@router.get(
    "/empresa/{id_empresa}",
    response_model=List[ProveedorResponse]
)
async def obtener_por_empresa(id_empresa: str):
    return await service.obtener_por_empresa(id_empresa)


@router.get(
    "/estado/{estado}",
    response_model=List[ProveedorResponse]
)
async def obtener_por_estado(
    estado: EstadoProveedor
):
    return await service.obtener_por_estado(
        estado.value
    )


@router.get(
    "/{id_proveedor}",
    response_model=ProveedorResponse
)
async def obtener_por_id(id_proveedor: str):
    return await service.obtener_por_id(id_proveedor)


@router.put(
    "/{id_proveedor}",
    response_model=ProveedorResponse
)
async def actualizar(
    id_proveedor: str,
    data: ProveedorUpdate
):
    return await service.actualizar(
        id_proveedor,
        data
    )


@router.delete("/{id_proveedor}")
async def eliminar(id_proveedor: str):
    return await service.eliminar(id_proveedor)