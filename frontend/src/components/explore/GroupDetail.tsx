import { Link } from 'react-router-dom'
import { GroupDetail as GroupDetailType } from '../../api/client'
import ReactMarkdown from 'react-markdown'
import './GroupDetail.css'

interface GroupDetailProps {
  group: GroupDetailType
  repoId?: string
}

export function GroupDetail({ group, repoId = 'default' }: GroupDetailProps) {
  return (
    <article className="group-detail">
      <header className="detail-header">
        <h1 className="detail-title">{group.id}</h1>
        <p className="detail-path mono">{group.path}</p>
      </header>

      {group.summary_md && (
        <div className="summary-section">
          <ReactMarkdown className="markdown-content">
            {group.summary_md}
          </ReactMarkdown>
        </div>
      )}

      {group.member_specs && group.member_specs.length > 0 && (
        <section className="specs-section">
          <h2 className="section-title">Member Specs</h2>
          <ul className="specs-list">
            {group.member_specs.map((specRef) => (
              <li key={specRef} className="spec-item">
                <Link to={`/repo/${repoId}/explore/specs/${specRef}`} className="spec-link">
                  <span className="spec-ref">{specRef}</span>
                  <span className="spec-badge" data-status="draft">
                    draft
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  )
}
