import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Loader } from 'lucide-react'
import { TopBar } from '../components/layout/TopBar'
import { Sidebar } from '../components/layout/Sidebar'
import { client } from '../api/client'
import './Projects.css'

interface FormData {
  name: string
  repoUrl: string
  pdfFile: File | null
  excelFile: File | null
  markdownFile: File | null
}

export default function Projects() {
  const navigate = useNavigate()
  const [showCreate, setShowCreate] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [formData, setFormData] = useState<FormData>({
    name: '',
    repoUrl: '',
    pdfFile: null,
    excelFile: null,
    markdownFile: null,
  })

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!formData.name.trim()) {
      setError('Project name is required')
      return
    }

    if (!formData.repoUrl && !formData.pdfFile && !formData.excelFile && !formData.markdownFile) {
      setError('Please provide at least one source (repository URL or file)')
      return
    }

    setIsLoading(true)

    try {
      // For now, we'll use the default project ID
      // In a full implementation, this would create a new project
      const projectId = 'default'

      // Ingest code repo if provided
      if (formData.repoUrl) {
        try {
          await client.addCodeSource(projectId, formData.repoUrl)
        } catch (err) {
          console.error('Failed to ingest repo:', err)
          // Continue with other sources even if repo fails
        }
      }

      // Ingest PDF if provided
      if (formData.pdfFile) {
        try {
          await client.uploadPDFSource(projectId, formData.pdfFile)
        } catch (err) {
          console.error('Failed to ingest PDF:', err)
        }
      }

      // TODO: Ingest Excel file when API endpoint is available
      if (formData.excelFile) {
        console.log('Excel upload not yet implemented')
      }

      // TODO: Ingest Markdown file when API endpoint is available
      if (formData.markdownFile) {
        console.log('Markdown upload not yet implemented')
      }

      // Navigate to ask page
      navigate(`/repo/${projectId}/ask`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    fileType: 'pdfFile' | 'excelFile' | 'markdownFile'
  ) => {
    const file = e.target.files?.[0] || null
    setFormData((prev) => ({
      ...prev,
      [fileType]: file,
    }))
  }

  return (
    <div className="projects-page-container">
      <Sidebar />
      <div className="projects-main">
        <TopBar variant="default" />
        <div className="projects-content">
          <div className="projects-header">
            <h1>Projects</h1>
            <button
              className="btn btn-primary"
              onClick={() => setShowCreate(!showCreate)}
            >
              <Plus size={18} />
              Create New Project
            </button>
          </div>

          {showCreate && (
            <div className="create-form-container">
              <form onSubmit={handleCreateProject} className="create-form">
                <h2>Create New Project</h2>

                <div className="form-group">
                  <label htmlFor="project-name">Project Name *</label>
                  <input
                    id="project-name"
                    type="text"
                    placeholder="My Project"
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    className="form-input"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="repo-url">Code Repository URL</label>
                  <input
                    id="repo-url"
                    type="url"
                    placeholder="https://github.com/user/repo"
                    value={formData.repoUrl}
                    onChange={(e) =>
                      setFormData({ ...formData, repoUrl: e.target.value })
                    }
                    className="form-input"
                  />
                  <small className="form-hint">
                    Supports GitHub, GitLab, Gitea, Codeberg
                  </small>
                </div>

                <div className="form-group">
                  <label htmlFor="pdf-file">PDF Document</label>
                  <input
                    id="pdf-file"
                    type="file"
                    accept=".pdf"
                    onChange={(e) => handleFileChange(e, 'pdfFile')}
                    className="form-input"
                  />
                  {formData.pdfFile && (
                    <small className="form-hint">
                      ✓ {formData.pdfFile.name}
                    </small>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="excel-file">Excel Spreadsheet</label>
                  <input
                    id="excel-file"
                    type="file"
                    accept=".xlsx"
                    onChange={(e) => handleFileChange(e, 'excelFile')}
                    className="form-input"
                  />
                  {formData.excelFile && (
                    <small className="form-hint">
                      ✓ {formData.excelFile.name}
                    </small>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="markdown-file">Markdown Document</label>
                  <input
                    id="markdown-file"
                    type="file"
                    accept=".md"
                    onChange={(e) => handleFileChange(e, 'markdownFile')}
                    className="form-input"
                  />
                  {formData.markdownFile && (
                    <small className="form-hint">
                      ✓ {formData.markdownFile.name}
                    </small>
                  )}
                </div>

                {error && <div className="form-error">{error}</div>}

                <div className="form-actions">
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <>
                        <Loader size={18} className="spinner" />
                        Creating...
                      </>
                    ) : (
                      'Create & Ingest'
                    )}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      setShowCreate(false)
                      setFormData({
                        name: '',
                        repoUrl: '',
                        pdfFile: null,
                        excelFile: null,
                        markdownFile: null,
                      })
                      setError('')
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          <div className="projects-info">
            <p>
              Create a new project and ingest code repositories, PDFs, spreadsheets, and
              documentation to build your knowledge graph.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
