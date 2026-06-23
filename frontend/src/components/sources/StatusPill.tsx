import { Source } from '../../lib/types'

export function StatusPill({ source }: { source: Source }) {
  const dotColor =
    source.status === 'ready'
      ? 'var(--l3)'
      : source.status === 'error'
        ? 'var(--rose)'
        : 'var(--primary)'

  const label =
    source.status === 'queued'
      ? 'Queued'
      : source.status === 'indexing'
        ? `Indexing (${source.progress || 0}%)`
        : source.status === 'ready'
          ? 'Ready'
          : 'Error'

  return (
    <div className="status-pill" style={{ '--dot-color': dotColor } as any}>
      <span className="status-dot" />
      <span>{label}</span>
    </div>
  )
}
