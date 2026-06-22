import { useState } from 'react'
import './AddSourceForm.css'

interface AddSourceFormProps {
  onAdd: (data: { type: 'code' | 'pdf'; url?: string; file?: File }) => Promise<void>
  onCancel: () => void
  isLoading: boolean
  error?: Error | null
}

export default function AddSourceForm({
  onAdd,
  onCancel,
  isLoading,
  error,
}: AddSourceFormProps) {
  const [type, setType] = useState<'code' | 'pdf'>('code')
  const [url, setUrl] = useState('')
  const [file, setFile] = useState<File | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (type === 'code' && url) {
      await onAdd({ type: 'code', url })
    } else if (type === 'pdf' && file) {
      await onAdd({ type: 'pdf', file })
    }
  }

  const isValid = type === 'code' ? !!url : !!file

  return (
    <form onSubmit={handleSubmit} className="add-source-form">
      <div className="form-group">
        <label htmlFor="source-type">Source type:</label>
        <select
          id="source-type"
          value={type}
          onChange={(e) => {
            setType(e.target.value as 'code' | 'pdf')
            setUrl('')
            setFile(null)
          }}
        >
          <option value="code">Git repository</option>
          <option value="pdf">PDF file</option>
        </select>
      </div>

      {type === 'code' && (
        <div className="form-group">
          <label htmlFor="repo-url">Repository URL:</label>
          <input
            id="repo-url"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/user/repo"
            required
            disabled={isLoading}
          />
        </div>
      )}

      {type === 'pdf' && (
        <div className="form-group">
          <label htmlFor="pdf-file">PDF file:</label>
          <input
            id="pdf-file"
            type="file"
            accept=".pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            required
            disabled={isLoading}
          />
        </div>
      )}

      {error && <div className="form-error">{error.message}</div>}

      <div className="form-actions">
        <button type="submit" disabled={!isValid || isLoading} className="btn-submit">
          {isLoading ? 'Adding...' : 'Add source'}
        </button>
        <button type="button" onClick={onCancel} disabled={isLoading} className="btn-cancel">
          Cancel
        </button>
      </div>
    </form>
  )
}
