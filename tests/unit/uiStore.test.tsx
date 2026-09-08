import { describe, expect, it, beforeEach } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useUiStore } from '@/stores/uiStore'

describe('useUiStore theme', () => {
  beforeEach(() => {
    useUiStore.setState({ theme: 'light' })
    document.documentElement.classList.remove('dark')
    document.documentElement.classList.add('light')
  })

  it('toggles between light and dark on documentElement', () => {
    const { result } = renderHook(() => useUiStore())

    act(() => {
      result.current.toggleTheme()
    })

    expect(result.current.theme).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)

    act(() => {
      result.current.toggleTheme()
    })

    expect(result.current.theme).toBe('light')
    expect(document.documentElement.classList.contains('light')).toBe(true)
  })
})
