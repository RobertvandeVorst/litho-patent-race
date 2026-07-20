import { int, year } from '../lib/format.js'

// Editorial masthead: 2px ink rule over 1px amber rule. Numbers come from data.
export default function Masthead({ kpis, meta }) {
  const gy = meta.date_window
  return (
    <header className="masthead">
      <div className="masthead__rules" aria-hidden="true">
        <div className="masthead__rule-ink" />
        <div className="masthead__rule-amber" />
      </div>
      <p className="masthead__eyebrow">
        Robert van de Vorst · An analytics-engineering field study
      </p>
      <h1 className="masthead__title">The lithography patent race</h1>
      <p className="masthead__standfirst">
        <span className="mono">{int(kpis.total_patents)}</span> granted lithography
        patents (CPC&nbsp;G03F), {year(gy.grant_start)}–{year(gy.grant_end)}, from real
        USPTO&nbsp;/&nbsp;PatentsView data — who pivoted to extreme-ultraviolet light,
        and who did not.
      </p>
    </header>
  )
}
