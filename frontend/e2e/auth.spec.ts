import { test, expect, type Page } from '@playwright/test'

const api = 'http://127.0.0.1:18080'
const details = { nombre: 'Empresa navegador', nombre_ceo: 'Carlos', ruc: '20123456789', sector: 'Alimentos', telefono: '987654321' }
const password = 'PsiTwin-browser-2026'

test.beforeEach(async ({ page, request }) => {
  expect((await request.post(`${api}/__test/reset`)).ok()).toBeTruthy()
  await page.route('https://accounts.google.com/**', async route => {
    const url = new URL(route.request().url())
    const callback = new URL(url.searchParams.get('redirect_uri')!)
    callback.searchParams.set('code', 'browser-test-code')
    callback.searchParams.set('state', url.searchParams.get('state')!)
    await route.fulfill({ contentType: 'text/html', body: `<h1>Google simulado para pruebas</h1><a href="${callback.href.replaceAll('&', '&amp;')}">Seleccionar Gmail de prueba</a>` })
  })
})

async function startRegistration(page: Page) {
  await page.goto('/registro')
  for (const [name, value] of Object.entries(details)) await page.locator(`input[name="${name}"]`).fill(value)
  await expect(page.getByPlaceholder('Nombre', { exact: true })).toHaveValue('Carlos')
  await expect(page.getByPlaceholder('Alimentos')).toBeVisible()
  await expect(page.locator('input[type=password]')).toHaveCount(0)
  await page.getByRole('button', { name: 'Continuar con Google', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Google simulado para pruebas' })).toBeVisible()
  expect((await (await page.request.get(`${api}/__test/status`)).json()).companies).toBe(0)
  await page.getByRole('link', { name: 'Seleccionar Gmail de prueba' }).click()
  await expect(page.getByRole('heading', { name: 'Crear contraseña de PsiTwin', exact: true })).toBeVisible()
  await expect(page.getByText('Empresa: Empresa navegador · CEO: Carlos')).toBeVisible()
  await expect(page.getByText('Gmail verificado: psitwin.browser.test@gmail.com')).toBeVisible()
  expect((await (await page.request.get(`${api}/__test/status`)).json()).companies).toBe(0)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Crear contraseña de PsiTwin', exact: true })).toBeVisible()
}

async function finishRegistration(page: Page) {
  await page.locator('input[name=password]').fill(password)
  await page.locator('input[name=confirmar]').fill(password)
  await page.getByRole('button', { name: 'Finalizar registro', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Almacenes', exact: true })).toBeVisible()
  await expect(page.getByText('Ocurrió un error inesperado')).toHaveCount(0)
}

test('complete registration, both logins, BSON profile, reload, logout and no duplicates', async ({ page, request }) => {
  const serverErrors: string[] = []
  page.on('response', response => { if (response.url().includes('/api/') && response.status() >= 500) serverErrors.push(`${response.status()} ${response.url()}`) })
  await startRegistration(page)
  await page.locator('input[name=password]').fill('short')
  await page.locator('input[name=confirmar]').fill('different')
  await page.getByRole('button', { name: 'Finalizar registro' }).click()
  await expect(page.getByText('Usa al menos 8 caracteres')).toBeVisible()
  await finishRegistration(page)
  let status = await (await request.get(`${api}/__test/status`)).json()
  expect(status).toMatchObject({ companies: 1, outbox: 1, google_linked: true, argon2id: true, sent: 1, personalized: true, company: details })
  expect(status.sender).toContain('psitwin2026@gmail.com')
  const companyId = status.company.id_empresa
  await request.post(`${api}/__test/bson-dates`)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Almacenes', exact: true })).toBeVisible()
  await page.goto('/perfil')
  await expect(page.getByRole('heading', { name: /Perfil/ })).toBeVisible()
  await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Iniciar sesión', exact: true })).toBeVisible()
  await page.goto('/perfil')
  await expect(page).toHaveURL(/\/login/)
  await page.locator('input[name=correo]').fill('psitwin.browser.test@gmail.com')
  await page.locator('input[name=password]').fill(password)
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click()
  await expect(page.getByRole('heading', { name: /Perfil/ })).toBeVisible()
  await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click()
  await page.getByRole('button', { name: 'Iniciar sesión con Google', exact: true }).click()
  await page.getByRole('link', { name: 'Seleccionar Gmail de prueba' }).click()
  await expect(page.getByRole('heading', { name: 'Almacenes', exact: true })).toBeVisible()
  status = await (await request.get(`${api}/__test/status`)).json()
  expect(status.companies).toBe(1)
  expect(status.company.id_empresa).toBe(companyId)
  expect(status.sent).toBe(1)
  await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click()
  await page.goto('/registro')
  for (const [name, value] of Object.entries(details)) await page.locator(`input[name="${name}"]`).fill(value)
  await page.getByRole('button', { name: 'Continuar con Google', exact: true }).click()
  await page.getByRole('link', { name: 'Seleccionar Gmail de prueba' }).click()
  await expect(page.getByRole('alert')).toContainText('Esta cuenta Google ya está registrada')
  expect((await (await request.get(`${api}/__test/status`)).json()).companies).toBe(1)
  expect(serverErrors).toEqual([])
})

test('SMTP failure preserves the company and permits password login', async ({ page, request }) => {
  await request.post(`${api}/__test/smtp-fail`)
  await startRegistration(page)
  await finishRegistration(page)
  await expect.poll(async () => (await (await request.get(`${api}/__test/status`)).json()).companies).toBe(1)
  expect((await (await request.get(`${api}/__test/status`)).json()).sent).toBe(0)
  await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click()
  await page.locator('input[name=correo]').fill('psitwin.browser.test@gmail.com')
  await page.locator('input[name=password]').fill(password)
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Almacenes', exact: true })).toBeVisible()
})
