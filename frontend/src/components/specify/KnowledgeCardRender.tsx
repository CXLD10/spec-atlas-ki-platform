import { useNavigate } from 'react-router-dom'
import { Download, Share2, CheckCircle, Save } from 'lucide-react'
import { KnowledgeCard } from '../../lib/types'
import './KnowledgeCardRender.css'

interface KnowledgeCardRenderProps {
  card: KnowledgeCard
  onSave?: () => void
  onVerify?: () => void
}

export function KnowledgeCardRender({ card, onSave, onVerify }: KnowledgeCardRenderProps) {
  const navigate = useNavigate()

  const handleExport = () => {
    const element = document.createElement('a')
    const file = new Blob([card.markdown], { type: 'text/markdown' })
    element.href = URL.createObjectURL(file)
    element.download = `${card.title.replace(/\s+/g, '-').toLowerCase()}.md`
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
  }

  return (
    <div className="card-render">
      {/* Header */}
      <header className="card-render-header">
        <div className="card-render-title-block">
          <h1 className="card-render-title">{card.title}</h1>
          <span className={`card-render-status card-render-status--${card.status}`}>
            {card.status}
          </span>
        </div>
        <p className="card-render-ref">{card.ref}</p>
      </header>

      {/* Body */}
      <article className="card-render-body">
        <pre className="card-render-markdown">{card.markdown}</pre>
      </article>

      {/* Sources/Provenance */}
      {card.provenance.length > 0 && (
        <section className="card-render-section">
          <h2 className="card-render-section-title">Sources</h2>
          <div className="card-render-provenance">
            {card.provenance.map((p, i) => (
              <span key={i} className={`card-render-prov card-render-prov--${p.kind}`}>
                <code className="card-render-prov-ref">{p.ref}</code>
                <span className="card-render-prov-loc">{p.loc}</span>
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Relations */}
      {card.relations.length > 0 && (
        <section className="card-render-section">
          <h2 className="card-render-section-title">Relations</h2>
          <div className="card-render-relations">
            {card.relations.map((r, i) => (
              <button
                key={i}
                className="card-render-relation"
                onClick={() => navigate(`/kb/${r.ref}`)}
              >
                <span className="card-render-rel-kind">{r.kind}</span>
                <span className="card-render-rel-ref">{r.ref}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Footer Actions */}
      <footer className="card-render-footer">
        <button className="card-render-btn" onClick={onSave} title="Save as new version">
          <Save size={16} />
          Save as version
        </button>
        <button className="card-render-btn" onClick={onVerify} title="Mark as verified">
          <CheckCircle size={16} />
          Mark verified
        </button>
        <button
          className="card-render-btn"
          onClick={() => navigate(`/graph?focus=${card.ref}`)}
          title="View in Knowledge Graph"
        >
          <Share2 size={16} />
          Browse in graph
        </button>
        <button className="card-render-btn" onClick={handleExport} title="Download as markdown">
          <Download size={16} />
          Export
        </button>
      </footer>
    </div>
  )
}
