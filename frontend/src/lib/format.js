// Number/label formatting for mono figures. All display numbers pass through here.
export const int = (n) => Number(n).toLocaleString('en-US')

export const pct = (n, d = 1) =>
  `${Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })}%`

export const year = (n) => String(Math.trunc(Number(n)))

export const signed = (n) => (n > 0 ? `+${n}` : String(n))
