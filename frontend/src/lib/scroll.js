// Smooth-scroll to a section, jumping instead when reduced motion is requested.
export function scrollToId(id) {
  const el = document.getElementById(id)
  if (!el) return
  const reduced =
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  el.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' })
}
