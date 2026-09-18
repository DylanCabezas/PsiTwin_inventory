from typing import List

from fastapi import APIRouter, status

from app.dto.recepcion_mercaderia_dto import (
    RecepcionMercaderiaCreate,
    RecepcionMercaderiaResponse
)

from app.services.recepcion_mercaderia_service import (
    RecepcionMercaderiaService
)


router = APIRouter(
    prefix="/recepciones",
    tags=["Recepciones de Mercaderia"]
)

service = RecepcionMercaderiaService()


@router.post(
    "",
    response_model=RecepcionMercaderiaResponse,
    status_code=status.HTTP_201_CREATED
)
async def crear(data: RecepcionMercaderiaCreate):
    return await service.crear(data)


@router.get(
    "",
    response_model=List[RecepcionMercaderiaResponse]
)
async def obtener_todos():
    return await service.obtener_todos()


@router.get(
    "/orden/{id_orden}",
    response_model=List[RecepcionMercaderiaResponse]
)
async def obtener_por_orden(id_orden: str):
    return await service.obtener_por_orden(id_orden)


@router.get(
    "/operario/{id_operario}",
    response_model=List[RecepcionMercaderiaResponse]
)
async def obtener_por_operario(id_operario: str):
    return await service.obtener_por_operario(
        id_operario
    )


@router.get(
    "/{id_recepcion}",
    response_model=RecepcionMercaderiaResponse
)
async def obtener_por_id(id_recepcion: str):
    return await service.obtener_por_id(id_recepcion)