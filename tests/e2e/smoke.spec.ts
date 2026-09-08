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

  await page.getByLabel('Usuario o email').fill('demo')
  await page.getByLabel('Contraseña').fill('ContrasenaLarga123')
  await page.getByRole('button', { name: 'Entrar' }).click()

  await expect(page.getByText('A la cama entre')).toBeVisible()
  await expect(page.getByText(/No es la hora de dormirte/i)).toBeVisible()

  // El desglose vive detrás de una pregunta, no ocupando la portada.
  await page.getByRole('button', { name: /Por qué esta hora/i }).click()
  await expect(page.getByRole('dialog')).toContainText('Necesidad basal')
})

test('se puede apuntar la noche sin reloj', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Usuario o email').fill('demo')
  await page.getByLabel('Contraseña').fill('ContrasenaLarga123')
  await page.getByRole('button', { name: 'Entrar' }).click()

  await page.getByRole('link', { name: 'Reloj' }).click()
  // El formulario va primero: sin reloj es la única forma de alimentar el motor.
  await expect(page.getByText('¿Cómo ha ido la noche?')).toBeVisible()
  await expect(page.getByText('7 h 10')).toBeVisible()
})

test('la navegación llega al historial y al importador', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Usuario o email').fill('demo')
  await page.getByLabel('Contraseña').fill('ContrasenaLarga123')
  await page.getByRole('button', { name: 'Entrar' }).click()

  await page.getByRole('link', { name: 'Historial' }).click()
  await expect(page.getByText(/Últimas \d+ noches/)).toBeVisible()

  await page.getByRole('link', { name: 'Reloj' }).click()
  await expect(page.getByText('Importar del reloj')).toBeVisible()
})
