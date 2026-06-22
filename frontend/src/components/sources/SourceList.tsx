import { Source } from '../../api/client'
import './SourceList.css'

interface SourceListProps {
  sources: Source[]
}

export default function SourceList({ sources }: SourceListProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'done':
        return '✓'
      case 'ingesting':
        return '⟳'
      case 'failed':
        return '✗'
      case 'queued':
        return '⋯'
      default:
        return '•'
    }
  }

  const getStatusClass = (status: string) => `status-${status}`

  return (
    <div className="source-list">
      {sources.map((src) => (
        <div key={src.source_id} className={`source-item ${getStatusClass(src.status)}`}>
          <div className="source-meta">
            <span className="source-icon">{getStatusIcon(src.status)}</span>
            <div className="source-info">
              <span className="source-name">{src.name}</span>
              <span className="source-type">[{src.type}]</span>
            </div>
            <span className="source-status">{src.status}</span>
          </div>

          {src.progress !== undefined && src.status === 'ingesting' && (
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${src.progress}%` }} />
              <span className="progress-text">{src.progress}%</span>
            </div>
          )}

          {src.error && <div className="source-error">{src.error}</div>}
        </div>
      ))}
    </div>
  )
}
