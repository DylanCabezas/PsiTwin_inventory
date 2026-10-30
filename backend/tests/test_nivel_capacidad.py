import asyncio
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.dto.abastecimiento_dto import NivelRequest, NivelUpdate
from app.dto.rack_dto import RackCreate
from app.services.jerarquia_service import JerarquiaService
from app.services.nivel_service import NivelService, peso_entrada
from app.services.rack_service import RackService
from tests.test_google_auth import isolated_database
from tests.test_abastecimiento_integral import seed


def test_level_weight_uses_kg_or_unit_weight():
    assert peso_entrada({'unidad': 'kg', 'peso': 99}, 12.5) == 12.5
    assert peso_entrada({'unidad': 'unidad', 'peso': 2.5}, 4) == 10
    NivelService.validar_carga({'codigo': 'N1', 'capacidad_kg': 20, 'libre_kg': 10}, {'unidad': 'kg'}, 10)
    with pytest.raises(HTTPException) as error:
        NivelService.validar_carga({'codigo': 'N1', 'capacidad_kg': 20, 'libre_kg': 10}, {'unidad': 'kg'}, 10.001)
    assert 'nivel N1' in error.value.detail


@pytest.mark.parametrize('capacity', [0, -1, float('inf'), float('nan')])
def test_invalid_level_capacity(capacity):
    with pytest.raises(ValidationError):
        NivelRequest(codigo='N1', numero=1, capacidad_kg=capacity)


def test_rack_limits_manual_levels_and_each_level_has_its_own_weight(monkeypatch):
    async def run():
        async with isolated_database(monkeypatch) as db:
            _, _, company = await seed(db)
            rack = await RackService().crear_rack(RackCreate(id_zona='z', codigo='R2', tipo_rack='Selectivo', max_niveles=2))
            assert await JerarquiaService.niveles(company, rack['id_rack']) == []
            first = await JerarquiaService.crear_nivel(company, rack['id_rack'], NivelRequest(codigo='N1', numero=1, capacidad_kg=10))
            second = await JerarquiaService.crear_nivel(company, rack['id_rack'], NivelRequest(codigo='N2', numero=2, capacidad_kg=100))
            with pytest.raises(HTTPException):
                await JerarquiaService.crear_nivel(company, rack['id_rack'], NivelRequest(codigo='N3', numero=3, capacidad_kg=10))
            await db.detalles_inventario.insert_one({'id_detalle_inventario': 'weight', 'id_inventario': 'i', 'id_producto': 'p',
                'id_rack': rack['id_rack'], 'id_nivel': first['id_nivel'], 'stock_actual': 8})
            enriched = await JerarquiaService.niveles(company, rack['id_rack'])
            assert [(n['carga_kg'], n['libre_kg']) for n in enriched] == [(8, 2), (0, 100)]
            await RackService.validar_asignacion(rack, {'unidad': 'kg'}, 2, id_nivel=first['id_nivel'])
            with pytest.raises(HTTPException):
                await RackService.validar_asignacion(rack, {'unidad': 'kg'}, 3, id_nivel=first['id_nivel'])
            await RackService.validar_asignacion(rack, {'unidad': 'kg'}, 99, id_nivel=second['id_nivel'])
            with pytest.raises(HTTPException):
                await NivelService.validar_ingreso('r', first['id_nivel'], {'unidad': 'kg'}, 1)
            with pytest.raises(HTTPException):
                await NivelService.validar_ingreso(rack['id_rack'], None, {'unidad': 'kg'}, 1)
            with pytest.raises(HTTPException):
                await JerarquiaService.actualizar_nivel(company, first['id_nivel'], NivelUpdate(capacidad_kg=7))
            await JerarquiaService.actualizar_nivel(company, first['id_nivel'], NivelUpdate(capacidad_kg=12))
            assert (await JerarquiaService.niveles(company, rack['id_rack']))[0]['libre_kg'] == 4
    asyncio.run(run())
