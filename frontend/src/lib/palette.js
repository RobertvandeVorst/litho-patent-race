// Palette mirrors the CSS tokens so D3/React code can reference the same values.
export const C = {
  ground: '#f1ce85',
  ink: '#1b1710',
  euv: '#211a5e', // reserved for EUV — never decorative
  rule: '#c9992f',
  hairline: '#e0c97e',
  muted: '#9a855a',
  umber: '#7a3b1e',
  panel: '#f6dca0',
}

export const CATEGORY = {
  Equipment: '#a6531f',
  Chipmaker: '#3e5c3a',
  // Materials darkened from #c79a3a → #8c6518: the original failed WCAG 3:1 on the
  // #f1ce85 ground (1.71:1); #8c6518 clears it (3.49:1) while keeping the gold identity.
  Materials: '#8c6518',
  'Metrology-EDA': '#6e6152',
  'Mask-substrate': '#8a4a3a',
  Other: '#7a6b45', // darkened muted so the fallback also passes 3:1 on ground
}

export function categoryColor(cat) {
  return CATEGORY[cat] || CATEGORY.Other
}

// Verdict → colour for the hero slope chart.
export const VERDICT_COLOR = {
  pivoted: C.euv, // EUV indigo, used meaningfully
  flat: C.muted,
  'moved away': C.umber,
}

// Short chart labels for long company names; tables keep full names.
export const SHORT = {
  'Carl Zeiss': 'Zeiss',
  'Tokyo Electron': 'TEL',
  'Applied Materials': 'AppMat',
  'GlobalFoundries': 'GloFo',
  'Molecular Imprints': 'MolImp',
  'Sumitomo Chemical': 'Sumitomo',
  'Nissan Chemical': 'Nissan',
  'Tokyo Ohka': 'TOK',
  'Rohm & Haas': 'Rohm&H',
  'KLA-Tencor': 'KLA',
  'Shin-Etsu': 'Shin-Etsu',
}

export function shortLabel(name) {
  return SHORT[name] || name
}
