from typing import List

from fastapi import (
    APIRouter,
    status
)

from app.dto.almacen_dto import (
    AlmacenCreate,
    AlmacenUpdate,
    AlmacenResponse
)

from app.services.almacen_service import (
    AlmacenService
)


router = APIRouter(
    prefix="/almacenes",
    tags=[
        "Almacenes"
    ]
)


# ============================================================
# CREAR
#
# POST /api/v1/almacenes
# ============================================================

@router.post(
    "",
    response_model=AlmacenResponse,
    status_code=(
        status.HTTP_201_CREATED
    ),
    summary="Crear almacén"
)
async def crear_almacen(
    data: AlmacenCreate
):

    return await (
        AlmacenService.crear(
            data
        )
    )


# ============================================================
# OBTENER TODOS
#
# GET /api/v1/almacenes
# ============================================================

@router.get(
    "",
    response_model=List[
        AlmacenResponse
    ],
    status_code=(
        status.HTTP_200_OK
    ),
    summary="Obtener almacenes"
)
async def obtener_almacenes():

    return await (
        AlmacenService.obtener_todos()
    )


# ============================================================
# OBTENER POR EMPRESA
#
# IMPORTANTE:
# Esta ruta debe ir ANTES de /{id_almacen}
#
# GET /api/v1/almacenes/empresa/{id_empresa}
# ============================================================

@router.get(
    "/empresa/{id_empresa}",
    response_model=List[
        AlmacenResponse
    ],
    status_code=(
        status.HTTP_200_OK
    ),
    summary=(
        "Obtener almacenes por empresa"
    )
)
async def obtener_almacenes_por_empresa(
    id_empresa: str
):

    return await (
        AlmacenService
        .obtener_por_empresa(
            id_empresa
        )
    )


# ============================================================
# OBTENER POR ID
#
# GET /api/v1/almacenes/{id_almacen}
# ============================================================

@router.get(
    "/{id_almacen}",
    response_model=AlmacenResponse,
    status_code=(
        status.HTTP_200_OK
    ),
    summary="Obtener almacén por ID"
)
async def obtener_almacen(
    id_almacen: str
):

    return await (
        AlmacenService.obtener_por_id(
            id_almacen
        )
    )


# ============================================================
# ACTUALIZAR
#
# PUT /api/v1/almacenes/{id_almacen}
# ============================================================

@router.put(
    "/{id_almacen}",
    response_model=AlmacenResponse,
    status_code=(
        status.HTTP_200_OK
    ),
    summary="Actualizar almacén"
)
async def actualizar_almacen(
    id_almacen: str,
    data: AlmacenUpdate
):

    return await (
        AlmacenService.actualizar(
            id_almacen,
            data
        )
    )


# ============================================================
# ELIMINAR
#
# DELETE /api/v1/almacenes/{id_almacen}
# ============================================================

@router.delete(
    "/{id_almacen}",
    status_code=(
        status.HTTP_200_OK
    ),
    summary="Eliminar almacén"
)
async def eliminar_almacen(
    id_almacen: str
):

    return await (
        AlmacenService.eliminar(
            id_almacen
        )
    )