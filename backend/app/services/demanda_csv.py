"""Read-only demand analysis of user-supplied CSV, with explicit column mapping."""
import asyncio
import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
from io import StringIO
import math
import re

from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator

MAX_CSV_BYTES = 2_000_000
MAX_ROWS = 20_000


class CsvFile(BaseModel):
    contenido: str = Field(min_length=1, max_length=MAX_CSV_BYTES)


class CsvAnalysisRequest(CsvFile):
    columna_fecha: str
    columna_cantidad: str
    columna_producto: str | None = None
    serie: str | None = None
    pronosticar: bool = False

    @model_validator(mode='after')
    def distinct_columns(self):
        columns = [self.columna_fecha, self.columna_cantidad]
        if self.columna_producto:
            columns.append(self.columna_producto)
        if len(set(columns)) != len(columns):
            raise ValueError('Selecciona columnas distintas para fecha, cantidad y producto')
        return self


def read_csv(content):
    if len(content.encode('utf-8')) > MAX_CSV_BYTES:
        raise HTTPException(413, 'El CSV no puede superar 2 MB')
    content = content.lstrip('\ufeff')
    try:
        try:
            dialect = csv.Sniffer().sniff(content[:8192], delimiters=',;\t|')
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(StringIO(content, newline=''), dialect=dialect, strict=True)
        columns = [c.strip() for c in next(reader)]
        if len(columns) < 2 or any(not c for c in columns) or len(set(columns)) != len(columns):
            raise HTTPException(422, 'La primera fila debe contener al menos dos encabezados únicos, sin columnas vacías')
        rows = []
        for number, values in enumerate(reader, start=2):
            if not any(v.strip() for v in values):
                continue
            if len(values) != len(columns):
                raise HTTPException(422, f'Fila {number}: número de columnas distinto al encabezado')
            rows.append((number, dict(zip(columns, values))))
            if len(rows) > MAX_ROWS:
                raise HTTPException(422, f'El CSV admite hasta {MAX_ROWS:,} registros')
        if not rows:
            raise HTTPException(422, 'El CSV no contiene registros')
        return columns, rows
    except (csv.Error, StopIteration) as error:
        raise HTTPException(422, 'CSV inválido; revisa los encabezados, separadores y comillas') from error


def csv_columns(content):
    columns, rows = read_csv(content)
    return {'columnas': columns, 'muestra': [row for _, row in rows[:5]], 'filas': len(rows)}


def parse_date(value):
    value = value.strip()
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
    except ValueError:
        pass
    for pattern in ('%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%Y%m%d'):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            pass
    # Excel serial date, not an inferred month/day ordering.
    if re.fullmatch(r'\d{4,5}(?:[.,]\d+)?', value):
        return date(1899, 12, 30) + timedelta(days=int(float(value.replace(',', '.'))))
    raise ValueError('fecha no interpretable; usa AAAA-MM-DD, DD/MM/AAAA o fecha numérica de Excel')


def parse_quantity(value):
    value = value.strip().replace('\u00a0', '').replace(' ', '')
    # Mixed separators: the last one is decimal (1.200,50 or 1,200.50).
    if ',' in value and '.' in value:
        decimal = ',' if value.rfind(',') > value.rfind('.') else '.'
        grouping = '.' if decimal == ',' else ','
        whole, fraction = value.rsplit(decimal, 1)
        if not re.fullmatch(r'\d{1,3}(?:' + re.escape(grouping) + r'\d{3})+', whole) or not fraction.isdigit():
            raise ValueError('cantidad con separadores inválidos')
        value = whole.replace(grouping, '') + '.' + fraction
    else:
        value = value.replace(',', '.')
    try:
        result = float(Decimal(value))
    except (InvalidOperation, ValueError, OverflowError) as error:
        raise ValueError('cantidad no numérica') from error
    if not math.isfinite(result) or result < 0:
        raise ValueError('la cantidad debe ser un número finito mayor o igual a cero')
    return result


def summarize(request):
    columns, rows = read_csv(request.contenido)
    required = [request.columna_fecha, request.columna_cantidad]
    if request.columna_producto:
        required.append(request.columna_producto)
    if any(column not in columns for column in required):
        raise HTTPException(422, 'Las columnas seleccionadas no existen en el CSV')
    series = {}
    failures = []
    for number, row in rows:
        try:
            day = parse_date(row[request.columna_fecha])
            quantity = parse_quantity(row[request.columna_cantidad])
            label = row[request.columna_producto].strip() if request.columna_producto else 'Serie del archivo'
            if not label:
                raise ValueError('producto vacío')
            points = series.setdefault(label, {})
            points[day] = points.get(day, 0) + quantity
            if not math.isfinite(points[day]):
                raise ValueError('la suma diaria supera el rango numérico permitido')
        except (ValueError, OverflowError) as error:
            failures.append(f'Fila {number}: {error}')
    if failures:
        raise HTTPException(422, f'{len(failures)} fila(s) inválida(s). ' + ' · '.join(failures[:5]))
    labels = sorted(series)
    chosen = request.serie or labels[0]
    if chosen not in series:
        raise HTTPException(422, 'La serie seleccionada no existe en este archivo')
    daily = series[chosen]
    history = [{'fecha': day.isoformat(), 'cantidad': daily[day]} for day in sorted(daily)]
    values = [p['cantidad'] for p in history]
    try:
        total = math.fsum(values)
    except OverflowError as error:
        raise HTTPException(422, 'La demanda total supera el rango numérico permitido') from error
    if not math.isfinite(total):
        raise HTTPException(422, 'La demanda total supera el rango numérico permitido')
    first, last = min(daily), max(daily)
    missing = (last - first).days + 1 - len(daily)
    return {'serie': chosen, 'series': labels, 'filas_archivo': len(rows), 'dias_observados': len(history),
            'fecha_inicio': first.isoformat(), 'fecha_fin': last.isoformat(), 'dias_sin_datos': missing,
            'total': total, 'promedio_diario': total / len(history), 'minimo_diario': min(values),
            'maximo_diario': max(values), 'historico': history, 'predicciones': [],
            'estado': 'ANALIZADO', 'detalle': None,
            'advertencias': ['Las filas del mismo producto y fecha se suman; cada serie debe usar una sola unidad.',
                             'Los días ausentes no se completan con ceros. El archivo no modifica inventarios ni el historial guardado.']}


async def analyze_csv(request, user, runtime=None):
    result = await asyncio.to_thread(summarize, request)
    if not request.pronosticar:
        return result
    if result['dias_observados'] < 91 or result['dias_sin_datos']:
        return {**result, 'estado': 'HISTORIAL_INSUFICIENTE',
                'detalle': 'Para pronosticar se necesitan al menos 91 días consecutivos, sin fechas ausentes.'}
    if result['fecha_fin'] >= datetime.now(timezone.utc).date().isoformat():
        return {**result, 'estado': 'HISTORIAL_INSUFICIENTE', 'detalle': 'El historial para pronosticar debe terminar antes de hoy.'}
    if runtime is None:
        from app.services.autogluon_runtime import runtime
    try:
        available = (await asyncio.to_thread(runtime.status))['validado']
    except Exception:
        return {**result, 'estado': 'ERROR_MODELO', 'detalle': 'No se pudo comprobar el modelo. El análisis histórico sigue disponible.'}
    if not available:
        return {**result, 'estado': 'MODELO_NO_DISPONIBLE', 'detalle': 'El modelo no está disponible. Puedes consultar el análisis histórico del CSV.'}
    series_id = 'csv_' + hashlib.sha256(result['serie'].encode()).hexdigest()[:20]
    history = [{'fecha': p['fecha'], 'demanda': p['cantidad']} for p in result['historico']]
    try:
        prediction, _ = await asyncio.to_thread(runtime.predict, user.id_empresa, series_id, history)
        points = prediction['predictions'][series_id]
        end = date.fromisoformat(result['fecha_fin'])
        if len(points) != 90:
            raise ValueError('Longitud de pronóstico inválida')
        for offset, point in enumerate(points, start=1):
            if date.fromisoformat(str(point['fecha'])[:10]) != end + timedelta(days=offset):
                raise ValueError('Fechas de pronóstico inválidas')
            if not math.isfinite(float(point['cantidad'])) or float(point['cantidad']) < 0:
                raise ValueError('Predicción inválida')
            if any(point.get(q) is not None and (not math.isfinite(float(point[q])) or float(point[q]) < 0)
                   for q in ('q10', 'q50', 'q90')):
                raise ValueError('Cuantil inválido')
        normalized = [{'fecha': str(p['fecha'])[:10], 'cantidad': float(p['cantidad']),
                       **{q: float(p[q]) if p.get(q) is not None else None for q in ('q10', 'q50', 'q90')}}
                      for p in points]
        return {**result, 'estado': 'DISPONIBLE', 'predicciones': normalized}
    except Exception:
        return {**result, 'estado': 'ERROR_MODELO', 'detalle': 'No se pudo generar el pronóstico. El análisis histórico sigue disponible.'}
