"""Exercise the existing operational risk/replenishment service, no writes."""
import asyncio,json
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from app.database import mongodb
from app.services.inventory_risk_service import InventoryRiskService
from app.services.autogluon_runtime import runtime
OUT=Path(__file__).resolve().parents[2]/'outputs/psitwin_pruebas'
async def main():
    client=AsyncIOMotorClient('mongodb://127.0.0.1:27017');db=client['psitwin_synthetic30_test'];mongodb.database=db
    try:
        info=json.loads((OUT/'importacion.json').read_text(encoding='utf-8'))
        header=await db.inventarios.find_one({'id_almacen':info['almacen']})
        result=await InventoryRiskService().evaluar(header['id_inventario'],generar_alertas=False,id_producto=info['mapeo_productos']['SYN-001'])
        assert result.stock_actual==0 and 0<=result.reposicion.cantidad_recomendada<=81
        (OUT/'recomendador_operativo_papaya.json').write_text(result.model_dump_json(indent=2),encoding='utf-8')
        print('Recomendador operativo verificado:',result.reposicion.cantidad_recomendada,'kg')
    except Exception as exc:
        (OUT/'recomendador_operativo_papaya.json').write_text(json.dumps({'error':str(exc),'tipo':type(exc).__name__}),encoding='utf-8');raise
    finally:runtime.close();client.close()
if __name__=='__main__':asyncio.run(main())
