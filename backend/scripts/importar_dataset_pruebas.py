"""Local-only test import, default preview. Never targets the configured production DB.

PYTHONPATH=backend python backend/scripts/importar_dataset_pruebas.py [--apply]
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from app.database import mongodb
from app.dto.auth_dto import UsuarioActual
from app.dto.almacen_dto import AlmacenCreate
from app.dto.zona_dto import ZonaCreate
from app.dto.rack_dto import RackCreate
from app.dto.abastecimiento_dto import NivelRequest
from app.dto.producto_dto import ProductoCreate
from app.dto.detalle_inventario_dto import DetalleInventarioCreate
from app.dto.movimiento_dto import MovimientoCreate
from app.services.jerarquia_service import JerarquiaService
from app.services.rack_service import RackService
from app.services.producto_service import ProductoService
from app.services.detalle_inventario_service import DetalleInventarioService
from app.services.movimiento_service import MovimientoService
from app.repositories.inventario_repository import InventarioRepository
from app.services.stock_lock import bloqueo_recurso
sys.path.insert(0,str(Path(__file__).resolve().parent))
from generar_dataset_pruebas import OUT, TENANT, ORIGIN

DATABASE='psitwin_synthetic30_test'

def read_excel(path):
    from openpyxl import load_workbook
    wb=load_workbook(path,read_only=True,data_only=True)
    data={}
    for sh in wb:
        rows=iter(sh.values); keys=next(rows)
        data[sh.title]=[dict(zip(keys,[v.date().isoformat() if isinstance(v,datetime) else v for v in row])) for row in rows]
    wb.close()
    return data

def validate(data):
    from generar_dataset_pruebas import START, END
    expected={'Productos':30,'Empresa':1,'Almacenes':1,'Zonas':3,'Racks':6,'Niveles':10,'Ubicaciones_Productos':30,'Demanda_Historica':11880}
    for sheet,n in expected.items():
        if len(data[sheet])!=n: raise ValueError(f'Cantidad incorrecta: {sheet}')
    for rows in data.values():
        if any(r['origen']!=ORIGIN or r['id_empresa']!=TENANT or r['sintetico'] is not True for r in rows): raise ValueError('Origen o empresa inválidos')
    levels={r['id_nivel']:r for r in data['Niveles']}
    racks={r['id_rack']:r for r in data['Racks']}
    products={r['id_producto']:r for r in data['Productos']}
    if len(products)!=30 or sum(p['familia']=='Helados' for p in products.values())!=4: raise ValueError('Catálogo inválido')
    for r in racks.values():
        if sum(n['id_rack']==r['id_rack'] for n in levels.values())!=r['max_niveles']: raise ValueError('Niveles inválidos')
    for r in data['Ubicaciones_Productos']:
        if levels[r['id_nivel']]['id_rack']!=r['id_rack']: raise ValueError('Ubicación inválida')
        if products[r['id_producto']]['familia']=='Helados' and racks[r['id_rack']]['tipo_rack']!='Congelado': raise ValueError('Helado fuera del congelador')
    seen=set()
    for r in data['Demanda_Historica']:
        key=(r['id_producto'],r['fecha'])
        if key in seen or not START.isoformat()<=r['fecha']<=END.isoformat(): raise ValueError('Demanda inválida')
        seen.add(key)
        if abs(r['cantidad']-r['cantidad_atendida']-r['demanda_insatisfecha'])>1e-6: raise ValueError('Venta perdida inválida')
    balances={p:0 for p in products}
    if len({r['id_movimiento'] for r in data['Movimientos']})!=len(data['Movimientos']):raise ValueError('Identificadores de movimientos duplicados')
    for r in data['Movimientos']:
        balances[r['id_producto']]+=r['cantidad']*(1 if r['tipo_movimiento']=='ENTRADA' else -1)
        if abs(balances[r['id_producto']]-r['stock_resultante'])>1e-6 or r['stock_resultante']<0: raise ValueError('Movimiento no reconciliado')
    for r in data['Inventario_Actual']:
        if abs(balances[r['id_producto']]-r['stock_final'])>1e-6: raise ValueError('Stock final incorrecto')
    return expected

async def import_dataset(data, apply=False):
    counts=validate(data)
    if not apply: return {'modo':'PREVIEW_SIN_ESCRITURAS','base':DATABASE,'registros':{k:len(v) for k,v in data.items()}}
    db=mongodb.get_database()
    if db.name!=DATABASE: raise ValueError('Solo se permite la base aislada de pruebas')
    async with bloqueo_recurso('synthetic30-import'):
        company=await db.empresas.find_one({'id_empresa':TENANT})
        if company and company.get('origen')!=ORIGIN: raise ValueError('Empresa no sintética: escritura rechazada')
        await db.movimientos.create_index([('id_almacen',1),('observacion',1)],name='synthetic30_lookup')
        await db.empresas.update_one({'id_empresa':TENANT},{'$setOnInsert':{**data['Empresa'][0],'estado':'ACTIVO','fecha_creacion':datetime.now(timezone.utc)}},upsert=True)
        user=UsuarioActual(rol='EMPRESA',id_empresa=TENANT)
        async def ensure(collection,key,creator):
            query={'origen':ORIGIN,'id_origen_sintetico':key}
            old=await db[collection].find_one(query,{'_id':0})
            if old:return old
            # Natural identifiers allow recovery if a previous run stopped before tagging.
            row=await creator()
            ids={k:v for k,v in row.items() if k.startswith('id_') and k not in ('id_empresa','id_proveedor','id_zona','id_rack','id_almacen')}
            if collection=='almacenes': ids={'id':row.get('id',row.get('id_almacen'))}
            if collection=='zonas': ids={'id':row.get('id',row.get('id_zona'))}
            if collection=='racks': ids={'id_rack':row['id_rack']}
            await db[collection].update_one(ids,{'$set':{**query,'sintetico':True}})
            return row
        w=await ensure('almacenes','ABC1',lambda:JerarquiaService.guardar_almacen(AlmacenCreate(id_empresa=TENANT,codigo='ABC1',nombre='Almacén Central',longitud=-77.04,latitud=-12.04,area_m2=500,aforo=20,tipo_almacen='SINTÉTICO',descripcion=ORIGIN)))
        wid=w.get('id',w.get('id_almacen'))
        zones={}; racks={}; levels={}; products={}; details={}
        for z in data['Zonas']:
            code=z['id_zona']; cold=code in ('B','C')
            row=await ensure('zonas',code,lambda z=z,cold=cold:JerarquiaService.crear_zona(ZonaCreate(id_almacen=wid,nombre=z['nombre'],codigo=z['id_zona'],tipo_zona='SINTÉTICA',capacidad=2,max_racks=2,refrigerada=cold,temperatura_min=-25 if cold else None,temperatura_max=25 if cold else None)))
            zones[code]=row.get('id',row.get('id_zona'))
        for r in data['Racks']:
            code=r['id_rack']; temp=(-22,-18) if code=='C1' else (2,6) if code.startswith('B') else (15,25)
            row=await ensure('racks',code,lambda r=r,temp=temp: RackService().crear_rack(RackCreate(id_zona=zones[r['id_zona']],codigo=r['codigo'],tipo_rack=r['tipo_rack'],max_niveles=r['max_niveles'],nivel=1 if r['codigo'].endswith('1') else 2,temperatura_min=temp[0] if r['id_zona'] in ('B','C') else None,temperatura_max=temp[1] if r['id_zona'] in ('B','C') else None)))
            racks[code]=row['id_rack']
        for n in data['Niveles']:
            row=await ensure('niveles',n['id_nivel'],lambda n=n:JerarquiaService.crear_nivel(user,racks[n['id_rack']],NivelRequest(codigo=n['codigo'],numero=n['numero'],capacidad_kg=n['capacidad_kg'])))
            levels[n['id_nivel']]=row['id_nivel']
        categories=['Tropicales','Tropicales','Tropicales','Frutas de pepita','Frutas de pepita','Tropicales','Cítricos','Cítricos','Cítricos','Frutos rojos','Frutos rojos','Tropicales','Tropicales','Tropicales','Tropicales','Hortalizas de fruto','Hortalizas de raíz','Verduras de hoja','Hortalizas de raíz','Papa','Camote','Hortalizas de tallo','Hortalizas de fruto','Verduras de hoja','Hortalizas de fruto','Yogures y postres lácteos']+['Helados y postres fríos']*4
        for i,p in enumerate(data['Productos']):
            loc=data['Ubicaciones_Productos'][i]; cold=loc['id_rack'].startswith('B') or i>=26
            row=await ensure('productos',p['id_producto'],lambda p=p,i=i,cold=cold:ProductoService.crear(ProductoCreate(id_empresa=TENANT,codigo=p['codigo'],nombre=p['nombre'],familia=p['familia'],categoria=categories[i],unidad=p['unidad'],peso=p['peso'],lead_time_dias=3,vida_util_dias=180 if i>=26 else 7,requiere_refrigeracion=cold,temperatura_min_almacenamiento=-25 if i>=26 else 0 if cold else None,temperatura_max_almacenamiento=-15 if i>=26 else 8 if cold else None)))
            products[p['id_producto']]=row['id_producto']
        inv=await InventarioRepository().garantizar(wid)
        await db.inventarios.update_one({'id_inventario':inv['id_inventario']},{'$set':{'origen':ORIGIN,'sintetico':True,'id_empresa':TENANT}})
        for p,loc in zip(data['Productos'],data['Ubicaciones_Productos']):
            row=await ensure('detalles_inventario',p['id_producto'],lambda p=p,loc=loc:DetalleInventarioService()._crear_detalle(DetalleInventarioCreate(id_inventario=inv['id_inventario'],id_producto=products[p['id_producto']],id_rack=racks[loc['id_rack']],id_nivel=levels[loc['id_nivel']],stock_actual=0,stock_minimo=p['stock_minimo'],stock_maximo=p['stock_maximo'])))
            details[p['id_producto']]=row['id_detalle_inventario']
        operator=TENANT+'-operator'
        await db.operarios.update_one({'id_operario':operator},{'$setOnInsert':{'id_operario':operator,'id_empresa':TENANT,'id_almacen':wid,'nombre':'Operario sintético','estado':'ACTIVO','origen':ORIGIN,'sintetico':True}},upsert=True)
        await db.operarios.update_one({'id_operario':operator},{'$set':{'origen':ORIGIN,'sintetico':True}})
        await db.inventario_historial.update_many({'id_inventario':inv['id_inventario']},{'$set':{'origen':ORIGIN,'sintetico':True,'id_empresa':TENANT}})
        for i,m in enumerate(data['Movimientos']):
            query={'observacion':ORIGIN+':'+m['id_movimiento'],'id_almacen':wid}
            old=await db.movimientos.find_one(query)
            if old:continue
            result=await MovimientoService().crear_movimiento(MovimientoCreate(id_inventario=inv['id_inventario'],id_detalle_inventario=details[m['id_producto']],id_operario=operator,tipo_movimiento=m['tipo_movimiento'],motivo_movimiento='VENTA' if m['tipo_movimiento']=='SALIDA' else 'REPOSICION',cantidad=m['cantidad'],observacion=query['observacion']),user)
            await db.movimientos.update_one({'id_movimiento':result['id_movimiento']},{'$set':{'fecha_hora':datetime.fromisoformat(m['fecha']).replace(tzinfo=timezone.utc),'origen':ORIGIN,'sintetico':True,'id_origen_sintetico':m['id_movimiento']}})
            if i%1000==0:print('Movimientos',i,flush=True)
        for sheet,collection,key in [('Demanda_Historica','demanda_historica','id_demanda'),('Pedidos','pedidos_sinteticos','id_pedido')]:
            from pymongo import UpdateOne
            rows=[]
            for r in data[sheet]:
                original=next(p for p in data['Productos'] if p['id_producto']==r['id_producto'])
                row={**r,'_id':ORIGIN+':'+r[key],'id_producto':products[r['id_producto']],'id_almacen':wid,'id_producto_origen':r['id_producto'],'producto_original':original['nombre'],'es_imputado':False}
                rows.append(UpdateOne({'_id':row['_id']},{'$setOnInsert':row},upsert=True))
            await db[collection].bulk_write(rows)
        for r in data['Inventario_Actual']:
            actual=await db.detalles_inventario.find_one({'id_detalle_inventario':details[r['id_producto']]})
            if abs(actual['stock_actual']-r['stock_final'])>1e-6:raise ValueError('Stock importado no reconciliado')
        return {'base':db.name,'empresa':TENANT,'mapeo_productos':products,'almacen':wid,'registros':{k:len(v) for k,v in data.items()},'sensores':await db.dispositivos.count_documents({'id_empresa':TENANT}),'reconciliacion':True,'nota_pedidos':'pedidos_sinteticos es un registro auxiliar, no órdenes operativas de reposición'}

async def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--file',default=str(OUT/'PsiTwin_Dataset_Pruebas_2025_2026.xlsx'));args=parser.parse_args()
    data=read_excel(args.file)
    client=AsyncIOMotorClient('mongodb://127.0.0.1:27017',serverSelectionTimeoutMS=3000)
    mongodb.database=client[DATABASE]
    try:
        result=await import_dataset(data,args.apply)
        (OUT/('importacion.json' if args.apply else 'preview_importacion.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=True))
    finally: client.close()

if __name__=='__main__':asyncio.run(main())
