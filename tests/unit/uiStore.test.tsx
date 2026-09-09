import { describe, expect, it, beforeEach } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { isNightHour, useUiStore } from '@/stores/uiStore'

function claseDelTema(): string[] {
  return ['light', 'dark', 'noche'].filter((c) =>
    document.documentElement.classList.contains(c),
  )
}

describe('useUiStore theme', () => {
  beforeEach(() => {
    useUiStore.setState({ theme: 'light', autoNoche: false })
    document.documentElement.classList.remove('dark', 'noche')
    document.documentElement.classList.add('light')
  })

  it('cicla claro → oscuro → noche y vuelve', () => {
    const { result } = renderHook(() => useUiStore())

    for (const esperado of ['dark', 'noche', 'light'] as const) {
      act(() => {
        result.current.toggleTheme()
      })
      expect(result.current.theme).toBe(esperado)
      // Exactamente una clase puesta: dos a la vez dejaban la mitad de los tokens
      // resolviéndose contra el tema equivocado.
      expect(claseDelTema()).toEqual([esperado])
    }
  })

  it('el modo noche cuenta como oscuro para el navegador', () => {
    const { result } = renderHook(() => useUiStore())
    act(() => {
      result.current.setTheme('noche')
    })
    // Si `colorScheme` se quedara en claro, los controles nativos y la barra de
    // scroll se pintarían blancos: justo el fogonazo que el tema evita.
    expect(document.documentElement.style.colorScheme).toBe('dark')
  })

  it('con el automático puesto, la franja nocturna enciende el modo noche', () => {
    const { result } = renderHook(() => useUiStore())
    act(() => {
      result.current.setAutoNoche(true)
      result.current.syncNightTheme(new Date(2026, 8, 9, 23, 30))
    })
    expect(result.current.theme).toBe('noche')

    act(() => {
      result.current.syncNightTheme(new Date(2026, 8, 10, 9, 0))
    })
    expect(result.current.theme).toBe('dark')
  })

  it('elegir tema a mano apaga el automático', () => {
    const { result } = renderHook(() => useUiStore())
    act(() => {
      result.current.setAutoNoche(true)
    })
    act(() => {
      result.current.setTheme('light')
    })
    expect(result.current.autoNoche).toBe(false)

    // Y ya no se lo cambia por debajo: sin esto, el botón parecía no funcionar.
    act(() => {
      result.current.syncNightTheme(new Date(2026, 8, 9, 23, 30))
    })
    expect(result.current.theme).toBe('light')
  })

  it('la franja cruza la medianoche', () => {
    expect(isNightHour(new Date(2026, 8, 9, 22, 0))).toBe(true)
    expect(isNightHour(new Date(2026, 8, 10, 3, 0))).toBe(true)
    expect(isNightHour(new Date(2026, 8, 10, 5, 59))).toBe(true)
    expect(isNightHour(new Date(2026, 8, 10, 6, 0))).toBe(false)
    expect(isNightHour(new Date(2026, 8, 9, 21, 59))).toBe(false)
  })
})
