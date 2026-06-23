import { useNavigate } from 'react-router-dom'
import type { LayeredGraphNode, LayeredGraphEdge } from '../../api/client'
import './Inspector.css'

const LAYER_LABELS: Record<string, string> = {
  L1: 'Source code — function, class, or module',
  L3: 'Knowledge card — spec or summary',
  L4: 'Domain — cluster or concept',
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
          <p className="inspector-empty-hint">
            L1 Sources · L3 Cards · L4 Domains
            <br />
            Beams show provenance between layers.
          </p>
        </div>
      </aside>
    )
  }

  // Neighbors are computed from the already-fetched graph — no extra request.
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

  const isCard = node.layer === 'L3'
  const kbRef = node.qualified_name || node.label

  return (
    <aside className="inspector">
      <header className="inspector-header">
        <span className={`inspector-tag inspector-tag--${node.layer.toLowerCase()}`}>{node.layer}</span>
        <h2 className="inspector-title">{node.label}</h2>
        <code className="inspector-id">{node.kind}{node.file_path ? ` · ${node.file_path}` : ''}</code>
      </header>

      <div className="inspector-body">
        <section className="inspector-section">
          <h3 className="inspector-section-label">Layer</h3>
          <p className="inspector-text">{LAYER_LABELS[node.layer]}</p>
        </section>

        <section className="inspector-section">
          <h3 className="inspector-section-label">Neighbors</h3>
          {neighbors.length === 0 && (
            <p className="inspector-dim">No edges in current view.</p>
          )}
          <div className="inspector-neighbor-list">
            {neighbors.map((nb, i) => {
              const graphNode = nodeMap.get(nb.id)
              return (
                <button
                  key={`${nb.id}-${i}`}
                  className="inspector-neighbor"
                  onClick={() => graphNode && onSelectNode(graphNode)}
                  title={`Select ${nb.label}`}
                >
                  <span className={`inspector-nb-dot inspector-nb-dot--${nb.layer.toLowerCase()}`} />
                  <span className="inspector-nb-kind">{nb.kind}</span>
                  <span className="inspector-nb-label">{nb.label}</span>
                  <span className="inspector-nb-arrow">{nb.dir === 'out' ? '→' : '←'}</span>
                </button>
              )
            })}
          </div>
        </section>
      </div>

      <footer className="inspector-footer">
        <button
          className="inspector-btn"
          onClick={() => navigate(`/ask?scope=${encodeURIComponent(node.label || node.id)}`)}
        >
          Ask Atlas about this
        </button>
        <button
          className={`inspector-btn inspector-btn--ghost ${!isCard ? 'inspector-btn--disabled' : ''}`}
          disabled={!isCard}
          onClick={() => isCard && navigate(`/kb/${encodeURIComponent(kbRef)}`)}
          title={!isCard ? 'Only available for L3 Knowledge Card nodes' : `Open card: ${kbRef}`}
        >
          Open Knowledge Card
        </button>
        <button
          className="inspector-btn inspector-btn--secondary"
          onClick={() => navigate(`/specify?component=${encodeURIComponent(node.label || node.id)}`)}
          title="Generate or edit specifications for this node"
        >
          Specify
        </button>
      </footer>
    </aside>
  )
}
