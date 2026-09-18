from typing import List

from fastapi import (
    APIRouter,
    status
)

from app.dto.producto_dto import (
    ProductoCreate,
    ProductoUpdate,
    ProductoResponse
)

from app.services.producto_service import (
    ProductoService
)


router = APIRouter(
    prefix="/productos",
    tags=[
        "Productos"
    ]
)


# ============================================================
# CREAR
# ============================================================

@router.post(
    "",
    response_model=ProductoResponse,
    status_code=(
        status.HTTP_201_CREATED
    ),
    summary="Crear producto"
)
async def crear_producto(
    data: ProductoCreate
):

    return await (
        ProductoService.crear(
            data
        )
    )


# ============================================================
# OBTENER TODOS
# ============================================================

@router.get(
    "",
    response_model=List[
        ProductoResponse
    ],
    summary="Obtener productos"
)
async def obtener_productos():

    return await (
        ProductoService
        .obtener_todos()
    )


# ============================================================
# REFRIGERADOS
#
# IMPORTANTE:
# antes de /{id_producto}
# ============================================================

@router.get(
    "/refrigerados",
    response_model=List[
        ProductoResponse
    ],
    summary=(
        "Obtener productos refrigerados"
    )
)
async def obtener_productos_refrigerados():

    return await (
        ProductoService
        .obtener_refrigerados()
    )


# ============================================================
# POR ALMACEN
# ============================================================

@router.get(
    "/almacen/{id_almacen}",
    response_model=List[
        ProductoResponse
    ],
    summary=(
        "Obtener productos por almacén"
    )
)
async def obtener_productos_por_almacen(
    id_almacen: str
):

    return await (
        ProductoService
        .obtener_por_almacen(
            id_almacen
        )
    )


# ============================================================
# POR RACK
# ============================================================

@router.get(
    "/rack/{id_rack}",
    response_model=List[
        ProductoResponse
    ],
    summary=(
        "Obtener productos por rack"
    )
)
async def obtener_productos_por_rack(
    id_rack: str
):

    return await (
        ProductoService
        .obtener_por_rack(
            id_rack
        )
    )


# ============================================================
# POR CATEGORIA
# ============================================================

@router.get(
    "/categoria/{categoria}",
    response_model=List[
        ProductoResponse
    ],
    summary=(
        "Obtener productos por categoría"
    )
)
async def obtener_productos_por_categoria(
    categoria: str
):

    return await (
        ProductoService
        .obtener_por_categoria(
            categoria
        )
    )


# ============================================================
# POR ID
#
# DEBE IR DESPUES DE LAS RUTAS ESPECIALES
# ============================================================

@router.get(
    "/{id_producto}",
    response_model=ProductoResponse,
    summary="Obtener producto por ID"
)
async def obtener_producto(
    id_producto: str
):

    return await (
        ProductoService
        .obtener_por_id(
            id_producto
        )
    )


# ============================================================
# ACTUALIZAR
# ============================================================

@router.put(
    "/{id_producto}",
    response_model=ProductoResponse,
    summary="Actualizar producto"
)
async def actualizar_producto(
    id_producto: str,
    data: ProductoUpdate
):

    return await (
        ProductoService.actualizar(
            id_producto,
            data
        )
    )


# ============================================================
# ELIMINAR
# ============================================================

@router.delete(
    "/{id_producto}",
    status_code=(
        status.HTTP_200_OK
    ),
    summary="Eliminar producto"
)
async def eliminar_producto(
    id_producto: str
):

    return await (
        ProductoService.eliminar(
            id_producto
        )
    )