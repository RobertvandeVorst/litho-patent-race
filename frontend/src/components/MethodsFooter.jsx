import { int, year } from '../lib/format.js'

// Everything here is read from meta.json. The licence is CC-BY 4.0 (attribution
// required) — explicitly NOT public domain.
export default function MethodsFooter({ meta, kpis }) {
  const gw = meta.date_window
  const cw = meta.complete_filing_window
  return (
    <footer className="methods" id="methods" aria-label="Methods and provenance">
      <h2>Methods &amp; provenance</h2>
      <dl>
        <dt>Source</dt>
        <dd>{meta.source}</dd>

        <dt>Licence</dt>
        <dd>
          <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">
            {meta.licence}
          </a>{' '}
          — attribution required. This is <b>not</b> public-domain data; reuse must credit
          PatentsView / USPTO.
        </dd>

        <dt>Scope</dt>
        <dd>
          {meta.cpc_scope}, granted {year(gw.grant_start)}–{year(gw.grant_end)}.{' '}
          {int(meta.total_patents)} patents in scope ({int(kpis.total_patents)} loaded).
        </dd>

        <dt>Complete window</dt>
        <dd>
          Time series use filing years {year(cw.start)}–{year(cw.end)} only. {meta.censoring_rationale}
        </dd>

        <dt>Pipeline</dt>
        <dd>PatentsView bulk TSVs → DuckDB (scope-filtered) → dbt (staging → marts) → JSON → React + D3.</dd>

        <dt>Figure sources</dt>
        <dd>
          <ul className="methods__figs">
            <li>Fig 1 — pivot.json</li>
            <li>Fig 2 — euv_share_by_year.json</li>
            <li>Fig 3 — subtech_network.json</li>
            <li>Key figures / leaderboard — kpis.json, leaderboard.json</li>
          </ul>
        </dd>

        <dt>Generated</dt>
        <dd>{meta.generated_at}</dd>
      </dl>
    </footer>
  )
}
