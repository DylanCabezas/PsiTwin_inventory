"""Reproducible synthetic fixture. Run from repository root; no database writes."""
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'outputs/psitwin_pruebas'
ORIGIN = 'PSITWIN-SINTETICO-2025-2026-v1'
TENANT = 'psitwin-synthetic-30-v1'
START, END = date(2025, 9, 28), date(2026, 10, 28)
NAMES = ['Papaya','Mango Kent','Piña Golden','Manzana roja','Manzana verde','Plátano de seda','Naranja','Mandarina','Limón','Fresa','Uva roja','Granadilla','Palta Hass','Sandía','Melón','Tomate','Zanahoria','Lechuga','Cebolla roja','Papa blanca','Camote amarillo','Brócoli','Pepino','Espinaca','Choclo','Yogur natural','Helado de vainilla','Helado de chocolate','Helado de fresa','Helado de lúcuma']
LOCATIONS = ['A1-1','A1-1','A1-2','B1-1','B1-1','A1-2','A2-1','A2-1','A2-1','B1-2','B1-2','A1-1','A1-2','A1-2','A1-1','B2-1','B2-1','B2-2','C2-1','C2-1','C2-1','B2-2','B2-1','B2-2','B2-1','B1-2','C1-2','C1-2','C1-1','C1-1']

def build():
    rng = random.Random(20260928)
    sheets = {}
    def add(sheet, **row):
        sheets.setdefault(sheet, []).append(dict(row, id_empresa=TENANT, origen=ORIGIN, sintetico=True))
    add('README', descripcion='DATOS SINTÉTICOS DE PRUEBA. Precios simulados en PEN, no cotizaciones.', periodo='2025-09-28 / 2026-10-28', semilla=20260928,
        importacion='Empresa > Almacenes > Zonas > Racks > Niveles > Productos > Ubicaciones > Demanda > Movimientos > Inventario > Pedidos',
        regla='Stock inicial cero; ENTRADA inicial explícita. Venta perdida = demanda - atendida. Sin stock negativo.',
        validacion='Entrenamiento hasta 2026-09-30; validación 2026-10-01..28. Referencia = promedio últimos 7 días de entrenamiento, NO AutoGluon.',
        conservacion='Frescos tropicales: rotación diaria a ambiente ventilado; hojas y yogur refrigerados; helados congelados. Sin lecturas reales.', plazo_entrega_dias=3)
    add('Empresa', nombre='PsiTwin — Empresa SINTÉTICA de pruebas', correo='synthetic30@example.invalid', ruc='00000000030')
    add('Almacenes', id_almacen='ABC1', codigo='ABC1', nombre='Almacén Central', descripcion='DATOS SINTÉTICOS DE PRUEBA')
    for code, name in [('A','Productos frescos'),('B','Productos refrigerados'),('C','Productos congelados y secos')]:
        add('Zonas', id_zona=code, id_almacen='ABC1', nombre=f'Zona {code} — {name}', max_racks=2)
    for code, kind, count in [('A1','Convencional',2),('A2','Convencional',1),('B1','Refrigerado',2),('B2','Refrigerado',2),('C1','Congelado',2),('C2','Convencional',1)]:
        add('Racks', id_rack=code, id_zona=code[0], codigo=code, tipo_rack=kind, max_niveles=count)
        for n in range(1,count+1):
            add('Niveles', id_nivel=f'{code}-{n}', id_rack=code, numero=n, codigo=f'{code}-{n}', capacidad_kg=10000, monitoreo='Sin datos de sensores')
    for i, name in enumerate(NAMES):
        pid = f'SYN-{i+1:03d}'
        family = 'Frutas' if i<15 else 'Tubérculos' if i in (19,20) else 'Verduras' if i<25 else 'Lácteos' if i==25 else 'Helados'
        unit = 'unidad' if i>=25 or i in (17,21,24) else 'kg'
        base = 9 + (i*7 % 24)
        minimum, maximum = base*2, base*9
        price = round(2.1+(i*1.37)%11,2)
        add('Productos', id_producto=pid, codigo=pid, nombre=name, familia=family, categoria='Congelados' if i>=26 else 'Refrigerados' if LOCATIONS[i][0]=='B' else 'Frescos', unidad=unit, precio_compra=price, precio_venta=round(price*1.45,2), moneda='PEN', stock_minimo=minimum, stock_maximo=maximum, activo=True, peso=0.12 if i>=26 else 0.2 if i==25 else 1, lead_time_dias=3)
        loc = LOCATIONS[i]
        add('Ubicaciones_Productos', id_ubicacion=pid+'-LOC', id_producto=pid, id_nivel=loc, id_rack=loc[:2], id_almacen='ABC1')
        stock = 0
        movements = []
        history = []
        def move(day, kind, qty, reason):
            nonlocal stock
            stock = round(stock + qty*(1 if kind=='ENTRADA' else -1),2)
            row = dict(id_movimiento=f'{pid}-{day}-{kind}', fecha=day.isoformat(), id_producto=pid, id_nivel=loc, id_rack=loc[:2], id_almacen='ABC1', tipo_movimiento=kind, cantidad=qty, unidad=unit, motivo=reason, stock_resultante=stock)
            if any(m['id_movimiento']==row['id_movimiento'] for m in movements):
                row['id_movimiento']+='-EXTRA'
            add('Movimientos', **row)
            movements.append(row)
        move(START,'ENTRADA',maximum,'APERTURA SINTÉTICA')
        for t in range((END-START).days+1):
            day = START+timedelta(days=t)
            season = 1+0.65*math.cos(2*math.pi*(day.timetuple().tm_yday-40)/365) if i>=26 else 1+0.27*math.sin(2*math.pi*t/365+i*0.73) if i<15 else 1+0.05*math.sin(t/29+i)
            weekly = (1.25 if day.weekday()>=5 else 0.94) if i>=26 or i<15 else (0.9 if day.weekday()>=5 else 1.04)
            holiday = 1.4 if (day.month,day.day) in [(12,24),(12,31),(7,28),(1,1)] else 1
            qty = max(0,base*season*weekly*holiday*(1+t*(i%5-2)/16000)*rng.uniform(.72,1.28))
            qty = 0 if rng.random()<.025 else round(qty,0 if unit=='unidad' else 2)
            # End scenarios deliberately include a stockout, low and excess stock.
            if stock<minimum and not (i in (0,1) and day>=END-timedelta(days=10)):
                move(day,'ENTRADA',round(maximum-stock,2),'REPOSICIÓN SINTÉTICA')
            served = min(stock,qty)
            if served: move(day,'SALIDA',served,'VENTA SINTÉTICA')
            add('Demanda_Historica', id_demanda=f'{pid}-{day}', fecha=day.isoformat(), id_producto=pid, id_almacen='ABC1', cantidad=qty, cantidad_atendida=served, demanda_insatisfecha=round(qty-served,2), unidad=unit)
            add('Pedidos', id_pedido=f'PED-{pid}-{day}', fecha=day.isoformat(), id_producto=pid, cantidad_solicitada=qty, cantidad_atendida=served, estado='VENTA_PERDIDA' if qty>served else 'ATENDIDO', unidad=unit)
            history.append((day,qty))
        if i==2: move(END,'ENTRADA',maximum,'EXCESO SINTÉTICO PARA PRUEBA')
        add('Inventario_Actual', id_producto=pid, id_nivel=loc, id_rack=loc[:2], id_almacen='ABC1', fecha=END.isoformat(), stock_inicial=0, entradas=round(sum(m['cantidad'] for m in movements if m['tipo_movimiento']=='ENTRADA'),2), salidas=round(sum(m['cantidad'] for m in movements if m['tipo_movimiento']=='SALIDA'),2), ajustes=0, stock_final=stock, stock_consolidado_producto=stock, unidad=unit)
        ref = sum(q for d,q in history if date(2026,9,24)<=d<=date(2026,9,30))/7
        for n in range(28):
            add('Pronosticos_Referencia', fecha=(date(2026,10,1)+timedelta(days=n)).isoformat(), id_producto=pid, cantidad=round(ref,2), unidad=unit, metodo='PROMEDIO_7D_REFERENCIA_NO_AUTOGLUON', corte_entrenamiento='2026-09-30')
    for key,count in [('Productos',30),('Almacenes',1),('Zonas',3),('Racks',6),('Niveles',10)]:
        add('Validaciones', comprobacion=key, esperado=count, observado=len(sheets[key]), resultado=len(sheets[key])==count)
    for row in sheets['Inventario_Actual']:
        add('Validaciones', comprobacion='Reconciliación '+row['id_producto'], esperado=row['stock_final'], observado=round(row['entradas']-row['salidas'],2), resultado=abs(row['entradas']-row['salidas']-row['stock_final'])<1e-6)
    order=['README','Empresa','Almacenes','Zonas','Racks','Niveles','Productos','Ubicaciones_Productos','Demanda_Historica','Movimientos','Inventario_Actual','Pedidos','Validaciones','Pronosticos_Referencia']
    return {k:sheets[k] for k in order}

if __name__=='__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    data=build()
    (OUT/'dataset.json').write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding='utf-8')
    print(json.dumps({k:len(v) for k,v in data.items()}))
