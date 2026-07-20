// Numbered section: eyebrow reads "2 / MEASUREMENT" in mono uppercase.
// Optional: `look` (what-to-look-for note) and `method` (collapsible + method note).
// Navigation lives entirely in the left rail (SideRail), not per-section.
export default function Section({ n, name, title, lede, look, method, children, id }) {
  return (
    <section className="section" id={id} aria-labelledby={`${id}-h`}>
      <p className="section__eyebrow" data-reveal style={{ '--d': 0 }}>
        {n} / {name}
      </p>
      <h2 className="section__head" id={`${id}-h`} data-reveal style={{ '--d': 1 }}>
        {title}
      </h2>
      {lede && (
        <p className="section__lede" data-reveal style={{ '--d': 2 }}>
          {lede}
        </p>
      )}

      {look && (
        <p className="look" data-reveal style={{ '--d': 3 }}>
          <span className="look__tag">
            <svg
              className="look__icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M1.7 12C4.8 6 19.2 6 22.3 12 19.2 18 4.8 18 1.7 12Z" />
              <circle cx="12" cy="12" r="3.1" />
            </svg>
            What to look for
          </span>
          {look}
        </p>
      )}

      {method && (
        <details className="method" data-reveal style={{ '--d': 4 }}>
          <summary className="method__toggle">+ method</summary>
          <div className="method__body">{method}</div>
        </details>
      )}

      <div data-reveal style={{ '--d': 5 }}>{children}</div>
    </section>
  )
}
