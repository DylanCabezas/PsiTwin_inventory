from typing import List

from fastapi import (
    APIRouter,
    status
)

from app.dto.zona_dto import (
    ZonaCreate,
    ZonaUpdate,
    ZonaResponse
)

from app.services.zona_service import (
    ZonaService
)


router = APIRouter(
    prefix="/zonas",
    tags=[
        "Zonas"
    ]
)


# ============================================================
# CREAR
# ============================================================

@router.post(
    "",
    response_model=ZonaResponse,
    status_code=(
        status.HTTP_201_CREATED
    )
)
async def crear_zona(
    data: ZonaCreate
):

    return await (
        ZonaService.crear(
            data
        )
    )


# ============================================================
# OBTENER TODAS
# ============================================================

@router.get(
    "",
    response_model=List[
        ZonaResponse
    ]
)
async def obtener_zonas():

    return await (
        ZonaService.obtener_todas()
    )


# ============================================================
# OBTENER POR ALMACEN
#
# Debe ir antes de /{id_zona}
# ============================================================

@router.get(
    "/almacen/{id_almacen}",
    response_model=List[
        ZonaResponse
    ]
)
async def obtener_zonas_por_almacen(
    id_almacen: str
):

    return await (
        ZonaService.obtener_por_almacen(
            id_almacen
        )
    )


# ============================================================
# OBTENER POR ID
# ============================================================

@router.get(
    "/{id_zona}",
    response_model=ZonaResponse
)
async def obtener_zona(
    id_zona: str
):

    return await (
        ZonaService.obtener_por_id(
            id_zona
        )
    )


# ============================================================
# ACTUALIZAR
# ============================================================

@router.put(
    "/{id_zona}",
    response_model=ZonaResponse
)
async def actualizar_zona(
    id_zona: str,
    data: ZonaUpdate
):

    return await (
        ZonaService.actualizar(
            id_zona,
            data
        )
    )


# ============================================================
# ELIMINAR
# ============================================================

@router.delete(
    "/{id_zona}",
    status_code=(
        status.HTTP_200_OK
    )
)
async def eliminar_zona(
    id_zona: str
):

    return await (
        ZonaService.eliminar(
            id_zona
        )
    )