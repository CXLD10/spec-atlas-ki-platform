import { useState } from 'react'
import { useSources } from '../lib/hooks'
import { SourceCard } from '../components/sources/SourceCard'
import { OmniIngest } from '../components/ingest/OmniIngest'
import './Sources.css'

type Filter = 'all' | 'repo' | 'document'

export function Sources() {
  const { data: sources = [], isLoading, error } = useSources()
  const [filter, setFilter] = useState<Filter>('all')
  const [search, setSearch] = useState('')

  const filtered = sources.filter((s) => {
    const matchesFilter =
      filter === 'all' ||
      (filter === 'repo' && s.type === 'repo') ||
      (filter === 'document' && s.type === 'document')
    const matchesSearch =
      !search ||
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      (s.subtitle ?? '').toLowerCase().includes(search.toLowerCase())
    return matchesFilter && matchesSearch
  })

  return (
    <div className="sources-page">
      <div className="sources-page-header">
        <div>
          <h1 className="sources-page-title">Your sources</h1>
          <p className="sources-page-subtitle">
            Index repositories and ingest documents to build your knowledge base.
          </p>
        </div>
      </div>

      <div className="sources-ingest-bar">
        <OmniIngest />
      </div>

      <div className="sources-controls">
        <div className="filter-tabs">
          {(['all', 'repo', 'document'] as Filter[]).map((f) => (
            <button
              key={f}
              className={`filter-tab ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f === 'all' ? 'All' : f === 'repo' ? 'Repositories' : 'Documents'}
              <span className="filter-count">
                {f === 'all'
                  ? sources.length
                  : sources.filter((s) => s.type === f).length}
              </span>
            </button>
          ))}
        </div>

        <input
          type="search"
          placeholder="Search sources…"
          className="sources-search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search sources"
        />
      </div>

      {isLoading ? (
        <div className="sources-loading">Loading sources…</div>
      ) : error ? (
        <div className="sources-empty">
          Couldn't load sources: {error instanceof Error ? error.message : 'unknown error'}
        </div>
      ) : filtered.length === 0 ? (
        <div className="sources-empty">
          {search || filter !== 'all'
            ? 'No sources match your filter.'
            : 'No sources indexed yet. Add one above.'}
        </div>
      ) : (
        <div className="sources-grid">
          {filtered.map((source) => (
            <SourceCard key={source.id} source={source} />
          ))}
        </div>
      )}
    </div>
  )
}

export default Sources
