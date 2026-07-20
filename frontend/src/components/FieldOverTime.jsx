import { useMemo, useState } from 'react'
import { scaleLinear } from 'd3-scale'
import { line as d3line } from 'd3-shape'
import { max } from 'd3-array'
import Figure from './Figure.jsx'
import Tooltip, { TipRow } from './Tooltip.jsx'
import { useMeasure } from '../hooks/useMeasure.js'
import { useInViewOnce } from '../hooks/useReveal.js'
import { useReducedMotion } from '../hooks/useReducedMotion.js'
import { C } from '../lib/palette.js'
import { pct, year, int } from '../lib/format.js'

export default function FieldOverTime({ euv }) {
  const [ref, width] = useMeasure()
  const reduced = useReducedMotion()
  const inView = useInViewOnce(ref, { threshold: 0.25 })
  const drawn = reduced || inView // draw-in triggers when the chart scrolls into view
  const [hover, setHover] = useState(null) // filing_year
  const [tip, setTip] = useState(null)

  const all = euv.overall_all
  const win = euv.window
  // /0.8: enlarge the viewBox so the SVG (CSS width:100%) renders its internals
  // at 80%, matching the rem scaling. The clientX→data map below divides by
  // rect.width (the rendered width), so it stays correct.
  const w = (width || 680) / 0.8
  const compact = w < 520
  const h = compact ? Math.round(w * 0.9) : 400
  const m = { top: 24, right: 20, bottom: 40, left: 46 }

  const model = useMemo(() => {
    const years = all.map((d) => d.filing_year)
    const x = scaleLinear().domain([Math.min(...years), Math.max(...years)]).range([m.left, w - m.right])
    const yMax = max(all, (d) => d.euv_share_pct) || 1
    const y = scaleLinear().domain([0, yMax * 1.08]).range([h - m.bottom, m.top]).nice()
    const mk = d3line().x((d) => x(d.filing_year)).y((d) => y(d.euv_share_pct))
    const complete = all.filter((d) => d.is_complete)
    // dedupe + space y ticks so the top pair never collides
    const ticks = []
    y.ticks(compact ? 5 : 7).forEach((t) => {
      if (!ticks.length || Math.abs(y(t) - y(ticks[ticks.length - 1])) >= 24) ticks.push(t)
    })
    const xTicks = years.filter((yr) => yr % 3 === 0 || yr === win.start || yr === win.end)
    const byYear = new Map(all.map((d) => [d.filing_year, d]))
    const peak = complete.reduce((a, b) => (b.euv_share_pct > a.euv_share_pct ? b : a))
    return { x, y, greyAll: mk(all), solid: mk(complete), complete, ticks, xTicks, years, byYear, peak }
  }, [all, w, h, m.left, m.right, m.top, m.bottom, win.start, win.end, compact])

  const { x, y } = model
  const plotTop = m.top
  const plotBot = h - m.bottom
  // band boundaries sit on the midpoint between the last censored and first complete year
  const leftBandX2 = x(win.start - 0.5)
  const rightBandX1 = x(win.end + 0.5)
  const solidLen = 1400

  const build = (d) => ({
    content: (
      <>
        <div className="tip__title">
          {year(d.filing_year)}
          {!d.is_complete && <span className="tip__flag"> · censored</span>}
        </div>
        <TipRow k="EUV share" v={pct(d.euv_share_pct)} accent={C.euv} />
        <TipRow k="EUV filings" v={int(d.euv_any)} />
        <TipRow k="Total filings" v={int(d.total)} />
      </>
    ),
  })

  const onMove = (e) => {
    const svg = e.currentTarget.ownerSVGElement || e.currentTarget
    const rect = svg.getBoundingClientRect()
    const px = (e.clientX - rect.left) * (w / rect.width)
    const yr = Math.max(model.years[0], Math.min(model.years[model.years.length - 1], Math.round(x.invert(px))))
    const d = model.byYear.get(yr)
    if (d) {
      setHover(yr)
      setTip({ x: e.clientX, y: e.clientY, ...build(d) })
    }
  }
  const clear = () => {
    setHover(null)
    setTip(null)
  }
  const focusYear = (d, el) => {
    const r = el.getBoundingClientRect()
    setHover(d.filing_year)
    setTip({ x: r.left + r.width / 2, y: r.top, ...build(d) })
  }

  const hoverD = hover != null ? model.byYear.get(hover) : null
  const desc = model.complete.map((d) => `${d.filing_year}: ${pct(d.euv_share_pct)}`).join(', ')

  return (
    <div ref={ref}>
      <Figure
        fig="2"
        caption="EUV share of filings by filing year — complete years solid, censored years grey"
      >
        <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-labelledby="fot-t fot-d">
          <title id="fot-t">EUV share of lithography filings by filing year</title>
          <desc id="fot-d">
            Complete window {year(win.start)}–{year(win.end)}. Values: {desc}. Years outside the window
            are censored and shown in grey.
          </desc>

          {/* censored bands */}
          <rect x={m.left} y={plotTop} width={leftBandX2 - m.left} height={plotBot - plotTop} fill={C.ink} opacity="0.05" />
          <rect x={rightBandX1} y={plotTop} width={w - m.right - rightBandX1} height={plotBot - plotTop} fill={C.ink} opacity="0.05" />
          {/* LEFT label: vertical, centred inside the band, clear of the y-axis */}
          <text
            x={(m.left + leftBandX2) / 2}
            y={(plotTop + plotBot) / 2}
            textAnchor="middle"
            fontSize="9.5"
            fill={C.muted}
            letterSpacing="0.1em"
            transform={`rotate(-90 ${(m.left + leftBandX2) / 2} ${(plotTop + plotBot) / 2})`}
          >
            LEFT-CENSORED
          </text>
          <text x={(rightBandX1 + w - m.right) / 2} y={plotTop - 10} textAnchor="middle" fontSize="10" fill={C.muted} letterSpacing="0.08em">
            RIGHT-CENSORED
          </text>

          {/* y grid + ticks */}
          {model.ticks.map((t) => (
            <g key={t}>
              <line x1={m.left} x2={w - m.right} y1={y(t)} y2={y(t)} stroke={C.hairline} strokeWidth="1" />
              <text x={m.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize="11" fill={C.muted}>
                {t}%
              </text>
            </g>
          ))}

          {/* x ticks */}
          {model.xTicks.map((yr) => (
            <text key={yr} x={x(yr)} y={plotBot + 18} textAnchor="middle" fontSize="10.5" fill={C.muted}>
              {yr}
            </text>
          ))}

          {/* crosshair */}
          {hoverD && (
            <line x1={x(hoverD.filing_year)} x2={x(hoverD.filing_year)} y1={plotTop} y2={plotBot} stroke={C.ink} strokeWidth="1" strokeDasharray="2 2" opacity="0.5" />
          )}

          {/* grey full line (censored context) */}
          <path d={model.greyAll} fill="none" stroke={C.muted} strokeWidth="1.5" strokeDasharray="3 3" opacity="0.55" />

          {/* solid EUV line over complete years, with draw-in */}
          <path
            d={model.solid}
            fill="none"
            stroke={C.euv}
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{
              strokeDasharray: solidLen,
              strokeDashoffset: drawn ? 0 : solidLen,
              transition: reduced ? 'none' : 'stroke-dashoffset 1100ms ease-out',
            }}
          />

          {/* points */}
          {all.map((d) =>
            d.is_complete ? (
              <circle key={d.filing_year} cx={x(d.filing_year)} cy={y(d.euv_share_pct)} r={hover === d.filing_year ? 5 : 3} fill={C.euv} />
            ) : (
              <circle key={d.filing_year} cx={x(d.filing_year)} cy={y(d.euv_share_pct)} r="2.6" fill="none" stroke={C.muted} strokeWidth="1.2" />
            ),
          )}

          <text x={x(model.peak.filing_year)} y={y(model.peak.euv_share_pct) - 9} textAnchor="middle" fontSize="11" fontWeight="700" fill={C.euv}>
            {pct(model.peak.euv_share_pct)}
          </text>

          {/* focusable points (keyboard) — announce the same content */}
          {all.map((d) => (
            <circle
              key={`f-${d.filing_year}`}
              cx={x(d.filing_year)}
              cy={y(d.euv_share_pct)}
              r="12"
              fill="transparent"
              tabIndex={0}
              role="img"
              aria-label={`${d.filing_year}${d.is_complete ? '' : ', censored'}: EUV share ${pct(d.euv_share_pct)}, ${int(d.euv_any)} EUV of ${int(d.total)} filings`}
              onFocus={(e) => focusYear(d, e.currentTarget)}
              onBlur={clear}
              style={{ outline: 'none', pointerEvents: 'none' }}
            />
          ))}

          {/* mouse overlay for the crosshair (pointerEvents:all so the transparent fill still captures) */}
          <rect
            className="fot-overlay"
            x={m.left}
            y={plotTop}
            width={w - m.right - m.left}
            height={plotBot - plotTop}
            fill="transparent"
            onMouseMove={onMove}
            onMouseLeave={clear}
            style={{ cursor: 'crosshair', pointerEvents: 'all' }}
          />
        </svg>
      </Figure>
      <Tooltip tip={tip} />
      <div className="legend" aria-hidden="true">
        <span>
          <i style={{ background: C.euv }} />
          EUV share (complete years)
        </span>
        <span>
          <i className="dot" style={{ background: 'transparent', border: `1.2px solid ${C.muted}` }} />
          Censored — excluded
        </span>
      </div>
    </div>
  )
}
