// @vitest-environment jsdom
import { readFileSync } from 'node:fs'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { DemandChart } from './DemandChart'
const dataset = JSON.parse(readFileSync('../outputs/psitwin_pruebas/dataset.json','utf8'))
describe('Synthetic Excel dataset: real application charts', () => {
  for (const product of dataset.Productos) it(`renders ${product.nombre}`, () => {
    const history = dataset.Demanda_Historica.filter((r: any) => r.id_producto === product.id_producto)
    const markup = renderToStaticMarkup(<DemandChart history={history} predictions={[]} />)
    expect(markup).toContain('<polyline')
    expect(markup).not.toContain('NaN')
    expect(markup).toContain('396')
  })
  it('spaces irregular dates using elapsed time', () => {
    const html=renderToStaticMarkup(<DemandChart history={[
      {fecha:'2026-01-01',cantidad:1},{fecha:'2026-01-02',cantidad:2},{fecha:'2026-01-11',cantidad:3}
    ]} predictions={[]} />)
    const points=html.match(/<polyline points="([^"]+)/)![1]!.split(' ').map(s=>Number(s.split(',')[0]))
    expect((points[2]!-points[1]!)/(points[1]!-points[0]!)).toBeCloseTo(9)
  })
})
