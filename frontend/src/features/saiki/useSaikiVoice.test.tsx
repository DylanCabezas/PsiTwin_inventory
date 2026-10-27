// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useSaikiVoice } from './useSaikiVoice'
import { browserTts } from './ttsProvider'

class FakeRecognition {
  static instances: FakeRecognition[] = []
  lang = ''; continuous = false; interimResults = false
  onstart: (() => void) | null = null
  onend: (() => void) | null = null
  onerror: ((event: { error: string }) => void) | null = null
  onresult: ((event: { resultIndex: number; results: { length: number; [index: number]: { isFinal: boolean; [index: number]: { transcript: string } } } }) => void) | null = null
  constructor() { FakeRecognition.instances.push(this) }
  start = vi.fn(() => this.onstart?.())
  abort = vi.fn(() => this.onend?.())
}
class FakeUtterance {
  lang = ''
  onstart: (() => void) | null = null
  onend: (() => void) | null = null
  onerror: (() => void) | null = null
  onboundary: (() => void) | null = null
  constructor(public text: string) {}
}

describe('Saiki voice session', () => {
  let root: Root
  let voice: ReturnType<typeof useSaikiVoice>
  const onText = vi.fn()
  const speak = vi.fn()
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('psitwin.saiki.voice', JSON.stringify({ enabled: true }))
    vi.useFakeTimers()
    Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
    FakeRecognition.instances = []
    vi.stubGlobal('SpeechRecognition', FakeRecognition)
    vi.stubGlobal('SpeechSynthesisUtterance', FakeUtterance)
    vi.stubGlobal('speechSynthesis', { speak, cancel: vi.fn() })
    function Harness() { voice = useSaikiVoice(onText, 'psitwin.saiki.voice', browserTts, FakeRecognition); return <span>{voice.listening ? 'listening' : 'idle'}</span> }
    root = createRoot(document.createElement('div'))
    act(() => root.render(<Harness />))
  })
  afterEach(() => { act(() => root.unmount()); vi.useRealTimers(); vi.unstubAllGlobals(); vi.clearAllMocks() })
  const advance = () => act(() => { vi.advanceTimersByTime(500) })
  it('enumerates real provider voices, persists selection and applies rate and volume', () => {
    const installed = [{ voiceURI: 'es-one', name: 'Voz instalada', lang: 'es-PE' }, { voiceURI: 'en-one', name: 'English installed', lang: 'en-US' }]
    Object.assign(window.speechSynthesis, { getVoices: () => installed })
    // Remount so getVoices is read as it would be on the voiceschanged event.
    act(() => root.unmount())
    root = createRoot(document.createElement('div'))
    function Harness() { voice = useSaikiVoice(onText, 'psitwin.saiki.voice', browserTts, FakeRecognition); return null }
    act(() => root.render(<Harness />))
    expect(voice.voices.map(v => v.id)).toEqual(['es-one', 'en-one'])
    act(() => voice.configure({ voiceId: 'es-one', rate: 1.3, volume: .5 }))
    act(() => voice.speak('Frase de prueba'))
    expect(speak.mock.calls[0]![0]).toMatchObject({ voice: installed[0], rate: 1.3, volume: .5, text: 'Frase de prueba' })
    expect(JSON.parse(localStorage.getItem('psitwin.saiki.voice')!)).toMatchObject({ voiceId: 'es-one', rate: 1.3, volume: .5 })
  })
  it('ignores silence, fillers and noise without sending a transcript', () => {
    act(() => voice.start())
    for (const transcript of ['', '...', 'eh eh mmm', 'qwerty']) {
      act(() => FakeRecognition.instances[0]!.onresult?.({ resultIndex: 0, results: { length: 1, 0: { isFinal: true, 0: { transcript } } } }))
    }
    expect(onText).not.toHaveBeenCalled()
    expect(voice.listening).toBe(true)
  })
  it('mutes speech without disabling text or microphone and reacts to playback boundaries', () => {
    act(() => voice.start())
    act(() => voice.toggleVoice())
    act(() => voice.speak('Respuesta'))
    expect(speak).not.toHaveBeenCalled()
    expect(voice.listening).toBe(true)
    act(() => voice.toggleVoice())
    act(() => voice.speak('Respuesta en español'))
    const utterance = speak.mock.calls[0]![0] as FakeUtterance
    expect(utterance.lang).toBe('es-PE')
    act(() => utterance.onstart?.())
    const initial = voice.audioLevel
    act(() => utterance.onboundary?.())
    expect(voice.audioLevel).not.toBe(initial)
    act(() => voice.interrupt())
    expect(voice.speaking).toBe(false)
    expect(voice.audioLevel).toBe(0)
  })
  it('waits for opt-in and restarts after browser silence until explicitly closed', () => {
    expect(FakeRecognition.instances).toHaveLength(0)
    act(() => voice.start())
    expect(voice.active).toBe(true)
    expect(voice.listening).toBe(true)
    act(() => FakeRecognition.instances[0]!.onend?.())
    advance()
    expect(FakeRecognition.instances).toHaveLength(2)
    act(() => voice.exit())
    advance()
    expect(voice.active).toBe(false)
    expect(FakeRecognition.instances).toHaveLength(2)
  })
  it('pauses the microphone and requires an explicit resume', () => {
    act(() => voice.start())
    act(() => voice.pause())
    advance()
    expect(voice.active).toBe(true)
    expect(voice.paused).toBe(true)
    expect(voice.listening).toBe(false)
    expect(FakeRecognition.instances).toHaveLength(1)
    act(() => voice.resume())
    expect(voice.listening).toBe(true)
    expect(FakeRecognition.instances).toHaveLength(2)
  })
  it('submits a final transcript once and never records the reply being spoken', () => {
    act(() => voice.start())
    const recognition = FakeRecognition.instances[0]!
    act(() => recognition.onresult?.({ resultIndex: 0, results: { length: 1, 0: { isFinal: true, 0: { transcript: 'abre inventario' } } } }))
    expect(onText).toHaveBeenCalledExactlyOnceWith('abre inventario')
    expect(voice.listening).toBe(false)
    advance()
    expect(FakeRecognition.instances).toHaveLength(1)
    act(() => { voice.speak('Estos son tus datos'); voice.release() })
    const utterance = speak.mock.calls[0]![0] as FakeUtterance
    act(() => utterance.onstart?.())
    expect(voice.speaking).toBe(true)
    advance()
    expect(FakeRecognition.instances).toHaveLength(1)
    act(() => utterance.onend?.())
    advance()
    expect(voice.speaking).toBe(false)
    expect(voice.listening).toBe(true)
  })
  it('does not restart when a late speech event fires after closing', () => {
    act(() => { voice.start(); voice.hold(); voice.speak('Respuesta'); voice.release() })
    const utterance = speak.mock.calls[0]![0] as FakeUtterance
    const lateEnd = utterance.onend
    act(() => voice.exit())
    act(() => lateEnd?.())
    advance()
    expect(voice.active).toBe(false)
    expect(voice.listening).toBe(false)
    expect(FakeRecognition.instances).toHaveLength(1)
  })
  it('pauses on denied permissions without retrying the microphone', () => {
    act(() => voice.start())
    act(() => FakeRecognition.instances[0]!.onerror?.({ error: 'not-allowed' }))
    advance()
    expect(voice.paused).toBe(true)
    expect(voice.error).toContain('permiso')
    expect(FakeRecognition.instances).toHaveLength(1)
  })
  it('keeps the microphone off between chunks of a long spoken answer', () => {
    act(() => { voice.start(); voice.hold(); voice.speak('Una respuesta larga con datos verificados. '.repeat(15)); voice.release() })
    advance()
    expect(FakeRecognition.instances).toHaveLength(1)
    let index = 0
    while (index < speak.mock.calls.length) {
      const utterance = speak.mock.calls[index++]![0] as FakeUtterance
      expect(utterance.text.length).toBeLessThanOrEqual(240)
      act(() => { utterance.onstart?.(); utterance.onend?.() })
    }
    expect(speak.mock.calls.length).toBeGreaterThan(1)
    advance()
    expect(voice.listening).toBe(true)
  })
  it('can interrupt speech to ask again without ending the voice session', () => {
    act(() => { voice.start(); voice.speak('Respuesta'); voice.release() })
    act(() => voice.interrupt())
    expect(voice.active).toBe(true)
    expect(voice.listening).toBe(true)
    expect(voice.speaking).toBe(false)
    expect(FakeRecognition.instances).toHaveLength(2)
  })
  it('cleans up when the authenticated layout unmounts', () => {
    act(() => voice.start())
    const first = FakeRecognition.instances[0]!
    act(() => root.render(<div />))
    advance()
    expect(first.abort).toHaveBeenCalled()
    expect(first.onresult).toBeNull()
    expect(FakeRecognition.instances).toHaveLength(1)
  })
})
