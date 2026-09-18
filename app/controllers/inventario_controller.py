from fastapi import (
    APIRouter,
    status
)

from app.dto.inventario_dto import (
    InventarioCreate,
    InventarioUpdate,
    InventarioResponse
)

from app.services.inventario_service import (
    InventarioService
)


router = APIRouter(
    prefix="/inventarios",
    tags=["Inventario"]
)


service = InventarioService()


# =============================================================
# CREAR INVENTARIO
# =============================================================

@router.post(
    "",
    response_model=InventarioResponse,
    status_code=status.HTTP_201_CREATED
)
async def crear_inventario(
    data: InventarioCreate
):

    return await service.crear_inventario(
        data
    )


# =============================================================
# OBTENER TODO
# =============================================================

@router.get(
    "",
    response_model=list[
        InventarioResponse
    ]
)
async def obtener_inventarios():

    return await (
        service.obtener_inventarios()
    )


# =============================================================
# STOCK BAJO
# =============================================================

@router.get(
    "/stock-bajo",
    response_model=list[
        InventarioResponse
    ]
)
async def obtener_stock_bajo():

    return await (
        service.obtener_stock_bajo()
    )


# =============================================================
# SIN STOCK
# =============================================================

@router.get(
    "/sin-stock",
    response_model=list[
        InventarioResponse
    ]
)
async def obtener_sin_stock():

    return await (
        service.obtener_sin_stock()
    )


# =============================================================
# SOBRE STOCK
# =============================================================

@router.get(
    "/sobre-stock",
    response_model=list[
        InventarioResponse
    ]
)
async def obtener_sobre_stock():

    return await (
        service.obtener_sobre_stock()
    )


# =============================================================
# POR PRODUCTO
# =============================================================

@router.get(
    "/producto/{id_producto}",
    response_model=list[
        InventarioResponse
    ]
)
async def obtener_inventario_producto(
    id_producto: str
):

    return await (
        service.obtener_por_producto(
            id_producto
        )
    )


# =============================================================
# POR RACK
# =============================================================

@router.get(
    "/rack/{id_rack}",
    response_model=list[
        InventarioResponse
    ]
)
async def obtener_inventario_rack(
    id_rack: str
):

    return await (
        service.obtener_por_rack(
            id_rack
        )
    )


# =============================================================
# POR ID
# =============================================================

@router.get(
    "/{id_inventario}",
    response_model=InventarioResponse
)
async def obtener_inventario(
    id_inventario: str
):

    return await (
        service.obtener_inventario(
            id_inventario
        )
    )


# =============================================================
# ACTUALIZAR
# =============================================================

@router.put(
    "/{id_inventario}",
    response_model=InventarioResponse
)
async def actualizar_inventario(
    id_inventario: str,
    data: InventarioUpdate
):

    return await (
        service.actualizar_inventario(
            id_inventario,
            data
        )
    )


# =============================================================
# ELIMINAR
# =============================================================

@router.delete(
    "/{id_inventario}",
    status_code=status.HTTP_200_OK
)
async def eliminar_inventario(
    id_inventario: str
):

    return await (
        service.eliminar_inventario(
            id_inventario
        )
    )