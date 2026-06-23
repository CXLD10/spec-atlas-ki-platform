import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { PipelineHUD } from '../components/hud/PipelineHUD'
import { useIndexJob } from '../api/useIndexJob'
import './IndexProgress.css'

export function IndexProgress() {
  const navigate = useNavigate()
  const { jobId } = useParams()
  const { data: job, isLoading, error } = useIndexJob(jobId || '')
  const phase = calculatePhase(job?.progress || 0)

  // Auto-redirect to Sources page when indexing completes
  useEffect(() => {
    if (job?.status === 'done') {
      // Small delay to let animation settle
      const timer = setTimeout(() => {
        navigate(`/sources`)
      }, 500)
      return () => clearTimeout(timer)
    }

    if (job?.status === 'failed') {
      // Stay on error page
    }
  }, [job?.status, job?.status, navigate, jobId])

  if (error) {
    return (
      <div className="index-progress-page">
        <main className="error-container">
          <div className="error-message" role="alert">
            <strong>Indexing failed:</strong> {error.message}
          </div>
          <button
            onClick={() => navigate('/')}
            className="back-button"
          >
            ← Back to home
          </button>
        </main>
      </div>
    )
  }

  return (
    <div className="index-progress-page">

      <main className="progress-main">
        <div className="progress-content">
          {job && <PipelineHUD activePhase={phase} />}

          <div className="status-overlay">
            {isLoading && !job ? (
              <p>Loading indexing status...</p>
            ) : job ? (
              <>
                <p className="status-text">Indexing {jobId}</p>
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
                <p className="progress-text">{job.progress}%</p>

                {job.status === 'failed' && (
                  <p className="error-text">{job.error}</p>
                )}
              </>
            ) : null}
          </div>
        </div>
      </main>
    </div>
  )
}

// Helper to convert progress % to phase (0-4)
function calculatePhase(progressPct: number) {
  return Math.min(Math.floor((progressPct / 100) * 4), 4)
}

export default IndexProgress
