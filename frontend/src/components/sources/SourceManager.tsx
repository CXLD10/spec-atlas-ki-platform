import { useState } from 'react'
import { useSources, useAddSource } from '../../api/useSources'
import SourceList from './SourceList'
import AddSourceForm from './AddSourceForm'
import './SourceManager.css'

interface SourceManagerProps {
  projectId: string
}

export default function SourceManager({ projectId }: SourceManagerProps) {
  const [showForm, setShowForm] = useState(false)
  const { data: sources, isLoading, error } = useSources(projectId)
  const addSource = useAddSource(projectId)

  const handleAddSource = async (data: {
    type: 'code' | 'pdf'
    url?: string
    file?: File
  }) => {
    try {
      await addSource.mutateAsync(data)
      setShowForm(false)
    } catch (err) {
      console.error('Failed to add source:', err)
    }
  }

  return (
    <div className="source-manager">
      <div className="source-header">
        <h2>Sources</h2>
        {!showForm && (
          <button
            className="btn-add-source"
            onClick={() => setShowForm(true)}
            disabled={isLoading}
          >
            + Add source
          </button>
        )}
      </div>

      {error && (
        <div className="error-message">Failed to load sources: {error.message}</div>
      )}

      {isLoading && <p className="loading-text">Loading sources...</p>}

      {sources && sources.length > 0 && <SourceList sources={sources} />}

      {sources && sources.length === 0 && !showForm && (
        <p className="no-sources">No sources yet. Add one to get started.</p>
      )}

      {showForm && (
        <AddSourceForm
          onAdd={handleAddSource}
          onCancel={() => setShowForm(false)}
          isLoading={addSource.isPending}
          error={addSource.error}
        />
      )}
    </div>
  )
}
