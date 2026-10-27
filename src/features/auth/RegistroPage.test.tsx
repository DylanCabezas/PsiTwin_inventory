// @vitest-environment jsdom
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import RegistroPage from './RegistroPage'

vi.mock('@/api/auth', () => ({ useRegister: () => ({ mutate: vi.fn(), isPending: false }), useAplicarLogin: () => vi.fn(), authApi: {} }))
vi.mock('@/components/ui', async original => ({ ...await original<typeof import('@/components/ui')>(), useToast: () => ({ success: vi.fn() }), useApiErrorHandler: () => vi.fn() }))

describe('Company registration', () => {
  it('asks for company and CEO names without surname or full-name constraints', () => {
    const html = renderToStaticMarkup(<MemoryRouter><RegistroPage /></MemoryRouter>)
    expect(html).toContain('Nombre de la empresa')
    expect(html).toContain('Nombre del CEO')
    expect(html).toContain('placeholder="Nombre"')
    expect(html).toContain('name="nombre_ceo"')
    expect(html).toContain('placeholder="Alimentos"')
    expect(html).not.toContain('apellido')
    expect(html).not.toContain('nombre completo')
  })
})
