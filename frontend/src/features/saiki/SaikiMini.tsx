import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { Button, Input } from '@/components/ui'
import { paths } from '@/paths'
import { useSaikiSessionOptional } from './SaikiSession'
import { SaikiPresence } from './SaikiPresence'

export function SaikiMini() {
  const session = useSaikiSessionOptional()
  const location = useLocation()
  const navigate = useNavigate()
  const [text, setText] = useState('')
  if (!session || !session.voice.active || (!session.minimized && location.pathname === paths.saiki)) return null
  const last = [...session.messages].reverse().find(m => m.de !== 'usuario')
  const submit = (event: FormEvent) => { event.preventDefault(); if (text.trim() && !session.pending) { void session.send(text); setText('') } }
  return <aside aria-label="Saiki, conversación de voz activa" className="saiki-mini fixed right-3 bottom-3 z-40 w-[min(23rem,calc(100vw-1.5rem))] overflow-hidden rounded-2xl border border-violet-400/30 bg-surface shadow-2xl shadow-blue-950/30 sm:right-5 sm:bottom-5">
    <header className="flex items-center justify-between border-b border-border px-4 py-2">
      <span className="text-sm font-semibold">Saiki te acompaña</span>
      <Button size="sm" variant="ghost" onClick={() => { session.setMinimized(false); navigate(paths.saiki) }}>Ampliar</Button>
    </header>
    <SaikiPresence compact />
    <div className="space-y-3 p-4">
      {session.guide && <button type="button" onClick={() => session.openGuide(session.guide!)} className="w-full rounded-lg border border-blue-400/25 bg-blue-500/5 px-3 py-2 text-left text-sm">Ir a {session.guide.title} <span aria-hidden="true">↗</span></button>}
      <p aria-live="polite" className="max-h-32 overflow-auto whitespace-pre-wrap text-sm leading-relaxed text-fg-muted">{last?.texto ?? 'Te escucho. Puedes pedirme que abra inventario o monitoreo y preguntarme por tus datos.'}</p>
      <form onSubmit={submit} className="flex gap-2">
        <Input aria-label="Seguir preguntando a Saiki" value={text} onChange={e => setText(e.target.value)} maxLength={1000} placeholder="O escribe aquí…" />
        <Button size="sm" type="submit" disabled={session.pending || !text.trim()}>Enviar</Button>
      </form>
    </div>
  </aside>
}
