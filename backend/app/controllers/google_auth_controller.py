from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from app.dependencies.dependencies import require_empresa
from app.dto.auth_dto import UsuarioActual
from app.services.google_auth_service import GoogleAuthService, CompanyDetails, verify_password
from app.services.welcome_email_service import WelcomeEmailService
import asyncio
from app.services.empresa_service import hash_password

router = APIRouter(prefix='/auth/google', tags=['Google OIDC'])
service = GoogleAuthService()

class StartRequest(BaseModel):
    binding: str = Field(min_length=40, max_length=128)
    company: CompanyDetails | None = None
    registration_password: str | None = Field(default=None, min_length=6, max_length=128, repr=False)

class CompleteRequest(BaseModel):
    binding: str = Field(min_length=40, max_length=128)
    state: str = Field(min_length=20, max_length=256)
    code: str = Field(min_length=1, max_length=4096)

class FinishRequest(StartRequest):
    registration_ticket: str = Field(min_length=20, max_length=256)
    company: CompanyDetails

class LinkRequest(StartRequest):
    password: str = Field(min_length=1, max_length=128)

class PasswordSetupRequest(StartRequest):
    new_password: str = Field(min_length=6, max_length=128)

@router.post('/password/start')
async def password_setup(data: PasswordSetupRequest, user: UsuarioActual = Depends(require_empresa)):
    company = await service.database()['empresas'].find_one({'id_empresa': user.id_empresa})
    if not company or not company.get('google_sub'):
        raise HTTPException(400, 'Primero vincula Google a tu cuenta.')
    hashed = await asyncio.to_thread(hash_password, data.new_password)
    return await service.start(data.binding, link_company=user.id_empresa, password_hash=hashed)

@router.post('/start')
async def start(data: StartRequest):
    if data.registration_password is not None and data.company is None:
        raise HTTPException(422, 'Completa los datos de la empresa para crear una contraseña.')
    hashed = await asyncio.to_thread(hash_password, data.registration_password) if data.registration_password is not None else None
    return await service.start(data.binding, data.company, password_hash=hashed)

@router.post('/link')
async def link(data: LinkRequest, user: UsuarioActual = Depends(require_empresa)):
    company = await service.database()['empresas'].find_one({'id_empresa': user.id_empresa})
    if not company or not verify_password(data.password, company.get('password', '')):
        raise HTTPException(400, 'Contraseña actual incorrecta')
    return await service.start(data.binding, link_company=user.id_empresa)

async def deliver(result):
    if result.get('empresa'):
        welcome = WelcomeEmailService(service.database)
        company = result['empresa']
        # Existing accounts do not acquire a new welcome on every login.
        if (await welcome.status(company['id_empresa']))['status'] != 'NO_SOLICITADO':
            await welcome.deliver_safely(company['id_empresa'])

@router.post('/complete')
async def complete(data: CompleteRequest, background_tasks: BackgroundTasks):
    result = await service.complete(data.state, data.code, data.binding)
    background_tasks.add_task(deliver, result)
    return result

@router.post('/register')
async def register(data: FinishRequest, background_tasks: BackgroundTasks):
    hashed = await asyncio.to_thread(hash_password, data.registration_password) if data.registration_password is not None else None
    result = await service.finish_registration(data.registration_ticket, data.binding, data.company, password_hash=hashed)
    background_tasks.add_task(deliver, result)
    return result
