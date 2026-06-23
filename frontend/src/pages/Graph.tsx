import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { IsoGraph, GraphNode } from '../components/graph/IsoGraph'
import { client, MockFallback } from '../lib/api'
import { MOCK_SUBGRAPH } from '../lib/mock'
import './Graph.css'

export default function Graph() {
  const [searchParams] = useSearchParams()
  const focusNode = searchParams.get('focus')

  const [graphData, setGraphData] = useState<{
    nodes: GraphNode[]
    edges: Array<{ s: string; d: string; kind: string; layer: string; inter?: boolean }>
  } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [active, setActive] = useState({ L1: true, L3: true, L4: true })

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        setLoading(true)
        const data = await client.getSubgraph(focusNode || undefined, 2)
        const typedData = {
          nodes: data.nodes as GraphNode[],
          edges: data.edges as Array<{ s: string; d: string; kind: string; layer: string; inter?: boolean }>,
        }
        setGraphData(typedData)
        setError(null)
      } catch (err) {
        if (err instanceof MockFallback) {
          // Use mock data
          const typedMock = {
            nodes: MOCK_SUBGRAPH.nodes as GraphNode[],
            edges: MOCK_SUBGRAPH.edges as Array<{ s: string; d: string; kind: string; layer: string; inter?: boolean }>,
          }
          setGraphData(typedMock)
          setError(null)
        } else {
          setError(err instanceof Error ? err.message : 'Failed to fetch graph data')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchGraph()
  }, [focusNode])

  if (loading) {
    return (
      <div className="graph-page">
        <div className="graph-loading">
          <p>Loading graph...</p>
        </div>
      </div>
    )
  }

  if (error || !graphData) {
    return (
      <div className="graph-page">
        <div className="graph-error">
          <p>{error || 'Failed to load graph'}</p>
          <small>Using mock data fallback</small>
        </div>
      </div>
    )
  }

  const visibleNodes: GraphNode[] = graphData.nodes.filter((n) =>
    active[n.layer as 'L1' | 'L3' | 'L4']
  )
  const activeNodeIds = new Set(visibleNodes.map((n) => n.id))
  const visibleEdges = graphData.edges.filter(
    (e) => activeNodeIds.has(e.s) && activeNodeIds.has(e.d)
  )

  const stats = {
    L1: visibleNodes.filter((n) => n.layer === 'L1').length,
    L3: visibleNodes.filter((n) => n.layer === 'L3').length,
    L4: visibleNodes.filter((n) => n.layer === 'L4').length,
  }

  return (
    <div className="graph-page">
      {/* HUD: Layer toggles */}
      <div className="graph-hud">
        <div className="hud-layers">
          <label className="layer-toggle">
            <input
              type="checkbox"
              checked={active.L1}
              onChange={(e) => setActive((a) => ({ ...a, L1: e.target.checked }))}
            />
            <span className="layer-dot l1" />
            <span>L1 Sources ({stats.L1})</span>
          </label>
          <label className="layer-toggle">
            <input
              type="checkbox"
              checked={active.L3}
              onChange={(e) => setActive((a) => ({ ...a, L3: e.target.checked }))}
            />
            <span className="layer-dot l3" />
            <span>L3 Cards ({stats.L3})</span>
          </label>
          <label className="layer-toggle">
            <input
              type="checkbox"
              checked={active.L4}
              onChange={(e) => setActive((a) => ({ ...a, L4: e.target.checked }))}
            />
            <span className="layer-dot l4" />
            <span>L4 Domains ({stats.L4})</span>
          </label>
        </div>

        {/* Stats */}
        <div className="hud-stats">
          <div className="stat">
            <span className="label">Nodes:</span>
            <span className="value">{visibleNodes.length}</span>
          </div>
          <div className="stat">
            <span className="label">Edges:</span>
            <span className="value">{visibleEdges.length}</span>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div className="graph-canvas-wrapper">
        <IsoGraph
          nodes={visibleNodes}
          edges={visibleEdges as any}
          active={active}
          onNodeClick={setSelectedNode}
        />

        {/* Help text */}
        <div className="graph-help">
          <p>
            Drag to rotate · Scroll to zoom · Click a node to inspect
          </p>
          <p className="help-secondary">
            Vertical beams show provenance: source → card → domain
          </p>
        </div>
      </div>

      {/* Inspector panel */}
      {selectedNode && (
        <div className="graph-inspector">
          <div className="inspector-header">
            <h3>{selectedNode.label}</h3>
            <span className={`layer-tag ${selectedNode.layer.toLowerCase()}`}>
              {selectedNode.layer}
            </span>
          </div>

          <div className="inspector-content">
            <div className="section">
              <h4>Node ID</h4>
              <code className="node-id">{selectedNode.id}</code>
            </div>

            <div className="section">
              <h4>Layer</h4>
              <p>
                {selectedNode.layer === 'L1'
                  ? 'Source code (functions, classes, modules)'
                  : selectedNode.layer === 'L3'
                    ? 'Knowledge cards (specs, summaries)'
                    : 'Domains (clusters, concepts)'}
              </p>
            </div>

            <div className="section">
              <h4>Position</h4>
              <p className="position">
                X: {selectedNode._x.toFixed(1)} | Y: {selectedNode._y.toFixed(1)} | Z:{' '}
                {selectedNode._z.toFixed(1)}
              </p>
            </div>

            <div className="section actions">
              <button className="action-btn">Ask about this</button>
              <button className="action-btn secondary">Open card</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
