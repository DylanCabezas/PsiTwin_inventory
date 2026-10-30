import asyncio
from datetime import date, timedelta
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from app.services.demanda_csv import (
    CsvAnalysisRequest, analyze_csv, csv_columns, parse_date, parse_quantity, summarize,
)


def request(content, **kwargs):
    return CsvAnalysisRequest(contenido=content, columna_fecha='fecha', columna_cantidad='cantidad', **kwargs)


@pytest.mark.parametrize('value,expected', [
    ('12', 12), ('12.5', 12.5), ('12,5', 12.5), ('1 200,50', 1200.5),
    ('1.200,50', 1200.5), ('1,200.50', 1200.5), ('0', 0), ('1e2', 100),
])
def test_numbers_are_converted_from_text(value, expected):
    assert parse_quantity(value) == expected


@pytest.mark.parametrize('value', ['-1', 'NaN', 'Infinity', 'true', '', '1.2.3', 'diez', '1,2.34'])
def test_uninterpretable_or_invalid_quantities_are_not_fabricated(value):
    with pytest.raises(ValueError):
        parse_quantity(value)


@pytest.mark.parametrize('value', ['2026-10-01', '01/10/2026', '01-10-2026', '2026/10/01', '20261001', '2026-10-01T10:30:00Z', '46296', '46296.5', '46296,5'])
def test_common_date_formats_and_excel_serial(value):
    assert parse_date(value) == date(2026, 10, 1)


def test_arbitrary_headers_bom_semicolons_quotes_and_product_isolation():
    content = '\ufeffDía;Artículo;Vendido;Otra\n01/10/2026;"Arroz; extra";12,5;x\n01/10/2026;"Arroz; extra";0,5;y\n03/10/2026;"Arroz; extra";2;z\n01/10/2026;Chocolate;99;a\n'
    preview = csv_columns(content)
    assert preview['columnas'] == ['Día', 'Artículo', 'Vendido', 'Otra'] and preview['filas'] == 4
    data = CsvAnalysisRequest(contenido=content, columna_fecha='Día', columna_cantidad='Vendido', columna_producto='Artículo', serie='Arroz; extra')
    result = summarize(data)
    assert result['total'] == 15 and result['dias_sin_datos'] == 1
    assert result['historico'] == [{'fecha': '2026-10-01', 'cantidad': 13}, {'fecha': '2026-10-03', 'cantidad': 2}]
    assert result['series'] == ['Arroz; extra', 'Chocolate']
    assert result['predicciones'] == []


@pytest.mark.parametrize('content', [
    'fecha,cantidad\n31/02/2026,2', 'fecha,cantidad\n2026-10-01,NaN',
    'fecha,cantidad\n2026-10-01,-2', 'fecha,cantidad\n2026-10-01,',
])
def test_invalid_rows_report_line_and_reject_entire_analysis(content):
    with pytest.raises(HTTPException) as error:
        summarize(request(content))
    assert error.value.status_code == 422 and 'Fila 2' in error.value.detail


@pytest.mark.parametrize('content', ['fecha,fecha\n1,2', 'fecha,cantidad\n1,2,3', 'fecha,cantidad\n', 'fecha,,cantidad\n1,2,3'])
def test_malformed_csv_rejected(content):
    with pytest.raises(HTTPException):
        csv_columns(content)


def test_missing_column_unknown_series_duplicate_mapping_and_overflow():
    with pytest.raises(HTTPException):
        summarize(request('otra,cantidad\n2026-10-01,2'))
    with pytest.raises(HTTPException):
        summarize(request('fecha,cantidad\n2026-10-01,2', serie='otro'))
    with pytest.raises(ValueError):
        CsvAnalysisRequest(contenido='a,b\n1,2', columna_fecha='a', columna_cantidad='a')
    with pytest.raises(HTTPException):
        summarize(request('fecha,cantidad\n2026-10-01,1e308\n2026-10-02,1e308'))


class Model:
    def __init__(self, available=True): self.available = available; self.calls = 0
    def status(self): return {'validado': self.available}
    def predict(self, tenant, series, history):
        self.calls += 1
        assert tenant == 'company' and history[-1]['demanda'] == 2
        last = date.fromisoformat(history[-1]['fecha'])
        return {'predictions': {series: [{'fecha': (last + timedelta(days=i)).isoformat(), 'cantidad': 3,
                                        'q10': 1, 'q50': 3, 'q90': 5} for i in range(1, 91)]}}, False


def long_history():
    return 'fecha,cantidad\n' + '\n'.join(f'{date(2025,1,1)+timedelta(days=i)},2' for i in range(91))


def test_forecast_uses_authenticated_company_and_real_model_interface_only():
    model = Model()
    result = asyncio.run(analyze_csv(request(long_history(), pronosticar=True), SimpleNamespace(id_empresa='company'), model))
    assert result['estado'] == 'DISPONIBLE' and len(result['predicciones']) == 90 and model.calls == 1


def test_insufficient_or_unavailable_model_never_invents_predictions():
    model = Model(False)
    user = SimpleNamespace(id_empresa='company')
    insufficient = asyncio.run(analyze_csv(request('fecha,cantidad\n2025-01-01,2', pronosticar=True), user, model))
    unavailable = asyncio.run(analyze_csv(request(long_history(), pronosticar=True), user, model))
    assert insufficient['estado'] == 'HISTORIAL_INSUFICIENTE'
    assert unavailable['estado'] == 'MODELO_NO_DISPONIBLE'
    assert not insufficient['predicciones'] and not unavailable['predicciones'] and model.calls == 0


def test_bad_model_output_preserves_historical_analysis():
    model = Model()
    model.predict = lambda *args: ({'predictions': {}}, False)
    result = asyncio.run(analyze_csv(request(long_history(), pronosticar=True), SimpleNamespace(id_empresa='company'), model))
    assert result['estado'] == 'ERROR_MODELO' and result['total'] == 182 and not result['predicciones']


def test_forecast_without_optional_quantiles_is_normalized_for_the_chart():
    model = Model()
    predict = model.predict
    def without_quantiles(*args):
        data, hit = predict(*args)
        for series in data['predictions'].values():
            for point in series:
                for key in ('q10', 'q50', 'q90'):
                    point.pop(key)
        return data, hit
    model.predict = without_quantiles
    result = asyncio.run(analyze_csv(request(long_history(), pronosticar=True), SimpleNamespace(id_empresa='company'), model))
    assert result['estado'] == 'DISPONIBLE'
    assert all(point['q10'] is None and point['q90'] is None for point in result['predicciones'])


def test_file_and_record_limits_are_enforced(monkeypatch):
    from app.services import demanda_csv
    monkeypatch.setattr(demanda_csv, 'MAX_ROWS', 2)
    with pytest.raises(HTTPException) as rows_error:
        csv_columns('fecha,cantidad\n2026-10-01,1\n2026-10-02,1\n2026-10-03,1')
    assert rows_error.value.status_code == 422
    monkeypatch.setattr(demanda_csv, 'MAX_CSV_BYTES', 10)
    with pytest.raises(HTTPException) as bytes_error:
        csv_columns('fecha,cantidad\n2026-10-01,1')
    assert bytes_error.value.status_code == 413


def test_http_contract_has_auth_and_requires_no_mongodb(monkeypatch):
    from app.controllers.analisis_controller import router
    from app.dependencies.dependencies import require_empresa_u_operario
    app = FastAPI(); app.include_router(router, prefix='/api/v1')
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            body = {'contenido': 'fecha,cantidad\n01/10/2026,12'}
            assert (await client.post('/api/v1/analisis/csv/columnas', json=body)).status_code in (401, 403)
            async def actor(): return SimpleNamespace(id_empresa='company')
            app.dependency_overrides[require_empresa_u_operario] = actor
            preview = await client.post('/api/v1/analisis/csv/columnas', json=body)
            assert preview.status_code == 200 and preview.json()['filas'] == 1
            result = await client.post('/api/v1/analisis/csv/analizar', json={**body, 'columna_fecha': 'fecha', 'columna_cantidad': 'cantidad'})
            assert result.status_code == 200 and result.json()['total'] == 12
    asyncio.run(run())
