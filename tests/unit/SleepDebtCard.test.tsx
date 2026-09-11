import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SleepDebtCard } from '@/components/night/SleepDebtCard'
import type { SleepDebt } from '@/api/morfeo'

function deuda(parcial: Partial<SleepDebt> = {}): SleepDebt {
  return {
    minutes: 840,
    level: 'moderada',
    nights_counted: 14,
    nights_with_deficit: 9,
    worst_night_deficit_minutes: 160,
    tonight_recovery_minutes: 60,
    nights_to_clear: 8,
    previous_minutes: 915,
    delta_minutes: -75,
    ...parcial,
  }
}

describe('Tarjeta de deuda de sueño', () => {
  it('enseña la deuda en horas y el nivel en palabras', () => {
    render(<SleepDebtCard debt={deuda()} />)
    expect(screen.getByText('14 h')).toBeInTheDocument()
    expect(screen.getByText('moderada')).toBeInTheDocument()
  })

  it('el plazo va con la cifra, nunca escondido', () => {
    // La regla que ordena la tarjeta: una deuda creciendo, sola y de noche, es
    // ansiedad. El plazo es lo que la convierte en algo que se pasa.
    render(<SleepDebtCard debt={deuda()} />)
    expect(screen.getByText(/Se salda en unas/i)).toBeInTheDocument()
    expect(screen.getByText('8 noches')).toBeInTheDocument()
    expect(screen.getByText(/No hace falta recuperarla de golpe/i)).toBeInTheDocument()
  })

  it('dice cuánto recupera la recomendación de esta noche', () => {
    render(<SleepDebtCard debt={deuda()} />)
    expect(screen.getByText('+60 min')).toBeInTheDocument()
  })

  it('sin noches medidas no dice que no haya deuda', () => {
    // `minutes: 0` con `nights_counted: 0` es lo que devuelve una cuenta recién
    // creada. Leerlo como "vas al día" sería felicitar por un dato que nadie ha medido.
    render(<SleepDebtCard debt={deuda({ minutes: 0, level: 'ninguna', nights_counted: 0, nights_with_deficit: 0, tonight_recovery_minutes: 0, nights_to_clear: 0 })} />)
    expect(screen.getByText(/Aparecerá en cuanto haya noches con horas reales/i)).toBeInTheDocument()
    expect(screen.queryByText(/Al día/i)).not.toBeInTheDocument()
  })

  it('con noches medidas y sin déficit sí dice que vas al día', () => {
    render(
      <SleepDebtCard
        debt={deuda({ minutes: 0, level: 'ninguna', nights_with_deficit: 0, nights_to_clear: 0 })}
      />,
    )
    expect(screen.getByText(/Al día/i)).toBeInTheDocument()
    // Sin deuda no hay plazo que dar: la frase sobraría.
    expect(screen.queryByText(/Se salda en unas/i)).not.toBeInTheDocument()
  })

  it('la tendencia se calla mientras no haya con qué comparar', () => {
    // Sin esta guarda, las tres primeras semanas de uso dirían "subiendo" siempre,
    // contra un cero que nadie midió.
    render(<SleepDebtCard debt={deuda({ previous_minutes: null, delta_minutes: null })} />)
    expect(screen.queryByText(/que hace una semana/i)).not.toBeInTheDocument()
  })

  it('distingue bajar de subir', () => {
    const { unmount } = render(<SleepDebtCard debt={deuda({ delta_minutes: -75 })} />)
    expect(screen.getByText(/menos que hace una semana/i)).toBeInTheDocument()
    unmount()

    render(<SleepDebtCard debt={deuda({ delta_minutes: 75 })} />)
    expect(screen.getByText(/más que hace una semana/i)).toBeInTheDocument()
  })

  it('en el histórico no se pinta nada', () => {
    // `/api/bedtime/history` devuelve `sleep_debt: null`: la deuda no se congeló con
    // la recomendación y recalcularla hoy daría un número que nunca se enseñó.
    const { container } = render(<SleepDebtCard debt={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})
