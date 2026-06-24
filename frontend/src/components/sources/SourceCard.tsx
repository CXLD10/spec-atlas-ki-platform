import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Trash2 } from 'lucide-react'
import { Source } from '../../lib/types'
import { TypeBadge } from './TypeBadge'
import { StatusPill } from './StatusPill'
import './SourceCard.css'

export function SourceCard({ source, onDelete }: { source: Source; onDelete?: (id: string) => void }) {
  const navigate = useNavigate()
  const [isDeleting, setIsDeleting] = useState(false)

  const handleClick = () => {
    navigate(`/sources/${source.id}`)
  }

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation()

    if (!confirm(`Delete "${source.name}"? This cannot be undone.`)) {
      return
    }

    setIsDeleting(true)
    try {
      const response = await fetch(`/api/sources/${source.id}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error('Failed to delete source')
      }

      onDelete?.(source.id)
      window.location.reload()
    } catch (error) {
      console.error('Delete error:', error)
      alert('Failed to delete source')
      setIsDeleting(false)
    }
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
        <button
          className="card-delete-btn"
          onClick={handleDelete}
          disabled={isDeleting}
          title="Delete this source"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </button>
  )
}
