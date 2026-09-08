import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RegularityCard } from '@/components/insights/RegularityCard'
import { AssociationsCard } from '@/components/insights/AssociationsCard'
import { AdherenceCard } from '@/components/insights/AdherenceCard'
import { SleepHeatmap } from '@/components/insights/SleepHeatmap'
import { mockInsights } from '@/mocks/fixtures'

describe('Regularidad', () => {
  it('sin noches con horas no inventa una puntuación', () => {
    // El caso importante: un cero aquí se leería como "tienes un horario malísimo",
    // cuando lo que pasa es que el importador solo trajo duraciones.
    render(<RegularityCard regularity={null} />)
    expect(screen.getByText(/Hacen falta al menos cinco noches/i)).toBeInTheDocument()
    expect(screen.queryByText('0')).not.toBeInTheDocument()
  })

  it('muestra la puntuación y la variación típica', () => {
    render(<RegularityCard regularity={mockInsights.regularity} />)
    expect(screen.getByText('62')).toBeInTheDocument()
    expect(screen.getByText('±46 min')).toBeInTheDocument()
  })
})

describe('Recomendado frente a real', () => {
  it('dice qué falta cuando no hay horas reales', () => {
    const sinReales = mockInsights.adherence.series.map((n) => ({ ...n, actual: null }))
    render(<AdherenceCard streak={0} rate={null} series={sinReales} />)
    expect(screen.getByText(/Faltan horas reales de acostarse/i)).toBeInTheDocument()
  })

  it('pinta la comparación y la racha cuando hay datos', () => {
    render(
      <AdherenceCard
        streak={mockInsights.adherence.streak}
        rate={mockInsights.adherence.rate}
        series={mockInsights.adherence.series}
      />,
    )
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('64%')).toBeInTheDocument()
    expect(
      screen.getByRole('img', { name: /hora recomendada y la hora real/i }),
    ).toBeInTheDocument()
  })
})

describe('Heatmap', () => {
  it('dibuja una casilla por noche de las ocho semanas', () => {
    const { container } = render(<SleepHeatmap nights={mockInsights.heatmap} />)
    const conDatos = container.querySelectorAll('[title*="eficiencia"]')
    expect(conDatos.length).toBe(mockInsights.heatmap.length)
    expect(container.querySelectorAll('[title*="sin datos"]').length).toBeGreaterThan(0)
  })
})

describe('Qué acompaña a tus mejores noches', () => {
  it('sin datos suficientes explica qué falta en vez de callarse', () => {
    render(<AssociationsCard associations={[]} />)
    expect(screen.getByText(/al menos tres noches con cada hábito/i)).toBeInTheDocument()
  })

  it('marca lo que resta y lo que suma, y avisa de que no es causa', () => {
    render(<AssociationsCard associations={mockInsights.associations} />)

    expect(screen.getByText('Con alcohol')).toBeInTheDocument()
    expect(screen.getByText('−1 h 13')).toBeInTheDocument()
    expect(screen.getByText('+31 min')).toBeInTheDocument()
    // El aviso no es letra pequeña por cumplir: frena la lectura causal.
    expect(screen.getByText(/asociaciones, no causas/i)).toBeInTheDocument()
  })
})
