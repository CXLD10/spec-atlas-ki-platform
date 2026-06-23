import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCards } from '../lib/hooks'
import './KnowledgeBase.css'

export function KnowledgeBase() {
  const navigate = useNavigate()
  const { data: cards = [], isLoading } = useCards()
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<string | null>(null)

  const filtered = cards.filter(
    (c) =>
      !search ||
      c.title.toLowerCase().includes(search.toLowerCase()) ||
      c.ref.toLowerCase().includes(search.toLowerCase())
  )

  const selectedCard = cards.find((c) => c.ref === selected)

  return (
    <div className="kb-page">
      <aside className="kb-nav">
        <div className="kb-nav-header">
          <h2 className="kb-nav-title">Knowledge Base</h2>
          <p className="kb-nav-count">{cards.length} cards</p>
          <input
            type="search"
            placeholder="Search cards…"
            className="kb-search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search knowledge cards"
          />
        </div>
        <nav className="kb-card-list">
          {isLoading ? (
            <div className="kb-list-loading">Loading…</div>
          ) : filtered.length === 0 ? (
            <div className="kb-list-empty">No cards found.</div>
          ) : (
            filtered.map((card) => (
              <button
                key={card.ref}
                className={`kb-card-item ${selected === card.ref ? 'active' : ''}`}
                onClick={() => setSelected(card.ref)}
              >
                <span className={`kb-status-dot kb-status--${card.status}`} />
                <span className="kb-card-item-title">{card.title}</span>
              </button>
            ))
          )}
        </nav>
      </aside>

      <main className="kb-content">
        {!selectedCard ? (
          <div className="kb-index">
            <h1 className="kb-index-title">Knowledge Base</h1>
            <p className="kb-index-desc">
              {cards.length} cards across{' '}
              {new Set(cards.flatMap((c) => c.provenance.map((p) => p.ref))).size} sources.
              Every card is generated from source and cites it.
            </p>
            <div className="kb-index-stats">
              <div className="kb-stat">
                <span className="kb-stat-value">
                  {cards.filter((c) => c.status === 'verified').length}
                </span>
                <span className="kb-stat-label">Verified</span>
              </div>
              <div className="kb-stat">
                <span className="kb-stat-value">
                  {cards.filter((c) => c.status === 'draft').length}
                </span>
                <span className="kb-stat-label">Draft</span>
              </div>
              <div className="kb-stat">
                <span className="kb-stat-value">
                  {cards.filter((c) => c.status === 'stale').length}
                </span>
                <span className="kb-stat-label">Stale</span>
              </div>
            </div>
            <p className="kb-index-hint">Select a card from the list to view it.</p>
          </div>
        ) : (
          <article className="kb-card-view">
            <div className="kb-card-header">
              <div>
                <h1 className="kb-card-title">{selectedCard.title}</h1>
                <div className="kb-card-meta">
                  <span className={`kb-card-status kb-status--${selectedCard.status}`}>
                    {selectedCard.status}
                  </span>
                  <span className="kb-card-ref">{selectedCard.ref}</span>
                </div>
              </div>
              <button
                className="kb-open-btn"
                onClick={() => navigate(`/kb/${selectedCard.ref}`)}
              >
                Open →
              </button>
            </div>

            <div className="kb-card-body">
              <pre className="kb-card-markdown">{selectedCard.markdown}</pre>
            </div>

            {selectedCard.provenance.length > 0 && (
              <div className="kb-card-provenance">
                <h3 className="kb-section-heading">Sources</h3>
                <div className="kb-citation-list">
                  {selectedCard.provenance.map((p, i) => (
                    <span key={i} className={`kb-citation kb-citation--${p.kind}`}>
                      {p.ref} · {p.loc}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {selectedCard.relations.length > 0 && (
              <div className="kb-card-relations">
                <h3 className="kb-section-heading">Relations</h3>
                <div className="kb-relation-list">
                  {selectedCard.relations.map((r, i) => (
                    <button
                      key={i}
                      className="kb-relation-item"
                      onClick={() => setSelected(r.ref)}
                    >
                      <span className="kb-relation-kind">{r.kind}</span>
                      <span className="kb-relation-ref">{r.ref}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </article>
        )}
      </main>
    </div>
  )
}

export default KnowledgeBase
