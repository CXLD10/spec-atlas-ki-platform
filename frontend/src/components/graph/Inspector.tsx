import { useNavigate } from 'react-router-dom'
import type { LayeredGraphNode, LayeredGraphEdge } from '../../api/client'
import './Inspector.css'

const LAYER_META: Record<string, { label: string; desc: string }> = {
  L1: { label: 'Code',    desc: 'Source symbol — function, class, or module' },
  L3: { label: 'Card',    desc: 'Knowledge card — generated spec or summary' },
  L4: { label: 'Domain',  desc: 'Semantic cluster — auto-grouped components' },
}

interface Neighbor {
  id: string
  label: string
  layer: 'L1' | 'L3' | 'L4'
  kind: string
  dir: 'out' | 'in'
}

interface InspectorProps {
  node: LayeredGraphNode | null
  allNodes: LayeredGraphNode[]
  allEdges: LayeredGraphEdge[]
  onSelectNode: (node: LayeredGraphNode) => void
}

export function Inspector({ node, allNodes, allEdges, onSelectNode }: InspectorProps) {
  const navigate = useNavigate()

  if (!node) {
    return (
      <aside className="inspector inspector--empty">
        <div className="inspector-empty-content">
          <div className="inspector-empty-glyph">◎</div>
          <p className="inspector-empty-label">Click any node to inspect</p>
          <p className="inspector-empty-hint">Code · Cards · Domains<br />Edges show provenance between layers.</p>
        </div>
      </aside>
    )
  }

  const nodeMap = new Map(allNodes.map((n) => [n.id, n]))
  const neighbors: Neighbor[] = []
  for (const e of allEdges) {
    if (e.source === node.id && nodeMap.has(e.target)) {
      const t = nodeMap.get(e.target)!
      neighbors.push({ id: t.id, label: t.label, layer: t.layer, kind: e.kind, dir: 'out' })
    } else if (e.target === node.id && nodeMap.has(e.source)) {
      const t = nodeMap.get(e.source)!
      neighbors.push({ id: t.id, label: t.label, layer: t.layer, kind: e.kind, dir: 'in' })
    }
  }

  const meta      = LAYER_META[node.layer] ?? LAYER_META.L1
  const kind      = node.kind || (node.layer === 'L1' ? 'function' : node.layer === 'L3' ? 'spec' : 'domain')
  const filePath  = node.file_path
  const nbCount   = neighbors.length
  const isCard    = node.layer === 'L3'
  const kbRef     = node.qualified_name || node.label

  return (
    <aside className="inspector">
      <header className="inspector-header">
        <div className="inspector-header-top">
          <span className={`inspector-tag inspector-tag--${node.layer.toLowerCase()}`}>{meta.label}</span>
          <span className={`inspector-kind-badge inspector-kind--${kind}`}>{kind}</span>
        </div>
        <h2 className="inspector-title">{node.label}</h2>
        <p className="inspector-desc">{meta.desc}</p>
      </header>

      <div className="inspector-body">
        {/* Stats row */}
        <div className="inspector-stats">
          <div className="inspector-stat">
            <span className="inspector-stat-val">{nbCount}</span>
            <span className="inspector-stat-lbl">connections</span>
          </div>
          <div className="inspector-stat-divider" />
          <div className="inspector-stat">
            <span className="inspector-stat-val">{node.layer}</span>
            <span className="inspector-stat-lbl">layer</span>
          </div>
          <div className="inspector-stat-divider" />
          <div className="inspector-stat">
            <span className="inspector-stat-val" style={{ textTransform: 'capitalize', fontSize: '0.8rem' }}>{kind}</span>
            <span className="inspector-stat-lbl">kind</span>
          </div>
        </div>

        {/* File path */}
        {filePath && (
          <section className="inspector-section">
            <h3 className="inspector-section-label">File path</h3>
            <div className="inspector-filepath">
              <span className="inspector-filepath-icon">📄</span>
              <code className="inspector-filepath-text">{filePath}</code>
            </div>
          </section>
        )}

        {/* Connections */}
        {neighbors.length > 0 && (
          <section className="inspector-section">
            <h3 className="inspector-section-label">Connections <span className="inspector-count">{neighbors.length}</span></h3>
            <div className="inspector-neighbor-list">
              {neighbors.slice(0, 5).map((nb, i) => {
                const graphNode = nodeMap.get(nb.id)
                return (
                  <button
                    key={`${nb.id}-${i}`}
                    className="inspector-neighbor"
                    onClick={() => graphNode && onSelectNode(graphNode)}
                  >
                    <span className={`inspector-nb-dot inspector-nb-dot--${nb.layer.toLowerCase()}`} />
                    <span className="inspector-nb-label">{nb.label}</span>
                    <span className="inspector-nb-kind">{nb.kind}</span>
                    <span className="inspector-nb-arrow">{nb.dir === 'out' ? '→' : '←'}</span>
                  </button>
                )
              })}
            </div>
          </section>
        )}
      </div>

      <footer className="inspector-footer">
        <button className="inspector-btn" onClick={() => navigate(`/ask?scope=${encodeURIComponent(node.label || node.id)}`)}>
          Ask Atlas about this
        </button>
        <button
          className={`inspector-btn inspector-btn--ghost ${!isCard ? 'inspector-btn--disabled' : ''}`}
          disabled={!isCard}
          onClick={() => isCard && navigate(`/kb/${encodeURIComponent(kbRef)}`)}
        >
          Open Knowledge Card
        </button>
      </footer>
    </aside>
  )
}
