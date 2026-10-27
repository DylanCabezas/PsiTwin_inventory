// @vitest-environment jsdom
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import RegistroPage from './RegistroPage'

vi.mock('@/api/auth', () => ({ useRegister: () => ({ mutate: vi.fn(), isPending: false }), useAplicarLogin: () => vi.fn(), authApi: {} }))
vi.mock('@/components/ui', async original => ({ ...await original<typeof import('@/components/ui')>(), useToast: () => ({ success: vi.fn() }), useApiErrorHandler: () => vi.fn() }))

describe('Company registration', () => {
  beforeEach(() => sessionStorage.clear())
  it('starts with Google before asking for company details or a password', () => {
    const html = renderToStaticMarkup(<MemoryRouter><RegistroPage /></MemoryRouter>)
    expect(html).toContain('Continuar con Google')
    expect(html).not.toContain('name="password"')
    expect(html).not.toContain('name="nombre_ceo"')
    expect(html).not.toContain('Crear mi cuenta')
  })
  it('asks for company and CEO names without surname or full-name constraints', () => {
    sessionStorage.setItem('psitwin.google.registration', 'verified-test-ticket')
    sessionStorage.setItem('psitwin.google.email', 'ceo@gmail.com')
    const html = renderToStaticMarkup(<MemoryRouter><RegistroPage /></MemoryRouter>)
    expect(html).toContain('Nombre de la empresa')
    expect(html).toContain('Nombre del CEO')
    expect(html).toContain('placeholder="Nombre"')
    expect(html).toContain('name="nombre_ceo"')
    expect(html).toContain('placeholder="Alimentos"')
    expect(html).not.toContain('apellido')
    expect(html).not.toContain('nombre completo')
    expect(html).toContain('name="password"')
    expect(html).toContain('name="confirmar"')
    expect(html).not.toContain('Usar registro con contraseña')
    expect(html).not.toContain('Ocultar registro con contraseña')
    expect(html).toContain('Crear mi cuenta')
    expect(html).toContain('ceo@gmail.com')
    expect(html).not.toContain('Continuar con Google')
  })
})
