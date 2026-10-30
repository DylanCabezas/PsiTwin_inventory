"""Compatibility API backed exclusively by the shared demand analysis runtime."""
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from app.dto.auth_dto import UsuarioActual
from app.dto.forecast_dto import ForecastResponse, PrediccionDiaria
from app.repositories.almacen_repository import AlmacenRepository
from app.services.analisis_service import service as analysis_service


class ForecastService:
    def __init__(self, analysis=None):
        self.analysis = analysis or analysis_service

    async def historial(self, id_almacen, id_producto, fecha_corte, dias=28):
        """Observed demand for the risk engine, with the same source as inference."""
        import pandas as pd
        warehouse = await AlmacenRepository.obtener_por_id(id_almacen)
        if not warehouse: raise HTTPException(404, 'Almacén no encontrado')
        user = UsuarioActual(rol='EMPRESA', id_empresa=warehouse['id_empresa'])
        await self.analysis.authorize(user,id_almacen,id_producto)
        repo=self.analysis.repository
        rows=await repo.dataset_history(user.id_empresa,id_almacen,id_producto,fecha_corte)
        if rows: values=[{'fecha':r['fecha'],'demanda':r['cantidad']} for r in rows]
        else: values=await repo.history(id_almacen,id_producto,fecha_corte)
        start=(fecha_corte-timedelta(days=dias-1)).isoformat()
        values=[r for r in values if start<=str(r['fecha'])[:10]<=fecha_corte.isoformat()]
        if len(values)!=dias:raise HTTPException(422,'Historial diario incompleto para evaluar reposición; no se inventan ceros')
        return pd.DataFrame(values).sort_values('fecha')

    async def predecir(self, id_almacen, id_producto, horizonte_dias=7, fecha_corte=None, dias=400):
        if horizonte_dias not in (1, 7, 30, 90):
            raise HTTPException(422, "Horizontes permitidos: 1, 7, 30, 90")
        if not 7 <= dias <= 500:
            raise HTTPException(422, "Ventana histórica: 7..500 días")
        # This legacy parameter is accepted for API compatibility; inference uses full history.
        cutoff = fecha_corte or datetime.now(timezone.utc).date() - timedelta(days=1)
        if cutoff >= datetime.now(timezone.utc).date():
            raise HTTPException(422, "El corte debe ser un día completo anterior a hoy UTC")
        warehouse = await AlmacenRepository.obtener_por_id(id_almacen)
        if not warehouse or not warehouse.get('id_empresa'):
            raise HTTPException(404, "Almacén no encontrado")
        user = UsuarioActual(rol='EMPRESA', id_empresa=warehouse['id_empresa'])
        result = await self.analysis.series(user, id_almacen, id_producto, wait=True, cutoff=cutoff)
        available = result.estado == 'DISPONIBLE'
        state = ('HISTORIAL_INSUFICIENTE' if result.estado == 'SIN_HISTORIAL' else
                 result.estado if result.estado in {'DISPONIBLE', 'HISTORIAL_INSUFICIENTE'} else 'MODELO_NO_DISPONIBLE')
        daily = [PrediccionDiaria(fecha=p.fecha, demanda_estimada=p.cantidad)
                 for p in result.predicciones[:horizonte_dias]] if available else []
        cutoff = result.fecha_corte
        return ForecastResponse(
            id_almacen=id_almacen, id_producto=id_producto, fecha_generacion=datetime.now(timezone.utc),
            fecha_corte=cutoff, horizonte_dias=horizonte_dias, fecha_inicio=cutoff+timedelta(days=1),
            fecha_fin=cutoff+timedelta(days=horizonte_dias), estado=state,
            demanda_total_estimada=round(sum(p.demanda_estimada for p in daily), 4) if available else None,
            predicciones_diarias=daily, modelo='AutoGluon', version_modelo='1.6.1',
            historial_suficiente=len(result.historico) >= 91, advertencias=result.advertencias)
