import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GitFork, ChevronDown, Code2, Zap, Database, Brain, Shield } from 'lucide-react'
import { TopBar } from '../components/layout/TopBar'
import './Landing.css'

interface RepoInput {
  url: string
  isValid: boolean
}

export function Landing() {
  const navigate = useNavigate()
  const [repo, setRepo] = useState<RepoInput>({ url: '', isValid: false })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const validateRepoUrl = (url: string): boolean => {
    if (!url.trim()) return false
    const patterns = [
      /^https:\/\/(www\.)?github\.com\/[\w-]+\/[\w.-]+\/?$/,
      /^https:\/\/(www\.)?gitlab\.com\/[\w-]+\/[\w.-]+\/?$/,
      /^https:\/\/(www\.)?gitea\.io\/[\w-]+\/[\w.-]+\/?$/,
      /^https:\/\/(www\.)?codeberg\.org\/[\w-]+\/[\w.-]+\/?$/,
    ]
    return patterns.some((p) => p.test(url))
  }

  const handleRepoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const url = e.target.value
    setRepo({
      url,
      isValid: validateRepoUrl(url),
    })
    setError('')
  }

  const handleIndexRepo = async () => {
    if (!repo.isValid) {
      setError('Please enter a valid HTTPS repository URL (e.g., https://github.com/user/repo)')
      return
    }

    setIsLoading(true)
    setError('')

    try {
      const response = await fetch('http://localhost:8000/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repo.url }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to start indexing')
      }

      const data = await response.json()
      navigate(`/index/${data.job_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && repo.isValid && !isLoading) {
      handleIndexRepo()
    }
  }

  return (
    <div className="landing-container">
      {/* Navigation */}
      <TopBar variant="marketing" />

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">
            Your Codebase,<br />
            <span className="hero-highlight">Understood</span>
          </h1>
          <p className="hero-subtitle">
            Index any GitHub, GitLab, Gitea, or Codeberg repository. Ask questions about your code
            and get grounded answers with exact source citations.
          </p>

          {/* Repo Input Card */}
          <div className="repo-input-card">
            <div className="input-group">
              <input
                type="text"
                placeholder="https://github.com/username/repo"
                value={repo.url}
                onChange={handleRepoChange}
                onKeyPress={handleKeyPress}
                className={`repo-input ${repo.isValid ? 'valid' : ''} ${error ? 'error' : ''}`}
                disabled={isLoading}
              />
            </div>

            {error && <div className="input-error">{error}</div>}

            <div className="input-actions">
              <button
                onClick={handleIndexRepo}
                disabled={!repo.isValid || isLoading}
                className="btn-primary"
              >
                {isLoading ? 'Indexing...' : 'Index Repository'}
              </button>
              <span className="input-hint">Takes 2-5 minutes for typical repositories</span>
            </div>
          </div>
        </div>

        {/* Scroll Indicator */}
        <div className="scroll-indicator">
          <ChevronDown size={24} />
        </div>
      </section>

      {/* How It Works Section */}
      <section className="how-it-works">
        <h2>How It Works</h2>
        <p className="section-subtitle">
          From raw code to structured knowledge in four layers
        </p>

        <div className="flow-diagram">
          <div className="flow-step">
            <div className="step-number">1</div>
            <div className="step-icon">
              <Code2 size={32} />
            </div>
            <h3>Parse & Extract</h3>
            <p>
              Multi-language parsing with tree-sitter. Extract symbols, functions, classes,
              and their relationships automatically.
            </p>
          </div>

          <div className="flow-arrow">→</div>

          <div className="flow-step">
            <div className="step-number">2</div>
            <div className="step-icon">
              <Brain size={32} />
            </div>
            <h3>Generate Specs</h3>
            <p>
              LLM reads your code and generates structured specs with purpose, inputs,
              outputs, dependencies, and edge cases.
            </p>
          </div>

          <div className="flow-arrow">→</div>

          <div className="flow-step">
            <div className="step-number">3</div>
            <div className="step-icon">
              <Database size={32} />
            </div>
            <h3>Build Graph</h3>
            <p>
              Link specs into a semantic graph. Cluster related functionality into a
              navigable group.md tree.
            </p>
          </div>

          <div className="flow-arrow">→</div>

          <div className="flow-step">
            <div className="step-number">4</div>
            <div className="step-icon">
              <Zap size={32} />
            </div>
            <h3>Ask & Explore</h3>
            <p>
              Ask natural language questions. Get grounded answers with exact file:line
              citations. Explore as living docs.
            </p>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <h2>Why Spec-Atlas?</h2>

        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">
              <Shield size={28} />
            </div>
            <h3>Grounded in Code</h3>
            <p>
              Every answer includes file:line citations. No hallucinations. No generic
              answers. Every claim traced to actual source.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <Zap size={28} />
            </div>
            <h3>Lightning Fast</h3>
            <p>
              Index a 20k-LOC repo in under 5 minutes. Answer questions in seconds. Built
              for local-first, offline operation.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <Database size={28} />
            </div>
            <h3>Multi-Language</h3>
            <p>
              Parse Python, TypeScript, JavaScript, and more. Unified graph regardless of
              language. Add new languages anytime.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <Brain size={28} />
            </div>
            <h3>LLM-Powered</h3>
            <p>
              Leverage local or cloud LLMs. Run Ollama offline or use free Groq tier.
              Always under your control, $0 cost.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <Code2 size={28} />
            </div>
            <h3>Living Docs</h3>
            <p>
              Auto-generated specs that stay in sync with code. Drift detection flags
              outdated docs. Specs never silently rot.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <GitFork size={28} />
            </div>
            <h3>Agent-Ready</h3>
            <p>
              MCP server for Claude Code, Codex, Gemini. Your agents fetch specs instead
              of re-reading the whole repo.
            </p>
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="use-cases">
        <h2>Perfect For</h2>
        <p className="section-subtitle">
          Save hours on every task that touches unfamiliar code
        </p>

        <div className="use-cases-grid">
          <div className="use-case">
            <h3>[LAUNCH] Onboarding</h3>
            <p>
              New to the codebase? Ask questions and get grounded answers in seconds
              instead of reading docs for hours.
            </p>
          </div>

          <div className="use-case">
            <h3>[AI] AI-Assisted Development</h3>
            <p>
              Hand Claude Code an accurate spec of the area you're editing. It builds
              correctly the first time.
            </p>
          </div>

          <div className="use-case">
            <h3>[DOCS] Living Documentation</h3>
            <p>
              Auto-generated, always-current specs. No hand-written docs to maintain. No
              outdated README.
            </p>
          </div>

          <div className="use-case">
            <h3>[REVIEW] Code Review</h3>
            <p>
              Understand what changed by exploring the impacted areas. See all cross-file
              implications.
            </p>
          </div>

          <div className="use-case">
            <h3>[ARCH] Architecture Understanding</h3>
            <p>
              Visualize your system as a graph. See how modules connect. Understand
              dependencies at a glance.
            </p>
          </div>

          <div className="use-case">
            <h3>[REFACTOR] Refactoring</h3>
            <p>
              Know exactly what breaks if you change this. See the full impact radius
              before you touch anything.
            </p>
          </div>
        </div>
      </section>

      {/* Tech Stack Section */}
      <section className="tech-stack">
        <h2>Built With</h2>
        <p className="section-subtitle">
          Open-source, local-first, zero cost
        </p>

        <div className="tech-grid">
          <div className="tech-item">
            <h4>Parser</h4>
            <p>tree-sitter</p>
            <small>Multi-language CST extraction</small>
          </div>

          <div className="tech-item">
            <h4>LLM</h4>
            <p>Ollama / Groq Free</p>
            <small>Local or cloud, completely free</small>
          </div>

          <div className="tech-item">
            <h4>Database</h4>
            <p>PostgreSQL + pgvector</p>
            <small>Semantic search with embeddings</small>
          </div>

          <div className="tech-item">
            <h4>Backend</h4>
            <p>Python + FastAPI</p>
            <small>High-performance async API</small>
          </div>

          <div className="tech-item">
            <h4>Frontend</h4>
            <p>React + TypeScript</p>
            <small>Modern, responsive UI</small>
          </div>

          <div className="tech-item">
            <h4>Agents</h4>
            <p>MCP Server</p>
            <small>Claude Code, Codex, Gemini ready</small>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section
        className="cta-section"
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        style={{ cursor: 'pointer' }}
      >
        <h2>Get Started In 2 Minutes</h2>
        <p>No installation. No credentials. Just indexing.</p>

        <div className="cta-actions">
          <input
            type="text"
            placeholder="Enter a repo URL above..."
            className="cta-input"
            disabled
          />
          <button className="cta-button" onClick={(e) => e.stopPropagation()}>
            Index Repository
          </button>
        </div>

        <p className="cta-note">
          ↑ Click anywhere to scroll back to the top and enter your repo URL
        </p>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <p>
          Spec-Atlas • Maps code into living knowledge graphs •{' '}
          <a href="https://github.com">GitHub</a>
        </p>
      </footer>
    </div>
  )
}

export default Landing
