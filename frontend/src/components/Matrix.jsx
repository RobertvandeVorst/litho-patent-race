import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import Figure from './Figure.jsx'
import Tooltip, { TipRow } from './Tooltip.jsx'
import { useMeasure } from '../hooks/useMeasure.js'
import { categoryColor } from '../lib/palette.js'
import { C } from '../lib/palette.js'
import { int, pct } from '../lib/format.js'

const SUBTECH_SHORT = {
  'Exposure: stage, handling & apparatus': 'Exp: stage/apparatus',
  'Masks / reticles': 'Masks / reticles',
  'Photoresist compositions': 'Resist compositions',
  'Exposure: projection & immersion': 'Exp: projection/immersion',
  'Exposure: alignment & overlay': 'Exp: alignment/overlay',
  'Exposure: illumination & source': 'Exp: illumination/source',
  'Exposure: method & dose control': 'Exp: method/dose',
  'Resist chemistry & formulation': 'Resist chemistry',
  'Development & resist removal': 'Development/removal',
  'Alignment / registration': 'Alignment/registration',
  'Resist layers & multilayers': 'Resist layers',
  'Illumination / exposure': 'Illumination/exposure',
  'Resist coating': 'Resist coating',
  'EUV masks': 'EUV masks',
  'Other G03F': 'Other G03F',
}
const colLabel = (s) => SUBTECH_SHORT[s] || s

const GC = [0xf1, 0xce, 0x85]
const EC = [0x21, 0x1a, 0x5e]
const ramp = (t) => `rgb(${GC.map((g, i) => Math.round(g + (EC[i] - g) * t)).join(',')})`

const LABELW = 158
const TOTALW = 56
const MINCOL = 34
const RAD = Math.PI / 4 // 45°

export default function Matrix({ network }) {
  const mx = network.matrix
  const { players, subtechs } = mx
  const maxCell = mx.max_cell || 1
  const N = subtechs.length
  const [hover, setHover] = useState(null) // {r, c}
  const [tip, setTip] = useState(null)
  const [measureRef, contentW] = useMeasure()
  const headRef = useRef(null)
  const [maxLen, setMaxLen] = useState(170) // measured intrinsic label width (px)

  const lookup = useMemo(() => {
    const m = new Map()
    mx.cells.forEach((c) => m.set(`${c.player}|${c.subtech}`, c.count))
    return m
  }, [mx.cells])

  // Geometry, all deterministic from the measured longest label.
  const headH = Math.ceil(maxLen * Math.sin(RAD)) + 8 // reserves exactly the labels' vertical span
  const rightPad = Math.ceil(maxLen * Math.cos(RAD)) + 10 // room for the last label's rightward reach
  const cw = contentW || 980
  const COLW = Math.max(MINCOL, Math.floor((cw - rightPad - LABELW - TOTALW) / N))
  const gridW = LABELW + N * COLW + TOTALW
  const svgW = gridW + rightPad
  const cx = (i) => LABELW + i * COLW + COLW / 2

  // Measure the actual rendered label widths (getComputedTextLength is
  // position-independent), and re-measure once web fonts finish loading.
  const measure = () => {
    const texts = headRef.current && headRef.current.querySelectorAll('.mx-head__l')
    if (!texts || !texts.length) return
    let m = 0
    texts.forEach((t) => {
      const l = t.getComputedTextLength()
      if (l > m) m = l
    })
    setMaxLen((prev) => (Math.abs(prev - m) > 0.5 ? m : prev))
  }
  useLayoutEffect(measure, [subtechs, contentW])
  useEffect(() => {
    if (typeof document !== 'undefined' && document.fonts && document.fonts.ready) {
      document.fonts.ready.then(measure)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const showCell = (r, c, p, s, n, x, y) => {
    setHover({ r, c })
    setTip({
      x,
      y,
      content: (
        <>
          <div className="tip__title">{p.player}</div>
          <div className="tip__sub">{s}</div>
          <TipRow k="Patents" v={int(n)} accent={n > 0 ? C.euv : C.muted} />
          <TipRow k="Share of row" v={p.total ? pct((n / p.total) * 100) : '0.0%'} />
        </>
      ),
    })
  }
  const clear = () => {
    setHover(null)
    setTip(null)
  }

  const legendSteps = [0.14, 0.35, 0.55, 0.75, 1].map((t) => ramp(t))

  return (
    <div>
      <Figure
        fig="3"
        caption={`Player × sub-technology — ${players.length} players, ${N} sub-technologies, shaded by patent count`}
      >
        <div className="mx-scroll" ref={measureRef}>
          <div className="mx-wrap" style={{ width: svgW }}>
            {/* column labels: SVG with explicit geometry. text-anchor=start + rotate(-45)
                about (cx, headH) makes each label extend up and to the right from its
                column, so nothing crosses the grid's top edge. */}
            <svg
              ref={headRef}
              className="mx-head"
              width={svgW}
              height={headH}
              viewBox={`0 0 ${svgW} ${headH}`}
              role="presentation"
              aria-hidden="true"
            >
              {subtechs.map((s, i) => (
                <text
                  key={s}
                  className="mx-head__l"
                  x={cx(i)}
                  y={headH}
                  textAnchor="start"
                  transform={`rotate(-45 ${cx(i)} ${headH})`}
                  fontSize="11"
                  fontWeight={hover && hover.c === i ? 700 : 400}
                  fill={hover && hover.c === i ? C.euv : C.ink}
                >
                  {colLabel(s)}
                </text>
              ))}
            </svg>

            <table className="mx" style={{ width: gridW }}>
              <caption className="visually-hidden">
                Heatmap of patent counts for the top {players.length} players (rows, by total patents
                descending) across {N} lithography sub-technologies (columns). Darker cells are more
                patents; empty cells have none.
              </caption>
              <colgroup>
                <col style={{ width: LABELW }} />
                {subtechs.map((s) => (
                  <col key={s} style={{ width: COLW }} />
                ))}
                <col style={{ width: TOTALW }} />
              </colgroup>
              <thead>
                <tr>
                  <th className="mx-corner" scope="col">
                    <span className="visually-hidden">Player</span>
                  </th>
                  {subtechs.map((s) => (
                    <th key={s} scope="col" className="mx-ch">
                      <span className="visually-hidden">{s}</span>
                    </th>
                  ))}
                  <th className="mx-total-h" scope="col">
                    Total
                  </th>
                </tr>
              </thead>
              <tbody>
                {players.map((p, ri) => (
                  <tr key={p.player} className={hover && hover.r === ri ? 'mx-tr--hi' : ''}>
                    <th className={`mx-row${hover && hover.r === ri ? ' mx-row--hi' : ''}`} scope="row">
                      <span className="swatch" style={{ background: categoryColor(p.category) }} aria-hidden="true" />
                      {p.player}
                    </th>
                    {subtechs.map((s, ci) => {
                      const n = lookup.get(`${p.player}|${s}`) || 0
                      const t = n > 0 ? 0.14 + 0.86 * Math.sqrt(n / maxCell) : 0
                      const share = p.total ? (n / p.total) * 100 : 0
                      const cls = ['mx-cell']
                      if (n === 0) cls.push('mx-cell--empty')
                      if (hover && hover.c === ci) cls.push('mx-cell--colhi')
                      return (
                        <td
                          key={s}
                          className={cls.join(' ')}
                          style={n > 0 ? { background: ramp(t) } : undefined}
                          tabIndex={0}
                          role="img"
                          aria-label={`${p.player}, ${s}, ${int(n)} patents, ${pct(share)} of ${p.player}'s total`}
                          onMouseEnter={(e) => showCell(ri, ci, p, s, n, e.clientX, e.clientY)}
                          onMouseMove={(e) => showCell(ri, ci, p, s, n, e.clientX, e.clientY)}
                          onMouseLeave={clear}
                          onFocus={(e) => {
                            const rr = e.currentTarget.getBoundingClientRect()
                            showCell(ri, ci, p, s, n, rr.left + rr.width / 2, rr.top)
                          }}
                          onBlur={clear}
                        />
                      )
                    })}
                    <td className="mx-total">{int(p.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Figure>
      <Tooltip tip={tip} />

      <div className="mx-legend" aria-hidden="true">
        <span className="mx-legend__label">patents / cell</span>
        <span className="mx-legend__swatch mx-legend__swatch--empty" />
        <span className="mx-legend__mini">0</span>
        {legendSteps.map((c, i) => (
          <span key={i} className="mx-legend__swatch" style={{ background: c }} />
        ))}
        <span className="mx-legend__mini">{int(maxCell)}</span>
      </div>
    </div>
  )
}
