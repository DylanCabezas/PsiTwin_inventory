from fastapi import (
    APIRouter,
    status
)

from app.dto.rack_dto import (
    RackCreate,
    RackUpdate,
    RackResponse
)

from app.services.rack_service import (
    RackService
)


router = APIRouter(
    prefix="/racks",
    tags=["Rack"]
)


service = RackService()


@router.post(
    "",
    response_model=RackResponse,
    status_code=status.HTTP_201_CREATED
)
async def crear_rack(
    data: RackCreate
):

    return await service.crear_rack(
        data
    )


@router.get(
    "",
    response_model=list[
        RackResponse
    ]
)
async def obtener_racks():

    return await service.obtener_racks()


@router.get(
    "/zona/{id_zona}",
    response_model=list[
        RackResponse
    ]
)
async def obtener_racks_zona(
    id_zona: str
):

    return await service.obtener_racks_zona(
        id_zona
    )


@router.get(
    "/{id_rack}",
    response_model=RackResponse
)
async def obtener_rack(
    id_rack: str
):

    return await service.obtener_rack(
        id_rack
    )


@router.put(
    "/{id_rack}",
    response_model=RackResponse
)
async def actualizar_rack(
    id_rack: str,
    data: RackUpdate
):

    return await service.actualizar_rack(
        id_rack,
        data
    )


@router.delete(
    "/{id_rack}"
)
async def eliminar_rack(
    id_rack: str
):

    return await service.eliminar_rack(
        id_rack
    )