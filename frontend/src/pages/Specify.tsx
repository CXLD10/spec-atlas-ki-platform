import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { TraceSteps } from '../components/specify/TraceSteps'
import { KnowledgeCardRender } from '../components/specify/KnowledgeCardRender'
import { client, GeneratedSpecResult } from '../api/client'
import { KnowledgeCard, Provenance, ProvenanceKind } from '../lib/types'
import './Specify.css'

function provenanceKind(filePath: string): ProvenanceKind {
  if (filePath.endsWith('.pdf')) return 'pdf'
  if (filePath.endsWith('.xlsx')) return 'xlsx'
  if (filePath.endsWith('.md') || filePath.endsWith('.markdown')) return 'md'
  return 'code'
}

// Adapts the real GenerateSpecResponse (specs.py) into the KnowledgeCard
// shape this page renders. Spec content is a structured object (purpose,
// inputs, outputs, ...), not pre-rendered markdown — rendered here so the
// card shows real fields, and real provenance spans (flattened server-side
// from {field: [span,...]} into a tagged list — see flatten_provenance).
function toKnowledgeCard(result: GeneratedSpecResult): KnowledgeCard {
  const content = result.content as Record<string, unknown>
  const lines: string[] = [`# ${result.component_ref}`, '']

  if (content.purpose) lines.push('## Purpose', '', String(content.purpose), '')

  const listSection = (title: string, key: string) => {
    const items = content[key]
    if (Array.isArray(items) && items.length > 0) {
      lines.push(`## ${title}`, '')
      for (const item of items) {
        lines.push(`- ${typeof item === 'string' ? item : JSON.stringify(item)}`)
      }
      lines.push('')
    }
  }
  listSection('Inputs', 'inputs')
  listSection('Outputs', 'outputs')
  listSection('Dependencies', 'dependencies')
  listSection('Invariants', 'invariants')
  listSection('Side Effects', 'side_effects')
  listSection('Failure Modes', 'failure_modes')

  const provenance: Provenance[] = (
    Array.isArray(result.provenance) ? (result.provenance as Array<Record<string, unknown>>) : []
  ).map((span) => {
    const file = String(span.file ?? '')
    return {
      ref: file,
      kind: provenanceKind(file),
      loc: `${span.start_line ?? '?'}-${span.end_line ?? '?'}${span.field ? ` (${span.field})` : ''}`,
    }
  })

  return {
    ref: result.component_ref,
    title: result.component_ref,
    status: result.status === 'verified' ? 'verified' : result.status === 'stale' ? 'stale' : 'draft',
    markdown: lines.join('\n'),
    provenance,
    relations: [],
  }
}

export default function Specify() {
  const [searchParams] = useSearchParams()
  const entityParam = searchParams.get('entity')
  const repoParam = searchParams.get('repo')

  const [repo, setRepo] = useState(repoParam || '')
  const [entity, setEntity] = useState(entityParam || '')
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [card, setCard] = useState<KnowledgeCard | null>(null)
  const [version, setVersion] = useState<number | null>(null)
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [verifyState, setVerifyState] = useState<'idle' | 'verifying' | 'error'>('idle')
  const [traceStep, setTraceStep] = useState(0)

  const TRACE_STEPS = [
    { id: 'graph',   title: 'Traversing knowledge graph',    detail: 'Resolving entity and collecting neighbouring nodes across L1 → L3 → L4' },
    { id: 'context', title: 'Loading source context',        detail: 'Reading referenced files and extracting relevant code spans' },
    { id: 'llm',     title: 'Synthesising specification',    detail: 'Generating structured fields: purpose, inputs, outputs, invariants' },
    { id: 'ground',  title: 'Grounding provenance',          detail: 'Matching each claim to a source line and computing confidence score' },
    { id: 'persist', title: 'Persisting to Spec DB',         detail: 'Writing versioned record and updating knowledge graph edges' },
  ]

  useEffect(() => {
    if (!generating) { setTraceStep(0); return }
    if (traceStep >= TRACE_STEPS.length - 1) return
    const id = setTimeout(() => setTraceStep(s => s + 1), 420)
    return () => clearTimeout(id)
  }, [generating, traceStep])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!repo.trim() || !entity.trim()) {
      setError('Please fill in all fields')
      return
    }

    setGenerating(true)
    setError(null)
    setCard(null)
    setSaveState('idle')
    setVerifyState('idle')
    setTraceStep(0)

    try {
      const data = await client.generateSpec(repo.trim(), entity.trim())
      setVersion(data.version)
      setCard(toKnowledgeCard(data))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate specification')
    } finally {
      setGenerating(false)
    }
  }

  const handleSave = async () => {
    if (!card) return
    setSaveState('saving')
    try {
      // Generate-on-demand already persisted this spec server-side; "Save"
      // confirms that by re-fetching from the Spec DB rather than trusting
      // local state — a real round trip, not a local flag flip.
      const fresh = await client.getSpecDetail(repo.trim(), card.ref)
      setVersion(fresh.version)
      setCard(toKnowledgeCard(fresh))
      setSaveState('saved')
    } catch {
      setSaveState('error')
    }
  }

  const handleVerify = async () => {
    if (!card || version === null) return
    setVerifyState('verifying')
    try {
      const result = await client.verifySpec(repo.trim(), card.ref, version)
      setCard({ ...card, status: result.status === 'verified' ? 'verified' : 'draft' })
      setVerifyState('idle')
    } catch {
      setVerifyState('error')
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
              setVersion(null)
              setSaveState('idle')
              setVerifyState('idle')
            }}
          >
            ← Generate another
          </button>
        </div>
        <KnowledgeCardRender card={card} onSave={handleSave} onVerify={handleVerify} />
        {saveState === 'saving' && <p className="specify-status">Confirming save…</p>}
        {saveState === 'saved' && <p className="specify-status">Saved — v{version} persisted in the Spec DB.</p>}
        {saveState === 'error' && <p className="specify-error">Save failed — could not confirm persistence.</p>}
        {verifyState === 'verifying' && <p className="specify-status">Verifying…</p>}
        {verifyState === 'error' && <p className="specify-error">Verification failed.</p>}
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
            Repository name
          </label>
          <input
            id="repo-input"
            type="text"
            className="specify-input"
            placeholder="e.g., the name shown on the Sources page"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            disabled={generating}
          />
        </div>

        <div className="specify-form-group">
          <label htmlFor="entity-input" className="specify-label">
            Component qualified name
          </label>
          <input
            id="entity-input"
            type="text"
            className="specify-input"
            placeholder="e.g., auth.session.mint_token"
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
            steps={TRACE_STEPS.map((s, i) => ({
              ...s,
              icon: null,
              status: i < traceStep ? 'done' : i === traceStep ? 'running' : 'queued',
            }))}
          />
        </div>
      )}
    </div>
  )
}
