import { useEffect, useRef, useState } from 'react'
import { intelligibleInput } from './saikiInput'
import { type TtsOptions, type TtsProvider } from './ttsProvider'
import { localTts, LocalRecognition, unlockLocalAudio } from './localVoice'

const defaults = { voiceId: 'em_santa', rate: 1, volume: 1, enabled: false, sensorAlerts: false }
function loadPreferences(key: string) {
  try {
    const saved = JSON.parse(localStorage.getItem(key) ?? '{}') as Partial<typeof defaults>
    return { voiceId: typeof saved.voiceId === 'string' && saved.voiceId ? saved.voiceId : defaults.voiceId,
      rate: typeof saved.rate === 'number' ? Math.max(.5, Math.min(2, saved.rate)) : 1,
      volume: typeof saved.volume === 'number' ? Math.max(0, Math.min(1, saved.volume)) : 1,
      enabled: saved.enabled === true, sensorAlerts: saved.sensorAlerts === true }
  } catch { return defaults }
}

interface Recognition {
  onprocessing?: (() => void) | null
  lang: string
  continuous: boolean
  interimResults: boolean
  onstart: (() => void) | null
  onend: (() => void) | null
  onerror: ((event: { error: string }) => void) | null
  onresult: ((event: { resultIndex: number; results: { length: number; [index: number]: { isFinal: boolean; [index: number]: { transcript: string } } } }) => void) | null
  start(): void
  abort(): void
}

/** One opt-in voice session. Recognition never runs during a request or playback. */
export function useSaikiVoice(onText: (text: string) => void, preferencesKey = 'psitwin.saiki.voice', tts: TtsProvider = localTts, recognitionConstructor?: new () => Recognition) {
  const [preferences, setPreferences] = useState(() => loadPreferences(preferencesKey))
  const preferenceRef = useRef(preferences)
  preferenceRef.current = preferences
  const [voices, setVoices] = useState(() => tts.voices())
  const [active, setActive] = useState(false)
  const [paused, setPaused] = useState(false)
  const [listening, setListening] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [preparing, setPreparing] = useState(false)
  const [error, setError] = useState('')
  const [voiceEnabled, setVoiceEnabled] = useState(preferences.enabled)
  const enabled = useRef(preferences.enabled)
  const [audioLevel, setAudioLevel] = useState(0)
  const callback = useRef(onText)
  callback.current = onText
  const recognition = useRef<Recognition | null>(null)
  const utterance = useRef<object | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const speechTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const flags = useRef({ active: false, paused: false, busy: false, speaking: false, mounted: true })
  const Constructor = recognitionConstructor ?? (typeof MediaRecorder !== 'undefined' && typeof navigator.mediaDevices?.getUserMedia === 'function' ? LocalRecognition : undefined)

  function stopRecognition() {
    clearTimeout(timer.current)
    const r = recognition.current
    recognition.current = null
    if (r) { r.onstart = null; r.onend = null; r.onerror = null; r.onresult = null; r.abort() }
    if (flags.current.mounted) setListening(false)
    if (flags.current.mounted) setTranscribing(false)
  }
  function cancelSpeech() {
    clearTimeout(speechTimer.current)
    utterance.current = null
    tts.cancel()
    flags.current.speaking = false
    if (flags.current.mounted) setSpeaking(false)
    if (flags.current.mounted) setPreparing(false)
    if (flags.current.mounted) setAudioLevel(0)
  }
  function eligible() {
    const f = flags.current
    return f.mounted && f.active && !f.paused && !f.busy && !f.speaking
  }
  function schedule() {
    clearTimeout(timer.current)
    if (eligible()) timer.current = setTimeout(beginRecognition, 450)
  }
  function beginRecognition() {
    if (!Constructor || !eligible() || recognition.current) return
    const r = new Constructor()
    recognition.current = r
    r.lang = 'es-PE'
    r.continuous = true
    r.interimResults = false
    r.onstart = () => { if (recognition.current === r) setListening(true) }
    r.onprocessing = () => { if (recognition.current === r) { setListening(false); setTranscribing(true) } }
    r.onend = () => {
      if (recognition.current !== r) return
      recognition.current = null
      setListening(false)
      setTranscribing(false)
      schedule() // Browsers end recognition after silence; the opt-in session stays open.
    }
    r.onerror = e => {
      if (recognition.current !== r) return
      if (e.error === 'no-speech' || e.error === 'aborted') return
      flags.current.paused = true
      setPaused(true)
      setError(e.error === 'not-allowed' || e.error === 'service-not-allowed'
        ? 'El micrófono no tiene permiso. Habilítalo en el navegador y pulsa Reanudar.'
        : 'No se pudo transcribir con el motor local. Revisa su instalación o continúa por texto.')
      stopRecognition()
    }
    r.onresult = e => {
      if (!eligible() || recognition.current !== r) return
      const parts: string[] = []
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const result = e.results[i]
        if (result?.isFinal && result[0]?.transcript) parts.push(result[0].transcript)
      }
      const text = parts.join(' ').trim()
      if (!intelligibleInput(text)) return
      flags.current.busy = true
      stopRecognition()
      callback.current(text)
    }
    try { r.start() } catch {
      recognition.current = null
      flags.current.paused = true
      setPaused(true)
      setError('El micrófono no está disponible. Pulsa Reanudar para volver a intentarlo.')
    }
  }
  function start() {
    unlockLocalAudio()
    if (!Constructor) { setError('Este navegador no admite reconocimiento de voz. Puedes seguir por texto.'); return }
    flags.current.active = true
    flags.current.paused = false
    setActive(true)
    setPaused(false)
    setError('')
    beginRecognition()
  }
  function pause() {
    flags.current.paused = true
    setPaused(true)
    stopRecognition()
    cancelSpeech()
  }
  function resume() {
    setError('')
    flags.current.paused = false
    setPaused(false)
    beginRecognition()
  }
  function exit() {
    flags.current.active = false
    flags.current.paused = false
    setActive(false)
    setPaused(false)
    setError('')
    stopRecognition()
    cancelSpeech()
  }
  function hold() {
    flags.current.busy = true
    stopRecognition()
    cancelSpeech()
  }
  function interrupt() {
    cancelSpeech()
    beginRecognition()
  }
  function release() {
    flags.current.busy = false
    schedule()
  }
  function speak(text: string) {
    if (!tts.available() || !text.trim() || flags.current.paused || !enabled.current) return
    stopRecognition()
    cancelSpeech()
    // Prefer sentence boundaries; keep each local inference bounded.
    const chunks: string[] = []
    let remaining = text.trim()
    while (remaining.length > 240) {
      const space = remaining.lastIndexOf(' ', 240)
      const punctuation = [...remaining.slice(0, 240).matchAll(/[.!?;:]\s/g)].at(-1)?.index
      const boundary = punctuation != null && punctuation > 60 ? punctuation + 1 : space > 80 ? space : 240
      chunks.push(remaining.slice(0, boundary))
      remaining = remaining.slice(boundary).trim()
    }
    if (remaining) chunks.push(remaining)
    flags.current.speaking = true
    setPreparing(true)
    function next() {
      clearTimeout(speechTimer.current)
      const chunk = chunks.shift()
      if (!chunk) { flags.current.speaking = false; setPreparing(false); setSpeaking(false); setAudioLevel(0); schedule(); return }
      const u = {}
      utterance.current = u
      setSpeaking(false)
      setPreparing(true)
      speechTimer.current = setTimeout(() => {
        if (utterance.current === u) setError('La voz local sigue preparándose. Puedes detenerla y continuar por texto.')
      }, 10_000)
      const fail = () => {
        if (utterance.current !== u) return
        chunks.length = 0
        utterance.current = null
        setError('No se pudo reproducir la voz. La respuesta sigue disponible por texto.')
        next()
      }
      try { tts.speak(chunk, preferenceRef.current, {
        start: () => { if (utterance.current === u) { clearTimeout(speechTimer.current); setError(''); setPreparing(false); setSpeaking(true); setAudioLevel(0) } },
        boundary: level => { if (utterance.current === u) setAudioLevel(previous => level ?? (previous > .5 ? .3 : .8)) },
        end: () => { if (utterance.current !== u) return; utterance.current = null; setAudioLevel(0); next() },
        error: fail,
      }) } catch { fail() }
    }
    next()
  }
  useEffect(() => {
    flags.current.mounted = true
    return () => {
      flags.current.mounted = false
      flags.current.active = false
      stopRecognition()
      cancelSpeech()
    }
  }, [])
  useEffect(() => {
    const refresh = () => setVoices(tts.voices().sort((a, b) => Number(b.lang.toLowerCase().startsWith('es')) - Number(a.lang.toLowerCase().startsWith('es')) || a.name.localeCompare(b.name)))
    refresh()
    return tts.subscribe(refresh)
  }, [tts])
  function configure(patch: Partial<TtsOptions> & { sensorAlerts?: boolean }) {
    setPreferences(previous => {
      const updated = { ...previous, ...patch }
      preferenceRef.current = updated
      try { localStorage.setItem(preferencesKey, JSON.stringify(updated)) } catch { /* memory fallback */ }
      return updated
    })
  }
  function toggleVoice() {
    unlockLocalAudio()
    enabled.current = !enabled.current
    setVoiceEnabled(enabled.current)
    setPreferences(previous => {
      const updated = { ...previous, enabled: enabled.current }
      try { localStorage.setItem(preferencesKey, JSON.stringify(updated)) } catch { /* memory fallback */ }
      return updated
    })
    if (!enabled.current) { cancelSpeech(); schedule() }
  }
  function finishRecording() { (recognition.current as LocalRecognition | null)?.finish?.() }
  return { active, paused, listening, transcribing, speaking, preparing, error, voiceEnabled, toggleVoice, audioLevel, canListen: !!Constructor, canSpeak: tts.available(), voices, preferences, configure, finishRecording,
    start, pause, resume, exit, hold, release, speak, interrupt,
    isEnabled: () => flags.current.active && !flags.current.paused }
}
