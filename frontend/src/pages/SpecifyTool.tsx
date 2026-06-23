import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { Loader } from 'lucide-react'
import { TopBar } from '../components/layout/TopBar'
import { Sidebar } from '../components/layout/Sidebar'
import './SpecifyTool.css'

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
  interconnections?: string[]
}

export function SpecifyTool() {
  const { repoId = 'default' } = useParams<{ repoId: string }>()
  const [searchParams] = useSearchParams()
  const projectId = searchParams.get('project') || repoId
  const [componentRef, setComponentRef] = useState('')
  const [generatedSpec, setGeneratedSpec] = useState<SpecResponse | null>(null)
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState('')

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

              {generatedSpec.interconnections && generatedSpec.interconnections.length > 0 && (
                <div className="spec-interconnections">
                  <h3>Interconnections</h3>
                  <p>{generatedSpec.interconnections.join(', ')}</p>
                </div>
              )}

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
    </div>
  )
}

export default SpecifyTool
