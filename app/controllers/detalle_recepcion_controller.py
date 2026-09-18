from typing import List

from fastapi import APIRouter, status

from app.dto.detalle_recepcion_dto import (
    DetalleRecepcionCreate,
    DetalleRecepcionResponse
)

from app.services.detalle_recepcion_service import (
    DetalleRecepcionService
)


router = APIRouter(
    tags=["Detalles de Recepcion"]
)

service = DetalleRecepcionService()


@router.post(
    "/recepciones/{id_recepcion}/detalles",
    response_model=DetalleRecepcionResponse,
    status_code=status.HTTP_201_CREATED
)
async def crear(
    id_recepcion: str,
    data: DetalleRecepcionCreate
):
    return await service.crear(
        id_recepcion,
        data
    )


@router.get(
    "/recepciones/{id_recepcion}/detalles",
    response_model=List[DetalleRecepcionResponse]
)
async def obtener_por_recepcion(
    id_recepcion: str
):
    return await service.obtener_por_recepcion(
        id_recepcion
    )


@router.get(
    "/detalles-recepcion/{id_detalle}",
    response_model=DetalleRecepcionResponse
)
async def obtener_por_id(id_detalle: str):
    return await service.obtener_por_id(
        id_detalle
    )