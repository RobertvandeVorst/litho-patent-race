import { scrollToId } from '../lib/scroll.js'
import { pct, int } from '../lib/format.js'

const ordinal = (n) => {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}

// Ruled "Key findings" block between the hero and section 1. Every number is
// interpolated from the JSON; each row links to the section that evidences it.
export default function KeyFindings({ kpis, pivot, leaderboard, euv }) {
  const early = kpis.euv_share_early
  const peak = euv.overall.reduce((a, b) => (b.euv_share_pct > a.euv_share_pct ? b : a))
  const mult = peak.euv_share_pct / early.euv_share_pct

  const P = Object.fromEntries(pivot.players.map((p) => [p.player, p]))
  const rankList = (field) =>
    [...leaderboard.players].sort((a, b) => b[field] - a[field]).map((p) => p.player)
  const asmlTitleRank = rankList('euv_title').indexOf('ASML') + 1
  const asmlCpcRank = rankList('euv_cpc').indexOf('ASML') + 1

  const findings = [
    {
      to: 'field',
      text: (
        <>
          EUV's share of filings grew <b>{mult.toFixed(1)}×</b> across the complete window — from{' '}
          {pct(early.euv_share_pct)} ({early.years}) to a {pct(peak.euv_share_pct)} peak in{' '}
          {peak.filing_year}.
        </>
      ),
    },
    {
      to: 'hero',
      text: (
        <>
          <b>TSMC</b> pivoted hardest, {pct(P.TSMC.early_share_pct)} → {pct(P.TSMC.late_share_pct)};{' '}
          <b>Canon</b> is the only retreat, {pct(P.Canon.early_share_pct)} → {pct(P.Canon.late_share_pct)}.
        </>
      ),
    },
    {
      to: 'measurement',
      text: (
        <>
          The choice of EUV definition changes the league table — <b>ASML</b> moves from{' '}
          {ordinal(asmlTitleRank)} on the title flag to <b>{ordinal(asmlCpcRank)}</b> on the CPC flag.
        </>
      ),
    },
    {
      to: 'field-map',
      text: (
        <>
          <b>{pct(kpis.coverage_pct)}</b> of patents map to <b>{int(kpis.distinct_named_players)}</b>{' '}
          named players; the remainder stay unattributed.
        </>
      ),
    },
  ]

  return (
    <section className="findings" aria-label="Key findings" data-reveal>
      <p className="findings__tag mono">Key findings</p>
      <ol className="findings__list">
        {findings.map((f, i) => (
          <li className="findings__row" key={i} style={{ '--d': i }} data-reveal>
            <a
              className="findings__rowlink"
              href={`#${f.to}`}
              onClick={(e) => {
                e.preventDefault()
                scrollToId(f.to)
              }}
            >
              <span className="findings__i mono">{String(i + 1).padStart(2, '0')}</span>
              <span className="findings__text">{f.text}</span>
              <span className="findings__link mono" aria-hidden="true">
                See ↓
              </span>
            </a>
          </li>
        ))}
      </ol>
    </section>
  )
}
