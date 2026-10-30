import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { renderToStaticMarkup } from 'react-dom/server'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { analisisApi } from '@/api/analisis'
import { CsvDemandPanel } from './CsvDemandPanel'

vi.mock('@/api/analisis', () => ({ analisisApi: { csvColumns: vi.fn(), analyzeCsv: vi.fn() } }))
vi.mock('./DemandChart', () => ({ DemandChart: () => <div>Gráfico de demanda del CSV</div> }))
afterEach(() => { vi.resetAllMocks(); vi.unstubAllGlobals() })

describe('Carga y análisis de CSV', () => {
  it('explica datos obligatorios, conversión de tipos y límites antes de cargar', () => {
    const html = renderToStaticMarkup(<CsvDemandPanel />)
    expect(html).toContain('No necesitas declarar tipos de datos')
    expect(html).toContain('cantidad demandada')
    expect(html).toContain('fecha,producto,cantidad')
    expect(html).toContain('2 MB')
    expect(html).toContain('ni guarda registros')
  })
  it('permite elegir encabezados personalizados y muestra el análisis sin alterar inventario', async () => {
    vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
    const csv = 'Día;Artículo;Vendido\n01/10/2026;Arroz;12,5'
    vi.mocked(analisisApi.csvColumns).mockResolvedValue({ columnas: ['Día', 'Artículo', 'Vendido'], muestra: [{ Día: '01/10/2026', Artículo: 'Arroz', Vendido: '12,5' }], filas: 1 })
    vi.mocked(analisisApi.analyzeCsv).mockResolvedValue({ serie: 'Arroz', series: ['Arroz'], filas_archivo: 1, dias_observados: 1,
      fecha_inicio: '2026-10-01', fecha_fin: '2026-10-01', dias_sin_datos: 0, total: 12.5, promedio_diario: 12.5,
      minimo_diario: 12.5, maximo_diario: 12.5, historico: [{ fecha: '2026-10-01', cantidad: 12.5 }], predicciones: [], estado: 'ANALIZADO', detalle: null, advertencias: [] })
    const container = document.createElement('div'); const root = createRoot(container)
    try {
      await act(async () => root.render(<CsvDemandPanel />))
      const file = new File([csv], 'ventas.csv', { type: 'text/csv' })
      Object.defineProperty(file, 'text', { value: async () => csv })
      const input = container.querySelector('input[type=file]')!
      Object.defineProperty(input, 'files', { value: [file], configurable: true })
      await act(async () => input.dispatchEvent(new Event('change', { bubbles: true })))
      expect(analisisApi.csvColumns).toHaveBeenCalledWith(csv)
      const selects = container.querySelectorAll('select')
      for (const [index, value] of ['Día', 'Vendido', 'Artículo'].entries()) {
        await act(async () => { selects[index]!.value = value; selects[index]!.dispatchEvent(new Event('change', { bubbles: true })) })
      }
      const button = Array.from(container.querySelectorAll('button')).find(b => b.textContent === 'Analizar CSV')!
      await act(async () => button.dispatchEvent(new MouseEvent('click', { bubbles: true })))
      expect(analisisApi.analyzeCsv).toHaveBeenCalledWith({ contenido: csv, columna_fecha: 'Día', columna_cantidad: 'Vendido', columna_producto: 'Artículo', pronosticar: false })
      expect(container.textContent).toContain('Resultado del CSV: Arroz')
      expect(container.textContent).toContain('Gráfico de demanda del CSV')
      expect(container.textContent).toContain('12,5')
    } finally { await act(async () => root.unmount()) }
  })
  it('rechaza un archivo demasiado grande antes de enviarlo', async () => {
    vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
    const container = document.createElement('div'); const root = createRoot(container)
    try {
      await act(async () => root.render(<CsvDemandPanel />))
      const input = container.querySelector('input[type=file]')!
      Object.defineProperty(input, 'files', { value: [new File(['x'.repeat(2_000_001)], 'grande.csv')] })
      await act(async () => input.dispatchEvent(new Event('change', { bubbles: true })))
      expect(container.querySelector('[role=alert]')?.textContent).toContain('2 MB')
      expect(analisisApi.csvColumns).not.toHaveBeenCalled()
    } finally { await act(async () => root.unmount()) }
  })
})
