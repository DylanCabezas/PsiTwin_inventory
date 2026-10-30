import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { renderToStaticMarkup } from 'react-dom/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Nivel } from '@/api/abastecimiento'
import { abastecimientoApi } from '@/api/abastecimiento'
import type { Rack } from '@/api/types'
import { NivelesPanel } from './NivelesPanel'

const state = vi.hoisted(() => ({ levels: [] as Nivel[], invalidate: vi.fn().mockResolvedValue(undefined) }))
vi.mock('@tanstack/react-query', () => ({ useQuery: () => ({ data: state.levels, isPending: false, isError: false }), useQueryClient: () => ({ invalidateQueries: state.invalidate }) }))
vi.mock('@/auth/useRol', () => ({ useRol: () => ({ esEmpresa: true }) }))
vi.mock('@/api/abastecimiento', () => ({ abastecimientoApi: { crearNivel: vi.fn(), actualizarNivel: vi.fn() } }))
vi.mock('@/api/inventarios', () => ({ useInventariosPorRack: () => ({ data: [{ id_detalle_inventario: 'd', id_nivel: 'n1', id_producto: 'p', stock_actual: 5 }], isPending: false, isError: false }) }))
vi.mock('@/api/productos', () => ({ useProductos: () => ({ data: [{ id_producto: 'p', nombre: 'Mango', unidad: 'kg' }] }) }))

const rack = { id_rack: 'r', max_niveles: 2 } as Rack
beforeEach(() => {
  vi.clearAllMocks()
  state.levels = [{ id_nivel: 'n1', id_rack: 'r', codigo: 'N-1', numero: 1, capacidad_kg: 100, carga_kg: 5, libre_kg: 95 }]
})

describe('NivelesPanel', () => {
  it('shows level capacity and its products without the old state controls', () => {
    const html = renderToStaticMarkup(<NivelesPanel rack={rack} />)
    expect(html).toContain('Niveles · 1 de 2')
    expect(html).toContain('5 / 100 kg · 95 kg libres')
    expect(html).toContain('Mango · 5 kg')
    expect(html).toContain('1 prod.')
    expect(html).toContain('Crear nivel')
    expect(html).not.toContain('Desactivar')
    expect(html).not.toContain('Archivar')
    expect(html).not.toContain('Eliminar nivel')
  })

  it('creates only a free level number with its kg limit and refreshes the map', async () => {
    vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
    const host = document.createElement('div')
    const root = createRoot(host)
    vi.mocked(abastecimientoApi.crearNivel).mockImplementation(async (_rack, body) => {
      const created = { ...body, id_rack: 'r', id_nivel: 'n2', carga_kg: 0, libre_kg: body.capacidad_kg }
      state.levels = [...state.levels, created]
      return created
    })
    try {
      await act(async () => root.render(<NivelesPanel rack={rack} />))
      const create = [...host.querySelectorAll('button')].find(b => b.textContent === 'Crear nivel')!
      await act(async () => create.click())
      expect([...host.querySelectorAll('option')].map(o => o.value)).toEqual(['2'])
      const capacity = host.querySelector('input[type="number"]')!
      await act(async () => {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(capacity, '50')
        capacity.dispatchEvent(new Event('input', { bubbles: true }))
      })
      await act(async () => { host.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })) })
      expect(abastecimientoApi.crearNivel).toHaveBeenCalledWith('r', { codigo: 'N-2', numero: 2, capacidad_kg: 50 })
      expect(state.invalidate).toHaveBeenCalledWith({ queryKey: ['niveles', 'r'] })
      expect(state.invalidate).toHaveBeenCalledWith({ queryKey: ['plano'] })
      expect(host.textContent).toContain('Niveles · 2 de 2')
      expect([...host.querySelectorAll('button')].some(b => b.textContent === 'Crear nivel')).toBe(false)
    } finally {
      await act(async () => root.unmount())
      vi.unstubAllGlobals()
    }
  })
})
