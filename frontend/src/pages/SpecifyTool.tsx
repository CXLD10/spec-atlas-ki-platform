import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { ChevronDown, ChevronRight, FileText, Package, Loader } from 'lucide-react'
import { TopBar } from '../components/layout/TopBar'
import { Sidebar } from '../components/layout/Sidebar'
import './SpecifyTool.css'

interface SpecNode {
  id: string
  name: string
  component_ref: string
  kind: 'module' | 'class' | 'function' | 'spec'
  children?: SpecNode[]
  status?: 'draft' | 'review' | 'approved'
}

interface SpecResponse {
  component_ref: string
  status: string
  version: number
  confidence?: number
  markdown?: string
  content?: { markdown: string }
  answer?: string
  issues?: Array<{ reason: string; severity?: string; message?: string }>
  claims?: Array<{ source: string; claim: string }>
}

export function SpecifyTool() {
  const { repoId = 'default' } = useParams<{ repoId: string }>()
  const [searchParams] = useSearchParams()
  const projectId = searchParams.get('project') || repoId
  const navigate = useNavigate()
  const [specs, setSpecs] = useState<SpecNode[]>([])
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
  const [selectedSpec, setSelectedSpec] = useState<SpecNode | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [componentRef, setComponentRef] = useState('')
  const [generatedSpec, setGeneratedSpec] = useState<SpecResponse | null>(null)
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState('')

  // Fetch graph nodes to build spec tree
  useEffect(() => {
    const fetchSpecs = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/graph/nodes?limit=1000')
        if (!response.ok) throw new Error('Failed to fetch nodes')

        const nodes = await response.json()

        // Build tree structure from nodes
        const tree = buildSpecTree(nodes)
        setSpecs(tree)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchSpecs()
  }, [repoId])

  const buildSpecTree = (nodes: any[]): SpecNode[] => {
    // Group nodes by file path to create a hierarchical tree
    const tree: SpecNode[] = []
    const nodeMap = new Map<string, SpecNode>()

    // Create spec nodes from graph nodes
    nodes.forEach((node) => {
      const specNode: SpecNode = {
        id: node.id,
        name: node.label || node.name,
        component_ref: node.id,
        kind: (node.kind || 'function') as any,
        children: [],
      }
      nodeMap.set(node.id, specNode)
    })

    // Group by file
    const byFile = new Map<string, SpecNode[]>()
    nodes.forEach((node) => {
      const file = node.file_path || 'root'
      if (!byFile.has(file)) byFile.set(file, [])
      const specNode = nodeMap.get(node.id)
      if (specNode) byFile.get(file)!.push(specNode)
    })

    // Create file structure
    byFile.forEach((nodeList, file) => {
      const fileNode: SpecNode = {
        id: file,
        name: file.split('/').pop() || file,
        component_ref: file,
        kind: 'module',
        children: nodeList,
      }
      tree.push(fileNode)
    })

    return tree.sort((a, b) => a.name.localeCompare(b.name))
  }

  const toggleNode = (nodeId: string) => {
    const newExpanded = new Set(expandedNodes)
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId)
    } else {
      newExpanded.add(nodeId)
    }
    setExpandedNodes(newExpanded)
  }

  const handleGenerateSpec = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!projectId || !componentRef) {
      setGenError('Please enter project ID and component name')
      return
    }

    setGenerating(true)
    setGenError('')
    setGeneratedSpec(null)

    try {
      const response = await fetch(
        `/api/specify/${encodeURIComponent(componentRef)}?project_id=${projectId}`,
        { method: 'POST' }
      )

      if (!response.ok) {
        throw new Error(`Failed to generate spec: ${response.statusText}`)
      }

      const data = await response.json()
      setGeneratedSpec(data)
    } catch (err) {
      setGenError(err instanceof Error ? err.message : 'Failed to generate spec')
    } finally {
      setGenerating(false)
    }
  }

  const TreeNode = ({ node, level = 0 }: { node: SpecNode; level?: number }) => {
    const isExpanded = expandedNodes.has(node.id)
    const hasChildren = node.children && node.children.length > 0
    const isSelected = selectedSpec?.id === node.id

    return (
      <div key={node.id}>
        <div
          className={`tree-node ${isSelected ? 'selected' : ''}`}
          style={{ paddingLeft: `${level * 24}px` }}
          onClick={() => {
            setSelectedSpec(node)
            if (hasChildren) toggleNode(node.id)
          }}
        >
          {hasChildren ? (
            <button
              className="tree-toggle"
              onClick={(e) => {
                e.stopPropagation()
                toggleNode(node.id)
              }}
            >
              {isExpanded ? (
                <ChevronDown size={16} />
              ) : (
                <ChevronRight size={16} />
              )}
            </button>
          ) : (
            <div className="tree-toggle-placeholder" />
          )}

          <div className="tree-node-icon">
            {node.kind === 'module' ? (
              <Package size={16} />
            ) : (
              <FileText size={16} />
            )}
          </div>

          <span className="tree-node-label">{node.name}</span>

          {node.status && (
            <span className={`tree-node-badge status-${node.status}`}>
              {node.status}
            </span>
          )}
        </div>

        {hasChildren && isExpanded && (
          <div className="tree-children">
            {node.children!.map((child) => (
              <TreeNode key={child.id} node={child} level={level + 1} />
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="specify-tool-page-wrapper">
      <Sidebar />
      <div className="specify-tool-page">
        <TopBar variant="default" />

        <div className="specify-page-content">
          <h1>Specify Tool</h1>
          <p className="page-subtitle">
            Auto-generate specifications for code components
          </p>

          {/* Spec Generation Form */}
          <form onSubmit={handleGenerateSpec} className="specify-form">
            <div className="form-group">
              <label htmlFor="project-id">Project ID</label>
              <input
                id="project-id"
                type="text"
                placeholder="UUID of your project"
                value={projectId || ''}
                disabled={!!projectId}
                onChange={() => {}}
                required
              />
              <small>From the URL query parameter</small>
            </div>

            <div className="form-group">
              <label htmlFor="component">Component Name</label>
              <input
                id="component"
                type="text"
                placeholder="e.g., fetch_sources, ParseEngine"
                value={componentRef}
                onChange={(e) => setComponentRef(e.target.value)}
                required
              />
              <small>Function, class, or module name</small>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={generating || !projectId || !componentRef}
            >
              {generating ? (
                <>
                  <Loader size={18} className="spinner" />
                  Generating...
                </>
              ) : (
                'Generate Spec'
              )}
            </button>
          </form>

          {genError && <div className="error-message">{genError}</div>}

          {generatedSpec && (
            <div className="spec-viewer">
              <div className="spec-header">
                <h2>{generatedSpec.component_ref}</h2>
                <div className="spec-meta">
                  <span
                    className={`status status-${
                      generatedSpec.status || 'draft'
                    }`.toLowerCase()}
                  >
                    {(generatedSpec.status || 'draft').toUpperCase()}
                  </span>
                  <span className="version">
                    v{generatedSpec.version || 1}
                  </span>
                  {generatedSpec.confidence !== undefined && (
                    <span className="confidence">
                      {(generatedSpec.confidence * 100).toFixed(0)}% confident
                    </span>
                  )}
                </div>
              </div>

              <div className="spec-content">
                {generatedSpec.markdown ||
                  generatedSpec.content?.markdown ||
                  generatedSpec.answer ||
                  'No spec generated'}
              </div>

              {generatedSpec.issues && generatedSpec.issues.length > 0 && (
                <div className="spec-issues">
                  <h3>⚠️ Issues Found</h3>
                  <ul>
                    {generatedSpec.issues.map((issue, idx) => (
                      <li key={idx}>
                        <strong>{issue.reason || issue.message}</strong>
                        {issue.severity && ` (${issue.severity})`}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Existing spec browser */}
      <div className="specify-tool-page-old">
        <div className="specify-tool-container">
        {/* Left sidebar: Specs tree */}
        <div className="specs-tree-sidebar">
          <div className="sidebar-header">
            <h2>Specifications</h2>
            <p className="sidebar-subtitle">Browse all specs in your codebase</p>
          </div>

          <div className="specs-tree">
            {loading && <div className="loading-state">Loading specs...</div>}

            {error && (
              <div className="error-state">
                <p>Error: {error}</p>
              </div>
            )}

            {!loading && !error && specs.length === 0 && (
              <div className="empty-state">
                <p>No specs found. Start by indexing a repository.</p>
              </div>
            )}

            {!loading && !error && specs.length > 0 && (
              <div className="tree-root">
                {specs.map((node) => (
                  <TreeNode key={node.id} node={node} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right side: Spec details or empty state */}
        <div className="spec-detail-panel">
          {!selectedSpec && (
            <div className="detail-empty-state">
              <p>Select a spec from the tree to view details</p>
            </div>
          )}

          {selectedSpec && (
            <div className="spec-detail-content">
              <div className="detail-header">
                <h3>{selectedSpec.name}</h3>
                <p className="detail-ref">{selectedSpec.component_ref}</p>
              </div>

              <div className="detail-meta">
                <div className="meta-item">
                  <span className="label">Kind:</span>
                  <span className="value">{selectedSpec.kind}</span>
                </div>
                {selectedSpec.status && (
                  <div className="meta-item">
                    <span className="label">Status:</span>
                    <span className={`value status-${selectedSpec.status}`}>
                      {selectedSpec.status}
                    </span>
                  </div>
                )}
              </div>

              <div className="detail-actions">
                <button
                  className="btn-primary"
                  onClick={() =>
                    navigate(`/repo/${repoId}/specify/${selectedSpec.component_ref}`)
                  }
                >
                  View Full Spec
                </button>
                <button className="btn-secondary" onClick={() => setSelectedSpec(null)}>
                  Clear Selection
                </button>
              </div>

              {selectedSpec.children && selectedSpec.children.length > 0 && (
                <div className="detail-children">
                  <h4>Child Components</h4>
                  <ul>
                    {selectedSpec.children.map((child) => (
                      <li
                        key={child.id}
                        onClick={() => setSelectedSpec(child)}
                        className="child-item"
                      >
                        {child.name}
                        <span className="child-kind">{child.kind}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
        </div>
      </div>
    </div>
  )
}

export default SpecifyTool
