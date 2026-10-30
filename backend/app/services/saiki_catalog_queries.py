"""Deterministic catalogue-family answers, using authorized operational records."""
import calendar
import re
from collections import defaultdict
from app.database.mongodb import get_database
from app.services.clasificacion_service import normalizar
from app.dto.inventario_consulta_dto import InventarioFiltros

async def catalog_answer(data,user):
    text=normalizar(data.message or '')
    from app.services.clasificacion_service import CATALOGO
    known={normalizar(f) for group in CATALOGO for f in group['familias']}
    family_mentioned=any(re.search(r'\b'+re.escape(f)+r'\b',text) for f in known)
    explicit_month=bool(re.search(r'\b(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b',text))
    if not family_mentioned and not explicit_month and not re.search(r'hay sensores registrados|hay dispositivos registrados',text):return None
    db=get_database()
    if re.search(r'hay sensores registrados|hay dispositivos registrados',text):
        query={'id_empresa':user.id_empresa}
        if user.es_operario:query['id_almacen']=user.id_almacen
        count=await db.dispositivos.count_documents(query)
        return ('No hay dispositivos ni sensores registrados en el alcance autorizado. No hay lecturas de sensores.' if not count else f'Hay {count} dispositivos registrados; el registro no confirma lecturas actuales.'),{'dispositivos_registrados':count}
    products=await db.productos.find({'id_empresa':user.id_empresa},{'_id':0}).to_list(length=None)
    families={normalizar(p.get('familia','')) for p in products if p.get('familia')}
    matched=[f for f in families if re.search(r'\b'+re.escape(f)+r'\b',text)]
    month_match=re.search(r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b(?:(?: de)? (20\d{2}))?',text)
    if not matched and not month_match:return None
    if len(matched)>1:return None
    from app.services.inventario_consulta_service import consultar_inventario
    filters=InventarioFiltros(id_almacen=data.id_almacen,id_producto=data.id_producto,id_zona=data.id_zona,id_rack=data.id_rack,id_nivel=data.id_nivel)
    inv=await consultar_inventario(user,filters)
    allowed={r['id_producto'] for r in inv['ubicaciones']}
    family=matched[0] if matched else None
    selected={p['id_producto']:p for p in products if p['id_producto'] in allowed and (not family or normalizar(p.get('familia',''))==family)}
    locations=[r for r in inv['ubicaciones'] if r['id_producto'] in selected]
    history_question=bool(re.search(r'demanda|evolucion|histor|temporada',text))
    if history_question:
        warehouse_ids=[w.get('id',w.get('id_almacen')) for w in inv['almacenes']]
        query={'id_empresa':user.id_empresa,'id_producto':{'$in':list(selected)},'id_almacen':{'$in':warehouse_ids}}
        if month_match:
            month=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'].index(month_match[1])+1
            if month_match[2]:year=int(month_match[2])
            else:
                dates=await db.demanda_historica.distinct('fecha',{**query,'fecha':{'$regex':rf'^\d{{4}}-{month:02d}-'}})
                years={int(day[:4]) for day in dates}
                if len(years)!=1:return 'Indica el año del mes consultado; no hay un único año identificable en los datos autorizados.',{'anios_disponibles':sorted(years)}
                year=years.pop()
            query['fecha']={'$gte':f'{year}-{month:02d}-01','$lte':f'{year}-{month:02d}-{calendar.monthrange(year,month)[1]}'}
        rows=await db.demanda_historica.find(query,{'_id':0}).to_list(length=None)
        if not rows:return 'No hay demanda histórica registrada para esos filtros.',{'filtros':query}
        if month_match:
            totals=defaultdict(float)
            for r in rows:totals[r['id_producto']]+=r['cantidad']
            units={p.get('unidad','unidad') for p in selected.values()};lines=[]
            for unit in sorted(units):
                candidates=[(pid,q) for pid,q in totals.items() if selected[pid].get('unidad','unidad')==unit]
                if candidates:
                    pid,q=max(candidates,key=lambda r:r[1]);lines.append(f"Mayor demanda en {month_match[1]} de {year}, entre productos vendidos en {unit}: {selected[pid]['nombre']}, {q:g} {unit}.")
            return '\n'.join(lines)+' No se comparan kg con unidades.',{'demanda_por_producto':dict(totals),'filtros':query}
        totals=defaultdict(float)
        for r in rows:totals[(r['fecha'][:7],selected[r['id_producto']].get('unidad','unidad'))]+=r['cantidad']
        return ('Evolución histórica de '+family+' (demanda, no existencias ni pronóstico):\n'+'\n'.join(f'{month}: {q:g} {unit}' for (month,unit),q in sorted(totals.items()))),{'demanda_mensual':[{'mes':m,'unidad':u,'cantidad':q} for (m,u),q in sorted(totals.items())]}
    totals=defaultdict(float)
    for r in locations:totals[r.get('unidad','unidad')]+=r['stock_actual']
    lines=[f"Hay {len(selected)} productos distintos de la familia {family}. Existencias: "+', '.join(f'{q:g} {u}' for u,q in sorted(totals.items()))+'.']
    for row in locations:
        lines.append(f"{row['producto']}: {row['stock_actual']:g} {row.get('unidad','unidad')} · {row.get('almacen')} / {row.get('zona')} / Rack {row.get('rack')} / Nivel {row.get('nivel')}.")
    return '\n'.join(lines),{'productos_familia':list(selected),'ubicaciones':locations,'existencias_por_unidad':dict(totals)}

async def resolve_forecast_product(data,user):
    """Resolve explicit names only. Ambiguous names retain the normal clarification."""
    text=normalizar(data.message or '')
    if data.id_producto or not re.search(r'pronostic|predicci|demanda futura',text):return
    from app.services.analisis_service import service
    filters=await service.filters(user)
    candidates=[p for p in filters['productos'] if re.search(r'\b'+re.escape(normalizar(p['nombre']))+r'\b',text)]
    if len(candidates)==1:
        data.id_producto=candidates[0]['id']
        if not data.id_almacen and len(filters['almacenes'])==1:data.id_almacen=filters['almacenes'][0]['id']
        return True
