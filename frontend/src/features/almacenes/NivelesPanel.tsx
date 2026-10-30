import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { abastecimientoApi, type Nivel } from '@/api/abastecimiento'
import { useInventariosPorRack } from '@/api/inventarios'
import { useProductos } from '@/api/productos'
import { ApiError } from '@/api/client'
import { useRol } from '@/auth/useRol'
import { Button, Field, Input, Select } from '@/components/ui'
import type { Rack } from '@/api/types'
import { formatNumero } from '@/lib/format'

export function NivelesPanel({ rack, gestionar = true }: { rack: Rack; gestionar?: boolean }) {
  const query = useQuery({ queryKey: ['niveles', rack.id_rack], queryFn: () => abastecimientoApi.niveles(rack.id_rack) })
  const inventory = useInventariosPorRack(rack.id_rack)
  const products = useProductos()
  const qc = useQueryClient()
  const { esEmpresa } = useRol()
  const [form, setForm] = useState<{ level?: Nivel } | null>(null)
  const [code, setCode] = useState('')
  const [number, setNumber] = useState('')
  const [capacity, setCapacity] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const levels = [...(query.data ?? [])].sort((a, b) => b.numero - a.numero)
  const available = Array.from({ length: rack.max_niveles ?? 1 }, (_, i) => i + 1).filter(n => !levels.some(level => level.numero === n))
  const selected = available.includes(Number(number)) ? number : String(available[0] ?? '')
  const openForm = (level?: Nivel) => {
    setCode(level?.codigo ?? `N-${available[0] ?? 1}`)
    setCapacity(level?.capacidad_kg == null ? '' : String(level.capacidad_kg))
    setNumber(String(level?.numero ?? available[0] ?? ''))
    setError(''); setForm(level ? { level } : {})
  }
  const save = async () => {
    if (!form || !code.trim() || !Number.isFinite(Number(capacity)) || Number(capacity) <= 0) return
    setBusy(true); setError('')
    try {
      if (form.level) await abastecimientoApi.actualizarNivel(form.level.id_nivel, { codigo: code.trim(), capacidad_kg: Number(capacity) })
      else await abastecimientoApi.crearNivel(rack.id_rack, { codigo: code.trim(), numero: Number(selected), capacidad_kg: Number(capacity) })
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['niveles', rack.id_rack] }),
        qc.invalidateQueries({ queryKey: ['plano'] }),
      ])
      setForm(null)
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.detail : 'No se pudo guardar el nivel.')
    } finally { setBusy(false) }
  }
  return <section className="mb-4 space-y-3" aria-label="Niveles del rack">
    <div className="flex items-center justify-between gap-2"><h3 className="font-semibold">Niveles · {levels.length} de {rack.max_niveles ?? 1}</h3>
      {esEmpresa && gestionar && available.length > 0 && !form && <Button size="sm" onClick={() => openForm()} disabled={query.isPending || query.isError}>Crear nivel</Button>}
    </div>
    {query.isError ? <p role="alert">No se pudieron consultar los niveles. <Button onClick={() => void query.refetch()}>Reintentar</Button></p>
      : query.isPending ? <p role="status">Consultando niveles…</p>
      : !levels.length ? <p className="text-sm text-fg-muted">Crea hasta {rack.max_niveles ?? 1} niveles dentro de este rack. Define la carga máxima de cada nivel en kg.</p>
      : levels.map(level => {
        const rows = inventory.data?.filter(i => i.id_nivel === level.id_nivel && i.stock_actual > 0) ?? []
        return <article key={level.id_nivel} data-nivel={level.id_nivel} className="rounded-lg border-x-2 border-b-4 border-t border-border-strong bg-surface-2 p-3">
          <div className="flex items-center justify-between gap-2"><h4 className="font-semibold">Nivel {level.numero} · {level.codigo}</h4>
            {esEmpresa && gestionar && <Button size="sm" variant="ghost" disabled={busy} onClick={() => openForm(level)}>Configurar</Button>}
          </div>
          <p className="text-xs text-fg-muted">{level.capacidad_kg == null ? 'Carga máxima pendiente de configurar' : `${formatNumero(level.carga_kg ?? 0)} / ${formatNumero(level.capacidad_kg)} kg · ${formatNumero(level.libre_kg ?? 0)} kg libres`}</p>
          {!inventory.isPending && !inventory.isError && <p className="mt-2 font-mono text-xs text-fg-muted">{new Set(rows.map(row => row.id_producto)).size} prod.</p>}
          {inventory.isError ? <p role="alert">No se pudieron consultar los productos.</p> : inventory.isPending ? <p role="status">Consultando productos…</p>
            : rows.length ? <ul className="mt-2 space-y-1 text-sm">{rows.map(row => {
              const product = products.data?.find(p => p.id_producto === row.id_producto) ?? row.producto
              return <li key={row.id_detalle_inventario ?? row.id_inventario}>{product?.nombre ?? 'Producto pendiente de consultar'} · {formatNumero(row.stock_actual)} {product?.unidad ?? 'unidades'}</li>
            })}</ul> : <p className="mt-2 text-sm text-fg-muted">Sin productos</p>}
        </article>
      })}
    {form && <form onSubmit={event => { event.preventDefault(); void save() }} className="space-y-3 rounded-lg border border-border p-3">
      <h4 className="font-semibold">{form.level ? `Configurar nivel ${form.level.numero}` : 'Crear nivel'}</h4>
      <Field label="Código del nivel" required><Input value={code} onChange={e => setCode(e.target.value)} maxLength={50} required disabled={busy} /></Field>
      {!form.level && <Field label="Número del nivel" required><Select value={selected} onChange={e => setNumber(e.target.value)} placeholder={false} options={available.map(n => ({ value: String(n), label: `Nivel ${n}` }))} disabled={busy} /></Field>}
      <Field label="Carga máxima del nivel" required><Input type="number" min="0.001" step="any" suffix="kg" value={capacity} onChange={e => setCapacity(e.target.value)} required disabled={busy} /></Field>
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      <div className="flex gap-2"><Button type="submit" size="sm" loading={busy} disabled={!code.trim() || !capacity || Number(capacity) <= 0 || (!form.level && !selected)}>Guardar nivel</Button><Button size="sm" variant="ghost" disabled={busy} onClick={() => setForm(null)}>Cancelar</Button></div>
    </form>}
  </section>
}
