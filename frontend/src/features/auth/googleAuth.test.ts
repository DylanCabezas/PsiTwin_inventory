// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '@/api/client'
import { startGoogle } from './googleAuth'

vi.mock('@/api/client', () => ({ api: { post: vi.fn() }, ApiError: class extends Error {} }))
describe('Google origin binding', () => {
  const assign = vi.fn()
  beforeEach(() => {
    sessionStorage.clear()
    vi.stubGlobal('window', { location: { origin: 'http://localhost:5173', assign } })
  })
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks() })
  it('keeps the callback on the origin that holds the OAuth state', async () => {
    const url = 'https://accounts.google.com/o/oauth2/v2/auth?redirect_uri=' + encodeURIComponent('http://localhost:5173/auth/google/callback')
    vi.mocked(api.post).mockResolvedValue({ authorization_url: url })
    await startGoogle()
    expect(assign).toHaveBeenCalledExactlyOnceWith(url)
    expect(sessionStorage.getItem('psitwin.google.binding')).toMatch(/^[a-f0-9]{64}$/)
  })
  it('explains a localhost versus IP mismatch before redirecting to Google', async () => {
    vi.mocked(api.post).mockResolvedValue({ authorization_url: 'https://accounts.google.com/o/oauth2/v2/auth?redirect_uri=' + encodeURIComponent('http://127.0.0.1:5173/auth/google/callback') })
    await expect(startGoogle()).rejects.toThrow('mismo origen')
    expect(assign).not.toHaveBeenCalled()
  })
  it('rejects a provider URL outside Google', async () => {
    vi.mocked(api.post).mockResolvedValue({ authorization_url: 'https://example.org/login' })
    await expect(startGoogle()).rejects.toThrow('Dirección de Google no válida')
    expect(assign).not.toHaveBeenCalled()
  })
})
