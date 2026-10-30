"""Read-only regression against the explicitly imported local test tenant."""
import asyncio
import json
from pathlib import Path
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from app.database import mongodb
from app.dto.auth_dto import UsuarioActual
from app.dto.saiki_dto import SaikiAskRequest
from app.services.saiki_catalog_queries import catalog_answer,resolve_forecast_product

OUT=Path(__file__).resolve().parents[2]/'outputs/psitwin_pruebas'

def run(fn):
    async def execute():
        client=AsyncIOMotorClient('mongodb://127.0.0.1:27017',serverSelectionTimeoutMS=2000)
        previous=mongodb.database;mongodb.database=client['psitwin_synthetic30_test']
        try:
            info=json.loads((OUT/'importacion.json').read_text(encoding='utf-8'))
            return await fn(info,UsuarioActual(rol='EMPRESA',id_empresa=info['empresa']))
        finally:mongodb.database=previous;client.close()
    return asyncio.run(execute())

@pytest.mark.parametrize('q',['¿Cuántos helados tengo?','¿Cuáles son los cuatro helados?','¿Dónde están almacenados los helados?'])
def test_family_stock_locations(q):
    async def check(info,user):
        answer,evidence=await catalog_answer(SaikiAskRequest(message=q,id_almacen=info['almacen']),user)
        assert len(evidence['productos_familia'])==4
        assert evidence['existencias_por_unidad']=={'unidad':417}
        assert all(r['rack']=='C1' for r in evidence['ubicaciones'])
        assert 'vainilla' in answer and 'chocolate' in answer and 'lúcuma' in answer and 'fresa' in answer
    run(check)
def test_family_evolution():
    async def check(info,user):
        answer,evidence=await catalog_answer(SaikiAskRequest(message='¿Cómo evolucionó la demanda de helados?',id_almacen=info['almacen']),user)
        assert len(evidence['demanda_mensual'])==14
        assert all(r['unidad']=='unidad' for r in evidence['demanda_mensual'])
        assert 'Manzana' not in answer
    run(check)
@pytest.mark.parametrize('q',['¿Qué producto tuvo mayor demanda en enero de 2026?','¿Qué producto tuvo mayor demanda en enero?'])
def test_january_ranking_by_unit(q):
    async def check(info,user):
        answer,evidence=await catalog_answer(SaikiAskRequest(message=q,id_almacen=info['almacen']),user)
        assert evidence['filtros']['fecha']=={'$gte':'2026-01-01','$lte':'2026-01-31'}
        assert 'en kg' in answer and 'en unidad' in answer
    run(check)
def test_no_registered_sensors():
    async def check(info,user):
        answer,evidence=await catalog_answer(SaikiAskRequest(message='¿Hay sensores registrados?'),user)
        assert evidence['dispositivos_registrados']==0 and 'No hay dispositivos' in answer
    run(check)
def test_forecast_name_resolution():
    async def check(info,user):
        request=SaikiAskRequest(message='¿Cuál es el pronóstico de papaya?')
        await resolve_forecast_product(request,user)
        assert request.id_producto==info['mapeo_productos']['SYN-001']
        assert request.id_almacen==info['almacen']
    run(check)
def test_other_tenant_cannot_see_family():
    async def check(info,user):
        result=await catalog_answer(SaikiAskRequest(message='¿Cuántos helados tengo?'),UsuarioActual(rol='EMPRESA',id_empresa='unrelated-test-tenant'))
        assert result is None
    run(check)

def test_operational_forecast_and_replenishment():
    async def check(info,user):
        from app.services.forecast_service import ForecastService
        from app.services.inventory_risk_service import InventoryRiskService
        from app.services.autogluon_runtime import runtime
        try:
            pid=info['mapeo_productos']['SYN-001']
            forecast=await ForecastService().predecir(info['almacen'],pid,7)
            assert str(forecast.fecha_corte)=='2026-10-28'
            assert str(forecast.fecha_inicio)=='2026-10-29'
            assert forecast.predicciones_diarias[0].fecha==forecast.fecha_inicio
            history=await ForecastService().historial(info['almacen'],pid,forecast.fecha_corte,28)
            assert len(history)==28 and history.iloc[-1]['fecha']=='2026-10-28'
            header=await mongodb.get_database().inventarios.find_one({'id_almacen':info['almacen']})
            result=await InventoryRiskService().evaluar(header['id_inventario'],generar_alertas=False,id_producto=pid)
            assert result.stock_actual==0
            assert 0<=result.reposicion.cantidad_minima<=result.reposicion.cantidad_recomendada<=result.reposicion.cantidad_segura<=81
        finally:runtime.close()
    run(check)
