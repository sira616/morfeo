import { expect, test } from '@playwright/test'

/**
 * Recorrido mínimo contra el build real servido por `preview`, con MSW respondiendo
 * la API. Cubre lo que un test unitario no ve: que el router, el guard de sesión y
 * el arranque de los mocks encajan de verdad.
 */
test('entrar y ver la ventana de esta noche', async ({ page }) => {
  await page.goto('/')

  // Sin sesión, el guard manda al login conservando el destino en `next`.
  await expect(page).toHaveURL(/\/login/)

  await page.getByLabel('Email').fill('demo@morfeo.app')
  await page.getByLabel('Contraseña').fill('contrasena-de-prueba')
  await page.getByRole('button', { name: 'Entrar' }).click()

  await expect(page.getByText('A la cama entre')).toBeVisible()
  await expect(page.getByText(/No es la hora de dormirte/i)).toBeVisible()
  await expect(page.getByText('Por qué esta hora')).toBeVisible()
})

test('la navegación llega al historial y al importador', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Email').fill('demo@morfeo.app')
  await page.getByLabel('Contraseña').fill('contrasena-de-prueba')
  await page.getByRole('button', { name: 'Entrar' }).click()

  await page.getByRole('link', { name: 'Historial' }).click()
  await expect(page.getByText(/Últimas \d+ noches/)).toBeVisible()

  await page.getByRole('link', { name: 'Reloj' }).click()
  await expect(page.getByText('Importar del reloj')).toBeVisible()
})
