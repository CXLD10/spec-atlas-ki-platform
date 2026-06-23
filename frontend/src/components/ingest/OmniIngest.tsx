import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { GitBranch, Paperclip, X } from 'lucide-react'
import { useIngestRepo, useUploadDocument } from '../../lib/hooks'
import './OmniIngest.css'

const REPO_REGEX = /^https?:\/\/(github\.com|gitlab\.com|gitea\.|codeberg\.org)\/\S+$/
const ALLOWED_TYPES = ['.pdf', '.xlsx', '.xls', '.md', '.markdown']

export function OmniIngest() {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [url, setUrl] = useState('')
  const [stagingFile, setStagingFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [urlError, setUrlError] = useState('')

  const { mutate: ingestRepo, isPending: isIngestingRepo } = useIngestRepo()
  const { mutate: uploadDocument, isPending: isUploading } = useUploadDocument()

  const isValidUrl = url.trim() && REPO_REGEX.test(url.trim())
  const isUrl = url.trim().length > 0
  const isLoading = isIngestingRepo || isUploading

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setUrl(val)
    const isValid = val.trim() && REPO_REGEX.test(val.trim())
    if (val && !isValid) {
      setUrlError('Invalid repo URL. Use GitHub, GitLab, Gitea, or Codeberg.')
    } else {
      setUrlError('')
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = () => {
    setDragOver(false)
  }

  const stageFile = (file: File) => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!ALLOWED_TYPES.includes(ext)) {
      setUrlError(`Only PDF, XLSX, and Markdown files allowed. Got ${ext}`)
      return
    }
    setStagingFile(file)
    setUrl('')
    setUrlError('')
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const files = Array.from(e.dataTransfer.files)
    const file = files[0]
    if (file) {
      stageFile(file)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.currentTarget.files
    if (files?.[0]) {
      stageFile(files[0])
    }
  }

  const handleRemoveFile = () => {
    setStagingFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setUrlError('')

    if (stagingFile) {
      uploadDocument(stagingFile, {
        onSuccess: (job) => {
          navigate(`/index/${job.job_id}`)
        },
        onError: (err) => {
          setUrlError(err instanceof Error ? err.message : 'Document upload failed')
        },
      })
    } else if (isValidUrl) {
      ingestRepo(url.trim(), {
        onSuccess: (job) => {
          navigate(`/index/${job.job_id}`)
        },
        onError: (err) => {
          setUrlError(err instanceof Error ? err.message : 'Repository ingest failed')
        },
      })
    }
  }

  const ctaLabel = stagingFile
    ? 'Ingest document'
    : isUrl
      ? 'Index repository'
      : 'Index or ingest'

  return (
    <form onSubmit={handleSubmit} className="omni-ingest">
      <div
        className={`ingest-field ${dragOver ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {!stagingFile ? (
          <>
            <GitBranch className="ingest-icon" size={20} />
            <input
              type="text"
              placeholder="Paste a repo URL — or drop a PDF, XLSX or Markdown file"
              value={url}
              onChange={handleUrlChange}
              disabled={isLoading}
              className="ingest-input"
              aria-label="Repository URL or file drop zone"
            />
            <button
              type="button"
              className="ingest-file-btn"
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              aria-label="Select a file"
              title="Select PDF, XLSX, or Markdown"
            >
              <Paperclip size={18} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept={ALLOWED_TYPES.join(',')}
              onChange={handleFileSelect}
              hidden
              aria-hidden="true"
            />
          </>
        ) : (
          <>
            <div className="file-chip">
              <span>{stagingFile.name}</span>
              <button
                type="button"
                onClick={handleRemoveFile}
                disabled={isLoading}
                className="file-chip-remove"
                aria-label="Remove file"
              >
                <X size={16} />
              </button>
            </div>
          </>
        )}
      </div>

      {urlError && (
        <div className="ingest-error" role="alert">
          {urlError}
        </div>
      )}

      <button
        type="submit"
        disabled={(!isValidUrl && !stagingFile) || isLoading}
        className="ingest-cta"
        aria-busy={isLoading}
      >
        {isLoading ? 'Processing...' : ctaLabel}
      </button>
    </form>
  )
}
