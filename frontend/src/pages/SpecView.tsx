import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Copy, Check } from 'lucide-react'
import { TopBar } from '../components/layout/TopBar'
import { client, type GeneratedSpec } from '../api/client'
import './SpecView.css'

export function SpecView() {
  const { repoId = 'default', specId } = useParams<{ repoId: string; specId: string }>()
  const navigate = useNavigate()
  const [spec, setSpec] = useState<GeneratedSpec | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  useEffect(() => {
    const fetchSpec = async () => {
      if (!specId) {
        setError('No spec ID provided')
        setLoading(false)
        return
      }

      try {
        const data = await client.getGeneratedSpec(repoId || 'default', specId)
        setSpec(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load spec')
      } finally {
        setLoading(false)
      }
    }

    fetchSpec()
  }, [repoId, specId])

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(spec?.spec_id || 'copy')
    setTimeout(() => setCopiedId(null), 2000)
  }

  const renderMarkdown = (markdown: string) => {
    // Escape HTML entities first to prevent XSS, then apply markdown transforms
    const escaped = markdown
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
    let html = escaped
      .replace(/^### (.*?)$/gm, '<h3>$1</h3>')
      .replace(/^## (.*?)$/gm, '<h2>$1</h2>')
      .replace(/^# (.*?)$/gm, '<h1>$1</h1>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/\n\n/g, '</p><p>')
      .split('\n')
      .join('<br/>')


    return <div className="markdown-content" dangerouslySetInnerHTML={{ __html: html }} />
  }

  return (
    <div className="spec-view-page">
      <TopBar variant="workspace" />

      <div className="spec-view-container">
        {/* Header with back button */}
        <div className="spec-view-header">
          <button className="back-button" onClick={() => navigate(`/repo/${repoId}/specify`)}>
            <ArrowLeft size={20} />
            Back to Specifications
          </button>
        </div>

        {/* Content */}
        <div className="spec-view-content">
          {loading && <div className="loading-state">Loading specification...</div>}

          {error && (
            <div className="error-state">
              <p>Error: {error}</p>
              <button onClick={() => navigate(`/repo/${repoId}/specify`)}>Back to Specs</button>
            </div>
          )}

          {spec && (
            <>
              {/* Spec Metadata */}
              <div className="spec-metadata">
                <div className="metadata-main">
                  <div className="spec-title">
                    <h1>{spec.content?.split('\n')[0].replace(/^#+\s*/, '') || 'Specification'}</h1>
                  </div>

                  <div className="spec-details">
                    <div className="detail-item">
                      <span className="label">Spec ID:</span>
                      <span className="value code">{spec.spec_id}</span>
                    </div>

                    <div className="detail-item">
                      <span className="label">Node ID:</span>
                      <span className="value code">{spec.node_id}</span>
                    </div>

                    <div className="detail-item">
                      <span className="label">Version:</span>
                      <span className="value">{spec.version}</span>
                    </div>

                    {spec.status && (
                      <div className="detail-item">
                        <span className="label">Status:</span>
                        <span className={`value status status-${spec.status}`}>{spec.status}</span>
                      </div>
                    )}

                    {spec.created_at && (
                      <div className="detail-item">
                        <span className="label">Created:</span>
                        <span className="value">{new Date(spec.created_at).toLocaleDateString()}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="metadata-actions">
                  <button
                    className="copy-button"
                    onClick={() => copyToClipboard(spec.content)}
                    title="Copy spec content"
                  >
                    {copiedId === spec.spec_id ? (
                      <>
                        <Check size={16} /> Copied
                      </>
                    ) : (
                      <>
                        <Copy size={16} /> Copy Content
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Spec Content */}
              <div className="spec-body">{renderMarkdown(spec.content)}</div>

              {/* Citations */}
              {spec.citations && spec.citations.length > 0 && (
                <div className="spec-citations">
                  <h3>Citations</h3>
                  <div className="citations-list">
                    {spec.citations.map((citation, idx) => (
                      <div key={idx} className="citation-item">
                        <span className="citation-file">{citation.file}</span>
                        <span className="citation-range">
                          lines {citation.start_line}–{citation.end_line}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default SpecView
