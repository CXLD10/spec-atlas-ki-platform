import { useParams } from 'react-router-dom'
import { useState } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { AmbientGrid } from '../components/layout/AmbientGrid'
import { SpecDetail } from '../components/explore/SpecDetail'
import { useSpec } from '../api/useSpec'
import { useSpecGraph } from '../api/useSpecGraph'
import './RepoSpec.css'

export function RepoSpec() {
  const { repoId = 'default', specRef = '' } = useParams()
  const { data: spec, isLoading, error } = useSpec(specRef || '')
  const { data: specGraph } = useSpecGraph(specRef || '')
  const [showDependencies, setShowDependencies] = useState(true)
  const [showDependents, setShowDependents] = useState(true)

  return (
    <div className="repo-spec-page">
      <AmbientGrid />
      <TopBar variant="workspace" />

      <main className="repo-spec-main">
        {error && (
          <div className="error-message" role="alert">
            <strong>Error loading spec:</strong> {error.message}
          </div>
        )}

        {isLoading ? (
          <div className="loading-state">
            <div className="spinner" />
            <p>Loading spec detail...</p>
          </div>
        ) : spec ? (
          <>
            <SpecDetail spec={spec} repoId={repoId} />

            {specGraph && (
              <aside className="spec-graph-panel">
                <div className="graph-panel-header">
                  <h3>Spec Relationships</h3>
                </div>

                {specGraph.dependencies && specGraph.dependencies.length > 0 && (
                  <div className="graph-section">
                    <button
                      className="section-toggle"
                      onClick={() => setShowDependencies(!showDependencies)}
                      aria-expanded={showDependencies}
                    >
                      <span className="toggle-icon">{showDependencies ? '▼' : '▶'}</span>
                      <span className="section-title">Dependencies ({specGraph.dependencies.length})</span>
                    </button>
                    {showDependencies && (
                      <ul className="relationship-list">
                        {specGraph.dependencies.map((dep: any, i: number) => (
                          <li key={i} className="relationship-item">
                            <a href={`/repo/${repoId}/explore/specs/${dep.component_ref}`}>{dep.component_ref}</a>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

                {specGraph.dependents && specGraph.dependents.length > 0 && (
                  <div className="graph-section">
                    <button
                      className="section-toggle"
                      onClick={() => setShowDependents(!showDependents)}
                      aria-expanded={showDependents}
                    >
                      <span className="toggle-icon">{showDependents ? '▼' : '▶'}</span>
                      <span className="section-title">Dependents ({specGraph.dependents.length})</span>
                    </button>
                    {showDependents && (
                      <ul className="relationship-list">
                        {specGraph.dependents.map((dep: any, i: number) => (
                          <li key={i} className="relationship-item">
                            <a href={`/repo/${repoId}/explore/specs/${dep.component_ref}`}>{dep.component_ref}</a>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

                {(!specGraph.dependencies || specGraph.dependencies.length === 0) &&
                  (!specGraph.dependents || specGraph.dependents.length === 0) && (
                    <div className="graph-empty">
                      <p>No related specs found</p>
                    </div>
                  )}
              </aside>
            )}
          </>
        ) : (
          <div className="empty-state">
            <p>Spec not found</p>
          </div>
        )}
      </main>
    </div>
  )
}

export default RepoSpec
