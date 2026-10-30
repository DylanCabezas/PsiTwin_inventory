/**
 * Detalle de zona: CRUD de racks mostrados como una grilla de posiciones (filas = niveles, color = estado)
 * y, para el rack seleccionado, el inventario que contiene (stock_actual vs mínimo/máximo con StockBadge).
 * El rack seleccionado se guarda en `?rack=<id>` para poder compartir el enlace.
 */
import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router'
import { useAlmacen } from '@/api/almacenes'
import { ApiError } from '@/api/client'
import { ESTADO_RACK_LABEL, ESTADOS_RACK_EDITABLES } from '@/api/enums'
import { useInventarios } from '@/api/inventarios'
import { useDeleteRack, useRacksPorZona } from '@/api/racks'
import type { Inventario, Rack } from '@/api/types'
import { useZona } from '@/api/zonas'
import { useRol } from '@/auth/useRol'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LinkButton,
  LoadingBlock,
  PageHeader,
  StatusBadge,
} from '@/components/ui'
import { cn } from '@/lib/cn'
import { formatNumero } from '@/lib/format'
import { temperaturaRack } from '@/lib/racks'
import { paths } from '@/paths'
import { EliminarDialog } from './EliminarDialog'
import { RackGrilla } from './RackGrilla'
import { RackFormModal } from './RackForm'
import { agruparPorNivel, codigoRack, estiloRack } from './ubicacionUtils'

export default function ZonaDetallePage() {
  const { idAlmacen = '', idZona } = useParams()
  const almacenQ = useAlmacen(idAlmacen || undefined)
  const zonaQ = useZona(idZona)
  const zona = zonaQ.data
  const back = { to: paths.almacen(idAlmacen), label: almacenQ.data?.nombre ?? 'Almacén' }

  if (zonaQ.isLoading) return <LoadingBlock label="Cargando zona…" />
  if (zonaQ.error || !zona || (zona.id_almacen && idAlmacen && zona.id_almacen !== idAlmacen)) {
    const noExiste = !zona || (zonaQ.error instanceof ApiError && zonaQ.error.isNotFound)
    return (
      <>
        <PageHeader title="Zona" back={back} />
        {zonaQ.error && !noExiste ? (
          <ErrorState error={zonaQ.error} onRetry={() => void zonaQ.refetch()} />
        ) : (
          <EmptyState
            icon="layers"
            title="Zona no encontrada"
            description="Puede que haya sido eliminada o que no pertenezca a este almacén."
            action={<LinkButton to={back.to}>Volver al almacén</LinkButton>}
          />
        )}
      </>
    )
  }

  return <Contenido idZona={zona.id_zona} back={back} />
}

/* ------------------------------------------------------------------ */

function Contenido({ idZona, back }: { idZona: string; back: { to: string; label: string } }) {
  const zona = useZona(idZona).data!
  const racksQ = useRacksPorZona(idZona)
  const invQ = useInventarios()
  const [params, setParams] = useSearchParams()
  const [form, setForm] = useState<{ rack: Rack | null } | null>(null)
  const [aEliminar, setAEliminar] = useState<Rack | null>(null)
  const del = useDeleteRack()
  const { esEmpresa, esOperario } = useRol()

  const racks = racksQ.data ?? []
  const niveles = agruparPorNivel(racks)
  const posiciones = new Map<string, string>()
  for (const n of niveles) for (const { rack, posicion } of n.racks) posiciones.set(rack.id_rack, codigoRack(rack, posicion))

  // Resumen de inventario por rack (una sola petición cacheada, compartida con Inicio / Inventario).
  const invPorRack = new Map<string, Inventario[] | undefined>()
  if (invQ.data) for (const r of racks) invPorRack.set(r.id_rack, [])
  for (const inv of invQ.data ?? []) invPorRack.set(inv.id_rack, [...(invPorRack.get(inv.id_rack) ?? []), inv])

  const paramRack = params.get('rack')
  const seleccionado = racks.find((r) => r.id_rack === paramRack) ?? racks[0] ?? null
  const seleccionar = (id: string) =>
    setParams(
      (p) => {
        p.set('rack', id)
        return p
      },
      { replace: true, preventScrollReset: true },
    )

  const conteoEstados = new Map<string, number>()
  for (const r of racks) conteoEstados.set(r.estado, (conteoEstados.get(r.estado) ?? 0) + 1)
  const estadosLeyenda = [...ESTADOS_RACK_EDITABLES, ...(['ACTIVO', 'INACTIVO'] as const).filter((e) => conteoEstados.has(e))]

  return (
    <>
      <PageHeader
        back={back}
        eyebrow={`Zona · ${back.label}`}
        title={zona.nombre}
        meta={
          <>
            <Badge tone="accent">{zona.tipo_zona}</Badge>
            <Badge tone="info" dot={false}>
              {zona.refrigerada ? 'Refrigerada' : 'No refrigerada'}
            </Badge>
            <Badge tone="neutral" dot={false}>
              {racks.length} de {formatNumero(zona.max_racks ?? zona.capacidad)} racks
            </Badge>
          </>
        }
        {...(esEmpresa
          ? {
              actions: (
                <Button icon="plus" onClick={() => setForm({ rack: null })}>
                  Nuevo rack
                </Button>
              ),
            }
          : {})}
      />

      {racksQ.isLoading ? (
        <LoadingBlock label="Cargando racks…" />
      ) : racksQ.error ? (
        <ErrorState error={racksQ.error} onRetry={() => void racksQ.refetch()} />
      ) : racks.length === 0 ? (
        <EmptyState
          icon="layers"
          title="Esta zona no tiene racks"
          description={esEmpresa ? 'Agrega racks para ubicar productos e inventario en esta zona.' : 'La empresa aún no creó racks en esta zona.'}
          {...(esEmpresa
            ? {
                action: (
                  <Button icon="plus" onClick={() => setForm({ rack: null })}>
                    Crear primer rack
                  </Button>
                ),
              }
            : {})}
        />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_26rem]">
          <section aria-labelledby="titulo-grilla" className="min-w-0">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <h2 id="titulo-grilla" className="label-stencil">
                Racks <span className="tabular">({racks.length})</span>
              </h2>
              <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-fg-muted" aria-label="Leyenda de estados">
                {estadosLeyenda.map((e) => (
                  <li key={e} className="inline-flex items-center gap-1.5">
                    <span className={cn('size-2.5 rounded-sm', estiloRack(e).punto)} aria-hidden="true" />
                    {ESTADO_RACK_LABEL[e]} <span className="tabular font-mono">({conteoEstados.get(e) ?? 0})</span>
                  </li>
                ))}
              </ul>
            </div>

            <RackGrilla racks={racks} seleccionado={seleccionado?.id_rack} onSelect={(r) => seleccionar(r.id_rack)} />
            <p className="mt-2 text-xs text-fg-subtle">Cada rack muestra sus niveles y los productos de cada nivel. Selecciona su cabecera para configurarlo.</p>
          </section>

          {seleccionado && (
            <RackPanel
              key={seleccionado.id_rack}
              rack={seleccionado}
              codigo={posiciones.get(seleccionado.id_rack) ?? ''}
              {...(esOperario || esEmpresa ? { onEditar: () => setForm({ rack: seleccionado }) } : {})}
              {...(esEmpresa ? { onEliminar: () => setAEliminar(seleccionado) } : {})}
            />
          )}
        </div>
      )}

      <RackFormModal
        open={!!form}
        idZona={idZona}
        rack={form?.rack ?? null}
        refrigerada={zona.refrigerada}
        niveles={zona.max_racks ?? zona.capacidad}
        nivelesOcupados={racks.map((r) => r.nivel)}
        onClose={() => setForm(null)}
        onGuardado={(r) => seleccionar(r.id_rack)}
      />
      <EliminarDialog
        open={!!aEliminar}
        title="Eliminar rack"
        description={
          <>
            Se eliminará el rack <strong className="text-fg">{aEliminar ? posiciones.get(aEliminar.id_rack) : ''}</strong>.
            {aEliminar && (invPorRack.get(aEliminar.id_rack)?.length ?? 0) > 0
              ? ' Contiene inventario: el sistema puede impedir la eliminación.'
              : ' Esta acción no se puede deshacer.'}
          </>
        }
        accion={() => del.mutateAsync(aEliminar!.id_rack)}
        mensajeExito="Rack eliminado"
        tituloError="No se pudo eliminar el rack"
        onClose={() => setAEliminar(null)}
        onEliminado={() =>
          setParams(
            (p) => {
              p.delete('rack')
              return p
            },
            { replace: true, preventScrollReset: true },
          )
        }
      />
    </>
  )
}

/* ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ */

function RackPanel({ rack, codigo, onEditar, onEliminar }: { rack: Rack; codigo: string; onEditar?: () => void; onEliminar?: () => void }) {
  const temp = temperaturaRack(rack)

  return (
    <Card
      as="section"
      aria-live="polite"
      eyebrow="Rack seleccionado"
      title={
        <span className="flex flex-wrap items-center gap-2">
          <span className="font-mono">{codigo}</span>
          <StatusBadge estado={rack.estado} />
        </span>
      }
      description={`${rack.tipo_rack || 'Tipo no definido'} · Hasta ${rack.max_niveles ?? 1} ${(rack.max_niveles ?? 1) === 1 ? 'nivel' : 'niveles'}${temp ? ` · ${temp}` : ''}`}
      actions={
        <>
          {onEditar && (
            <Button variant="secondary" size="sm" icon="edit" onClick={onEditar}>
              Estado{temp ? ' y temperatura' : ''}
            </Button>
          )}
          {onEliminar && (
            <Button variant="ghost" size="sm" iconOnly icon="trash" aria-label={`Eliminar rack ${codigo}`} onClick={onEliminar} className="hover:text-danger" />
          )}
        </>
      }
      className="self-start xl:sticky xl:top-4"
    />
  )
}
