import { Card } from '@/components/ui'
import { DemandChart } from './DemandChart'

const history = [12, 15, 10, 18, 14, 20, 16, 19, 13, 21, 17, 22].map((cantidad, index) => ({
  fecha: `2026-10-${String(index + 1).padStart(2, '0')}`, cantidad,
}))

export function AnalysisDemo() {
  return <Card title="Gráfica con datos de ejemplo" description="Datos ficticios para mostrar cómo se lee la gráfica; no corresponden al inventario ni a pedidos de la empresa.">
    <p className="mb-4 text-sm text-fg-muted">Serie ilustrativa de demanda diaria. No es un pronóstico generado por el modelo.</p>
    <DemandChart history={history} predictions={[]} />
  </Card>
}
