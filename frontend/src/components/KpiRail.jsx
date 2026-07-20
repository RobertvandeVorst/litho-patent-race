import { int, pct, year } from '../lib/format.js'

// Ruled KPI table. Every value comes from kpis.json.
export default function KpiRail({ kpis }) {
  const win = kpis.complete_filing_year_window
  const early = kpis.euv_share_early
  const late = kpis.euv_share_late
  const rows = [
    { label: 'Patents in scope', value: int(kpis.total_patents) },
    { label: 'Named-player coverage', value: pct(kpis.coverage_pct) },
    { label: 'Distinct named players', value: int(kpis.distinct_named_players) },
    {
      label: `EUV share, ${early.years}`,
      value: pct(early.euv_share_pct),
      sub: `${int(early.euv_any)} of ${int(early.patents)}`,
    },
    {
      label: `EUV share, ${late.years}`,
      value: pct(late.euv_share_pct),
      sub: `${int(late.euv_any)} of ${int(late.patents)}`,
    },
    {
      label: 'Complete filing window',
      value: `${year(win.start)}–${year(win.end)}`,
    },
  ]
  return (
    <div className="kpi" role="table" aria-label="Key figures">
      {rows.map((r) => (
        <div className="kpi__row" role="row" key={r.label}>
          <span className="kpi__label" role="cell">
            {r.label}
          </span>
          <span className="kpi__value" role="cell">
            {r.value}
            {r.sub && <small>{r.sub}</small>}
          </span>
        </div>
      ))}
    </div>
  )
}
