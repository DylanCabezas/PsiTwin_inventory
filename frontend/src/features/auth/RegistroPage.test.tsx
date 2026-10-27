// @vitest-environment jsdom
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import RegistroPage from './RegistroPage'

vi.mock('@/api/auth', () => ({ useRegister: () => ({ mutate: vi.fn(), isPending: false }), useAplicarLogin: () => vi.fn(), authApi: {} }))
vi.mock('@/components/ui', async original => ({ ...await original<typeof import('@/components/ui')>(), useToast: () => ({ success: vi.fn() }), useApiErrorHandler: () => vi.fn() }))

describe('Company registration', () => {
  beforeEach(() => sessionStorage.clear())
  it('restores all business fields before Google and postpones password creation', () => {
    const html = renderToStaticMarkup(<MemoryRouter><RegistroPage /></MemoryRouter>)
    expect(html).toContain('Continuar con Google')
    expect(html).not.toContain('name="password"')
    for (const field of ['nombre', 'nombre_ceo', 'ruc', 'sector', 'telefono']) expect(html).toContain(`name="${field}"`)
    expect(html).toContain('placeholder="Nombre"')
    expect(html).toContain('placeholder="Alimentos"')
    expect(html).not.toContain('Crear mi cuenta')
  })
  it('shows only the password screen after Google and preserves the business draft', () => {
    sessionStorage.setItem('psitwin.google.registration', 'verified-test-ticket')
    sessionStorage.setItem('psitwin.google.email', 'ceo@gmail.com')
    sessionStorage.setItem('psitwin.google.company', JSON.stringify({ nombre: 'Empresa', nombre_ceo: 'Carlos', ruc: '20123456789', sector: 'Alimentos', telefono: '987654321' }))
    const html = renderToStaticMarkup(<MemoryRouter><RegistroPage /></MemoryRouter>)
    expect(html).toContain('Crear contraseña de PsiTwin')
    expect(html).toContain('Carlos')
    expect(html).not.toContain('name="nombre_ceo"')
    expect(html).not.toContain('apellido')
    expect(html).not.toContain('nombre completo')
    expect(html).toContain('name="password"')
    expect(html).toContain('name="confirmar"')
    expect(html).not.toContain('Usar registro con contraseña')
    expect(html).not.toContain('Ocultar registro con contraseña')
    expect(html).toContain('Finalizar registro')
    expect(html).toContain('ceo@gmail.com')
    expect(html).not.toContain('Continuar con Google')
  })
})
