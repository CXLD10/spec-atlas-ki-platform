import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { PipelineHUD } from '../components/hud/PipelineHUD'
import { useIndexJob } from '../api/useIndexJob'
import './IndexProgress.css'

export function IndexProgress() {
  const navigate = useNavigate()
  const { jobId } = useParams()
  const { data: job, isLoading, error } = useIndexJob(jobId || '')
  const progress = job?.progress ?? 0

  useEffect(() => {
    if (job?.status === 'done') {
      const timer = setTimeout(() => navigate('/sources'), 800)
      return () => clearTimeout(timer)
    }
  }, [job?.status, navigate])

  if (error) {
    return (
      <div className="ip-page">
        <div className="ip-error">
          <strong>Indexing failed:</strong> {error.message}
          <button className="ip-back" onClick={() => navigate('/')}>← Back</button>
        </div>
      </div>
    )
  }

  return (
    <div className="ip-page">
      <div className="ip-inner">
        <div className="ip-eyebrow">Knowledge Intelligence Platform</div>
        <h1 className="ip-title">Building your knowledge base</h1>

        <div className="ip-hud-wrap">
          {(job || isLoading) && <PipelineHUD progress={progress} />}
        </div>

        <div className="ip-bar-wrap">
          <div className="ip-bar">
            <div className="ip-bar-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="ip-bar-labels">
            <span className="ip-pct">{progress}%</span>
            {job?.eta_seconds != null && job.eta_seconds > 0 && (
              <span className="ip-eta">{formatETA(job.eta_seconds)}</span>
            )}
          </div>
        </div>
      </div>

      {job?.show_warning && (
        <div className="ip-warning">{job.warning_message ?? 'Large repository — this may take a while'}</div>
      )}
    </div>
  )
}

function formatETA(s: number): string {
  const m = Math.floor(s / 60), sec = s % 60
  if (m === 0) return `${sec}s remaining`
  if (sec === 0) return `${m}m remaining`
  return `${m}m ${sec}s remaining`
}

export default IndexProgress
