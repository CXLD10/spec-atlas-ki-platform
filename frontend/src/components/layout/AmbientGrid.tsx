import './AmbientGrid.css'

export function AmbientGrid() {
  return (
    <div className="ambient-grid" aria-hidden="true">
      <div className="grid-lines" />
      <div className="grid-vignette" />
    </div>
  )
}
