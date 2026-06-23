import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { GraphCanvas3D } from '../components/graph/GraphCanvas3D'
import { Inspector } from '../components/graph/Inspector'
import { useLayeredGraph } from '../api/useGraph'
import { useSources } from '../lib/hooks'
import type { LayeredGraphNode } from '../api/client'
import './Graph.css'

export default function Graph() {
  const [searchParams] = useSearchParams()
  const focusNode = searchParams.get('focus')

  const { data: sources = [], isLoading: sourcesLoading } = useSources()
  const repos = useMemo(() => sources.filter((s) => s.type === 'repo'), [sources])
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null)

  // Default to the first indexed repo once sources load.
  useEffect(() => {
    if (!selectedRepo && repos.length > 0) {
      setSelectedRepo(repos[0].name)
    }
  }, [repos, selectedRepo])

  const { data: graphData, isLoading: graphLoading, error } = useLayeredGraph(selectedRepo ?? undefined)

  const [selectedNode, setSelectedNode] = useState<LayeredGraphNode | null>(null)
  const [active, setActive] = useState({ L1: true, L3: true, L4: true })

  // Select the node passed via ?focus= once the graph data is in.
  useEffect(() => {
    if (focusNode && graphData) {
      const match = graphData.nodes.find(
        (n) => n.id === focusNode || n.qualified_name === focusNode
      )
      if (match) setSelectedNode(match)
    }
  }, [focusNode, graphData])

  if (sourcesLoading || (selectedRepo && graphLoading)) {
    return (
      <div className="graph-page graph-page--loading">
        <p>Loading graph…</p>
      </div>
    )
  }

  if (repos.length === 0) {
    return (
      <div className="graph-page graph-page--error">
        <p>No indexed repositories yet.</p>
        <small>Index a repository from the Dashboard to explore its graph.</small>
      </div>
    )
  }

  if (error || !graphData) {
    return (
      <div className="graph-page graph-page--error">
        <p>{error instanceof Error ? error.message : 'Failed to load graph'}</p>
        <small>Backend unavailable — check VITE_API_URL</small>
      </div>
    )
  }

  const visibleNodes = graphData.nodes.filter((n) => active[n.layer])
  const visibleNodeIds = new Set(visibleNodes.map((n) => n.id))
  const visibleEdges = graphData.edges.filter(
    (e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)
  )

  const countL1 = visibleNodes.filter((n) => n.layer === 'L1').length
  const countL3 = visibleNodes.filter((n) => n.layer === 'L3').length
  const countL4 = visibleNodes.filter((n) => n.layer === 'L4').length

  return (
    <div className="graph-page">
      <div className="graph-canvas-area">
        <div className="graph-hud">
          {repos.length > 1 && (
            <select
              className="layer-toggle"
              value={selectedRepo ?? ''}
              onChange={(e) => setSelectedRepo(e.target.value)}
              aria-label="Select repository"
            >
              {repos.map((r) => (
                <option key={r.id} value={r.name}>
                  {r.name}
                </option>
              ))}
            </select>
          )}
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

        <GraphCanvas3D
          nodes={visibleNodes}
          edges={visibleEdges}
          selectedNodeId={selectedNode?.id}
          onSelectNode={setSelectedNode}
        />

        <div className="graph-help" aria-hidden="true">
          <p>Drag to rotate · Scroll to zoom · Click a node to inspect</p>
          <p className="graph-help-secondary">
            Cross-layer beams show provenance: source → card → domain
          </p>
        </div>
      </div>

      <Inspector
        node={selectedNode}
        allNodes={visibleNodes}
        allEdges={visibleEdges}
        onSelectNode={setSelectedNode}
      />
    </div>
  )
}
