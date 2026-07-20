import { useData } from './useData.js'
import { useScrollReveal } from './hooks/useReveal.js'
import Masthead from './components/Masthead.jsx'
import SideRail from './components/SideRail.jsx'
import KeyFindings from './components/KeyFindings.jsx'
import Section from './components/Section.jsx'
import KpiRail from './components/KpiRail.jsx'
import HeroSlope from './components/HeroSlope.jsx'
import Measurement from './components/Measurement.jsx'
import FieldOverTime from './components/FieldOverTime.jsx'
import Matrix from './components/Matrix.jsx'
import MethodsFooter from './components/MethodsFooter.jsx'
import { pct, year, int } from './lib/format.js'

const NAV = [
  { id: 'hero', n: '1', name: 'Pivot' },
  { id: 'measurement', n: '2', name: 'Measurement' },
  { id: 'field', n: '3', name: 'Over time' },
  { id: 'field-map', n: '4', name: 'The field' },
  { id: 'methods', n: '', name: 'Methods' },
]

export default function App() {
  const { data, error, loading } = useData()
  useScrollReveal(!loading && !error && !!data)

  if (loading) return <div className="loading mono">Loading field data…</div>
  if (error)
    return (
      <div className="error mono">
        Could not load data: {error}
        <br />
        Run <code>python scripts/export_marts.py</code> to (re)generate frontend/public/data/*.json.
      </div>
    )

  const { kpis, pivot, leaderboard, euv_share_by_year, subtech_network, meta } = data
  const win = kpis.complete_filing_year_window

  // ---- narrative notes, interpolated from the JSON (never hardcoded) ----
  const P = Object.fromEntries(pivot.players.map((p) => [p.player, p]))
  const look1 =
    P.TSMC && P.Canon
      ? `TSMC's line climbs from ${pct(P.TSMC.early_share_pct)} to ${pct(
          P.TSMC.late_share_pct,
        )}, crossing every rival on the way up. Canon's is the only descent — ${pct(
          P.Canon.early_share_pct,
        )} down to ${pct(P.Canon.late_share_pct)}.`
      : null

  const O = Object.fromEntries(euv_share_by_year.overall.map((d) => [d.filing_year, d]))
  const look2 =
    O[2013] && O[2019] && O[win.end]
      ? `A first step lands around 2012–13, where the share reaches ${pct(
          O[2013].euv_share_pct,
        )}. Then it climbs steadily from 2019 (${pct(O[2019].euv_share_pct)}) to ${pct(
          O[win.end].euv_share_pct,
        )} by ${year(win.end)}.`
      : null

  const M = subtech_network.matrix
  const cellCount = (pl, st) => {
    const c = M.cells.find((x) => x.player === pl && x.subtech === st)
    return c ? c.count : 0
  }
  const rowTotal = (pl) => {
    const p = M.players.find((x) => x.player === pl)
    return p ? p.total : 0
  }
  const EXP = 'Exposure: stage, handling & apparatus'
  const ALN = 'Exposure: alignment & overlay'
  const asmlN = cellCount('ASML', EXP)
  const asmlT = rowTotal('ASML')
  const klaN = cellCount('KLA-Tencor', ALN)
  const klaT = rowTotal('KLA-Tencor')
  const look3 =
    asmlT && klaT
      ? `ASML owns the exposure-apparatus column — ${int(asmlN)} patents, ${pct(
          (asmlN / asmlT) * 100,
        )} of its own output. The materials firms cluster in the resist columns, while KLA‑Tencor sits almost entirely in alignment & overlay (${pct(
          (klaN / klaT) * 100,
        )} of its row).`
      : null

  const ag = leaderboard.agreement
  const method2 = (
    <>
      Two independent EUV signals guard against bias. <b>is_euv_title</b> matches EUV keywords in the
      patent title; <b>is_euv_cpc</b> flags four EUV-specific CPC classification codes. Firms that
      describe EUV generically — ASML titles its scanners “lithographic apparatus” — are invisible to
      the title flag but caught by classification, so <b>is_euv_any</b> (their union) is the fairest
      measure: it finds {int(ag.cpc_only)} patents the title alone misses.
    </>
  )
  const method3 = (
    <>
      Filing year is censored at both ends. The corpus holds only patents granted by end-2025, so
      recent filing years are missing their slower-to-issue patents (right-censoring); and it begins
      at grant year {year(meta.date_window.grant_start)}, so patents filed earlier but granted before
      then are absent (left-censoring). Only {year(win.start)}–{year(win.end)} is complete — drawn
      solid — with censored years greyed and excluded.
    </>
  )

  return (
    <>
      <a href="#hero" className="skip mono">
        Skip to content
      </a>
      <main className="shell">
        <Masthead kpis={kpis} meta={meta} />
        <SideRail items={NAV} />
        <KeyFindings kpis={kpis} pivot={pivot} leaderboard={leaderboard} euv={euv_share_by_year} />

        <Section
          id="hero"
          n="1"
          name="The pivot"
          title="Who turned toward EUV, and who turned away"
          lede={`Each line runs from a player's EUV share of filings in ${kpis.euv_share_early.years} to ${kpis.euv_share_late.years}. Indigo rose, umber retreated, muted held flat.`}
          look={look1}
        >
          <div className="split split--rail-left">
            <KpiRail kpis={kpis} />
            <HeroSlope pivot={pivot} />
          </div>
        </Section>

        <Section
          id="measurement"
          n="2"
          name="Measurement"
          title="The title flag was biased; the CPC flag corrects it"
          lede="A patent's title need not name EUV. Switch the flag to see the ranking reorder — ASML, which titles its scanners generically, climbs sharply under the classification-based signal."
          method={method2}
        >
          <Measurement leaderboard={leaderboard} />
        </Section>

        <Section
          id="field"
          n="3"
          name="Field over time"
          title="EUV's true annual share of filings"
          lede={`Filing year, not grant year. Only ${year(win.start)}–${year(win.end)} is complete; censored years are drawn in grey and excluded from every figure above.`}
          look={look2}
          method={method3}
        >
          <FieldOverTime euv={euv_share_by_year} />
        </Section>

        <Section
          id="field-map"
          n="4"
          name="The field"
          title="Who competes where"
          lede="A matrix of the top 15 players against the lithography sub-technologies. Each cell is shaded by how many patents a player holds in that sub-technology — darker means more; empty means none."
          look={look3}
        >
          <Matrix network={subtech_network} />
        </Section>

        <MethodsFooter meta={meta} kpis={kpis} />
      </main>
    </>
  )
}
