export interface TtsVoice { id: string; name: string; lang: string }
export interface TtsOptions { voiceId: string; rate: number; volume: number }
export interface TtsCallbacks { start(): void; boundary(level?: number): void; end(): void; error(): void }
export interface TtsProvider {
  readonly id: string
  available(): boolean
  voices(): TtsVoice[]
  subscribe(listener: () => void): () => void
  speak(text: string, options: TtsOptions, callbacks: TtsCallbacks): void
  cancel(): void
}
// Future cloud adapters implement this interface; conversation and history stay unchanged.
export const browserTts: TtsProvider = {
  id: 'web-speech',
  available: () => typeof window.speechSynthesis?.speak === 'function',
  voices: () => (window.speechSynthesis?.getVoices?.() ?? []).map(v => ({ id: v.voiceURI, name: v.name, lang: v.lang })),
  subscribe(listener) {
    window.speechSynthesis?.addEventListener?.('voiceschanged', listener)
    return () => window.speechSynthesis?.removeEventListener?.('voiceschanged', listener)
  },
  speak(text, options, callbacks) {
    const u = new SpeechSynthesisUtterance(text)
    const voices = window.speechSynthesis.getVoices?.() ?? []
    u.voice = voices.find(v => v.voiceURI === options.voiceId) ?? voices.find(v => v.lang.toLowerCase().startsWith('es')) ?? null
    u.lang = u.voice?.lang ?? 'es-PE'
    u.rate = options.rate; u.volume = options.volume
    u.onstart = callbacks.start; u.onboundary = () => callbacks.boundary()
    u.onend = callbacks.end; u.onerror = callbacks.error
    window.speechSynthesis.speak(u)
  },
  cancel: () => window.speechSynthesis?.cancel(),
}
