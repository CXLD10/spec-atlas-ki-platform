import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { IsoGraph, GraphNode, GraphEdge } from '../components/graph/IsoGraph'
import { Inspector } from '../components/graph/Inspector'
import { client, MockFallback } from '../lib/api'
import { MOCK_SUBGRAPH } from '../lib/mock'
import './Graph.css'

type SubgraphData = {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export default function Graph() {
  const [searchParams] = useSearchParams()
  const focusNode = searchParams.get('focus')

  const [graphData, setGraphData] = useState<SubgraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [active, setActive] = useState({ L1: true, L3: true, L4: true })

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    const fetchGraph = async () => {
      try {
        const data = await client.getSubgraph(focusNode || undefined, 2)
        if (!cancelled) {
          setGraphData({
            nodes: data.nodes as GraphNode[],
            edges: data.edges as GraphEdge[],
          })
        }
      } catch (err) {
        if (cancelled) return
        if (err instanceof MockFallback) {
          setGraphData({
            nodes: MOCK_SUBGRAPH.nodes as GraphNode[],
            edges: MOCK_SUBGRAPH.edges as GraphEdge[],
          })
        } else {
          setError(err instanceof Error ? err.message : 'Failed to fetch graph data')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchGraph()
    return () => { cancelled = true }
  }, [focusNode])

  if (loading) {
    return (
      <div className="graph-page graph-page--loading">
        <p>Loading graph…</p>
      </div>
    )
  }

  if (error || !graphData) {
    return (
      <div className="graph-page graph-page--error">
        <p>{error || 'Failed to load graph'}</p>
        <small>Backend unavailable — check VITE_API_URL</small>
      </div>
    )
  }

  const visibleNodes = graphData.nodes.filter((n) => active[n.layer as 'L1' | 'L3' | 'L4'])
  const visibleNodeIds = new Set(visibleNodes.map((n) => n.id))
  const visibleEdges = graphData.edges.filter(
    (e) => visibleNodeIds.has(e.s) && visibleNodeIds.has(e.d)
  )

  const countL1 = visibleNodes.filter((n) => n.layer === 'L1').length
  const countL3 = visibleNodes.filter((n) => n.layer === 'L3').length
  const countL4 = visibleNodes.filter((n) => n.layer === 'L4').length

  return (
    <div className="graph-page">
      {/* Canvas area */}
      <div className="graph-canvas-area">
        {/* HUD: layer toggles + stats */}
        <div className="graph-hud">
          <div className="hud-layers">
            {(
              [
                { key: 'L1', label: 'Sources', count: countL1 },
                { key: 'L3', label: 'Cards', count: countL3 },
                { key: 'L4', label: 'Domains', count: countL4 },
              ] as const
            ).map(({ key, label, count }) => (
              <label key={key} className="layer-toggle">
                <input
                  type="checkbox"
                  checked={active[key]}
                  onChange={(e) => setActive((a) => ({ ...a, [key]: e.target.checked }))}
                  aria-label={`Toggle ${label} layer`}
                />
                <span className={`layer-dot layer-dot--${key.toLowerCase()}`} />
                <span>
                  {key} {label} ({count})
                </span>
              </label>
            ))}
          </div>
          <div className="hud-stats">
            <div className="hud-stat">
              <span className="hud-stat-value">{visibleNodes.length}</span>
              <span className="hud-stat-label">Nodes</span>
            </div>
            <div className="hud-stat">
              <span className="hud-stat-value">{visibleEdges.length}</span>
              <span className="hud-stat-label">Edges</span>
            </div>
          </div>
        </div>

        {/* Canvas */}
        <IsoGraph
          nodes={visibleNodes}
          edges={visibleEdges}
          active={active}
          selected={selectedNode}
          onNodeClick={setSelectedNode}
        />

        {/* Help text */}
        <div className="graph-help" aria-hidden="true">
          <p>Drag to rotate · Scroll to zoom · Click a node to inspect</p>
          <p className="graph-help-secondary">
            Vertical beams show provenance: source → card → domain
          </p>
        </div>
      </div>

      {/* Inspector: always rendered, shows empty state when nothing selected */}
      <Inspector
        node={selectedNode}
        allNodes={visibleNodes}
        onSelectNode={setSelectedNode}
      />
    </div>
  )
}
