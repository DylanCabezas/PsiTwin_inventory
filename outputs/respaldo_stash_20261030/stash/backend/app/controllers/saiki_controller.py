from fastapi import APIRouter

from app.dto.saiki_dto import SaikiAskRequest, SaikiAskResponse
from app.services.saiki_service import SaikiService


router = APIRouter(
    prefix="/saiki",
    tags=["Saiki"]
)

service = SaikiService()


@router.get(
    "/health",
    summary="Comprobar disponibilidad de Ollama y Saiki"
)
async def health():
    return await service.health()


@router.get(
    "/system-prompt",
    summary="Obtener el prompt del sistema de Saiki"
)
async def system_prompt():
    return {
        "system_prompt": service.get_system_prompt()
    }


@router.post(
    "/ask",
    response_model=SaikiAskResponse,
    summary="Resolver una consulta operativa con datos reales de PsiTwin"
)
async def ask(request: SaikiAskRequest):
    return await service.ask(request)


@router.post(
    "/chat",
    response_model=SaikiAskResponse,
    summary="Alias para chat operativo de Saiki"
)
async def chat(request: SaikiAskRequest):
    return await service.ask(request)
