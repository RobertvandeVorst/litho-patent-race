import { useEffect, useState } from 'react'
import { scrollToId } from '../lib/scroll.js'

// Single navigation surface: a fixed left rail on desktop (markers + labels +
// reading-progress line + Next/Top control), collapsing to markers-only on
// mid widths and a sticky top bar on mobile — all driven by one scroll-spy.
export default function SideRail({ items }) {
  const [active, setActive] = useState(items[0].id)

  useEffect(() => {
    const last = items[items.length - 1].id
    // the short footer can't reach the observer's mid-band, so treat page-bottom
    // as the last section explicitly (and let it win over the observer there).
    const atBottom = () =>
      window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4
    const obs = new IntersectionObserver(
      (entries) => {
        if (atBottom()) return setActive(last)
        entries.forEach((e) => {
          if (e.isIntersecting) setActive(e.target.id)
        })
      },
      { rootMargin: '-45% 0px -50% 0px', threshold: 0 },
    )
    items.forEach((it) => {
      const el = document.getElementById(it.id)
      if (el) obs.observe(el)
    })
    const onScroll = () => {
      if (atBottom()) setActive(last)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      obs.disconnect()
      window.removeEventListener('scroll', onScroll)
    }
  }, [items])

  const activeIndex = Math.max(0, items.findIndex((it) => it.id === active))
  const isLast = activeIndex === items.length - 1

  const go = (id) => scrollToId(id)
  const onNext = () => {
    if (isLast) {
      const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
      window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' })
      setActive(items[0].id)
    } else {
      go(items[activeIndex + 1].id)
    }
  }

  const railLabel = (it) => (it.n ? `${it.n} · ${it.short || it.name}` : it.short || it.name)
  const barLabel = (it) => (it.n ? `${it.n} · ${it.name}` : it.name)

  return (
    <>
      {/* desktop / mid: fixed left rail */}
      <nav className="rail" aria-label="Sections" style={{ '--rail-item': '46px' }}>
        <div className="rail__body">
          <span className="rail__line" aria-hidden="true" />
          <span
            className="rail__progress"
            aria-hidden="true"
            style={{ height: `calc(${activeIndex} * var(--rail-item))` }}
          />
          <ol className="rail__list">
            {items.map((it, i) => (
              <li className="rail__li" key={it.id}>
                <button
                  type="button"
                  className={`rail__item${i === activeIndex ? ' is-active' : ''}`}
                  aria-current={i === activeIndex ? 'true' : undefined}
                  aria-label={barLabel(it)}
                  title={barLabel(it)}
                  onClick={() => go(it.id)}
                >
                  <span className="rail__marker" aria-hidden="true" title={barLabel(it)} />
                  <span className="rail__label">{railLabel(it)}</span>
                </button>
              </li>
            ))}
          </ol>
        </div>
        <button
          type="button"
          className="rail__next"
          onClick={onNext}
          aria-label={isLast ? 'Back to top' : 'Next section'}
        >
          <span className="rail__next-label">{isLast ? 'Top' : 'Next'}</span>
          <span className="rail__next-arrow" aria-hidden="true">
            {isLast ? '↑' : '↓'}
          </span>
        </button>
      </nav>

      {/* mobile: compact sticky top bar */}
      <nav className="topbar" aria-label="Sections">
        <ul className="topbar__list">
          {items.map((it, i) => (
            <li key={it.id}>
              <button
                type="button"
                className={`topbar__link${i === activeIndex ? ' is-active' : ''}`}
                aria-current={i === activeIndex ? 'true' : undefined}
                aria-label={barLabel(it)}
                title={barLabel(it)}
                onClick={() => go(it.id)}
              >
                {barLabel(it)}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </>
  )
}
