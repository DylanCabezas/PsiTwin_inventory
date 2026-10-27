import { API_URL } from '@/api/client'
import { getToken } from '@/lib/storage'
import type { TtsProvider } from './ttsProvider'

async function audioRequest(path: string, body: BodyInit, type: string, signal: AbortSignal) {
  const response = await fetch(`${API_URL}/saiki/voice/${path}`, { method: 'POST', signal, body,
    headers: { Authorization: `Bearer ${getToken() ?? ''}`, 'Content-Type': type } })
  if (!response.ok) throw new Error('No se pudo procesar la voz local. Puedes seguir por texto.')
  return response
}

let controller: AbortController | undefined
let playback: HTMLAudioElement | undefined
let objectUrl: string | undefined
let frame = 0
let context: AudioContext | undefined
export function unlockLocalAudio() {
  try { context ??= new AudioContext(); void context.resume() } catch { /* Playback reports its own error. */ }
}
export const localTts: TtsProvider = {
  id: 'kokoro-local',
  available: () => typeof Audio !== 'undefined',
  voices: () => [{ id: 'em_santa', name: 'Saiki Cálido', lang: 'es' }, { id: 'em_alex', name: 'Saiki Natural', lang: 'es' }],
  subscribe: () => () => {},
  speak(text, options, callbacks) {
    localTts.cancel()
    const current = new AbortController()
    controller = current
    void (async () => {
      try {
        // Create/unlock the context within the initiating user interaction.
        context ??= new AudioContext()
        await context.resume()
        const response = await audioRequest('synthesize', JSON.stringify({ text,
          voice: ['em_santa', 'em_alex'].includes(options.voiceId) ? options.voiceId : 'em_santa', speed: options.rate }), 'application/json', current.signal)
        const blob = await response.blob()
        if (current.signal.aborted) return
        objectUrl = URL.createObjectURL(blob)
        const audio = new Audio(objectUrl)
        playback = audio
        audio.volume = options.volume
        const analyser = context.createAnalyser()
        analyser.fftSize = 256
        const source = context.createMediaElementSource(audio)
        source.connect(analyser); analyser.connect(context.destination)
        const values = new Uint8Array(analyser.fftSize)
        const update = () => {
          if (current.signal.aborted || audio.paused) return
          analyser.getByteTimeDomainData(values)
          const rms = Math.sqrt(values.reduce((sum, v) => sum + ((v - 128) / 128) ** 2, 0) / values.length)
          callbacks.boundary(Math.min(1, rms * 5))
          frame = requestAnimationFrame(update)
        }
        audio.onplaying = () => { callbacks.start(); update() }
        audio.onended = () => { if (!current.signal.aborted) { localTts.cancel(); callbacks.end() } }
        audio.onerror = () => { if (!current.signal.aborted) { localTts.cancel(); callbacks.error() } }
        await audio.play()
      } catch { if (!current.signal.aborted) { localTts.cancel(); callbacks.error() } }
    })()
  },
  cancel() {
    controller?.abort(); controller = undefined
    cancelAnimationFrame(frame)
    if (playback) { playback.onended = null; playback.onerror = null; playback.pause(); playback.removeAttribute('src'); playback.load() }
    playback = undefined
    if (objectUrl) URL.revokeObjectURL(objectUrl)
    objectUrl = undefined
  },
}

/** Local STT through our backend; never uses browser cloud recognition. */
export class LocalRecognition {
  lang = 'es'; continuous = false; interimResults = false
  onstart: (() => void) | null = null
  onend: (() => void) | null = null
  onprocessing: (() => void) | null = null
  onerror: ((event: { error: string }) => void) | null = null
  onresult: ((event: { resultIndex: number; results: { length: number; [index: number]: { isFinal: boolean; [index: number]: { transcript: string } } } }) => void) | null = null
  private stream?: MediaStream
  private recorder?: MediaRecorder
  private controller = new AbortController()
  private timer?: ReturnType<typeof setTimeout>
  start() {
    void (async () => {
      try {
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true }, video: false })
        if (this.controller.signal.aborted) { this.stream.getTracks().forEach(t => t.stop()); return }
        const mimeType = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4'].find(t => MediaRecorder.isTypeSupported(t))
        const recorder = new MediaRecorder(this.stream, mimeType ? { mimeType } : undefined)
        this.recorder = recorder
        const chunks: BlobPart[] = []
        recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data) }
        recorder.onstop = () => {
          this.stream?.getTracks().forEach(t => t.stop())
          clearTimeout(this.timer)
          if (this.controller.signal.aborted) return
          this.onprocessing?.()
          void (async () => {
            try {
              const response = await audioRequest('transcribe', new Blob(chunks, { type: recorder.mimeType }), recorder.mimeType, this.controller.signal)
              const { text } = await response.json() as { text: string }
              if (!this.controller.signal.aborted && text.trim()) this.onresult?.({ resultIndex: 0, results: { length: 1, 0: { isFinal: true, 0: { transcript: text } } } })
            } catch { if (!this.controller.signal.aborted) this.onerror?.({ error: 'local-unavailable' }) }
            finally { if (!this.controller.signal.aborted) this.onend?.() }
          })()
        }
        recorder.start(); this.onstart?.()
        this.timer = setTimeout(() => this.finish(), 30_000)
      } catch { if (!this.controller.signal.aborted) this.onerror?.({ error: 'not-allowed' }) }
    })()
  }
  finish() { if (this.recorder?.state === 'recording') this.recorder.stop() }
  abort() {
    this.controller.abort(); clearTimeout(this.timer)
    this.finish(); this.stream?.getTracks().forEach(t => t.stop())
  }
}
