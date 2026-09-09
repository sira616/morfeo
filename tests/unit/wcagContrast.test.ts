import { describe, expect, it } from 'vitest'
import {
  blendOver,
  contrastRatio,
  meetsContrast,
  parseHex,
  relativeLuminance,
} from '@/lib/colorContrast'
import {
  DARK_AA_PAIRS,
  LIGHT_AA_PAIRS,
  NOCHE_AA_PAIRS,
  UI_COMPONENT_PAIRS,
} from '@/lib/wcagPalette'

describe('colorContrast helpers', () => {
  it('parses 3- and 6-digit hex', () => {
    expect(parseHex('#fff')).toEqual([255, 255, 255])
    expect(parseHex('#0b0e14')).toEqual([11, 14, 20])
  })

  it('rejects invalid hex', () => {
    expect(() => parseHex('red')).toThrow(/Invalid hex/)
  })

  it('matches WCAG white/black reference ratio (~21:1)', () => {
    expect(contrastRatio('#ffffff', '#000000')).toBeCloseTo(21, 0)
  })

  it('is commutative', () => {
    expect(contrastRatio('#eceaf6', '#0b0e14')).toBeCloseTo(
      contrastRatio('#0b0e14', '#eceaf6'),
      5,
    )
  })

  it('relative luminance of black is 0 and white is 1', () => {
    expect(relativeLuminance('#000000')).toBeCloseTo(0, 5)
    expect(relativeLuminance('#ffffff')).toBeCloseTo(1, 5)
  })

  it('blendOver approximates translucent tint over white', () => {
    expect(blendOver('#1aa897', '#ffffff', 0.12).toLowerCase()).toBe('#e4f5f3')
  })
})

describe('WCAG 2.1 AA — dark theme text pairs', () => {
  it.each(DARK_AA_PAIRS)(
    '$id ≥ 4.5:1 ($usage)',
    ({ foreground, background, size = 'normal' }) => {
      const ratio = contrastRatio(foreground, background)
      expect(
        meetsContrast(foreground, background, 'AA', size),
        `ratio ${ratio.toFixed(2)} for ${foreground} on ${background}`,
      ).toBe(true)
      if (size === 'normal') {
        expect(ratio).toBeGreaterThanOrEqual(4.5)
      }
    },
  )
})

describe('WCAG 2.1 AA — light theme text pairs', () => {
  it.each(LIGHT_AA_PAIRS)(
    '$id ≥ 4.5:1 ($usage)',
    ({ foreground, background, size = 'normal' }) => {
      const ratio = contrastRatio(foreground, background)
      expect(
        meetsContrast(foreground, background, 'AA', size),
        `ratio ${ratio.toFixed(2)} for ${foreground} on ${background}`,
      ).toBe(true)
      if (size === 'normal') {
        expect(ratio).toBeGreaterThanOrEqual(4.5)
      }
    },
  )
})

describe('WCAG 2.1 AA — deep night theme text pairs', () => {
  it.each(NOCHE_AA_PAIRS)(
    '$id ≥ 4.5:1 ($usage)',
    ({ foreground, background, size = 'normal' }) => {
      const ratio = contrastRatio(foreground, background)
      expect(
        meetsContrast(foreground, background, 'AA', size),
        `ratio ${ratio.toFixed(2)} for ${foreground} on ${background}`,
      ).toBe(true)
      if (size === 'normal') {
        expect(ratio).toBeGreaterThanOrEqual(4.5)
      }
    },
  )

  /**
   * El techo, que en los otros temas no tiene sentido y aquí es la mitad del asunto.
   *
   * El modo noche existe para no deslumbrar: el texto del tema oscuro normal da 17:1
   * sobre su fondo, y eso a las doce es un flash. Sin este tope, cualquier "se lee
   * poco, lo subo un pelo" acaba devolviendo el tema al punto de partida sin que
   * ningún test se queje, porque subir el contraste nunca rompe la regla de AA.
   */
  it('no deslumbra: el texto se queda muy por debajo del tema oscuro', () => {
    const cuerpo = NOCHE_AA_PAIRS.find((p) => p.id === 'noche-ink-on-canvas')!
    const ratio = contrastRatio(cuerpo.foreground, cuerpo.background)
    expect(ratio).toBeGreaterThanOrEqual(4.5)
    expect(ratio).toBeLessThanOrEqual(12)
  })

  it('no queda ni un color frío: todo tira a ámbar', () => {
    for (const { id, foreground } of NOCHE_AA_PAIRS) {
      const [r, , b] = parseHex(foreground)
      // El azul por encima del rojo es lo que la app le pide al usuario que evite
      // antes de dormir; el tema no puede ser el primero en saltárselo.
      expect(b, `${id}: ${foreground} tiene más azul que rojo`).toBeLessThan(r)
    }
  })
})

describe('WCAG 2.1 AA — UI / large text (≥ 3:1)', () => {
  it.each(UI_COMPONENT_PAIRS)(
    '$id ≥ 3:1 ($usage)',
    ({ foreground, background }) => {
      const ratio = contrastRatio(foreground, background)
      expect(
        meetsContrast(foreground, background, 'AA', 'large'),
        `ratio ${ratio.toFixed(2)} for ${foreground} on ${background}`,
      ).toBe(true)
      expect(ratio).toBeGreaterThanOrEqual(3)
    },
  )
})
