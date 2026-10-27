import asyncio
from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math

from fastapi import HTTPException
from app.dto.analisis_dto import DemandAnalysis
from app.ml.autogluon_calendar import series_id
from app.repositories.analisis_repository import AnalisisRepository
from app.services.acceso_service import AccesoService
from app.services.autogluon_runtime import runtime, MANIFEST, ModelUnavailable


class AnalisisService:
    def __init__(self, repository=None, model=None):
        self.repository = repository or AnalisisRepository()
        self.model = model or runtime
        self.tasks = {}
        self.results = OrderedDict()
        self.gate = asyncio.Semaphore(1)

    def metadata(self):
        return {**MANIFEST, 'runtime': self.model.status(),
                'advertencias': ['WAPE es evaluación histórica acumulada sobre 200 series, no precisión garantizada de una predicción futura.',
                                'Q10/Q90 forman una banda central del 80 %; Q50 es la mediana. No se suman cuantiles diarios como intervalo acumulado.',
                                'Las predicciones dependen del historial disponible y no garantizan la demanda futura.']}

    async def filters(self, user):
        warehouses, products = await self.repository.catalog(user.id_empresa)
        return {'id_empresa': user.id_empresa,
                'almacenes': [{'id': w.get('id', w.get('id_almacen')), 'nombre': w.get('nombre')} for w in warehouses],
                'productos': [{'id': p['id_producto'], 'nombre': p.get('nombre')} for p in products]}

    async def authorize(self, user, warehouse=None, product=None, tenant=None):
        if tenant and tenant != user.id_empresa: raise HTTPException(403, 'Empresa no autorizada')
        for identifier, verifier, field in ((warehouse, AccesoService.verificar_almacen, 'almacen'),
                                             (product, AccesoService.verificar_producto, 'producto')):
            if not identifier: continue
            try:
                await verifier(user, identifier)
            except HTTPException as error:
                if error.status_code != 404 or not user.es_empresa or not hasattr(self.repository, 'dataset_history'): raise
                from app.repositories.demanda_historica_repository import DemandaHistoricaRepository
                rows = await DemandaHistoricaRepository().catalog(user.id_empresa)
                if not any(row['_id'][field] == identifier for row in rows): raise

    async def _compute(self, key, user, warehouse, product, history, base):
        async with self.gate:
            try:
                result, hit = await asyncio.to_thread(self.model.predict, user.id_empresa, base.series_id, history)
                points = result['predictions'][base.series_id]
                if len(points) != 90 or any(
                    date.fromisoformat(str(p['fecha'])[:10]) != base.fecha_corte + timedelta(days=i + 1)
                    or not math.isfinite(float(p['cantidad'])) or float(p['cantidad']) < 0
                    or any(p.get(q) is not None and (not math.isfinite(float(p[q])) or float(p[q]) < 0)
                           for q in ('q10', 'q50', 'q90'))
                    for i, p in enumerate(points)):
                    raise ValueError('Pronóstico incompatible con las fechas o serie solicitadas')
                base.predicciones = points
                base.horizontes = [{'horizonte_dias': h, 'demanda_acumulada': round(sum(p['cantidad'] for p in points[:h]), 4), 'demanda_del_dia': points[h-1]['cantidad']} for h in (1, 7, 30, 90)]
                base.estado = 'DISPONIBLE'; base.cache = hit
                if result.get('negative_values_clipped'):
                    base.advertencias.append('Salidas negativas del modelo truncadas a cero para representar demanda no negativa.')
            except Exception as error:
                base.estado = 'ERROR_MODELO'
                import logging
                logging.getLogger(__name__).exception('Demand inference failed')
                base.detalle = 'No se pudo calcular el pronóstico. Inténtalo de nuevo más tarde.'
            self.results[key] = base
            self.tasks.pop(key, None)
            while len(self.results) > 512: self.results.popitem(last=False)

    async def series(self, user, warehouse, product, wait=False, cutoff=None):
        await self.authorize(user, warehouse, product)
        # A complete UTC day, never an incomplete today's observation.
        cutoff = cutoff or datetime.now(timezone.utc).date() - timedelta(days=1)
        if cutoff >= datetime.now(timezone.utc).date():
            raise HTTPException(422, 'El corte debe ser anterior a hoy UTC')
        imported = (await self.repository.dataset_history(user.id_empresa, warehouse, product, cutoff)
                    if hasattr(self.repository, 'dataset_history') else [])
        operational = True
        if not imported and hasattr(self.repository, 'dataset_history'):
            try:
                await AccesoService.verificar_almacen(user, warehouse)
                await AccesoService.verificar_producto(user, product)
            except HTTPException as error:
                if error.status_code != 404: raise
                operational = False
        if imported:
            cutoff = date.fromisoformat(imported[-1]['fecha'])
            rows = [{'fecha': r['fecha'], 'demanda': r['cantidad']} for r in imported]
        else:
            rows = await self.repository.history(warehouse, product, cutoff) if operational else []
        values = {date.fromisoformat(str(row['fecha'])[:10]): float(row['demanda']) for row in rows}
        if any(not math.isfinite(value) or value < 0 for value in values.values()):
            raise HTTPException(422, 'Demanda histórica inválida; se conserva el dato original')
        history = []
        if imported:
            history = [{'fecha': day.isoformat(), 'cantidad': value} for day, value in sorted(values.items())]
        elif values:
            current = min(values)
            while current <= cutoff:
                history.append({'fecha': current.isoformat(), 'cantidad': values.get(current, 0.0)})
                current += timedelta(days=1)
        if imported:
            stock = await self.repository.stock_for_tenant(user.id_empresa, warehouse, product) if hasattr(self.repository, 'stock_for_tenant') else None
        else:
            stock = await self.repository.stock(warehouse, product) if operational else None
        base = DemandAnalysis(estado='SIN_HISTORIAL', id_empresa=user.id_empresa, id_almacen=warehouse, id_producto=product,
                              series_id=series_id(warehouse, product), fecha_corte=cutoff, historico=history, stock_actual=stock,
                              advertencias=['cantidad es demanda observada (toda SALIDA), no stock ni demanda latente.',
                                            'Se usa todo el historial disponible hasta el día de corte UTC. Días sin SALIDA se representan con 0 según el contrato operativo; esto no acredita observación ni disponibilidad de producto.',
                                            'Las predicciones son estimaciones sujetas a incertidumbre.'])
        if imported:
            base.advertencias = ['Demanda histórica del CSV; cantidad no representa stock. Incluye registros marcados es_imputado.',
                                 'No se completan fechas ausentes. El corte corresponde al último día importado anterior a hoy UTC.',
                                 'El pronóstico usa exclusivamente AutoGluon y corresponde a las fechas posteriores al corte del dataset.']
            if any(date.fromisoformat(b['fecha']) - date.fromisoformat(a['fecha']) != timedelta(days=1)
                   for a, b in zip(history, history[1:])):
                base.estado = 'HISTORIAL_INSUFICIENTE'
                base.detalle = 'El historial importado tiene fechas ausentes; no se inventan valores para el modelo.'
                return base
        if not history: return base
        # Operational guard, not a claim of 91 days of actual observations.
        if len(history) < 91:
            base.estado = 'HISTORIAL_INSUFICIENTE'
            base.detalle = 'La integración exige al menos 91 días de cobertura para un horizonte de 90 días; cobertura no equivale a observaciones completas.'
            return base
        if not self.model.status()['validado']:
            base.estado = 'MODELO_NO_DISPONIBLE'
            base.detalle = 'El servicio de pronósticos no está disponible.'
            return base
        key = hashlib.sha256(json.dumps([user.id_empresa, warehouse, product, history, self.model.status().get('model_fingerprint')], sort_keys=True).encode()).hexdigest()
        if key in self.results:
            cached = self.results[key].model_copy(deep=True)
            cached.stock_actual = stock
            cached.cache = True
            return cached
        if key not in self.tasks:
            if len(self.tasks) >= 200:
                raise HTTPException(429, 'Cola de predicciones ocupada; vuelve a intentarlo.')
            self.tasks[key] = asyncio.create_task(self._compute(key, user, warehouse, product, history, base))
        if wait:
            await self.tasks[key]
            return self.results[key]
        return base.model_copy(update={'estado': 'CALCULANDO', 'detalle': 'Inferencia en cola. La misma consulta reutiliza el trabajo en curso.'})

    async def summary(self, user, horizon=30, warehouse=None, product=None, limit=50):
        await self.authorize(user, warehouse, product)
        if horizon not in (1, 7, 30, 90): raise HTTPException(422, 'Horizonte inválido')
        pairs = await self.repository.pairs(user.id_empresa, warehouse, product)
        warehouses, products = await self.repository.catalog(user.id_empresa)
        wn = {w.get('id', w.get('id_almacen')): w.get('nombre') for w in warehouses}
        pn = {p['id_producto']: p.get('nombre') for p in products}
        rows = []
        for w, p in pairs[:limit]:
            result = await self.series(user, w, p)
            total = next((h.demanda_acumulada for h in result.horizontes if h.horizonte_dias == horizon), None) if result.estado == 'DISPONIBLE' else None
            # Assignment validation is enabled in DemandAnalysis; dicts become typed totals.
            rows.append({'id_almacen': w, 'id_producto': p, 'almacen': wn.get(w), 'producto': pn.get(p),
                         'estado': result.estado, 'demanda_acumulada': total, 'stock_actual': result.stock_actual,
                         'brecha_stock': max(0, total - result.stock_actual) if total is not None and result.stock_actual is not None else None})
        rows.sort(key=lambda row: (row['demanda_acumulada'] is None, -(row['demanda_acumulada'] or 0)))
        return {'horizonte_dias': horizon, 'filas': rows, 'series_totales': len(pairs), 'series_consultadas': len(rows),
                'completo': len(pairs) <= limit and all(r['estado'] == 'DISPONIBLE' for r in rows),
                'calculando': any(r['estado'] == 'CALCULANDO' for r in rows), 'modelo': 'WeightedEnsemble',
                'advertencias': ['Ranking solo de las series consultadas con pronóstico disponible; no se suman stocks entre almacenes para tomar decisiones.',
                                'La brecha demanda-stock es una comparación orientativa; no incluye entradas pendientes, capacidad ni políticas de reposición. No ejecuta compras.']}


service = AnalisisService()
