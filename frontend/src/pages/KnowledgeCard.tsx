import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useCard } from '../lib/hooks'
import './KnowledgeCard.css'

export function KnowledgeCard() {
  const { ref = '' } = useParams<{ ref: string }>()
  const navigate = useNavigate()
  const { data: card, isLoading, error } = useCard(ref)

  if (isLoading) {
    return <div className="kc-loading">Loading card…</div>
  }

  if (error || !card) {
    return (
      <div className="kc-error">
        <p>Knowledge card not found.</p>
        <button className="kc-back-btn" onClick={() => navigate('/kb')}>
          ← Back to Knowledge Base
        </button>
      </div>
    )
  }

  return (
    <div className="kc-page">
      <button className="kc-back-btn" onClick={() => navigate('/kb')}>
        <ArrowLeft size={16} />
        Knowledge Base
      </button>

      <header className="kc-header">
        <div className="kc-header-left">
          <h1 className="kc-title">{card.title}</h1>
          <div className="kc-meta">
            <span className={`kc-status kc-status--${card.status}`}>{card.status}</span>
            <span className="kc-ref">{card.ref}</span>
          </div>
        </div>
        <div className="kc-header-actions">
          <button className="kc-action-btn" onClick={() => navigate(`/ask?scope=${encodeURIComponent(card.ref)}`)}>
            Ask Atlas
          </button>
          <button className="kc-action-btn secondary" onClick={() => navigate(`/graph?focus=${card.ref}`)}>
            Open in graph
          </button>
        </div>
      </header>

      <div className="kc-layout">
        <article className="kc-body">
          <div className="kc-markdown">
            <pre className="kc-pre">{card.markdown}</pre>
          </div>

          {card.provenance.length > 0 && (
            <section className="kc-section">
              <h2 className="kc-section-title">Sources</h2>
              <div className="kc-citations">
                {card.provenance.map((p, i) => (
                  <span key={i} className={`kc-citation kc-citation--${p.kind}`}>
                    <span className="kc-citation-ref">{p.ref}</span>
                    <span className="kc-citation-loc">{p.loc}</span>
                  </span>
                ))}
              </div>
            </section>
          )}
        </article>

        {card.relations.length > 0 && (
          <aside className="kc-relations">
            <h2 className="kc-relations-title">Relations</h2>
            <div className="kc-relation-list">
              {card.relations.map((r, i) => (
                <button
                  key={i}
                  className="kc-relation-item"
                  onClick={() => navigate(`/kb/${r.ref}`)}
                >
                  <span className="kc-relation-kind">{r.kind}</span>
                  <span className="kc-relation-ref">{r.ref}</span>
                </button>
              ))}
            </div>
          </aside>
        )}
      </div>
    </div>
  )
}

export default KnowledgeCard
