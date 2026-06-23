import { useNavigate } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { Source } from '../../lib/types'
import { TypeBadge } from './TypeBadge'
import { StatusPill } from './StatusPill'
import './SourceCard.css'

export function SourceCard({ source }: { source: Source }) {
  const navigate = useNavigate()

  const handleClick = () => {
    navigate(`/sources/${source.id}`)
  }

  return (
    <button className="source-card" onClick={handleClick}>
      <div className="card-header">
        <div>
          <h3 className="card-title">{source.name}</h3>
          {source.subtitle && <p className="card-subtitle">{source.subtitle}</p>}
        </div>
        <div className="card-badges">
          <TypeBadge source={source} />
          <StatusPill source={source} />
        </div>
      </div>

      <div className="card-progress">
        {source.status === 'indexing' && source.progress && (
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${source.progress}%` }} />
          </div>
        )}
      </div>

      <div className="card-stats">
        <div className="stat">
          <span className="stat-value">{source.stats.entities}</span>
          <span className="stat-label">{source.type === 'repo' ? 'Symbols' : 'Pages'}</span>
        </div>
        <div className="stat">
          <span className="stat-value">{source.stats.cards}</span>
          <span className="stat-label">Cards</span>
        </div>
      </div>

      <div className="card-footer">
        <ArrowRight size={16} />
      </div>
    </button>
  )
}
