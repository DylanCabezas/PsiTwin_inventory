from fastapi import (
    APIRouter,
    status
)

from app.dto.operario_dto import (
    OperarioCreate,
    OperarioUpdate,
    OperarioResponse
)
from app.dto.email_verification_dto import (
    EmailVerificationCodeRequest,
    EmailVerificationResponse,
    EmailVerificationSendResponse,
)

from app.services.operario_service import (
    OperarioService
)
from app.services.email_verification_service import EmailVerificationService


router = APIRouter(
    prefix="/operarios",
    tags=["Operarios"]
)


service = OperarioService()
email_verification_service = EmailVerificationService()


# ============================================================
# CREAR OPERARIO
# ============================================================

@router.post(
    "",
    response_model=OperarioResponse,
    status_code=
        status.HTTP_201_CREATED
)
async def crear_operario(
    data: OperarioCreate
):

    return await (
        service.crear_operario(
            data
        )
    )


# ============================================================
# OBTENER TODOS
# ============================================================

@router.get(
    "",
    response_model=
        list[OperarioResponse]
)
async def obtener_operarios():

    return await (
        service.obtener_operarios()
    )


# ============================================================
# POR EMPRESA
# ============================================================

@router.get(
    "/empresa/{id_empresa}",
    response_model=
        list[OperarioResponse]
)
async def obtener_por_empresa(
    id_empresa: str
):

    return await (
        service.obtener_por_empresa(
            id_empresa
        )
    )


# ============================================================
# POR ESTADO
# ============================================================

@router.get(
    "/estado/{estado}",
    response_model=
        list[OperarioResponse]
)
async def obtener_por_estado(
    estado: str
):

    return await (
        service.obtener_por_estado(
            estado
        )
    )


# ============================================================
# POR TURNO
# ============================================================

@router.get(
    "/turno/{turno}",
    response_model=
        list[OperarioResponse]
)
async def obtener_por_turno(
    turno: str
):

    return await (
        service.obtener_por_turno(
            turno
        )
    )


# ============================================================
# POR ID
# ============================================================

@router.get(
    "/{id_operario}",
    response_model=
        OperarioResponse
)
async def obtener_operario(
    id_operario: str
):

    return await (
        service.obtener_operario(
            id_operario
        )
    )


# ============================================================
# ACTUALIZAR
# ============================================================

@router.put(
    "/{id_operario}",
    response_model=
        OperarioResponse
)
async def actualizar_operario(
    id_operario: str,
    data: OperarioUpdate
):

    return await (
        service.actualizar_operario(
            id_operario,
            data
        )
    )


@router.post(
    "/{id_operario}/correo/enviar-verificacion",
    response_model=EmailVerificationSendResponse,
    summary="Enviar verificación de correo de operario",
)
async def send_operario_email_verification(id_operario: str):
    return await email_verification_service.request_entity_verification(
        "operario",
        id_operario,
    )


@router.post(
    "/{id_operario}/correo/verificar",
    response_model=EmailVerificationResponse,
    summary="Verificar correo de operario",
)
async def verify_operario_email(
    id_operario: str,
    data: EmailVerificationCodeRequest,
):
    return await email_verification_service.verify_entity_code(
        "operario",
        id_operario,
        data.codigo,
    )


# ============================================================
# ELIMINAR
# ============================================================

@router.delete(
    "/{id_operario}",
    status_code=
        status.HTTP_200_OK
)
async def eliminar_operario(
    id_operario: str
):

    return await (
        service.eliminar_operario(
            id_operario
        )
    )