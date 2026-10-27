"""Real MongoDB isolated database + FastAPI/JWT; Google's external exchange is controlled.
These tests do NOT claim an interactive Google consent has occurred.
"""
import asyncio
import json
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4
from unittest.mock import AsyncMock

import httpx
import jwt
import pytest
from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from cryptography.hazmat.primitives.asymmetric import rsa
from app.config.settings import settings
from app.controllers import google_auth_controller as controller, empresa_controller
from app.database import mongodb
from app.services.google_auth_service import GoogleAuthService, CompanyDetails, digest
from app.services.empresa_service import hash_password

DETAILS = dict(nombre='Empresa de prueba', nombre_ceo='Carlos', ruc='20123456789', sector='Alimentos', telefono='987654321')
BINDING = 'b' * 64

@asynccontextmanager
async def isolated_database(monkeypatch):
    client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
    name = 'psitwin_test_google_' + uuid4().hex
    try:
        try: await client.admin.command('ping')
        except Exception: pytest.skip('MongoDB no disponible para prueba de integración')
        db = client[name]
        monkeypatch.setattr(mongodb, 'database', db)
        monkeypatch.setattr(controller, 'service', GoogleAuthService(lambda: db))
        monkeypatch.setattr(settings, 'google_client_id', 'synthetic-client')
        monkeypatch.setattr(settings, 'google_client_secret', 'synthetic-secret')
        monkeypatch.setattr(settings, 'email_enabled', False)
        yield db
    finally:
        if not name.startswith('psitwin_test_google_') or len(name) != len('psitwin_test_google_') + 32:
            raise AssertionError('Refusing to clean a non-test database')
        await client.drop_database(name)
        client.close()

def app():
    instance = FastAPI()
    instance.include_router(controller.router)
    instance.include_router(empresa_controller.router)
    return instance

def state(url): return parse_qs(urlsplit(url).query)['state'][0]


@pytest.mark.parametrize('google_first', [False, True])
def test_google_registration_enables_chosen_password_after_verified_identity(monkeypatch, google_first):
    async def run():
        async with isolated_database(monkeypatch) as db:
            monkeypatch.setattr(controller.service, 'identity', AsyncMock(return_value={'sub': 'password-google-sub', 'email': 'carlos@example.com'}))
            password = 'chosen-registration-password'
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app()), base_url='http://test') as client:
                initial = {'binding': BINDING} if google_first else {'binding': BINDING, 'company': DETAILS, 'registration_password': password}
                start = await client.post('/auth/google/start', json=initial)
                assert start.status_code == 200
                flow = await db.google_oauth_flows.find_one({'_id': digest(state(start.json()['authorization_url']))})
                assert password not in json.dumps(flow, default=str)
                assert await db.empresas.count_documents({}) == 0
                result = await client.post('/auth/google/complete', json={'binding': BINDING, 'state': state(start.json()['authorization_url']), 'code': 'controlled-code'})
                if google_first:
                    assert result.json()['registration_required']
                    result = await client.post('/auth/google/register', json={'binding': BINDING, 'company': DETAILS, 'registration_password': password, 'registration_ticket': result.json()['registration_ticket']})
                assert result.status_code == 200
                assert result.json()['empresa']['password_local_habilitada'] is True
                assert password not in result.text
                company = await db.empresas.find_one({'google_sub': 'password-google-sub'})
                assert company['correo_verificado'] and company['password'] != password
                assert controller.verify_password(password, company['password'])
                login = await client.post('/auth/login', json={'correo': 'carlos@example.com', 'password': password})
                assert login.status_code == 200
                assert (await client.post('/auth/login', json={'correo': 'carlos@example.com', 'password': 'incorrect-password'})).status_code == 401
                # Registering again must never replace the existing account's password.
                again = await client.post('/auth/google/start', json={**initial, 'company': DETAILS, 'registration_password': 'different-password'})
                confirmed = await client.post('/auth/google/complete', json={'binding': BINDING, 'state': state(again.json()['authorization_url']), 'code': 'controlled-code'})
                assert confirmed.status_code == 200
                assert controller.verify_password(password, (await db.empresas.find_one({'google_sub': 'password-google-sub'}))['password'])
    asyncio.run(run())


def test_missing_google_configuration_has_explicit_safe_error(monkeypatch):
    monkeypatch.setattr(settings, 'google_client_id', '')
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app()), base_url='http://test') as client:
            result = await client.post('/auth/google/start', json={'binding': BINDING})
            assert result.status_code == 503
            assert result.json()['detail']['code'] == 'GOOGLE_NOT_CONFIGURED'
    asyncio.run(run())

def test_google_registration_login_replay_and_legacy_password_session(monkeypatch):
    async def run():
        async with isolated_database(monkeypatch) as db:
            service = controller.service
            identity = AsyncMock(return_value={'sub': 'stable-google-sub', 'email': 'carlos@example.com'})
            monkeypatch.setattr(service, 'identity', identity)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app()), base_url='http://test') as client:
                start = await client.post('/auth/google/start', json={'binding': BINDING, 'company': DETAILS})
                assert start.status_code == 200
                query = parse_qs(urlsplit(start.json()['authorization_url']).query)
                assert query['code_challenge_method'] == ['S256'] and query['nonce'] and query['scope'] == ['openid email profile']
                payload = {'binding': BINDING, 'state': query['state'][0], 'code': 'controlled-code'}
                wrong = await client.post('/auth/google/complete', json={**payload, 'binding': 'x' * 64})
                assert wrong.status_code == 400
                result = await client.post('/auth/google/complete', json=payload)
                assert result.status_code == 200
                session = result.json(); token = session['access_token']
                assert session['empresa']['nombre_ceo'] == 'Carlos' and session['empresa']['correo_verificado']
                assert 'google_sub' not in session['empresa'] and 'password' not in session['empresa']
                headers = {'Authorization': 'Bearer ' + token}
                for endpoint in ('/auth/me', '/empresas/me'):
                    assert (await client.get(endpoint, headers=headers)).status_code == 200
                assert (await client.get('/auth/me')).status_code in (401, 403)
                assert (await client.post('/auth/google/complete', json=payload)).status_code == 400
                assert await db.empresas.count_documents({}) == 1
                assert await db.bienvenidas_email.count_documents({}) == 1
                # A fresh OAuth login with a different email is linked by stable sub.
                identity.return_value = {'sub': 'stable-google-sub', 'email': 'new-name@example.com'}
                start2 = await client.post('/auth/google/start', json={'binding': BINDING})
                login = await client.post('/auth/google/complete', json={**payload, 'state': state(start2.json()['authorization_url'])})
                assert login.status_code == 200 and login.json()['empresa']['id_empresa'] == session['empresa']['id_empresa']
                assert await db.empresas.count_documents({}) == 1
                # Legacy credentials remain valid after the Mongo datetime update.
                await db.empresas.update_one({'id_empresa': session['empresa']['id_empresa']}, {'$set': {
                    'password': hash_password('legacy-test-password'), 'fecha_verificacion_correo': datetime.now(timezone.utc)}})
                legacy = await client.post('/auth/login', json={'correo': 'carlos@example.com', 'password': 'legacy-test-password'})
                assert legacy.status_code == 200
                assert (await client.get('/auth/me', headers={'Authorization': 'Bearer ' + legacy.json()['access_token']})).status_code == 200
                # Sensitive setup requires Google proof from the already linked subject.
                setup = await client.post('/auth/google/password/start', json={'binding': BINDING, 'new_password': 'configured-local-password'}, headers=headers)
                assert setup.status_code == 200
                confirmed = await client.post('/auth/google/complete', json={**payload, 'state': state(setup.json()['authorization_url'])})
                assert confirmed.status_code == 200 and confirmed.json()['empresa']['password_local_habilitada'] is True
                enabled = await client.post('/auth/login', json={'correo': 'carlos@example.com', 'password': 'configured-local-password'})
                assert enabled.status_code == 200
    asyncio.run(run())

def test_google_unlinked_registration_and_secure_link_no_email_takeover(monkeypatch):
    async def run():
        async with isolated_database(monkeypatch) as db:
            service = controller.service
            monkeypatch.setattr(service, 'identity', AsyncMock(return_value={'sub': 'new-sub', 'email': 'new@example.com'}))
            start = await service.start(BINDING)
            required = await service.complete(state(start['authorization_url']), 'code', BINDING)
            assert required['registration_required']
            result = await service.finish_registration(required['registration_ticket'], BINDING, CompanyDetails(**DETAILS))
            assert result['empresa']['correo'] == 'new@example.com'
            with pytest.raises(HTTPException):
                await service.finish_registration(required['registration_ticket'], BINDING, CompanyDetails(**DETAILS))
            await db.empresas.update_one({'id_empresa': result['empresa']['id_empresa']}, {'$unset': {'google_sub': ''}, '$set': {'password': hash_password('old-account-pass')}})
            start = await service.start(BINDING, CompanyDetails(**DETAILS))
            with pytest.raises(HTTPException) as error:
                await service.complete(state(start['authorization_url']), 'code', BINDING)
            assert error.value.status_code == 409
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app()), base_url='http://test') as client:
                headers = {'Authorization': 'Bearer ' + result['access_token']}
                assert (await client.post('/auth/google/link', json={'binding': BINDING, 'password': 'wrong'}, headers=headers)).status_code == 400
                link = await client.post('/auth/google/link', json={'binding': BINDING, 'password': 'old-account-pass'}, headers=headers)
                assert link.status_code == 200
                linked = await client.post('/auth/google/complete', json={'binding': BINDING, 'state': state(link.json()['authorization_url']), 'code': 'code'})
                assert linked.status_code == 200
                assert await db.empresas.count_documents({}) == 1
    asyncio.run(run())

def test_expired_and_concurrent_callbacks_never_create_duplicates(monkeypatch):
    async def run():
        async with isolated_database(monkeypatch) as db:
            service = controller.service
            monkeypatch.setattr(service, 'identity', AsyncMock(return_value={'sub': 'race-sub', 'email': 'race@example.com'}))
            start = await service.start(BINDING, CompanyDetails(**DETAILS))
            current = state(start['authorization_url'])
            await db.google_oauth_flows.update_one({'_id': digest(current)}, {'$set': {'expires_at': datetime.now(timezone.utc) - timedelta(minutes=1)}})
            with pytest.raises(HTTPException): await service.complete(current, 'code', BINDING)
            assert await db.empresas.count_documents({}) == 0
            start = await service.start(BINDING, CompanyDetails(**DETAILS))
            current = state(start['authorization_url'])
            results = await asyncio.gather(service.complete(current, 'code', BINDING), service.complete(current, 'code', BINDING), return_exceptions=True)
            assert sum(isinstance(result, dict) and 'access_token' in result for result in results) == 1
            assert await db.empresas.count_documents({}) == 1
            assert await db.bienvenidas_email.count_documents({}) == 1
    asyncio.run(run())

@pytest.mark.parametrize('invalid', [None, 'signature', 'audience', 'issuer', 'expired', 'nonce', 'unverified', 'azp'])
def test_real_signature_and_oidc_claim_validation(monkeypatch, invalid):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key())); public['kid'] = 'test-key'
    now = datetime.now(timezone.utc)
    claims = {'iss': 'https://accounts.google.com', 'aud': 'client', 'sub': 'subject', 'email': 'carlos@example.com',
        'email_verified': True, 'iat': now, 'exp': now + timedelta(minutes=5), 'nonce': 'nonce'}
    if invalid == 'audience': claims['aud'] = 'attacker'
    if invalid == 'issuer': claims['iss'] = 'https://attacker.example'
    if invalid == 'expired': claims['exp'] = now - timedelta(minutes=1)
    if invalid == 'nonce': claims['nonce'] = 'wrong'
    if invalid == 'unverified': claims['email_verified'] = False
    if invalid == 'azp': claims['azp'] = 'attacker'
    token = jwt.encode(claims, other if invalid == 'signature' else private, algorithm='RS256', headers={'kid': 'test-key'})
    original = httpx.AsyncClient
    def handler(request):
        return httpx.Response(200, json={'id_token': token} if request.url.path == '/token' else {'keys': [public]})
    monkeypatch.setattr('app.services.google_auth_service.httpx.AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(settings, 'google_client_id', 'client')
    call = GoogleAuthService().identity('code', {'nonce': 'nonce', 'verifier': 'v' * 43})
    if invalid:
        with pytest.raises(HTTPException) as error: asyncio.run(call)
        assert error.value.status_code == 401
    else:
        assert asyncio.run(call) == {'sub': 'subject', 'email': 'carlos@example.com'}
