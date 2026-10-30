import { describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import type { Rack } from '@/api/types'
import { RackGrilla } from './RackGrilla'

vi.mock('@tanstack/react-query', () => ({
  useQuery: ({ queryKey }: { queryKey: string[] }) => ({
    data: Array.from({ length: queryKey[1] === 'r1' ? 3 : 1 }, (_, i) => ({
      id_nivel: `${queryKey[1]}-n${i + 1}`, id_rack: queryKey[1], numero: i + 1, codigo: `N-${i + 1}`, capacidad_kg: 100, carga_kg: i ? 0 : 5, libre_kg: i ? 100 : 95,
    })), isPending: false, isError: false,
  }),
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}))
vi.mock('@/auth/useRol', () => ({ useRol: () => ({ esEmpresa: false }) }))
vi.mock('@/api/inventarios', () => ({ useInventariosPorRack: (rack: string) => ({ data: rack === 'r1' ? [
  { id_detalle_inventario: 'd', id_nivel: 'r1-n1', id_producto: 'p', stock_actual: 5 },
] : [], isPending: false, isError: false }) }))
vi.mock('@/api/productos', () => ({ useProductos: () => ({ data: [{ id_producto: 'p', nombre: 'Mango', unidad: 'kg' }] }) }))

describe('RackGrilla', () => {
  it('shows racks within the zone and the configured number of levels inside each rack', () => {
    const rack = { id_rack: 'r1', id_zona: 'z', codigo: 'R01', nivel: 1, max_niveles: 3,
      tipo_rack: 'Selectivo', capacidad: 100, carga_kg: 0, libre_kg: 100, estado: 'DISPONIBLE', temperatura_min: 2, temperatura_max: 8 } as Rack
    const html = renderToStaticMarkup(<RackGrilla racks={[rack, { ...rack, id_rack: 'r2', codigo: 'R02', max_niveles: 1 }]} />)
    expect(html).toContain('Racks de la zona')
    expect(html).toContain('3 niveles')
    expect(html).toContain('1 nivel')
    expect(html).not.toContain('aria-label="Nivel 1"')
    expect(html).not.toContain('Agregar nivel')
    expect(html).not.toContain('Eliminar nivel')
    const document = new DOMParser().parseFromString(html, 'text/html')
    const racks = document.querySelectorAll('article[aria-label^="Rack "]')
    expect(racks).toHaveLength(2)
    const first = racks[0]!
    const header = first.querySelector('[data-rack-header]')!
    expect(header.textContent).toContain('Selectivo')
    expect(header.textContent).toContain('3 niveles')
    expect(header.textContent).toContain('2 a 8 °C')
    expect(header.textContent).not.toContain('prod.')
    expect(header.textContent).not.toContain('Mango')
    expect(header.textContent).not.toContain('kg')
    const levels = first.querySelectorAll('[data-nivel]')
    expect([...levels].map(level => level.getAttribute('data-nivel'))).toEqual(['r1-n3', 'r1-n2', 'r1-n1'])
    expect(first.querySelector('[data-nivel="r1-n1"]')!.textContent).toContain('1 prod.')
    expect(first.querySelector('[data-nivel="r1-n1"]')!.textContent).toContain('Mango · 5 kg')
    expect(first.querySelector('[data-nivel="r1-n2"]')!.textContent).not.toContain('Mango')
    expect(racks[1]!.querySelectorAll('[data-nivel]')).toHaveLength(1)
    expect(racks[1]!.textContent).not.toContain('Mango')
  })
})
