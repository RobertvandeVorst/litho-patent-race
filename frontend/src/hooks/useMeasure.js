import { useCallback, useLayoutEffect, useRef, useState } from 'react'

// Measures a container's width so charts can be responsive (near-square < 520px).
export function useMeasure() {
  const ref = useRef(null)
  const [width, setWidth] = useState(0)

  const observe = useCallback(() => {
    if (ref.current) setWidth(ref.current.clientWidth)
  }, [])

  useLayoutEffect(() => {
    observe()
    if (!ref.current || typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', observe)
      return () => window.removeEventListener('resize', observe)
    }
    const ro = new ResizeObserver(observe)
    ro.observe(ref.current)
    return () => ro.disconnect()
  }, [observe])

  return [ref, width]
}
