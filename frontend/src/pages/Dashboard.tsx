import { useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { GitBranch, MessageSquare, FileText, Plug } from 'lucide-react'
import { useSources } from '../lib/hooks'
import { OmniIngest } from '../components/ingest/OmniIngest'
import { SourceCard } from '../components/sources/SourceCard'
import './Dashboard.css'

export function Dashboard() {
  const navigate = useNavigate()
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

      {/* How It Works */}
      <section className="how-it-works">
        <div className="how-container">
          <h2>How it works</h2>
          <div className="feature-grid">
            <div className="feature-block">
              <div className="feature-num">1</div>
              <h3>Understand section by section</h3>
              <p>Comprehensive analysis of code and documents with intelligent parsing.</p>
            </div>
            <div className="feature-block">
              <div className="feature-num">2</div>
              <h3>Generated automatically</h3>
              <p>LLM reads your code and docs, generates knowledge cards with zero manual work.</p>
            </div>
            <div className="feature-block">
              <div className="feature-num">3</div>
              <h3>Always up-to-date</h3>
              <p>Drift detection flags stale cards when code changes, keeping knowledge fresh.</p>
            </div>
            <div className="feature-block">
              <div className="feature-num">4</div>
              <h3>Linked back to source</h3>
              <p>Every claim cites file:line, page number, or spreadsheet cell for provenance.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Capabilities */}
      <section className="capabilities">
        <div className="caps-container">
          <h2>Capabilities</h2>
          <div className="caps-grid">
            <button className="cap-tile" onClick={() => navigate('/graph')}>
              <div className="cap-icon"><GitBranch size={22} /></div>
              <h3>Knowledge Graph</h3>
              <p>Explore domains, specs, and relationships in 3D.</p>
            </button>
            <button className="cap-tile" onClick={() => navigate('/ask')}>
              <div className="cap-icon"><MessageSquare size={22} /></div>
              <h3>Ask Atlas</h3>
              <p>Ask questions. Get grounded answers with citations.</p>
            </button>
            <button className="cap-tile" onClick={() => navigate('/specify')}>
              <div className="cap-icon"><FileText size={22} /></div>
              <h3>Specify</h3>
              <p>Generate knowledge cards for any entity with one click.</p>
            </button>
            <button className="cap-tile" onClick={() => navigate('/mcp')}>
              <div className="cap-icon"><Plug size={22} /></div>
              <h3>MCP Server</h3>
              <p>Integration point for your CI/CD and IDE tools.</p>
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}

export default Dashboard
