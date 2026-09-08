/**
 * Resolved hex pairs that mirror `src/styles/tokens.css`.
 * Keep in sync when palette tokens change — unit tests assert WCAG AA.
 */

export type ContrastPair = {
  id: string
  foreground: string
  background: string
  /** WCAG text size category for the intended use. */
  size?: 'normal' | 'large'
  usage: string
}

/** Dark theme (default / `:root`). */
export const DARK_AA_PAIRS: ContrastPair[] = [
  {
    id: 'dark-ink-on-canvas',
    foreground: '#eceaf6',
    background: '#0b0e14',
    usage: 'Body text on canvas',
  },
  {
    id: 'dark-ink-on-surf',
    foreground: '#eceaf6',
    background: '#17151f',
    usage: 'Body text on cards',
  },
  {
    id: 'dark-ink-dim-on-canvas',
    foreground: '#a29db4',
    background: '#0b0e14',
    usage: 'Secondary copy on canvas',
  },
  {
    id: 'dark-ink-dim-on-surf',
    foreground: '#a29db4',
    background: '#17151f',
    usage: 'Secondary copy on cards',
  },
  {
    id: 'dark-ink-faint-on-canvas',
    foreground: '#8b8698',
    background: '#0b0e14',
    usage: 'Field labels on canvas',
  },
  {
    id: 'dark-ink-faint-on-surf',
    foreground: '#8b8698',
    background: '#17151f',
    usage: 'Field labels on cards',
  },
  {
    id: 'dark-on-primary',
    foreground: '#ffffff',
    background: '#6c5ce7',
    usage: 'Text on indigo / user bubbles',
  },
  {
    id: 'dark-on-brand-yellow',
    foreground: '#0b0e14',
    background: '#f5d23a',
    usage: 'CTA text on brand yellow',
  },
  {
    id: 'dark-on-brand-green',
    foreground: '#0b0e14',
    background: '#4fd6a0',
    usage: 'Texto sobre el verde de estado',
  },
  {
    id: 'dark-accent-link',
    foreground: '#4fd6a0',
    background: '#0b0e14',
    usage: 'Verde de estado sobre el lienzo',
  },
  {
    id: 'dark-teal-on-surf',
    foreground: '#3fd1c0',
    background: '#17151f',
    usage: 'Teal accents on cards',
  },
  {
    id: 'dark-on-teal-chip',
    foreground: '#052e2a',
    background: '#3fd1c0',
    usage: 'Chip label on teal fill',
  },
  {
    id: 'dark-on-gold-chip',
    foreground: '#241a04',
    background: '#f4b860',
    usage: 'Chip label on gold fill',
  },
  {
    id: 'dark-error',
    foreground: '#f0797b',
    background: '#0b0e14',
    usage: 'Error text on canvas',
  },
  {
    id: 'dark-blue-on-surf',
    foreground: '#6688ff',
    background: '#17151f',
    usage: 'Blue Team labels on cards',
  },
  {
    id: 'dark-on-blue-chip',
    foreground: '#0b0e14',
    background: '#6688ff',
    usage: 'Chip label on blue fill',
  },
]

/** Light theme (`.light`). */
export const LIGHT_AA_PAIRS: ContrastPair[] = [
  {
    id: 'light-ink-on-canvas',
    foreground: '#0b0e14',
    background: '#f3f5f0',
    usage: 'Body text on canvas',
  },
  {
    id: 'light-ink-on-surf',
    foreground: '#0b0e14',
    background: '#ffffff',
    usage: 'Body text on cards',
  },
  {
    id: 'light-ink-dim-on-surf',
    foreground: '#3a4452',
    background: '#ffffff',
    usage: 'Secondary copy on cards',
  },
  {
    id: 'light-ink-faint-on-surf',
    foreground: '#6a7482',
    background: '#ffffff',
    usage: 'Field labels on cards',
  },
  {
    id: 'light-accent-link-on-surf',
    foreground: '#0f6b4d',
    background: '#ffffff',
    usage: 'Accent links on cards',
  },
  {
    id: 'light-accent-link-on-canvas',
    foreground: '#0f6b4d',
    background: '#f3f5f0',
    usage: 'Verde de estado sobre el lienzo',
  },
  {
    id: 'light-on-primary',
    foreground: '#ffffff',
    background: '#5b4bd6',
    usage: 'Text on indigo controls',
  },
  {
    id: 'light-on-brand-yellow',
    foreground: '#0b0e14',
    background: '#f5d23a',
    usage: 'CTA text on brand yellow',
  },
  {
    // En tema claro el verde de estado es oscuro y se usa como texto o como relleno
    // con texto blanco encima, no como fondo de tinta oscura.
    id: 'light-on-brand-green',
    foreground: '#ffffff',
    background: '#0f6b4d',
    usage: 'Texto sobre el verde de estado',
  },
  {
    id: 'light-teal-on-tint',
    foreground: '#0a6b60',
    background: '#e2edec',
    usage: 'Teal text on teal-tinted chip',
  },
  {
    id: 'light-teal-on-surf',
    foreground: '#0a6b60',
    background: '#ffffff',
    usage: 'Teal text on white',
  },
  {
    id: 'light-on-primary-container',
    foreground: '#2f2478',
    background: '#ebe7ff',
    usage: 'Text on indigo container',
  },
  {
    id: 'light-on-teal-chip',
    foreground: '#04312c',
    background: '#3fd1c0',
    usage: 'Chip label on teal fill',
  },
  {
    id: 'light-on-gold-chip',
    foreground: '#2a1c04',
    background: '#d4922a',
    usage: 'Chip label on gold fill',
  },
  {
    id: 'light-error',
    foreground: '#c03940',
    background: '#ffffff',
    usage: 'Error text on cards',
  },
  {
    id: 'light-blue-on-surf',
    foreground: '#1a5fd0',
    background: '#ffffff',
    usage: 'Blue Team labels on cards',
  },
  {
    id: 'light-on-blue-chip',
    foreground: '#ffffff',
    background: '#1a5fd0',
    usage: 'Chip label on blue fill',
  },
]

/** UI / non-text graphics and large text — WCAG AA ≥ 3:1. */
export const UI_COMPONENT_PAIRS: ContrastPair[] = [
  {
    id: 'dark-indigo-on-canvas',
    foreground: '#6c5ce7',
    background: '#0b0e14',
    size: 'large',
    usage: 'Indigo icon/control on canvas',
  },
  {
    id: 'light-indigo-on-canvas',
    foreground: '#5b4bd6',
    background: '#f3f5f0',
    size: 'large',
    usage: 'Indigo icon/control on light canvas',
  },
  {
    id: 'dark-focus-border-proxy',
    foreground: '#6c5ce7',
    background: '#17151f',
    size: 'large',
    usage: 'Focus accent vs card surface',
  },
]
