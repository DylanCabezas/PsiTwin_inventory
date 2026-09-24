from typing import List

from fastapi import (
    APIRouter,
    Query
)

from app.dto.inventory_risk_dto import (
    InventoryRiskResponse
)

from app.services.inventory_risk_service import (
    InventoryRiskService
)


router = APIRouter(
    prefix="/inventory-risk",
    tags=["Inventory Intelligence"]
)

service = InventoryRiskService()


@router.get(
    "",
    response_model=List[
        InventoryRiskResponse
    ],
    summary=(
        "Evaluar riesgo de todos "
        "los inventarios"
    )
)
async def evaluar_todos(

    generar_alertas: bool = Query(
        default=False,
        description=(
            "Si es true, crea o actualiza "
            "alertas y recomendaciones "
            "para inventarios con riesgo "
            "alto o crítico."
        )
    )
):

    return await service.evaluar_todos(
        generar_alertas=
            generar_alertas
    )


@router.get(
    "/{id_inventario}",
    response_model=InventoryRiskResponse,
    summary=(
        "Evaluar riesgo de un inventario"
    )
)
async def evaluar_inventario(

    id_inventario: str,

    generar_alertas: bool = Query(
        default=True,
        description=(
            "Si es true, crea o actualiza "
            "automáticamente la alerta y "
            "la recomendación cuando existe "
            "riesgo alto o crítico."
        )
    )
):

    return await service.evaluar(
        id_inventario=
            id_inventario,

        generar_alertas=
            generar_alertas
    )