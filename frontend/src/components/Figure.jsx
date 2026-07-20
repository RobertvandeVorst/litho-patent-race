// A figure: a mono caption above a hairline, then its SVG (passed as children).
// `fig` is the sequential figure number; `caption` the short description.
// Provenance (which JSON each figure reads) lives in the methods footer, not here.
export default function Figure({ fig, caption, children }) {
  return (
    <figure className="figure">
      <figcaption className="figure__caption">
        <span>
          <b>Fig. {fig}</b> — {caption}
        </span>
      </figcaption>
      {children}
    </figure>
  )
}
