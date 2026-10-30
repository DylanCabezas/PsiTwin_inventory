"""Explicit localhost-only integration server; actual routers and isolated MongoDB.

No production startup hooks, IoT, mail or background jobs. A test identity replaces
login only; business permissions continue through the existing dependencies.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from app.database import mongodb
from app.dto.auth_dto import UsuarioActual
from app.dependencies.dependencies import require_empresa,require_empresa_u_operario
from app.controllers import analisis_controller,inventario_consulta_controller,saiki_controller,almacen_controller,zona_controller,rack_controller,producto_controller

if os.getenv('PSITWIN_SYNTHETIC30_BROWSER')!='1':raise RuntimeError('Solo ejecución explícita de pruebas')
TENANT='psitwin-synthetic-30-v1'
@asynccontextmanager
async def lifespan(app):
    client=AsyncIOMotorClient('mongodb://127.0.0.1:27017');mongodb.database=client['psitwin_synthetic30_test']
    yield
    client.close()
app=FastAPI(lifespan=lifespan)
async def identity():return UsuarioActual(rol='EMPRESA',id_empresa=TENANT)
app.dependency_overrides[require_empresa]=identity
app.dependency_overrides[require_empresa_u_operario]=identity
for module in (analisis_controller,inventario_consulta_controller,saiki_controller,almacen_controller,zona_controller,rack_controller,producto_controller):app.include_router(module.router,prefix='/api/v1')
@app.get('/__test/status')
async def status():
    db=mongodb.get_database()
    w=await db.almacenes.find_one({'id_empresa':TENANT},{'_id':0})
    products=await db.productos.find({'id_empresa':TENANT},{'_id':0}).to_list(length=None)
    return {'empresa':TENANT,'almacen':w,'productos':products}
@app.get('/api/v1/empresas/me')
async def me():
    row=await mongodb.get_database().empresas.find_one({'id_empresa':TENANT},{'_id':0})
    return row or {}
@app.get('/api/v1/auth/me')
async def session():return {'rol':'EMPRESA','empresa':await me()}
