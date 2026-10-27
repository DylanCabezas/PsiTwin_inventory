import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router'
import { z } from 'zod'
import { authApi, useAplicarLogin } from '@/api/auth'
import { useState } from 'react'
import { startGoogle, googleDraft, pendingGoogleRegistration, finishGoogleRegistration, clearGoogleFlow } from './googleAuth'
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

  const form = useForm<RegistroForm>({
    resolver: zodResolver(schema),
    defaultValues: { nombre: '', nombre_ceo: '', ruc: '', sector: '', telefono: '', password: '', confirmar: '', ...googleDraft() },
  })
  const { register, handleSubmit, formState } = form
  const err = formState.errors
  async function withGoogle() {
    if (!await form.trigger()) return
    const values = form.getValues()
    const company = { nombre: values.nombre.trim(), nombre_ceo: values.nombre_ceo.trim(), ruc: values.ruc.trim(), sector: values.sector.trim(), telefono: values.telefono.trim() }
    setGoogleBusy(true)
    try {
      if (pendingGoogleRegistration()) {
        const result = await finishGoogleRegistration(company, values.password)
        apply(authApi.fromGoogle(result)); clearGoogleFlow(); navigate('/', { replace: true })
      } else await startGoogle(company, undefined, undefined, values.password)
    } catch (e) { handleError(e, { title: 'No se pudo registrar con Google' }) }
    finally { setGoogleBusy(false) }
  }

  const onSubmit = handleSubmit(() => withGoogle())

  return (
    <AuthLayout
      title="Registrar empresa"
      subtitle="Crea la cuenta de administración de tu empresa."
      footer={
        <>
          ¿Ya tienes cuenta?{' '}
          <Link to={paths.login} className="font-semibold text-fg underline decoration-accent decoration-2 underline-offset-4">
            Inicia sesión
          </Link>
        </>
      }
    >
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
        <Button type="submit" size="lg" fullWidth loading={googleBusy}>Continuar con Google</Button>
        <p className="text-sm text-fg-muted">Google verifica tu correo. Después podrás iniciar sesión con Google o con ese correo y la contraseña que acabas de crear.</p>
      </form>
    </AuthLayout>
  )
}
