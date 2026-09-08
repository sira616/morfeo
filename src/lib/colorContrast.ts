/**
 * WCAG 2.x relative luminance and contrast helpers.
 * @see https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio
 * @see https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
 */

export type Rgb = readonly [number, number, number]

const WCAG_AA_NORMAL = 4.5
const WCAG_AA_LARGE = 3
const WCAG_AAA_NORMAL = 7
const WCAG_AAA_LARGE = 4.5

/** Parse `#rgb` / `#rrggbb` into 0–255 channels. */
export function parseHex(hex: string): Rgb {
  const raw = hex.trim().replace(/^#/, '')
  if (!/^([0-9a-f]{3}|[0-9a-f]{6})$/i.test(raw)) {
    throw new Error(`Invalid hex color: ${hex}`)
  }
  const full =
    raw.length === 3
      ? [...raw].map((ch) => `${ch}${ch}`).join('')
      : raw
  const value = Number.parseInt(full, 16)
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255]
}

function channelToLinear(channel: number): number {
  const c = channel / 255
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
}

/** Relative luminance of a hex color (0–1). */
export function relativeLuminance(hex: string): number {
  const [r, g, b] = parseHex(hex)
  return (
    0.2126 * channelToLinear(r) +
    0.7152 * channelToLinear(g) +
    0.0722 * channelToLinear(b)
  )
}

/** Contrast ratio between two hex colors (≥ 1). */
export function contrastRatio(foreground: string, background: string): number {
  const lighter = Math.max(
    relativeLuminance(foreground),
    relativeLuminance(background),
  )
  const darker = Math.min(
    relativeLuminance(foreground),
    relativeLuminance(background),
  )
  return (lighter + 0.05) / (darker + 0.05)
}

export type ContrastLevel = 'AA' | 'AAA'
export type TextSize = 'normal' | 'large'

/**
 * Whether a pair meets WCAG contrast for the given level and text size.
 * Large text = ≥18pt regular or ≥14pt bold.
 */
export function meetsContrast(
  foreground: string,
  background: string,
  level: ContrastLevel = 'AA',
  size: TextSize = 'normal',
): boolean {
  const ratio = contrastRatio(foreground, background)
  if (level === 'AAA') {
    return size === 'large' ? ratio >= WCAG_AAA_LARGE : ratio >= WCAG_AAA_NORMAL
  }
  return size === 'large' ? ratio >= WCAG_AA_LARGE : ratio >= WCAG_AA_NORMAL
}

/** Alpha-blend `fg` over opaque `bg` (alpha 0–1) → hex. */
export function blendOver(fg: string, bg: string, alpha: number): string {
  const a = Math.min(1, Math.max(0, alpha))
  const [fr, fgC, fb] = parseHex(fg)
  const [br, bgC, bb] = parseHex(bg)
  const mix = (f: number, b: number) => Math.round(f * a + b * (1 - a))
  return `#${[mix(fr, br), mix(fgC, bgC), mix(fb, bb)]
    .map((n) => n.toString(16).padStart(2, '0'))
    .join('')}`
}
