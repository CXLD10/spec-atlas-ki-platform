import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, RefreshCw, Zap } from 'lucide-react'
import { useSource, useCards } from '../lib/hooks'
import { client } from '../api/client'
import { TypeBadge } from '../components/sources/TypeBadge'
import { StatusPill } from '../components/sources/StatusPill'
import './SourceDetail.css'

export function SourceDetail() {
  const { id = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: source, isLoading: loadingSource } = useSource(id)
  const { data: allCards = [] } = useCards()
  const [isReingestingLoading, setIsReingestingLoading] = useState(false)

  const relatedCards = allCards.filter((c) =>
    c.provenance.some((p) => p.ref === source?.name)
  )

  const handleReingest = async () => {
    if (!source?.subtitle) return
    setIsReingestingLoading(true)
    try {
      const result = await client.reingestSource(source.subtitle)
      navigate(`/index/${result.job_id}`)
    } catch (error) {
      console.error('Reingest failed:', error)
      alert('Reingest failed. Check the console for details.')
    } finally {
      setIsReingestingLoading(false)
    }
  }

  if (loadingSource) {
    return <div className="source-detail-loading">Loading source…</div>
  }

  if (!source) {
    return (
      <div className="source-detail-error">
        <p>Source not found.</p>
        <button className="back-btn" onClick={() => navigate('/sources')}>
          ← Back to sources
        </button>
      </div>
    )
  }

  return (
    <div className="source-detail-page">
      <button className="back-btn" onClick={() => navigate('/sources')}>
        <ArrowLeft size={16} />
        All sources
      </button>

      <div className="source-detail-header">
        <div className="source-detail-meta">
          <h1 className="source-detail-title">{source.name}</h1>
          {source.subtitle && (
            <p className="source-detail-subtitle">{source.subtitle}</p>
          )}
          <div className="source-detail-badges">
            <TypeBadge source={source} />
            <StatusPill source={source} />
          </div>
        </div>
        <div className="source-detail-buttons">
          <button
            className="reingest-btn"
            onClick={handleReingest}
            disabled={isReingestingLoading}
          >
            <RefreshCw size={16} style={{ animation: isReingestingLoading ? 'spin 1s linear infinite' : 'none' }} />
            {isReingestingLoading ? 'Reingesting...' : 'Re-ingest'}
          </button>
          {source.type === 'repo' && (
            <button
              className="specify-btn"
              onClick={() => navigate(`/specify?repo=${encodeURIComponent(source.name)}&entity=${encodeURIComponent(source.name)}`)}
              title="Generate knowledge cards for this source"
            >
              <Zap size={16} />
              Specify
            </button>
          )}
        </div>
      </div>

      {source.status === 'indexing' && (
        <div className="source-progress">
          <div className="progress-label">
            Indexing… {source.progress ?? 0}%
          </div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${source.progress ?? 0}%` }}
            />
          </div>
        </div>
      )}

      <div className="source-detail-stats">
        <div className="detail-stat">
          <div className="detail-stat-value">{source.stats.entities}</div>
          <div className="detail-stat-label">
            {source.type === 'repo' ? 'Symbols' : 'Pages'}
          </div>
        </div>
        <div className="detail-stat">
          <div className="detail-stat-value">{source.stats.cards}</div>
          <div className="detail-stat-label">Knowledge cards</div>
        </div>
        <div className="detail-stat">
          <div className="detail-stat-value">
            {source.format?.toUpperCase() ?? '—'}
          </div>
          <div className="detail-stat-label">Format</div>
        </div>
      </div>

      <section className="source-cards-section">
        <h2 className="section-heading">Generated knowledge cards</h2>
        {relatedCards.length === 0 ? (
          <p className="section-empty">
            No cards generated yet. Cards appear once indexing completes.
          </p>
        ) : (
          <div className="card-list">
            {relatedCards.map((card) => (
              <button
                key={card.ref}
                className="card-list-item"
                onClick={() => navigate(`/kb/${card.ref}`)}
              >
                <div className="card-list-title">{card.title}</div>
                <span className={`card-status card-status--${card.status}`}>
                  {card.status}
                </span>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

export default SourceDetail
