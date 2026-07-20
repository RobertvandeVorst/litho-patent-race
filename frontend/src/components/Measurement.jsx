import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import { max } from 'd3-array'
import { categoryColor } from '../lib/palette.js'
import { C } from '../lib/palette.js'
import { int } from '../lib/format.js'
import { useReducedMotion } from '../hooks/useReducedMotion.js'

// dense-ish rank map (1-based) by a numeric field, descending.
function rankBy(players, field) {
  const sorted = [...players].sort((a, b) => b[field] - a[field])
  const m = new Map()
  sorted.forEach((p, i) => m.set(p.player, i + 1))
  return m
}

export default function Measurement({ leaderboard }) {
  const [flag, setFlag] = useState('cpc') // 'title' | 'cpc'
  const reduced = useReducedMotion()
  const rowRefs = useRef(new Map())
  const prevRects = useRef(new Map())

  const players = leaderboard.players
  const titleRank = useMemo(() => rankBy(players, 'euv_title'), [players])
  const cpcRank = useMemo(() => rankBy(players, 'euv_cpc'), [players])

  // stable set: top 12 by union count; reorder within by the active flag
  const pool = useMemo(
    () => [...players].sort((a, b) => b.euv_any - a.euv_any).slice(0, 12),
    [players],
  )
  const field = flag === 'cpc' ? 'euv_cpc' : 'euv_title'
  const rows = useMemo(
    () => [...pool].sort((a, b) => b[field] - a[field]),
    [pool, field],
  )
  // scale bars to the active flag's max so the top player's bar nearly fills the column
  const maxVal = max(rows, (d) => d[field]) || 1

  // FLIP: animate row reordering
  useLayoutEffect(() => {
    if (reduced) return
    const refs = rowRefs.current
    refs.forEach((el, key) => {
      if (!el) return
      const newRect = el.getBoundingClientRect()
      const prev = prevRects.current.get(key)
      if (prev) {
        const dy = prev.top - newRect.top
        if (dy) {
          el.style.transition = 'none'
          el.style.transform = `translateY(${dy}px)`
          requestAnimationFrame(() => {
            el.style.transition = 'transform 520ms cubic-bezier(.2,.7,.2,1)'
            el.style.transform = ''
          })
        }
      }
    })
    refs.forEach((el, key) => el && prevRects.current.set(key, el.getBoundingClientRect()))
  }, [rows, reduced])

  const ag = leaderboard.agreement
  const agTotal = ag.any_total
  const seg = [
    { key: 'Title only', v: ag.title_only, bg: C.muted, fg: C.ink },
    { key: 'Both flags', v: ag.both, bg: C.euv, fg: C.ground },
    { key: 'CPC only', v: ag.cpc_only, bg: '#726ab8', fg: C.ground },
  ]
  const pctShare = (v) => Math.round((v / agTotal) * 1000) / 10

  return (
    <div className="meas">
      {/* agreement stacked bar — full width, the CPC-only segment being widest is the argument */}
      <div className="agbar-wrap">
        <div
          className="agbar"
          role="img"
          aria-label={`Of ${int(agTotal)} EUV-flagged patents: title only ${int(ag.title_only)}, both flags ${int(ag.both)}, CPC only ${int(ag.cpc_only)}.`}
        >
          {seg.map((s) => (
            <div
              key={s.key}
              className="agbar__seg"
              style={{ width: `${(s.v / agTotal) * 100}%`, background: s.bg, color: s.fg }}
              title={`${s.key}: ${int(s.v)} (${pctShare(s.v)}%)`}
            >
              <span className="agbar__name">{s.key}</span>
              <span className="agbar__num">
                {int(s.v)} · {pctShare(s.v)}%
              </span>
            </div>
          ))}
        </div>
        <p className="mono agbar__note">
          Of {int(agTotal)} EUV-flagged patents, the CPC flag surfaces {int(ag.cpc_only)} the title
          misses — the title under-counts firms that describe EUV generically.
        </p>
      </div>

      <div className="toggle" role="group" aria-label="EUV signal">
        <button
          type="button"
          className="toggle__btn"
          aria-pressed={flag === 'title'}
          onClick={() => setFlag('title')}
        >
          Title flag
        </button>
        <button
          type="button"
          className="toggle__btn"
          aria-pressed={flag === 'cpc'}
          onClick={() => setFlag('cpc')}
        >
          CPC flag
        </button>
      </div>
      <p className="mono" style={{ fontSize: 12, color: C.muted, margin: '10px 0 16px' }}>
        Ordered by EUV patents under the <b style={{ color: C.ink }}>{flag === 'cpc' ? 'CPC' : 'title'}</b> flag ·
        chip shows rank under title → CPC
      </p>

      <div role="table" aria-label={`Top players by ${flag} EUV flag`}>
          <div className="meas-head mono" role="row" aria-hidden="true">
            <span>#</span>
            <span>Player</span>
            <span>{flag === 'cpc' ? 'CPC' : 'Title'} EUV patents</span>
            <span style={{ textAlign: 'right' }}>#</span>
            <span style={{ textAlign: 'right' }}>Δ rank</span>
          </div>
          {rows.map((p, i) => {
            const tr = titleRank.get(p.player)
            const cr = cpcRank.get(p.player)
            const from = flag === 'cpc' ? tr : cr
            const to = flag === 'cpc' ? cr : tr
            const dir = to < from ? 'up' : to > from ? 'down' : 'same'
            const val = p[field]
            return (
              <div
                className="meas-row"
                role="row"
                key={p.player}
                ref={(el) => rowRefs.current.set(p.player, el)}
              >
                <span className="mono meas-rank">{i + 1}</span>
                <span className="meas-name">
                  <span className="swatch" style={{ background: categoryColor(p.player_category) }} aria-hidden="true" />
                  {p.player}
                  <span className="mono meas-sub">
                    title {int(p.euv_title)} · cpc {int(p.euv_cpc)}
                  </span>
                </span>
                <span className="meas-bar" aria-hidden="true">
                  <i style={{ width: `${(val / maxVal) * 100}%`, background: categoryColor(p.player_category) }} />
                </span>
                <b className="mono meas-count">{int(val)}</b>
                <span
                  className={`chip chip--${dir}`}
                  title={`Rank ${tr} under title, ${cr} under CPC`}
                >
                  {dir === 'up' ? '▲' : dir === 'down' ? '▼' : '■'} {from}→{to}
                </span>
              </div>
            )
          })}
        </div>
    </div>
  )
}
