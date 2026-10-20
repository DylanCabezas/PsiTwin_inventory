/**
 * Saiki: chat con el asistente del backend. Opcionalmente se le da contexto (un producto o un inventario)
 * para que responda con sus datos reales, su riesgo, alertas y recomendaciones.
 * La conversación vive solo en esta pantalla (el backend no guarda historial ni recibe los mensajes anteriores).
 */
import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError } from '@/api/client'
import { saikiApi } from '@/api/saiki'
import { InventarioSelect, ProductoSelect } from '@/components/selects'
import { Badge, Button, Card, Field, PageHeader, Spinner, Textarea } from '@/components/ui'
import { cn } from '@/lib/cn'

interface Mensaje {
  de: 'usuario' | 'saiki' | 'error'
  texto: string
  avisos?: string[]
}

const SUGERENCIAS = ['¿Qué inventarios tienen más riesgo de quedarse sin stock?', '¿Qué debería reponer esta semana?', 'Resume el estado de este inventario.']

/** qwen3 puede devolver su razonamiento entre <think>…</think>: no se muestra. */
const limpiar = (t: string) => t.replace(/<think>[\s\S]*?<\/think>/g, '').trim()

export default function SaikiPage() {
  const [mensajes, setMensajes] = useState<Mensaje[]>([])
  const [pregunta, setPregunta] = useState('')
  const [idProducto, setIdProducto] = useState('')
  const [idInventario, setIdInventario] = useState('')
  const finRef = useRef<HTMLDivElement>(null)

  // /saiki/health hace una consulta real al modelo (lenta): una sola vez al entrar.
  const salud = useQuery({ queryKey: ['saiki', 'health'], queryFn: saikiApi.health, staleTime: Infinity, retry: false })
  const preguntar = useMutation({ mutationFn: saikiApi.ask })

  useEffect(() => {
    finRef.current?.scrollIntoView({ block: 'end' })
  }, [mensajes, preguntar.isPending])

  const enviar = (texto: string) => {
    const q = texto.trim()
    if (!q || preguntar.isPending) return
    setMensajes((m) => [...m, { de: 'usuario', texto: q }])
    setPregunta('')
    preguntar.mutate(
      { question: q, ...(idInventario ? { id_inventario: idInventario } : idProducto ? { id_producto: idProducto } : {}) },
      {
        onSuccess: (r) => setMensajes((m) => [...m, { de: 'saiki', texto: limpiar(r.answer), avisos: r.warnings }]),
        onError: (e) =>
          setMensajes((m) => [
            ...m,
            {
              de: 'error',
              texto:
                e instanceof ApiError && e.status === 503
                  ? 'Saiki no está disponible: el modelo (Ollama) no responde en el servidor.'
                  : e instanceof ApiError
                    ? e.detail
                    : 'No se pudo obtener la respuesta.',
            },
          ]),
      },
    )
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    enviar(pregunta)
  }

  return (
    <>
      <PageHeader
        eyebrow="Asistente"
        title="Saiki"
        description="Pregunta sobre tu inventario. Saiki interpreta los datos reales, el riesgo calculado y el pronóstico; no modifica nada."
        meta={
          salud.isLoading ? (
            <Badge tone="neutral">Comprobando…</Badge>
          ) : salud.data?.ready ? (
            <Badge tone="success">Disponible · {salud.data.model}</Badge>
          ) : (
            <Badge tone="danger">No disponible</Badge>
          )
        }
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Card padding="none" className="flex min-h-[28rem] flex-col">
          <div className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
            {mensajes.length === 0 && (
              <div className="flex flex-col items-start gap-2">
                <p className="text-sm text-fg-muted">Prueba con una de estas preguntas:</p>
                {SUGERENCIAS.map((s) => (
                  <Button key={s} variant="secondary" size="sm" onClick={() => enviar(s)}>
                    {s}
                  </Button>
                ))}
              </div>
            )}
            {mensajes.map((m, i) => (
              <div key={i} className={cn('flex', m.de === 'usuario' ? 'justify-end' : 'justify-start')}>
                <div
                  className={cn(
                    'max-w-[85%] rounded-lg border px-3 py-2 text-sm whitespace-pre-wrap',
                    m.de === 'usuario' && 'border-accent/60 bg-accent-soft text-fg',
                    m.de === 'saiki' && 'border-border bg-surface-2 text-fg',
                    m.de === 'error' && 'border-danger/40 bg-danger-soft text-danger',
                  )}
                  {...(m.de === 'error' ? { role: 'alert' } : {})}
                >
                  {m.de !== 'usuario' && <p className="label-stencil mb-1">{m.de === 'saiki' ? 'Saiki' : 'Error'}</p>}
                  {m.texto}
                  {m.avisos?.map((a) => (
                    <p key={a} className="mt-2 text-xs text-fg-subtle">
                      {a}
                    </p>
                  ))}
                </div>
              </div>
            ))}
            {preguntar.isPending && (
              <p className="flex items-center gap-2 text-sm text-fg-muted">
                <Spinner size="sm" label="Saiki está respondiendo" /> Saiki está respondiendo… puede tardar hasta un minuto.
              </p>
            )}
            <div ref={finRef} />
          </div>

          <form onSubmit={onSubmit} className="flex items-end gap-2 border-t border-border p-3">
            <Textarea
              aria-label="Pregunta para Saiki"
              rows={2}
              maxLength={1000}
              placeholder="Escribe tu pregunta…"
              value={pregunta}
              onChange={(e) => setPregunta(e.target.value)}
              onKeyDown={(e) => {
                if (e.key !== 'Enter' || e.shiftKey) return
                e.preventDefault()
                enviar(pregunta)
              }}
            />
            <Button type="submit" loading={preguntar.isPending} disabled={pregunta.trim() === ''}>
              Enviar
            </Button>
          </form>
        </Card>

        <Card title="Contexto" description="Opcional. Elige sobre qué quieres preguntar." className="self-start">
          <div className="flex flex-col gap-4">
            <Field label="Producto">
              <ProductoSelect
                value={idProducto}
                onChange={(e) => {
                  setIdProducto(e.target.value)
                  setIdInventario('')
                }}
              />
            </Field>
            <Field label="Inventario (ubicación)" hint="Con un inventario, Saiki recibe su riesgo, alertas y recomendaciones.">
              <InventarioSelect
                idProducto={idProducto || undefined}
                emptyText="Este producto no tiene inventario"
                value={idInventario}
                onChange={(e) => setIdInventario(e.target.value)}
              />
            </Field>
            {(idProducto || idInventario) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setIdProducto('')
                  setIdInventario('')
                }}
              >
                Quitar contexto
              </Button>
            )}
          </div>
        </Card>
      </div>
    </>
  )
}
