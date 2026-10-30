"""Weight belongs to a rack level, never to the rack itself."""
from fastapi import HTTPException
from app.database.mongodb import get_database


def peso_entrada(producto, cantidad):
    return float(cantidad) * (1.0 if producto.get('unidad') == 'kg' else float(producto.get('peso') or 0))


class NivelService:
    @staticmethod
    async def enriquecer(levels):
        if not levels:
            return []
        db = get_database()
        rows = await db['detalles_inventario'].find(
            {'id_nivel': {'$in': [n['id_nivel'] for n in levels]}}, {'_id': 0}).to_list(length=None)
        products = await db['productos'].find(
            {'id_producto': {'$in': list({r['id_producto'] for r in rows})}},
            {'_id': 0, 'id_producto': 1, 'unidad': 1, 'peso': 1}).to_list(length=None)
        products = {p['id_producto']: p for p in products}
        result = []
        for level in levels:
            load = round(sum(peso_entrada(products.get(r['id_producto'], {}), r.get('stock_actual', 0))
                             for r in rows if r['id_nivel'] == level['id_nivel'] and r.get('id_rack') == level['id_rack']), 3)
            capacity = level.get('capacidad_kg')
            result.append({**level, 'capacidad_kg': capacity, 'carga_kg': load,
                           'libre_kg': round(capacity - load, 3) if capacity is not None else None})
        return result

    @staticmethod
    async def validar_ingreso(rack_id, nivel_id, producto, cantidad):
        if not nivel_id:
            raise HTTPException(422, 'Seleccione un nivel del rack para ubicar el producto')
        level = await get_database()['niveles'].find_one(
            {'id_rack': rack_id, 'id_nivel': nivel_id}, {'_id': 0})
        if not level or level.get('estado', 'ACTIVO') != 'ACTIVO':
            raise HTTPException(409, 'El nivel no pertenece al rack seleccionado o no está activo')
        level = (await NivelService.enriquecer([level]))[0]
        if cantidad > 0:
            NivelService.validar_carga(level, producto, cantidad)
        return level

    @staticmethod
    def validar_carga(level, producto, cantidad):
        if level.get('capacidad_kg') is None:
            raise HTTPException(409, 'Configure la carga máxima en kg del nivel antes de ingresar productos')
        if producto.get('unidad') != 'kg' and not producto.get('peso'):
            raise HTTPException(409, 'Configure el peso unitario del producto para validar la capacidad del nivel')
        load = peso_entrada(producto, cantidad)
        if load > level['libre_kg'] + 1e-9:
            raise HTTPException(409, f"Capacidad insuficiente en el nivel {level['codigo']}. "
                                f"Libre: {max(level['libre_kg'], 0):g} kg. Carga a ingresar: {load:g} kg")
