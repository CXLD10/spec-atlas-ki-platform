import { useParams, useNavigate } from 'react-router-dom'
import { TopBar } from '../components/layout/TopBar'
import SourceManager from '../components/sources/SourceManager'
import './ProjectDetail.css'

export function ProjectDetail() {
  const { projectId = 'default' } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  return (
    <div className="project-detail-page">
      <TopBar variant="workspace" />

      <div className="project-detail-header">
        <button
          className="back-button"
          onClick={() => navigate(-1)}
        >
          ← Back
        </button>
        <h1>{projectId}</h1>
      </div>

      <div className="project-detail-content">
        <section className="project-section">
          <SourceManager projectId={projectId} />
        </section>
      </div>
    </div>
  )
}

export default ProjectDetail
