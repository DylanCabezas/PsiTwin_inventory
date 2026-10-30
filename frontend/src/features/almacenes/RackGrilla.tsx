/** Cada rack contiene sus niveles; los productos y sus cantidades pertenecen al nivel. */
import { ESTADO_RACK_LABEL } from '@/api/enums'
import type { Rack } from '@/api/types'
import { cn } from '@/lib/cn'
import { temperaturaRack } from '@/lib/racks'
import { codigoRack, estiloRack } from './ubicacionUtils'
import { NivelesPanel } from './NivelesPanel'

export interface RackGrillaProps {
  racks: Rack[]
  seleccionado?: string | null | undefined
  onSelect?: (rack: Rack) => void
}

export function RackGrilla({ racks, seleccionado, onSelect }: RackGrillaProps) {
  const ordenados = [...racks].sort((a, b) => a.codigo.localeCompare(b.codigo, 'es', { numeric: true }))
  return <ul aria-label="Racks de la zona" className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,17rem),1fr))] items-start gap-4">
    {ordenados.map((rack, index) => <li key={rack.id_rack}>
      <RackCelda rack={rack} codigo={codigoRack(rack, index + 1)} seleccionado={seleccionado === rack.id_rack}
        {...(onSelect ? { onClick: () => onSelect(rack) } : {})} />
    </li>)}
  </ul>
}

export interface RackCeldaProps {
  rack: Rack
  codigo: string
  seleccionado: boolean
  onClick?: () => void
}

export function RackCelda({ rack, codigo, seleccionado, onClick }: RackCeldaProps) {
  const est = estiloRack(rack.estado)
  const label = ESTADO_RACK_LABEL[rack.estado] ?? rack.estado
  const temp = temperaturaRack(rack)
  const Tag = onClick ? 'button' : 'div'
  return <article aria-label={`Rack ${codigo}`} className={cn(
    'overflow-hidden rounded-xl border-2 bg-surface shadow-card', est.celda,
    seleccionado && 'ring-2 ring-focus ring-offset-2 ring-offset-surface',
  )}>
    <Tag data-rack-header="" {...(onClick ? { type: 'button' as const, onClick, 'aria-pressed': seleccionado } : {})}
      className="flex w-full flex-col gap-1 border-b border-border p-3 text-left">
      <span className="flex items-center justify-between gap-2"><strong className="font-mono">Rack {codigo}</strong>
        <span className="inline-flex items-center gap-1.5 text-xs"><span className={cn('size-2 rounded-full', est.punto)} aria-hidden="true" />{label}</span>
      </span>
      <span className="text-sm text-fg-muted">{rack.tipo_rack || 'Tipo no definido'}</span>
      <span className="text-xs text-fg-muted">{rack.max_niveles ?? 1} {(rack.max_niveles ?? 1) === 1 ? 'nivel' : 'niveles'}</span>
      {temp && <span className="font-mono text-xs text-info">{temp}</span>}
    </Tag>
    <div data-rack-levels="" className="bg-surface p-3"><NivelesPanel rack={rack} gestionar={seleccionado} /></div>
  </article>
}
