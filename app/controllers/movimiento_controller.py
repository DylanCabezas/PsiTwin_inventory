from typing import List

from fastapi import APIRouter, status

from app.dto.movimiento_dto import (
    MovimientoCreate,
    MovimientoResponse,
    TipoMovimiento,
    MotivoMovimiento
)

from app.services.movimiento_service import (
    MovimientoService
)


router = APIRouter(
    prefix="/movimientos",
    tags=["Movimientos"]
)

service = MovimientoService()


# ============================================================
# CREAR
# ============================================================

@router.post(
    "",
    response_model=MovimientoResponse,
    status_code=status.HTTP_201_CREATED
)
async def crear_movimiento(
    data: MovimientoCreate
):

    return await service.crear_movimiento(
        data
    )


# ============================================================
# OBTENER TODOS
# ============================================================

@router.get(
    "",
    response_model=List[MovimientoResponse]
)
async def obtener_movimientos():

    return await service.obtener_movimientos()


# ============================================================
# POR INVENTARIO
# ============================================================

@router.get(
    "/inventario/{id_inventario}",
    response_model=List[MovimientoResponse]
)
async def obtener_por_inventario(
    id_inventario: str
):

    return await service.obtener_por_inventario(
        id_inventario
    )


# ============================================================
# POR PRODUCTO
# ============================================================

@router.get(
    "/producto/{id_producto}",
    response_model=List[MovimientoResponse]
)
async def obtener_por_producto(
    id_producto: str
):

    return await service.obtener_por_producto(
        id_producto
    )


# ============================================================
# POR RACK
# ============================================================

@router.get(
    "/rack/{id_rack}",
    response_model=List[MovimientoResponse]
)
async def obtener_por_rack(
    id_rack: str
):

    return await service.obtener_por_rack(
        id_rack
    )


# ============================================================
# POR OPERARIO
# ============================================================

@router.get(
    "/operario/{id_operario}",
    response_model=List[MovimientoResponse]
)
async def obtener_por_operario(
    id_operario: str
):

    return await service.obtener_por_operario(
        id_operario
    )


# ============================================================
# POR TIPO
# ============================================================

@router.get(
    "/tipo/{tipo_movimiento}",
    response_model=List[MovimientoResponse]
)
async def obtener_por_tipo(
    tipo_movimiento: TipoMovimiento
):

    return await service.obtener_por_tipo(
        tipo_movimiento
    )


# ============================================================
# POR MOTIVO
# ============================================================

@router.get(
    "/motivo/{motivo_movimiento}",
    response_model=List[MovimientoResponse]
)
async def obtener_por_motivo(
    motivo_movimiento: MotivoMovimiento
):

    return await service.obtener_por_motivo(
        motivo_movimiento
    )


# ============================================================
# POR ID
# IMPORTANTE: ESTA RUTA VA AL FINAL
# ============================================================

@router.get(
    "/{id_movimiento}",
    response_model=MovimientoResponse
)
async def obtener_movimiento(
    id_movimiento: str
):

    return await service.obtener_movimiento(
        id_movimiento
    )