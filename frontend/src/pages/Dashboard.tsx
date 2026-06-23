import { useRef } from 'react'
import { useSources } from '../lib/hooks'
import { OmniIngest } from '../components/ingest/OmniIngest'
import { SourceCard } from '../components/sources/SourceCard'
import './Dashboard.css'

export function Dashboard() {
  const { data: sources = [] } = useSources()
  const omniBaRef = useRef<HTMLDivElement>(null)

  const stats = {
    entities: sources.reduce((sum, s) => sum + s.stats.entities, 0),
    cards: sources.reduce((sum, s) => sum + s.stats.cards, 0),
    domains: Math.ceil(sources.length * 0.3), // Mock: ~30% of sources become domains
  }

  const handleAddSource = () => {
    omniBaRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="dashboard">
      {/* Hero */}
      <section className="hero" ref={omniBaRef}>
        <div className="hero-glow" />
        <div className="hero-content">
          <div className="hero-eyebrow">Knowledge Intelligence</div>
          <h1 className="hero-title">
            Your engineering
            <span className="title-accent"> knowledge, understood.</span>
          </h1>
          <p className="hero-subtitle">
            Index any repository and ingest your PDFs, spreadsheets and docs into one referenced,
            queryable knowledge base.
          </p>

          <div className="omni-ingest-wrapper">
            <OmniIngest />
          </div>

          {/* Stats */}
          <div className="hero-stats">
            <div className="stat">
              <div className="stat-value">{stats.entities.toLocaleString()}</div>
              <div className="stat-label">Symbols &amp; Fragments</div>
            </div>
            <div className="stat">
              <div className="stat-value">{stats.cards.toLocaleString()}</div>
              <div className="stat-label">Knowledge Cards</div>
            </div>
            <div className="stat">
              <div className="stat-value">{stats.domains}</div>
              <div className="stat-label">Domains</div>
            </div>
            <div className="stat">
              <div className="stat-value">$0</div>
              <div className="stat-label">Cost · Local-first</div>
            </div>
          </div>
        </div>
      </section>

      {/* Your Sources */}
      <section className="sources-section">
        <div className="sources-container">
          <h2 className="sources-title">Your sources</h2>

          {sources.length === 0 ? (
            <div className="empty-state">
              <p>No sources yet. Upload a document or index a repository to get started.</p>
              <button className="empty-cta" onClick={handleAddSource}>
                Add your first source
              </button>
            </div>
          ) : (
            <div className="sources-grid">
              {sources.map(source => (
                <SourceCard key={source.id} source={source} />
              ))}
              <button className="source-card add-card" onClick={handleAddSource}>
                <div className="add-card-content">
                  <span className="add-icon">+</span>
                  <span>Add source</span>
                </div>
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}

export default Dashboard
