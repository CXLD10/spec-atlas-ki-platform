import { Link } from 'react-router-dom'
import { Spec, SpecField } from '../../api/client'
import { CitationChip } from '../qa/CitationChip'
import './SpecDetail.css'

interface SpecDetailProps {
  spec: Spec
  repoId?: string
}

function renderField(field: SpecField | undefined, index?: number) {
  if (!field) return null

  return (
    <div key={`field-${index}`} className="spec-field">
      <p className="field-text">{field.text}</p>
      {field.file && field.start_line && (
        <CitationChip
          file={field.file}
          startLine={field.start_line}
          endLine={field.end_line}
          layer={2}
        />
      )}
    </div>
  )
}

export function SpecDetail({ spec, repoId = 'default' }: SpecDetailProps) {
  const statusColor = {
    draft: '--ink-faint',
    verified: '--l2',
    stale: '--l3',
  }[spec.status]

  return (
    <article className="spec-detail-view">
      <header className="spec-detail-header">
        <div className="header-left">
          <Link to={`/repo/${repoId}/explore`} className="back-link">
            ← Back to Groups
          </Link>
          <h1 className="spec-ref-title">{spec.ref}</h1>
        </div>

        <span className="status-badge" style={{ '--badge-color': `var(${statusColor})` } as any}>
          {spec.status}
        </span>
      </header>

      <div className="spec-sections">
        {spec.purpose && (
          <section className="spec-section">
            <h2 className="section-title">Purpose</h2>
            {renderField(spec.purpose)}
          </section>
        )}

        <div className="two-column">
          {spec.inputs && spec.inputs.length > 0 && (
            <section className="spec-section">
              <h2 className="section-title">Inputs</h2>
              <ul className="field-list">
                {spec.inputs.map((field, i) => (
                  <li key={i}>{renderField(field, i)}</li>
                ))}
              </ul>
            </section>
          )}

          {spec.outputs && spec.outputs.length > 0 && (
            <section className="spec-section">
              <h2 className="section-title">Outputs</h2>
              <ul className="field-list">
                {spec.outputs.map((field, i) => (
                  <li key={i}>{renderField(field, i)}</li>
                ))}
              </ul>
            </section>
          )}
        </div>

        <div className="two-column">
          {spec.dependencies && spec.dependencies.length > 0 && (
            <section className="spec-section">
              <h2 className="section-title">Dependencies</h2>
              <ul className="field-list">
                {spec.dependencies.map((field, i) => (
                  <li key={i}>{renderField(field, i)}</li>
                ))}
              </ul>
            </section>
          )}

          {spec.invariants && spec.invariants.length > 0 && (
            <section className="spec-section">
              <h2 className="section-title">Invariants</h2>
              <ul className="field-list">
                {spec.invariants.map((field, i) => (
                  <li key={i}>{renderField(field, i)}</li>
                ))}
              </ul>
            </section>
          )}
        </div>

        <div className="two-column">
          {spec.side_effects && spec.side_effects.length > 0 && (
            <section className="spec-section">
              <h2 className="section-title">Side Effects</h2>
              <ul className="field-list">
                {spec.side_effects.map((field, i) => (
                  <li key={i}>{renderField(field, i)}</li>
                ))}
              </ul>
            </section>
          )}

          {spec.failure_modes && spec.failure_modes.length > 0 && (
            <section className="spec-section">
              <h2 className="section-title">Failure Modes</h2>
              <ul className="field-list">
                {spec.failure_modes.map((field, i) => (
                  <li key={i}>{renderField(field, i)}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </div>
    </article>
  )
}
