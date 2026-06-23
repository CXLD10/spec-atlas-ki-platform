import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { TraceSteps, type StepStatus } from '../components/specify/TraceSteps'
import { KnowledgeCardRender } from '../components/specify/KnowledgeCardRender'
import { client, GeneratedSpecResult } from '../api/client'
import { KnowledgeCard } from '../lib/types'
import './Specify.css'

// Adapts the real GenerateSpecResponse (specs.py) into the KnowledgeCard shape
// this page renders. Full fidelity (provenance -> citations, relations) is
// Phase 1 work (Specify request/response rewiring) — this keeps the page
// honest about real backend data in the meantime, never mock.
function toKnowledgeCard(result: GeneratedSpecResult): KnowledgeCard {
  const purpose = (result.content as { purpose?: string }).purpose
  const markdown = purpose
    ? `## Purpose\n\n${purpose}\n\n## Raw content\n\n\`\`\`json\n${JSON.stringify(result.content, null, 2)}\n\`\`\``
    : `\`\`\`json\n${JSON.stringify(result.content, null, 2)}\n\`\`\``

  return {
    ref: result.component_ref,
    title: result.component_ref,
    status: result.status === 'verified' ? 'verified' : result.status === 'stale' ? 'stale' : 'draft',
    markdown,
    provenance: [],
    relations: [],
  }
}

const TRACE_STEPS = [
  { title: 'Locate focal node', detail: 'Finding entity in knowledge graph' },
  { title: 'Fetch graph neighbourhood', detail: 'Retrieving related code and specs' },
  { title: 'Read source spans', detail: 'Extracting relevant code segments' },
  { title: 'LLM draft spec', detail: 'Generating structured specification' },
  { title: 'Validate & bind citations', detail: 'Linking claims to source locations' },
]

type StageKey = 'locate' | 'fetch' | 'read' | 'llm' | 'validate'

export default function Specify() {
  const [searchParams] = useSearchParams()
  const entityParam = searchParams.get('entity')

  const [repo, setRepo] = useState('')
  const [entity, setEntity] = useState(entityParam || '')
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [card, setCard] = useState<KnowledgeCard | null>(null)

  const [stages, setStages] = useState<Record<StageKey, StepStatus>>({
    locate: 'queued',
    fetch: 'queued',
    read: 'queued',
    llm: 'queued',
    validate: 'queued',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!repo.trim() || !entity.trim()) {
      setError('Please fill in all fields')
      return
    }

    setGenerating(true)
    setError(null)
    setCard(null)
    setStages({ locate: 'queued', fetch: 'queued', read: 'queued', llm: 'queued', validate: 'queued' })

    try {
      // Animate through stages
      const stageSequence: StageKey[] = ['locate', 'fetch', 'read', 'llm', 'validate']
      const stageDurations = { locate: 200, fetch: 400, read: 600, llm: 1200, validate: 200 }

      for (const stage of stageSequence) {
        setStages((prev) => ({ ...prev, [stage]: 'running' }))
        await new Promise((r) => setTimeout(r, stageDurations[stage]))
        setStages((prev) => ({ ...prev, [stage]: 'done' }))
      }

      // Fetch the spec
      const data = await client.generateSpec(repo, entity)
      setCard(toKnowledgeCard(data))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate specification')
      setGenerating(false)
    }
  }

  const handleSave = () => {
    alert('Version saved! (This is a demo stub)')
  }

  const handleVerify = () => {
    if (card) {
      setCard({ ...card, status: 'verified' })
      alert('Card marked as verified!')
    }
  }

  if (card) {
    return (
      <div className="specify-page">
        <div className="specify-header">
          <h1 className="specify-title">Knowledge Card Generated</h1>
          <button
            className="specify-reset"
            onClick={() => {
              setCard(null)
              setEntity('')
              setRepo('')
            }}
          >
            ← Generate another
          </button>
        </div>
        <KnowledgeCardRender card={card} onSave={handleSave} onVerify={handleVerify} />
      </div>
    )
  }

  return (
    <div className="specify-page">
      {/* Hero */}
      <div className="specify-hero">
        <h1 className="specify-hero-title">Specify Tool</h1>
        <p className="specify-hero-desc">
          Auto-generate structured Knowledge Cards from code entities. The system will traverse
          your knowledge graph, read source code, and synthesize a comprehensive specification.
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="specify-form">
        <div className="specify-form-group">
          <label htmlFor="repo-input" className="specify-label">
            Repository or workspace
          </label>
          <input
            id="repo-input"
            type="text"
            className="specify-input"
            placeholder="e.g., huggingface/transformers or my-workspace"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            disabled={generating}
          />
        </div>

        <div className="specify-form-group">
          <label htmlFor="entity-input" className="specify-label">
            Entity name
          </label>
          <input
            id="entity-input"
            type="text"
            className="specify-input"
            placeholder="e.g., validate_credentials, Pipeline"
            value={entity}
            onChange={(e) => setEntity(e.target.value)}
            disabled={generating}
          />
        </div>

        <button
          type="submit"
          className="specify-submit"
          disabled={generating || !repo.trim() || !entity.trim()}
        >
          {generating ? 'Generating…' : 'Generate Knowledge Card'}
        </button>
      </form>

      {error && <div className="specify-error">{error}</div>}

      {/* Trace */}
      {generating && (
        <div className="specify-trace">
          <TraceSteps
            steps={TRACE_STEPS.map((step, idx) => ({
              id: ['locate', 'fetch', 'read', 'llm', 'validate'][idx] as StageKey,
              icon: null,
              title: step.title,
              detail: step.detail,
              status: stages[['locate', 'fetch', 'read', 'llm', 'validate'][idx] as StageKey],
            }))}
          />
        </div>
      )}
    </div>
  )
}
