"""Read-only service-level audit against the isolated MongoDB import."""
import asyncio
import json
import sys
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from generar_dataset_pruebas import OUT,TENANT,ORIGIN
from importar_dataset_pruebas import DATABASE,import_dataset,read_excel
from motor.motor_asyncio import AsyncIOMotorClient
from app.database import mongodb
from app.dto.auth_dto import UsuarioActual
from app.dto.saiki_dto import SaikiAskRequest
from app.dto.inventario_consulta_dto import InventarioFiltros
from app.services.inventario_consulta_service import consultar_inventario
from app.repositories.demanda_historica_repository import DemandaHistoricaRepository
from app.services.saiki_service import SaikiService

async def main():
    client=AsyncIOMotorClient('mongodb://127.0.0.1:27017',serverSelectionTimeoutMS=3000)
    db=client[DATABASE];mongodb.database=db
    try:
        info=json.loads((OUT/'importacion.json').read_text(encoding='utf-8'));user=UsuarioActual(rol='EMPRESA',id_empresa=TENANT)
        counts_before={c:await db[c].count_documents({}) for c in await db.list_collection_names()}
        await import_dataset(read_excel(OUT/'PsiTwin_Dataset_Pruebas_2025_2026.xlsx'),True)
        counts_after={c:await db[c].count_documents({}) for c in await db.list_collection_names()}
        assert counts_before==counts_after,(counts_before,counts_after)
        inventory=await consultar_inventario(user,InventarioFiltros(id_almacen=info['almacen']))
        assert len(inventory['zonas'])==3 and len(inventory['racks'])==6 and len(inventory['niveles'])==10
        assert all(n['monitoreo']=='sin_datos' and not n['sensores'] for n in inventory['niveles'])
        (OUT/'plano_importado.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
        histories=[]
        for source,pid in info['mapeo_productos'].items():
            for frequency in ('diaria','semanal','mensual'):
                result=await DemandaHistoricaRepository().report(TENANT,info['almacen'],pid,frequency=frequency)
                assert result['documentos']==396 and result['fecha_inicio']=='2025-09-28' and result['fecha_fin']=='2026-10-28'
                assert len(result['serie'])=={'diaria':396,'semanal':58,'mensual':14}[frequency]
                histories.append({'producto':source,'frecuencia':frequency,'puntos':len(result['serie']),'total':result['total']})
        questions=['¿Qué productos tengo en inventario?','Enumera los 30 productos.','¿Cuántos helados tengo?','¿Cuáles son los cuatro helados?','¿Dónde están almacenados los helados?','¿Cuántos racks tiene ABC1?','¿Cuántos niveles tiene cada rack?','¿Qué productos están en la Zona C?','¿Qué producto tuvo mayor demanda en enero de 2026?','¿Cómo evolucionó la demanda de helados?','¿Cuál es el pronóstico de papaya?','¿Qué productos necesitan reposición?','¿Hay sensores registrados?']
        saiki=SaikiService();answers=[]
        from app.services.analisis_service import service as analysis
        try:
            forecast=await asyncio.wait_for(analysis.series(user,info['almacen'],info['mapeo_productos']['SYN-001'],wait=True),timeout=240)
            (OUT/'pronostico_servicio_papaya.json').write_text(forecast.model_dump_json(indent=2),encoding='utf-8')
        except Exception as exc:
            (OUT/'pronostico_servicio_papaya.json').write_text(json.dumps({'error':str(exc)}),encoding='utf-8')
        for q in questions:
            try:
                r=await asyncio.wait_for(saiki.ask(SaikiAskRequest(message=q,id_almacen=info['almacen'],page_size=100),user),timeout=65)
                answers.append({'pregunta':q,'respuesta':r})
            except Exception as exc:answers.append({'pregunta':q,'error':str(exc),'tipo':type(exc).__name__})
            print(q,flush=True)
            (OUT/'saiki_consultas.json').write_text(json.dumps(answers,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
        from app.services.autogluon_runtime import runtime
        report={'idempotente':True,'conteos_antes':counts_before,'conteos_despues':counts_after,'plano':{'zonas':3,'racks':6,'niveles':10,'niveles_sin_datos':10},'historias':histories,'runtime_produccion':runtime.status(),'consultas_saiki':len(answers),'errores_saiki':sum('error' in a for a in answers)}
        (OUT/'auditoria_integracion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=True))
        runtime.close()
    finally:client.close()
if __name__=='__main__':asyncio.run(main())
