import { useMemo, useState } from 'react'
import { scaleLinear } from 'd3-scale'
import { max } from 'd3-array'
import Figure from './Figure.jsx'
import Tooltip, { TipRow } from './Tooltip.jsx'
import { useMeasure } from '../hooks/useMeasure.js'
import { useInViewOnce } from '../hooks/useReveal.js'
import { useReducedMotion } from '../hooks/useReducedMotion.js'
import { VERDICT_COLOR, shortLabel } from '../lib/palette.js'
import { C } from '../lib/palette.js'
import { pct } from '../lib/format.js'

// Push overlapping label y-positions apart while preserving order.
function decollide(items, minGap, minY, maxY) {
  const out = items.map((d) => ({ ...d }))
  out.sort((a, b) => a.y - b.y)
  for (let i = 1; i < out.length; i++) {
    if (out[i].y - out[i - 1].y < minGap) out[i].y = out[i - 1].y + minGap
  }
  if (out.length) {
    const last = out[out.length - 1]
    if (last.y > maxY) {
      last.y = maxY
      for (let i = out.length - 2; i >= 0; i--) {
        if (out[i + 1].y - out[i].y < minGap) out[i].y = out[i + 1].y - minGap
      }
    }
    if (out[0].y < minY) out[0].y = minY
  }
  return out
}

export default function HeroSlope({ pivot }) {
  const [ref, width] = useMeasure()
  const reduced = useReducedMotion()
  const inView = useInViewOnce(ref, { threshold: 0.25 })
  const drawn = reduced || inView // draw-in triggers when the chart scrolls into view
  const [hover, setHover] = useState(null) // player
  const [tip, setTip] = useState(null)
  const [selected, setSelected] = useState('All') // player filter

  const players = pivot.players
  const early = players[0].early_years
  const late = players[0].late_years
  // /0.8: enlarge the viewBox so the SVG (CSS width:100%) renders its internals
  // — fonts, margins, height-via-aspect-ratio — at 80%, matching the rem scaling.
  const w = (width || 640) / 0.8
  const compact = w < 520
  const h = compact ? Math.round(w * 0.95) : 440
  const m = { top: 26, right: compact ? 96 : 132, bottom: 40, left: 44 }

  const model = useMemo(() => {
    const yMax = max(players, (d) => Math.max(d.early_share_pct, d.late_share_pct)) || 1
    const y = scaleLinear().domain([0, yMax * 1.06]).range([h - m.bottom, m.top]).nice()
    const xL = m.left
    const xR = w - m.right
    const lines = players.map((d) => ({
      player: d.player,
      short: shortLabel(d.player),
      verdict: d.verdict,
      color: VERDICT_COLOR[d.verdict] || C.muted,
      early: d.early_share_pct,
      late: d.late_share_pct,
      x1: xL,
      y1: y(d.early_share_pct),
      x2: xR,
      y2: y(d.late_share_pct),
    }))
    const labels = decollide(
      lines.map((l) => ({ key: l.player, y: l.y2, target: l.y2, ref: l })),
      15,
      m.top,
      h - m.bottom,
    )
    const ticks = y.ticks(compact ? 4 : 5)
    return { y, xL, xR, lines, labels, ticks, yMax }
  }, [players, w, h, m.left, m.right, m.top, m.bottom, compact])

  const build = (l) => {
    const change = l.late - l.early
    return {
      content: (
        <>
          <div className="tip__title" style={{ color: l.color }}>
            {l.player}
          </div>
          <TipRow k={early} v={pct(l.early)} />
          <TipRow k={late} v={pct(l.late)} />
          <TipRow k="Change" v={`${change >= 0 ? '+' : ''}${change.toFixed(1)} pp`} accent={l.color} />
          <TipRow k="Verdict" v={l.verdict} />
        </>
      ),
    }
  }
  const enter = (l, e) => {
    setHover(l.player)
    setTip({ x: e.clientX, y: e.clientY, ...build(l) })
  }
  const focus = (l, el) => {
    const r = el.getBoundingClientRect()
    setHover(l.player)
    setTip({ x: r.left + r.width / 2, y: r.top + r.height / 2, ...build(l) })
  }
  const clear = () => {
    setHover(null)
    setTip(null)
  }

  const desc = players
    .map((d) => `${d.player} ${pct(d.early_share_pct)} to ${pct(d.late_share_pct)}, ${d.verdict}`)
    .join('; ')

  return (
    <div ref={ref}>
      <div className="chips" role="group" aria-label="Filter to one player">
        <button
          type="button"
          className={`chip-btn${selected === 'All' ? ' is-active' : ''}`}
          aria-pressed={selected === 'All'}
          onClick={() => setSelected('All')}
        >
          All
        </button>
        {players.map((p) => (
          <button
            type="button"
            key={p.player}
            className={`chip-btn${selected === p.player ? ' is-active' : ''}`}
            aria-pressed={selected === p.player}
            onClick={() => setSelected(p.player)}
          >
            {p.player}
          </button>
        ))}
      </div>
      <Figure fig="1" caption="EUV share of filings — early vs recent, per player">
        <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-labelledby="slope-t slope-d">
          <title id="slope-t">Slope chart: change in EUV share of filings per player</title>
          <desc id="slope-d">{desc}</desc>

          {model.ticks.map((t) => (
            <g key={t}>
              <line x1={model.xL} x2={model.xR} y1={model.y(t)} y2={model.y(t)} stroke={C.hairline} strokeWidth="1" />
              <text x={model.xL - 8} y={model.y(t)} dy="0.32em" textAnchor="end" fontSize="11" fill={C.muted}>
                {t}%
              </text>
            </g>
          ))}

          {[
            { x: model.xL, label: early, anchor: 'start' },
            { x: model.xR, label: late, anchor: 'end' },
          ].map((col) => (
            <g key={col.label}>
              <line x1={col.x} x2={col.x} y1={m.top} y2={h - m.bottom} stroke={C.ink} strokeWidth="1.5" />
              <text x={col.x} y={h - m.bottom + 20} textAnchor={col.anchor} fontSize="11" fill={C.umber} letterSpacing="0.06em">
                {col.label}
              </text>
            </g>
          ))}

          {/* slope lines + invisible hit areas */}
          {model.lines.map((l) => {
            const len = Math.hypot(l.x2 - l.x1, l.y2 - l.y1)
            const faded = selected !== 'All' && selected !== l.player // filtered out — kept as faint context
            const dim = !faded && hover && hover !== l.player
            const op = faded ? 0.13 : dim ? 0.22 : 1
            const sw = faded ? 1 : hover === l.player ? 3.4 : l.verdict === 'pivoted' ? 2.4 : 2
            return (
              <g key={l.player} opacity={op} style={{ transition: reduced ? 'none' : 'opacity 250ms ease' }}>
                <line
                  x1={l.x1}
                  y1={l.y1}
                  x2={l.x2}
                  y2={l.y2}
                  stroke={l.color}
                  strokeWidth={sw}
                  strokeLinecap="round"
                  style={{
                    strokeDasharray: len,
                    strokeDashoffset: drawn ? 0 : len,
                    transition: reduced
                      ? 'none'
                      : 'stroke-dashoffset 900ms ease-out, stroke-width 250ms ease',
                  }}
                />
                <circle cx={l.x1} cy={l.y1} r="3" fill={l.color} />
                <circle cx={l.x2} cy={l.y2} r="3.5" fill={l.color} />
                {/* hit area (mouse + keyboard) */}
                <line
                  x1={l.x1}
                  y1={l.y1}
                  x2={l.x2}
                  y2={l.y2}
                  stroke="transparent"
                  strokeWidth="16"
                  tabIndex={0}
                  role="img"
                  aria-label={`${l.player}: EUV share ${pct(l.early)} in ${early}, ${pct(l.late)} in ${late}, change ${(l.late - l.early).toFixed(1)} points, ${l.verdict}`}
                  onMouseEnter={(e) => enter(l, e)}
                  onMouseMove={(e) => enter(l, e)}
                  onMouseLeave={clear}
                  onFocus={(e) => focus(l, e.currentTarget)}
                  onBlur={clear}
                  style={{ outline: 'none', cursor: 'pointer' }}
                />
              </g>
            )
          })}

          {/* de-collided right labels with leader lines */}
          {model.labels.map((lab) => {
            const l = lab.ref
            const lx = model.xR + 10
            const faded = selected !== 'All' && selected !== l.player
            const dim = !faded && hover && hover !== l.player
            const labOp = !drawn ? 0 : faded ? 0 : dim ? 0.3 : 1
            return (
              <g key={lab.key} opacity={labOp} style={{ transition: reduced ? 'none' : 'opacity 250ms ease' }}>
                {Math.abs(lab.y - l.y2) > 1 && (
                  <line x1={model.xR + 4} y1={l.y2} x2={lx} y2={lab.y} stroke={l.color} strokeWidth="1" opacity="0.6" />
                )}
                <text x={lx} y={lab.y} dy="0.32em" fontSize={compact ? 11 : 12} fill={C.ink}>
                  <tspan fontWeight="700" fill={l.color}>
                    {l.short}
                  </tspan>
                  <tspan dx="6" fill={C.ink}>
                    {pct(l.late)}
                  </tspan>
                </text>
              </g>
            )
          })}
        </svg>
      </Figure>
      <Tooltip tip={tip} />
      <div className="legend" aria-hidden="true">
        <span>
          <i style={{ background: VERDICT_COLOR.pivoted }} />
          Pivoted to EUV
        </span>
        <span>
          <i style={{ background: VERDICT_COLOR.flat }} />
          Held flat
        </span>
        <span>
          <i style={{ background: VERDICT_COLOR['moved away'] }} />
          Moved away
        </span>
      </div>
    </div>
  )
}
