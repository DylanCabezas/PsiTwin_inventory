import { Button, Card, Field, Select } from '@/components/ui'
import { useSaikiSession } from './SaikiSession'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { TtsVoice } from './ttsProvider'

export function SaikiVoiceSettings() {
  const { voice, pending } = useSaikiSession()
  const configuration = useQuery({ queryKey: ['saiki', 'voice-config'], queryFn: () => api.get<{ provider: string; installed: boolean; voices: TtsVoice[] }>('/saiki/voice/config'), staleTime: 60_000 })
  const voices = configuration.data?.voices ?? voice.voices
  return <Card title="Voz de Saiki" description={configuration.data?.provider === 'piper' ? 'Piper local está configurado como alternativa. Usa el modelo de voz instalado por el administrador.' : 'Voz masculina en español con Kokoro local. No consume créditos por mensaje.'}>
    <div className="space-y-4">
      <Field label="Voz"><Select value={voice.preferences.voiceId || 'em_santa'} onChange={e => voice.configure({ voiceId: e.target.value })} placeholder={false} options={voices.map(v => ({ value: v.id, label: `${v.name} (${v.lang})` }))} /></Field>
      {configuration.data?.installed === false && <p role="status" className="text-sm text-fg-muted">El entorno de voz local aún no está instalado. Puedes seguir por texto.</p>}
      {!voice.voices.length && <p className="text-sm text-fg-muted">El navegador aún no ofrece voces instaladas.</p>}
      <Field label={`Velocidad: ${voice.preferences.rate.toFixed(1)}`}><input aria-label="Velocidad de habla" type="range" min="0.5" max="2" step="0.1" value={voice.preferences.rate} onChange={e => voice.configure({ rate: Number(e.target.value) })} /></Field>
      <Field label={`Volumen: ${Math.round(voice.preferences.volume * 100)}%`}><input aria-label="Volumen de voz" type="range" min="0" max="1" step="0.05" value={voice.preferences.volume} onChange={e => voice.configure({ volume: Number(e.target.value) })} /></Field>
      <Button variant="secondary" aria-pressed={voice.voiceEnabled} onClick={voice.toggleVoice}>{voice.voiceEnabled ? 'Desactivar' : 'Activar'} respuesta hablada</Button>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={voice.preferences.sensorAlerts} onChange={e => voice.configure({ sensorAlerts: e.target.checked })} />Avisos hablados de sensores (durante la sesión de voz)</label>
      <Button variant="ghost" onClick={voice.interrupt}>Detener reproducción</Button>
      {voice.listening && <Button variant="secondary" onClick={voice.finishRecording}>Enviar grabación</Button>}
      <Button variant="ghost" disabled={!voice.canSpeak || !voice.voiceEnabled || pending || voice.paused} onClick={() => voice.speak('¡Hola! Soy Saiki, tu asistente de PsiTwin. Estoy aquí para ayudarte.')}>Probar voz</Button>
    </div>
  </Card>
}
