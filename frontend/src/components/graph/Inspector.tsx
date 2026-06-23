import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GraphNode } from './IsoGraph'
import { client, MockFallback } from '../../lib/api'
import { MOCK_SUBGRAPH } from '../../lib/mock'
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
  node: GraphNode | null
  allNodes: GraphNode[]
  onSelectNode: (node: GraphNode) => void
}

export function Inspector({ node, allNodes, onSelectNode }: InspectorProps) {
  const navigate = useNavigate()
  const [neighbors, setNeighbors] = useState<Neighbor[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!node) { setNeighbors([]); return }

    let cancelled = false
    setLoading(true)

    const run = async () => {
      let edges: Array<{ s: string; d: string; kind: string; layer: string }> = []
      let nodeMap: Record<string, { id: string; label: string; layer: string }> = {}

      try {
        const data = await client.getSubgraph(node.id, 1)
        edges = data.edges
        for (const n of data.nodes) nodeMap[n.id] = n
      } catch (err) {
        if (!(err instanceof MockFallback)) throw err
        // Derive from mock
        edges = MOCK_SUBGRAPH.edges
        for (const n of MOCK_SUBGRAPH.nodes) nodeMap[n.id] = n
      }

      if (cancelled) return

      const list: Neighbor[] = []
      for (const e of edges) {
        if (e.s === node.id && nodeMap[e.d]) {
          const t = nodeMap[e.d]
          list.push({ id: t.id, label: t.label, layer: t.layer as Neighbor['layer'], kind: e.kind, dir: 'out' })
        } else if (e.d === node.id && nodeMap[e.s]) {
          const t = nodeMap[e.s]
          list.push({ id: t.id, label: t.label, layer: t.layer as Neighbor['layer'], kind: e.kind, dir: 'in' })
        }
      }

      setNeighbors(list)
      setLoading(false)
    }

    run().catch(() => setLoading(false))
    return () => { cancelled = true }
  }, [node?.id])

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

  // Derive kb ref from node id: card-foo-bar → foo-bar, or just use id
  const isCard = node.layer === 'L3'
  const kbRef = node.id.startsWith('card-') ? node.id.slice(5) : node.id

  return (
    <aside className="inspector">
      <header className="inspector-header">
        <span className={`inspector-tag inspector-tag--${node.layer.toLowerCase()}`}>{node.layer}</span>
        <h2 className="inspector-title">{node.label}</h2>
        <code className="inspector-id">{node.id}</code>
      </header>

      <div className="inspector-body">
        <section className="inspector-section">
          <h3 className="inspector-section-label">Layer</h3>
          <p className="inspector-text">{LAYER_LABELS[node.layer]}</p>
        </section>

        <section className="inspector-section">
          <h3 className="inspector-section-label">
            Neighbors
            {loading && <span className="inspector-spinner"> ···</span>}
          </h3>
          {!loading && neighbors.length === 0 && (
            <p className="inspector-dim">No edges in current view.</p>
          )}
          <div className="inspector-neighbor-list">
            {neighbors.map((nb, i) => {
              const graphNode = allNodes.find((n) => n.id === nb.id)
              return (
                <button
                  key={`${nb.id}-${i}`}
                  className={`inspector-neighbor ${!graphNode ? 'inspector-neighbor--faded' : ''}`}
                  onClick={() => graphNode && onSelectNode(graphNode)}
                  disabled={!graphNode}
                  title={graphNode ? `Select ${nb.label}` : 'Not in current view'}
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
          onClick={() => navigate(`/ask?scope=${encodeURIComponent(node.id)}`)}
        >
          Ask Atlas about this
        </button>
        <button
          className={`inspector-btn inspector-btn--ghost ${!isCard ? 'inspector-btn--disabled' : ''}`}
          disabled={!isCard}
          onClick={() => isCard && navigate(`/kb/${kbRef}`)}
          title={!isCard ? 'Only available for L3 Knowledge Card nodes' : `Open card: ${kbRef}`}
        >
          Open Knowledge Card
        </button>
      </footer>
    </aside>
  )
}
