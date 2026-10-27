import { api, ApiError } from '@/api/client'
import type { LoginResponseRaw } from '@/api/types'

export type GoogleCompany = { nombre: string; nombre_ceo: string; sector: string; ruc: string; telefono: string }
export type GoogleResult = LoginResponseRaw & { registration_required?: boolean; registration_ticket?: string }
const BINDING = 'psitwin.google.binding'
const TICKET = 'psitwin.google.registration'
const DRAFT = 'psitwin.google.company'
export function googleBinding() {
  let binding = sessionStorage.getItem(BINDING)
  if (!binding) {
    binding = Array.from(crypto.getRandomValues(new Uint8Array(32)), b => b.toString(16).padStart(2, '0')).join('')
    sessionStorage.setItem(BINDING, binding)
  }
  return binding
}
export async function startGoogle(company?: GoogleCompany, password?: string, newPassword?: string, registrationPassword?: string) {
  sessionStorage.removeItem(TICKET)
  const binding = googleBinding()
  if (company) sessionStorage.setItem(DRAFT, JSON.stringify(company))
  const result = await api.post<{ authorization_url: string }>(newPassword ? '/auth/google/password/start' : password === undefined ? '/auth/google/start' : '/auth/google/link',
    { binding, company, ...(registrationPassword ? { registration_password: registrationPassword } : {}), ...(password === undefined ? {} : { password }), ...(newPassword ? { new_password: newPassword } : {}) }, { auth: password !== undefined || !!newPassword, logoutOnAuthError: false })
  const url = new URL(result.authorization_url)
  if (url.origin !== 'https://accounts.google.com') throw new Error('Dirección de Google no válida')
  const callback = new URL(url.searchParams.get('redirect_uri') ?? '')
  if (callback.origin !== window.location.origin)
    throw new Error(`Abre PsiTwin en ${callback.origin} antes de continuar con Google. El registro debe regresar al mismo origen para conservar su sesión segura.`)
  window.location.assign(url.href)
}
export function googleDraft(): Partial<GoogleCompany> {
  try { return JSON.parse(sessionStorage.getItem(DRAFT) ?? '{}') as Partial<GoogleCompany> } catch { return {} }
}
export function pendingGoogleRegistration() { return sessionStorage.getItem(TICKET) }
export function saveGoogleRegistration(ticket: string) { sessionStorage.setItem(TICKET, ticket) }
export function clearGoogleFlow() { for (const key of [BINDING, TICKET, DRAFT]) sessionStorage.removeItem(key) }
export async function finishGoogleRegistration(company: GoogleCompany, registrationPassword?: string) {
  try {
    return await api.post<GoogleResult>('/auth/google/register', { company, ...(registrationPassword ? { registration_password: registrationPassword } : {}), binding: googleBinding(), registration_ticket: pendingGoogleRegistration() }, { auth: false })
  } catch (error) {
    if (error instanceof ApiError && [400, 409].includes(error.status)) sessionStorage.removeItem(TICKET)
    throw error
  }
}
