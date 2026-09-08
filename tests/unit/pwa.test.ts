import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * Guardia de la instalación en el iPhone.
 *
 * Nada de esto se ve al ejecutar la app en el portátil: si alguien borra una meta,
 * la web sigue funcionando y solo se nota al añadirla a la pantalla de inicio, que
 * es cuando ya no estás mirando el código.
 */
const root = resolve(__dirname, '../..')
const html = readFileSync(resolve(root, 'index.html'), 'utf-8')
const manifest = JSON.parse(
  readFileSync(resolve(root, 'public/manifest.webmanifest'), 'utf-8'),
) as {
  display: string
  start_url: string
  theme_color: string
  icons: { src: string; sizes: string; purpose: string }[]
}

describe('instalación como PWA', () => {
  it('el viewport cubre el notch', () => {
    // Sin `viewport-fit=cover` iOS deja franjas negras arriba y abajo.
    expect(html).toContain('viewport-fit=cover')
  })

  it('trae las metas que iOS necesita, que no lee del manifest', () => {
    expect(html).toContain('name="apple-mobile-web-app-capable" content="yes"')
    expect(html).toContain('name="apple-mobile-web-app-status-bar-style"')
    expect(html).toContain('name="apple-mobile-web-app-title" content="Morfeo"')
    // iOS no acepta SVG aquí: tiene que ser un PNG.
    expect(html).toMatch(/rel="apple-touch-icon" href="\/apple-touch-icon\.png"/)
  })

  it('enlaza el manifest y el color de la barra', () => {
    expect(html).toContain('rel="manifest" href="/manifest.webmanifest"')
    expect(html).toContain('name="theme-color"')
  })

  it('el manifest abre a pantalla completa y en la portada', () => {
    expect(manifest.display).toBe('standalone')
    expect(manifest.start_url).toBe('/')
    expect(manifest.theme_color).toMatch(/^#[0-9a-f]{6}$/i)
  })

  it('incluye un icono maskable, o Android lo recorta mal', () => {
    expect(manifest.icons.some((i) => i.purpose === 'maskable')).toBe(true)
    expect(manifest.icons.map((i) => i.sizes)).toContain('192x192')
    expect(manifest.icons.map((i) => i.sizes)).toContain('512x512')
  })

  it('los iconos que declara el manifest existen de verdad', () => {
    for (const icon of manifest.icons) {
      expect(() => readFileSync(resolve(root, 'public', icon.src.slice(1)))).not.toThrow()
    }
    expect(() => readFileSync(resolve(root, 'public/apple-touch-icon.png'))).not.toThrow()
  })
})
