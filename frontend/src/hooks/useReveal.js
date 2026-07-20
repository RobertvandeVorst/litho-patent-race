import { useEffect, useLayoutEffect, useState } from 'react'

const prefersReduced = () =>
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

// Returns true once the referenced element has been ~visible (stays true).
// Falls back to true when observation isn't possible, so content is never gated.
export function useInViewOnce(ref, { threshold = 0.2 } = {}) {
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref && ref.current
    if (!el || typeof IntersectionObserver === 'undefined') {
      setInView(true)
      return
    }
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setInView(true)
          obs.disconnect()
        }
      },
      { threshold },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [ref, threshold])
  return inView
}

// Global scroll-reveal: elements marked [data-reveal] fade up as they enter view,
// once each. Progressive enhancement — without JS nothing is hidden; under reduced
// motion the enhancement is skipped entirely (everything renders immediately).
// Uses useLayoutEffect so the hidden state is set before paint (no flash).
export function useScrollReveal(ready = true) {
  useLayoutEffect(() => {
    if (!ready) return
    if (prefersReduced() || typeof IntersectionObserver === 'undefined') return
    const root = document.documentElement
    root.classList.add('js-reveal')
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('is-visible')
            obs.unobserve(e.target)
          }
        })
      },
      { threshold: 0.15 },
    )
    const els = document.querySelectorAll('[data-reveal]')
    els.forEach((el) => obs.observe(el))
    return () => {
      obs.disconnect()
      root.classList.remove('js-reveal')
    }
  }, [ready])
}
