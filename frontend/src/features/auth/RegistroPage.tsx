import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router'
import { z } from 'zod'
import { useState } from 'react'
import { authApi, useAplicarLogin } from '@/api/auth'
import { startGoogle, googleDraft, saveGoogleDraft, pendingGoogleRegistration, googleRegistrationEmail, finishGoogleRegistration, clearGoogleFlow } from './googleAuth'
import { ApiError } from '@/api/client'
import { Button, Field, Input, useApiErrorHandler } from '@/components/ui'
import { texto } from '@/lib/zod'
import { paths } from '@/paths'
import { AuthLayout } from './AuthLayout'

export const companySchema = z.object({
  nombre: texto({ min: 2, max: 100 }),
  nombre_ceo: texto({ max: 100 }),
  ruc: z.string().trim().regex(/^\d{11}$/, 'El RUC debe tener 11 dígitos'),
  sector: texto({ min: 2, max: 100 }),
  telefono: z.string().trim().regex(/^\+?[\d\s-]{6,20}$/, 'Teléfono no válido (solo dígitos, espacios o guiones)'),
})
const passwordSchema = z.object({
  password: z.string().min(8, 'Usa al menos 8 caracteres').max(128, 'Máximo 128 caracteres'),
  confirmar: z.string().min(1, 'Confirma tu contraseña'),
}).refine(v => v.password === v.confirmar, { path: ['confirmar'], message: 'Las contraseñas no coinciden' })

export default function RegistroPage() {
  const navigate = useNavigate()
  const handleError = useApiErrorHandler()
  const apply = useAplicarLogin()
  const [busy, setBusy] = useState(false)
  const [step, setStep] = useState<'company' | 'password'>(() => pendingGoogleRegistration() && companySchema.safeParse(googleDraft()).success ? 'password' : 'company')
  const [flowError, setFlowError] = useState('')
  const company = useForm<z.input<typeof companySchema>>({ resolver: zodResolver(companySchema), defaultValues: { nombre: '', nombre_ceo: '', ruc: '', sector: '', telefono: '', ...googleDraft() } })
  const password = useForm<z.input<typeof passwordSchema>>({ resolver: zodResolver(passwordSchema), defaultValues: { password: '', confirmar: '' } })
  const err = company.formState.errors

  const beginGoogle = company.handleSubmit(async values => {
    if (busy) return
    setBusy(true); setFlowError('')
    try {
      saveGoogleDraft(values)
      if (pendingGoogleRegistration()) setStep('password')
      else await startGoogle(values)
    } catch (error) { setFlowError(error instanceof Error ? error.message : 'No se pudo iniciar la verificación con Google.') }
    finally { setBusy(false) }
  })

  const finish = password.handleSubmit(async values => {
    if (busy) return
    if (!pendingGoogleRegistration()) { setStep('company'); setFlowError('La verificación expiró. Continúa nuevamente con Google.'); return }
    setBusy(true); setFlowError('')
    try {
      const details = companySchema.parse(googleDraft())
      const result = await finishGoogleRegistration(details, values.password)
      apply(authApi.fromGoogle(result)); clearGoogleFlow(); password.reset()
      navigate('/', { replace: true })
    } catch (error) {
      if (!pendingGoogleRegistration()) {
        password.reset(); setStep('company')
        setFlowError(error instanceof ApiError ? error.detail : 'Vuelve a verificar tu cuenta con Google.')
      } else handleError(error, { title: 'No se pudo finalizar el registro' })
    } finally { setBusy(false) }
  })

  return <AuthLayout title={step === 'company' ? 'Registrar empresa' : 'Crear contraseña de PsiTwin'}
    subtitle={step === 'company' ? 'Completa los datos de tu empresa para continuar con Google.' : 'Tu Gmail ya está verificado. Crea una contraseña exclusiva para PsiTwin.'}
    footer={<>¿Ya tienes cuenta? <Link to={paths.login} className="font-semibold text-fg underline decoration-accent decoration-2 underline-offset-4">Inicia sesión</Link></>}>
    {flowError && <p role="alert" className="mb-4 text-sm text-danger">{flowError}</p>}
    {step === 'company' ? <form onSubmit={beginGoogle} noValidate className="flex flex-col gap-4">
      <Field label="Nombre de la empresa" required error={err.nombre?.message}><Input autoComplete="organization" placeholder="PsiTwin Logistics" {...company.register('nombre')} /></Field>
      <Field label="Nombre del CEO" required error={err.nombre_ceo?.message}><Input autoComplete="given-name" placeholder="Nombre" maxLength={100} {...company.register('nombre_ceo')} /></Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="RUC" required error={err.ruc?.message}><Input inputMode="numeric" maxLength={11} placeholder="20123456789" {...company.register('ruc')} /></Field>
        <Field label="Sector" required error={err.sector?.message}><Input placeholder="Alimentos" {...company.register('sector')} /></Field>
      </div>
      <Field label="Teléfono" required error={err.telefono?.message}><Input type="tel" autoComplete="tel" placeholder="987654321" {...company.register('telefono')} /></Field>
      <Field label="Correo de registro" hint="Se obtiene de tu cuenta Gmail verificada al continuar con Google."><Input type="text" readOnly value={googleRegistrationEmail()} placeholder="Google proporcionará tu Gmail" /></Field>
      <Button type="submit" size="lg" fullWidth loading={busy}>Continuar con Google</Button>
    </form> : <form onSubmit={finish} noValidate className="flex flex-col gap-4">
      <p className="text-sm text-fg-muted">Gmail verificado: {googleRegistrationEmail()}</p>
      <p className="text-sm text-fg-muted">Empresa: {googleDraft().nombre} · CEO: {googleDraft().nombre_ceo}</p>
      <Field label="Contraseña nueva" required error={password.formState.errors.password?.message} hint="Entre 8 y 128 caracteres. No uses tu contraseña de Gmail."><Input type="password" autoComplete="new-password" {...password.register('password')} /></Field>
      <Field label="Confirmar contraseña" required error={password.formState.errors.confirmar?.message}><Input type="password" autoComplete="new-password" {...password.register('confirmar')} /></Field>
      <Button type="submit" size="lg" fullWidth loading={busy}>Finalizar registro</Button>
    </form>}
  </AuthLayout>
}
