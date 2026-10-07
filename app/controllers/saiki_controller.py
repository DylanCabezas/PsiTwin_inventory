from fastapi import APIRouter, Depends

from app.dependencies.dependencies import require_empresa
from app.dto.auth_dto import UsuarioActual
from app.dto.saiki_dto import SaikiAskRequest, SaikiAskResponse
from app.services.saiki_service import SaikiService


router = APIRouter(
    prefix="/saiki",
    tags=["Saiki"],
    dependencies=[Depends(require_empresa)],
)
service = SaikiService()


@router.get("/health", summary="Comprobar disponibilidad de Ollama y Saiki")
async def health():
    return await service.health()


@router.post(
    "/ask",
    response_model=SaikiAskResponse,
    summary="Resolver una consulta operacional con datos de PsiTwin",
)
async def ask(
    data: SaikiAskRequest,
    user: UsuarioActual = Depends(require_empresa),
):
    return await service.ask(data, user)


@router.post(
    "/chat",
    response_model=SaikiAskResponse,
    summary="Alias de consulta operacional de Saiki",
)
async def chat(
    data: SaikiAskRequest,
    user: UsuarioActual = Depends(require_empresa),
):
    return await service.ask(data, user)
