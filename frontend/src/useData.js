import { useEffect, useState } from 'react'

// All figures on the page come from these files at runtime. Nothing is hardcoded.
const FILES = [
  'kpis',
  'pivot',
  'leaderboard',
  'euv_share_by_year',
  'filings_by_player_year',
  'subtech_network',
  'meta',
]

export function useData() {
  const [state, setState] = useState({ data: null, error: null, loading: true })

  useEffect(() => {
    let cancelled = false
    const base = import.meta.env.BASE_URL || '/'
    Promise.all(
      FILES.map((name) =>
        fetch(`${base}data/${name}.json`).then((r) => {
          if (!r.ok) throw new Error(`${name}.json → HTTP ${r.status}`)
          return r.json()
        }),
      ),
    )
      .then((results) => {
        if (cancelled) return
        const data = {}
        FILES.forEach((name, i) => (data[name] = results[i]))
        setState({ data, error: null, loading: false })
      })
      .catch((err) => {
        if (!cancelled) setState({ data: null, error: err.message, loading: false })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return state
}
