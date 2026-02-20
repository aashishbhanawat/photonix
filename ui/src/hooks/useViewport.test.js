import React from 'react'
import { renderHook, act } from '@testing-library/react'
import useViewport from './useViewport'

describe('useViewport', () => {
  let originalInnerWidth
  let originalInnerHeight

  beforeAll(() => {
    originalInnerWidth = window.innerWidth
    originalInnerHeight = window.innerHeight

    // Mock window.innerWidth and window.innerHeight
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    })
    Object.defineProperty(window, 'innerHeight', {
      writable: true,
      configurable: true,
      value: 768,
    })
  })

  afterAll(() => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: originalInnerWidth,
    })
    Object.defineProperty(window, 'innerHeight', {
      writable: true,
      configurable: true,
      value: originalInnerHeight,
    })
  })

  test('should return initial window dimensions', () => {
    const { result } = renderHook(() => useViewport())

    expect(result.current.width).toBe(1024)
    expect(result.current.height).toBe(768)
  })

  test('should update dimensions on window resize', () => {
    const { result } = renderHook(() => useViewport())

    act(() => {
      window.innerWidth = 800
      window.innerHeight = 600
      window.dispatchEvent(new Event('resize'))
    })

    expect(result.current.width).toBe(800)
    expect(result.current.height).toBe(600)
  })

  test('should remove event listener on unmount', () => {
    const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener')
    const { unmount } = renderHook(() => useViewport())

    unmount()

    expect(removeEventListenerSpy).toHaveBeenCalledWith(
      'resize',
      expect.any(Function)
    )
    removeEventListenerSpy.mockRestore()
  })
})
