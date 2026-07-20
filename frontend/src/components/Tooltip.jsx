// Shared hover/focus tooltip. Positioned with position:fixed at client coords so
// it works over SVG and scrolled tables alike. Design language: ground fill, ink
// border, Space Mono, square corners (styled in .tip).
export default function Tooltip({ tip }) {
  if (!tip) return null
  const pad = 16
  const vw = typeof window !== 'undefined' ? window.innerWidth : 1200
  const vh = typeof window !== 'undefined' ? window.innerHeight : 800
  const flipX = tip.x > vw - 230
  const flipY = tip.y > vh - 150
  const style = {
    left: tip.x,
    top: tip.y,
    transform: `translate(${flipX ? `calc(-100% - ${pad}px)` : `${pad}px`}, ${
      flipY ? `calc(-100% - ${pad}px)` : `${pad}px`
    })`,
  }
  return (
    <div className="tip mono" role="status" aria-live="polite" style={style}>
      {tip.content}
    </div>
  )
}

// helper: a titled row inside a tooltip
export function TipRow({ k, v, accent }) {
  return (
    <div className="tip__row">
      <span className="tip__k">{k}</span>
      <span className="tip__v" style={accent ? { color: accent } : undefined}>
        {v}
      </span>
    </div>
  )
}
