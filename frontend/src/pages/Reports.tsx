import { useEffect, useMemo, useState } from 'react'
import { useSources } from '../lib/hooks'
import { useVerificationReport, useVerificationIssues, useConfidenceDistribution } from '../api/useReports'
import './Reports.css'

export default function Reports() {
  const { data: sources = [], isLoading: sourcesLoading } = useSources()
  const repos = useMemo(() => sources.filter((s) => s.type === 'repo'), [sources])
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null)

  useEffect(() => {
    if (!selectedRepo && repos.length > 0) setSelectedRepo(repos[0].name)
  }, [repos, selectedRepo])

  const report = useVerificationReport(selectedRepo ?? undefined)
  const issues = useVerificationIssues(selectedRepo ?? undefined)
  const confidence = useConfidenceDistribution(selectedRepo ?? undefined)

  if (sourcesLoading) {
    return <div className="reports-page reports-loading">Loading…</div>
  }

  if (repos.length === 0) {
    return (
      <div className="reports-page reports-empty">
        <p>No indexed repositories yet.</p>
        <small>Index a repository from the Dashboard to see verification reports.</small>
      </div>
    )
  }

  return (
    <div className="reports-page">
      <header className="reports-header">
        <div>
          <h1 className="reports-title">Verification Report</h1>
          <p className="reports-subtitle">
            Spec status, confidence distribution, and open grounding issues — computed live from
            the Spec DB.
          </p>
        </div>
        {repos.length > 1 && (
          <select
            className="reports-repo-select"
            value={selectedRepo ?? ''}
            onChange={(e) => setSelectedRepo(e.target.value)}
            aria-label="Select repository"
          >
            {repos.map((r) => (
              <option key={r.id} value={r.name}>
                {r.name}
              </option>
            ))}
          </select>
        )}
      </header>

      {report.isLoading ? (
        <div className="reports-loading">Loading report…</div>
      ) : report.error ? (
        <div className="reports-empty">
          Couldn't load report: {report.error instanceof Error ? report.error.message : 'unknown error'}
        </div>
      ) : report.data ? (
        <>
          <section className="reports-stats-grid">
            <div className="reports-stat">
              <span className="reports-stat-value">{report.data.total_specs}</span>
              <span className="reports-stat-label">Total specs</span>
            </div>
            <div className="reports-stat reports-stat--verified">
              <span className="reports-stat-value">{report.data.verified_count}</span>
              <span className="reports-stat-label">Verified</span>
            </div>
            <div className="reports-stat reports-stat--review">
              <span className="reports-stat-value">{report.data.review_count}</span>
              <span className="reports-stat-label">Needs review</span>
            </div>
            <div className="reports-stat reports-stat--draft">
              <span className="reports-stat-value">{report.data.draft_count}</span>
              <span className="reports-stat-label">Draft</span>
            </div>
            <div className="reports-stat">
              <span className="reports-stat-value">{(report.data.avg_confidence * 100).toFixed(0)}%</span>
              <span className="reports-stat-label">Avg confidence</span>
            </div>
            <div className="reports-stat">
              <span className="reports-stat-value">{(report.data.verification_rate * 100).toFixed(0)}%</span>
              <span className="reports-stat-label">Verification rate</span>
            </div>
          </section>

          <div className="reports-columns">
            <section className="reports-card">
              <h2 className="reports-card-title">Confidence distribution</h2>
              {confidence.isLoading ? (
                <p className="reports-dim">Loading…</p>
              ) : confidence.data && confidence.data.bins.length > 0 ? (
                <div className="reports-histogram">
                  {confidence.data.bins.map((bin, i) => {
                    const count = confidence.data!.counts[i]
                    const max = Math.max(...confidence.data!.counts, 1)
                    return (
                      <div key={bin} className="reports-histogram-row">
                        <span className="reports-histogram-bin">{bin}</span>
                        <div className="reports-histogram-bar-track">
                          <div
                            className="reports-histogram-bar"
                            style={{ width: `${(count / max) * 100}%` }}
                          />
                        </div>
                        <span className="reports-histogram-count">{count}</span>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p className="reports-dim">No confidence data yet — verify some specs first.</p>
              )}
            </section>

            <section className="reports-card">
              <h2 className="reports-card-title">Open verification issues</h2>
              {issues.isLoading ? (
                <p className="reports-dim">Loading…</p>
              ) : issues.data && issues.data.issues.length > 0 ? (
                <ul className="reports-issue-list">
                  {issues.data.issues.map((issue, i) => (
                    <li key={i} className="reports-issue">
                      <span className="reports-issue-count">{issue.count}×</span>
                      <span className="reports-issue-reason">{issue.reason}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="reports-dim">No open issues — every verified spec is grounded.</p>
              )}
            </section>
          </div>
        </>
      ) : null}
    </div>
  )
}
