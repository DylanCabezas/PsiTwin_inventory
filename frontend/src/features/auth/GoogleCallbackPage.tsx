import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { api, ApiError } from '@/api/client'
import { authApi, useAplicarLogin } from '@/api/auth'
import { googleBinding, clearGoogleFlow, saveGoogleRegistration, type GoogleResult } from './googleAuth'
import { AuthLayout } from './AuthLayout'

export default function GoogleCallbackPage() {
  const started = useRef(false)
  const [error, setError] = useState('')
  const apply = useAplicarLogin()
  const navigate = useNavigate()
  useEffect(() => {
    if (started.current) return
    started.current = true
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code'), state = params.get('state')
    window.history.replaceState(null, '', window.location.pathname)
    if (!code || !state || params.has('error')) { setError('La autorización se canceló o no es válida.'); return }
    void api.post<GoogleResult>('/auth/google/complete', { code, state, binding: googleBinding() }, { auth: false }).then(result => {
      if (result.registration_required && result.registration_ticket) {
        saveGoogleRegistration(result.registration_ticket, result.verified_email)
        navigate('/registro?google=continuar', { replace: true })
      } else {
        apply(authApi.fromGoogle(result))
        clearGoogleFlow()
        navigate('/', { replace: true })
      }
    }).catch((err: unknown) => setError(err instanceof ApiError ? err.detail : 'No se pudo completar el acceso con Google. Intenta nuevamente.'))
  }, [apply, navigate])
  return <AuthLayout title="Acceso con Google" subtitle={error || 'Validando tu identidad…'} footer={<Link to="/login">Volver a iniciar sesión</Link>}>
    <p role={error ? 'alert' : 'status'}>{error || 'Estamos preparando tu sesión de PsiTwin.'}</p>
  </AuthLayout>
}
