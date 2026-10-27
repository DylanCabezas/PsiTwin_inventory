import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router'
import { z } from 'zod'
import { authApi, useAplicarLogin } from '@/api/auth'
import { useState } from 'react'
import { startGoogle, googleDraft, pendingGoogleRegistration, googleRegistrationEmail, finishGoogleRegistration, clearGoogleFlow } from './googleAuth'
import { ApiError } from '@/api/client'
import { Button, Field, Input, useApiErrorHandler } from '@/components/ui'
import { texto } from '@/lib/zod'
import { paths } from '@/paths'
import { AuthLayout } from './AuthLayout'

const schema = z
  .object({
    nombre: texto({ max: 100 }),
    nombre_ceo: texto({ max: 100 }),
    ruc: z.string().trim().regex(/^\d{11}$/, 'El RUC debe tener 11 dígitos'),
    sector: texto({ max: 100 }),
    telefono: z
      .string()
      .trim()
      .regex(/^\+?[\d\s-]{6,20}$/, 'Teléfono no válido (solo dígitos, espacios o guiones)'),
    password: z.string().min(6, 'La contraseña debe tener al menos 6 caracteres').max(128, 'Máximo 128 caracteres'),
    confirmar: z.string().min(1, 'Repite la contraseña'),
  })
  .refine((v) => v.password === v.confirmar, { path: ['confirmar'], message: 'Las contraseñas no coinciden' })

type RegistroForm = z.input<typeof schema>

export default function RegistroPage() {
  const navigate = useNavigate()
  const handleError = useApiErrorHandler()
  const apply = useAplicarLogin()
  const [googleBusy, setGoogleBusy] = useState(false)
  const [verified, setVerified] = useState(() => !!pendingGoogleRegistration())
  const [flowError, setFlowError] = useState('')

  const form = useForm<RegistroForm>({
    resolver: zodResolver(schema),
    defaultValues: { nombre: '', nombre_ceo: '', ruc: '', sector: '', telefono: '', password: '', confirmar: '', ...googleDraft() },
  })
  const { register, handleSubmit, formState } = form
  const err = formState.errors
  async function beginGoogle() {
    setGoogleBusy(true)
    setFlowError('')
    try { await startGoogle() }
    catch (error) { setFlowError(error instanceof Error ? error.message : 'No se pudo iniciar la verificación con Google.') }
    finally { setGoogleBusy(false) }
  }
  async function withGoogle() {
    if (!await form.trigger()) return
    const values = form.getValues()
    const company = { nombre: values.nombre.trim(), nombre_ceo: values.nombre_ceo.trim(), ruc: values.ruc.trim(), sector: values.sector.trim(), telefono: values.telefono.trim() }
    setGoogleBusy(true)
    setFlowError('')
    try {
      if (pendingGoogleRegistration()) {
        const result = await finishGoogleRegistration(company, values.password)
        apply(authApi.fromGoogle(result)); clearGoogleFlow(); navigate('/', { replace: true })
      } else { setVerified(false); setFlowError('Verifica tu Gmail con Google antes de crear tu cuenta.') }
    } catch (e) {
      if (!pendingGoogleRegistration()) {
        setVerified(false)
        setFlowError(e instanceof ApiError ? e.detail : 'La verificación expiró. Vuelve a continuar con Google.')
      } else handleError(e, { title: 'No se pudo completar el registro' })
    }
    finally { setGoogleBusy(false) }
  }

  const onSubmit = handleSubmit(() => withGoogle())

  return (
    <AuthLayout
      title="Registrar empresa"
      subtitle={verified ? 'Gmail verificado. Completa tu empresa y crea tu contraseña de PsiTwin.' : 'Primero verifica tu Gmail con Google. Después crearás tu contraseña de PsiTwin.'}
      footer={
        <>
          ¿Ya tienes cuenta?{' '}
          <Link to={paths.login} className="font-semibold text-fg underline decoration-accent decoration-2 underline-offset-4">
            Inicia sesión
          </Link>
        </>
      }
    >
      {flowError && <p role="alert" className="mb-4 text-sm text-danger">{flowError}</p>}
      {!verified ? <div className="flex flex-col gap-4">
        <Button type="button" size="lg" fullWidth loading={googleBusy} onClick={() => void beginGoogle()}>Continuar con Google</Button>
        <p className="text-sm text-fg-muted">Selecciona una cuenta Gmail (@gmail.com). La contraseña de PsiTwin se crea después de verificar tu correo.</p>
      </div> : <>
      <p className="mb-4 text-sm text-fg-muted">{googleRegistrationEmail() ? `Gmail verificado: ${googleRegistrationEmail()}` : 'Tu identidad de Google está verificada.'}</p>
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        <Field label="Nombre de la empresa" error={err.nombre?.message} required>
          <Input autoComplete="organization" placeholder="PsiTwin Logistics" {...register('nombre')} />
        </Field>
        <Field label="Nombre del CEO" error={err.nombre_ceo?.message} required>
          <Input autoComplete="given-name" placeholder="Nombre" maxLength={100} {...register('nombre_ceo')} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="RUC" error={err.ruc?.message} required>
            <Input inputMode="numeric" maxLength={11} placeholder="20123456789" className="font-mono" {...register('ruc')} />
          </Field>
          <Field label="Sector" error={err.sector?.message} required>
            <Input placeholder="Alimentos" {...register('sector')} />
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Teléfono" error={err.telefono?.message} required>
            <Input type="tel" autoComplete="tel" inputMode="tel" placeholder="987654321" {...register('telefono')} />
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Contraseña" error={err.password?.message} required hint="Mínimo 6 caracteres.">
            <Input type="password" autoComplete="new-password" {...register('password')} />
          </Field>
          <Field label="Repetir contraseña" error={err.confirmar?.message} required>
            <Input type="password" autoComplete="new-password" {...register('confirmar')} />
          </Field>
        </div>
        <Button type="submit" size="lg" fullWidth loading={googleBusy}>Crear mi cuenta</Button>
        <p className="text-sm text-fg-muted">Esta contraseña es para PsiTwin. No escribas la contraseña de tu cuenta Google.</p>
      </form>
      </>}
    </AuthLayout>
  )
}
