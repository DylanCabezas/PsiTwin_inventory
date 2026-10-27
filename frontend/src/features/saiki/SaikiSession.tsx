import { createContext, use, useEffect, useRef, useState, type ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { useSession } from '@/auth/SessionContext'
import { ApiError } from '@/api/client'
import { paths } from '@/paths'
import { saikiApi, type SaikiAnswer, type SaikiAskBody } from '@/api/saiki'
import { useSaikiVoice } from './useSaikiVoice'
import { intelligibleInput } from './saikiInput'
import { cleanAnswer, requestsNavigation, speechText, suggestedGuide, voiceCommand, type SaikiGuide } from './saikiGuidance'

export interface SaikiMessage { de: 'usuario' | 'saiki' | 'error'; texto: string; avisos?: string[] }
function savedMessages(company?: string): SaikiMessage[] {
  if (!company) return []
  try {
    const rows: unknown = JSON.parse(localStorage.getItem(`psitwin.saiki.history.${company}`) ?? '[]')
    if (!Array.isArray(rows)) return []
    return rows.filter((row): row is SaikiMessage => row && ['usuario', 'saiki', 'error'].includes(row.de) && typeof row.texto === 'string')
      .slice(-80).map(row => ({ de: row.de, texto: row.texto.slice(0, 8000) }))
  } catch { return [] }
}
const SaikiSessionContext = createContext<ReturnType<typeof useSessionState> | null>(null)

function useSessionState() {
  const { empresa } = useSession()
  const [messages, setMessages] = useState<SaikiMessage[]>(() => savedMessages(empresa?.id_empresa))
  useEffect(() => {
    if (!empresa?.id_empresa) return
    try { localStorage.setItem(`psitwin.saiki.history.${empresa.id_empresa}`, JSON.stringify(messages.slice(-80))) } catch { /* In-memory history remains available. */ }
  }, [messages, empresa?.id_empresa])
  const [pending, setPending] = useState(false)
  const [idProducto, setIdProducto] = useState('')
  const [idInventario, setIdInventario] = useState('')
  const [minimized, setMinimized] = useState(false)
  const [guide, setGuide] = useState<SaikiGuide | null>(null)
  const [result, setResult] = useState<SaikiAnswer | null>(null)
  const [sensorContext, setSensorContext] = useState<Pick<SaikiAskBody, 'id_dispositivo' | 'sensor_horas'> | undefined>(undefined)
  const locked = useRef(false)
  const alive = useRef(true)
  const request = useRef<AbortController | null>(null)
  const generation = useRef(0)
  const [phase, setPhase] = useState('Pensando')
  const navigate = useNavigate()
  const location = useLocation()
  const voice = useSaikiVoice(text => {
    const command = voiceCommand(text)
    if (command === 'pause') { voice.pause(); voice.release(); return }
    if (command === 'exit') { voice.exit(); voice.release(); return }
    void send(text)
  }, `psitwin.saiki.voice.${empresa?.id_empresa ?? 'local'}`)

  useEffect(() => { alive.current = true; return () => { alive.current = false; request.current?.abort() } }, [])

  function openGuide(destination: SaikiGuide) {
    // Destinations only come from our local allowlist or a verified device selector.
    setGuide(destination)
    setMinimized(true)
    navigate(destination.to)
    if (voice.isEnabled() && !locked.current) voice.speak(speechText(destination.description))
  }

  async function send(text: string, sensor?: Pick<SaikiAskBody, 'id_dispositivo' | 'sensor_horas'>, analysis?: Pick<SaikiAskBody, 'id_almacen' | 'id_producto' | 'horizonte_dias'>) {
    const question = text.trim().slice(0, 1000)
    if (!question || !intelligibleInput(question) || locked.current) { voice.release(); return }
    locked.current = true
    const current = ++generation.current
    setPhase('Pensando')
    voice.hold()
    setPending(true)
    const nextGuide = suggestedGuide(question)
    const effectiveSensor = sensor ?? (nextGuide && nextGuide.to !== paths.monitoreo ? undefined : sensorContext)
    if (sensor) setSensorContext(sensor)
    else if (nextGuide && nextGuide.to !== paths.monitoreo) setSensorContext(undefined)
    setGuide(nextGuide)
    const navigated = nextGuide && requestsNavigation(question) && voice.active
    if (navigated) openGuide(nextGuide)
    const history = messages.filter(m => m.de !== 'error').slice(-38).map(m => ({ role: m.de === 'usuario' ? 'user' as const : 'assistant' as const, content: m.texto.slice(0, 8000) }))
    setMessages(previous => [...previous, { de: 'usuario', texto: question }])
    try {
      const controller = new AbortController()
      request.current = controller
      const response = await saikiApi.ask({ question, history,
        context: { pagina_actual: location.pathname },
        ...effectiveSensor,
        ...(analysis ?? { ...(idInventario ? { id_inventario: idInventario } : {}), ...(idProducto ? { id_producto: idProducto } : {}) }) }, controller.signal,
        progress => { if (generation.current === current) setPhase(progress.detail) })
      if (!alive.current || current !== generation.current || controller.signal.aborted) return
      const answer = cleanAnswer(response.answer)
      setResult(response)
      setMessages(previous => [...previous, { de: 'saiki', texto: answer, avisos: response.warnings }])
      if (voice.isEnabled()) voice.speak(speechText(`${navigated ? `He abierto ${nextGuide.title}. ` : ''}${answer}`))
    } catch (error) {
      if (!alive.current || current !== generation.current || request.current?.signal.aborted) return
      const message = error instanceof ApiError ? error.detail : 'No se pudo obtener la respuesta. Comprueba la conexión y vuelve a intentarlo.'
      setMessages(previous => [...previous, { de: 'error', texto: message }])
      if (voice.isEnabled()) voice.pause() // Do not enter a retry loop during a network outage.
    } finally {
      if (current !== generation.current) return
      request.current = null
      if (alive.current) { setPending(false); voice.release() }
      locked.current = false
    }
  }

  function stop() {
    generation.current++
    request.current?.abort()
    request.current = null
    locked.current = false
    setPending(false)
    voice.hold()
    if (voice.active) voice.pause()
    voice.release()
  }

  const state: 'thinking' | 'speaking' | 'listening' | 'idle' = pending || voice.preparing || voice.transcribing ? 'thinking' : voice.speaking ? 'speaking' : voice.listening ? 'listening' : 'idle'
  const status = voice.paused ? 'Sesión en pausa' : pending ? phase : voice.transcribing ? 'Transcribiendo tu grabación en el equipo' : voice.preparing ? 'Preparando voz local. Puedes detener la operación.' : voice.speaking ? 'Saiki está hablando' : voice.listening ? 'Te escucho (máximo 30 segundos)' : voice.active ? 'Esperando para escucharte' : 'Listo para ayudarte'
  return { messages, pending, send, voice, state, status, idProducto, setIdProducto, idInventario, setIdInventario,
    minimized, setMinimized, guide, openGuide, result, sensorContext, setSensorContext, stop }
}

function Session({ children }: { children: ReactNode }) {
  const session = useSessionState()
  return <SaikiSessionContext value={session}>{children}</SaikiSessionContext>
}

export function SaikiSessionProvider({ children }: { children: ReactNode }) {
  const { rol, empresa } = useSession()
  if (rol !== 'EMPRESA') return children
  return <Session key={empresa?.id_empresa ?? 'empresa'}>{children}</Session>
}

export function useSaikiSessionOptional() { return use(SaikiSessionContext) }
export function useSaikiSession() {
  const value = useSaikiSessionOptional()
  if (!value) throw new Error('Saiki necesita una sesión EMPRESA activa.')
  return value
}
