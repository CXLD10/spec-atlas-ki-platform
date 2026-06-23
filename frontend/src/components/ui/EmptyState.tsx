import { ReactNode } from 'react'
import './EmptyState.css'

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description: string
  cta?: {
    label: string
    href?: string
    onClick?: () => void
  }
}

export function EmptyState({ icon, title, description, cta }: EmptyStateProps) {
  return (
    <div className="empty-state">
      {icon && <div className="empty-state-icon">{icon}</div>}
      <h2 className="empty-state-title">{title}</h2>
      <p className="empty-state-desc">{description}</p>
      {cta && (
        <a
          href={cta.href || '#'}
          onClick={(e) => {
            if (cta.onClick) {
              e.preventDefault()
              cta.onClick()
            }
          }}
          className="empty-state-cta"
        >
          {cta.label} →
        </a>
      )}
    </div>
  )
}
