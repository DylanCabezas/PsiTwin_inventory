import { describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import type { Plano, UbicacionStock } from '@/api/inventarioConsultas'
import { WarehouseMap, productosNivel, productosSinNivel } from './WarehouseMap'

vi.mock('@/api/monitoreo', () => ({ useMonitoreoVivo: () => null }))

const stock = (name: string, quantity = 1, rejected = false): UbicacionStock => ({ id_nivel: 'n1', producto: name, stock_actual: quantity, ubicacion_valida: true, rechazado: rejected } as UbicacionStock)
const plano = (): Plano => ({ almacen: { id: 'w', nombre: 'Central' }, zonas: [{ id: 'z', nombre: 'Zona B', capacidad: 5 }], racks: [{ id_rack: 'r', id_zona: 'z', codigo: 'R01', tipo_rack: 'Selectivo', max_niveles: 2, capacidad: 100, estado: 'DISPONIBLE' }], niveles: [{ id_nivel: 'n1', id_rack: 'r', numero: 1, codigo: 'N1', monitoreo: 'critico' }, { id_nivel: 'n2', id_rack: 'r', numero: 2, codigo: 'N2' }], inventario: [stock('Papaya'),stock('Papaya'),stock('Mango',0),stock('Rechazado',4,true)], alertas: [], generado_en: '' })

describe('WarehouseMap', () => {
  it('renders type, actual level count, unique available names and empty levels', () => {
    const html = renderToStaticMarkup(<WarehouseMap data={plano()} />)
    expect(html).toContain('Rack R01 — Selectivo')
    expect(html).toContain('2 niveles')
    expect(html.match(/Papaya/g)).toHaveLength(1)
    expect(html).toContain('Vacío')
    expect(html).not.toContain('Rechazado')
    expect(html).not.toContain('Mango')
    expect(html).toContain('data-nivel="n1" data-estado="critico"')
    expect(html).toContain('data-nivel="n2" data-estado="sin_datos"')
  })
  it('shows legacy fallback and expandable complete lists', () => {
    const data = plano(); delete data.racks[0]!.tipo_rack
    data.inventario = ['A','B','C','D','E','F'].map(n => stock(n))
    const html = renderToStaticMarkup(<WarehouseMap data={data} />)
    expect(html).toContain('Tipo no definido')
    expect(html).toContain('+3 productos')
    expect(html).toContain('D, E, F')
  })
  it('moves names when the server snapshot changes', () => {
    const data = plano()
    data.inventario.forEach(i => { if (i.producto === 'Papaya') i.id_nivel = 'n2' })
    expect(productosNivel(data,'n1')).toEqual([])
    expect(productosNivel(data,'n2')).toEqual(['Papaya'])
  })
  it('uses available quantities and shows rack stock without assigning a fictitious level', () => {
    const data = plano()
    data.inventario = [
      { ...stock('Reservado'), cantidad_disponible: 0 },
      { ...stock('Sin nivel'), id_rack: 'r', id_nivel: null },
      { ...stock('Otro rack'), id_rack: 'other', id_nivel: null },
    ]
    expect(productosNivel(data, 'n1')).toEqual([])
    expect(productosSinNivel(data, 'r')).toEqual(['Sin nivel'])
    const html = renderToStaticMarkup(<WarehouseMap data={data} />)
    expect(html).toContain('Productos sin nivel asignado:')
    expect(html).toContain('Sin nivel')
    expect(html).not.toContain('Reservado')
    expect(html).not.toContain('Otro rack')
  })
  it('refreshes rack codes, types, level codes and product names in an already mounted map', async () => {
    const host = document.createElement('div')
    const root = createRoot(host)
    try {
      await act(async () => root.render(<WarehouseMap data={plano()} />))
      expect(host.textContent).toContain('Papaya')
      const updated = plano()
      updated.racks[0]!.codigo = 'R-NUEVO'
      updated.racks[0]!.tipo_rack = 'Refrigerado'
      updated.niveles[0]!.codigo = 'N-RENOMBRADO'
      updated.inventario = [stock('Mango actualizado')]
      updated.racks.push({ ...updated.racks[0]!, id_rack: 'r2', codigo: 'R02' })
      await act(async () => root.render(<WarehouseMap data={updated} />))
      expect(host.textContent).toContain('Rack R-NUEVO — Refrigerado')
      expect(host.textContent).toContain('Nivel 1 · N-RENOMBRADO')
      expect(host.textContent).toContain('Mango actualizado')
      expect(host.textContent).toContain('Rack R02')
      expect(host.textContent).toContain('Sin niveles registrados')
      expect(host.textContent).not.toContain('Papaya')
      updated.racks = []
      await act(async () => root.render(<WarehouseMap data={{ ...updated }} />))
      expect(host.textContent).not.toContain('R-NUEVO')
      expect(host.textContent).not.toContain('Mango actualizado')
    } finally {
      await act(async () => root.unmount())
    }
  })
})
