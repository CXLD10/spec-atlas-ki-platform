import { AlertCircle } from 'lucide-react'
import './ErrorState.css'

interface ErrorStateProps {
  title: string
  message: string
  retry?: () => void
  back?: () => void
}

export function ErrorState({ title, message, retry, back }: ErrorStateProps) {
  return (
    <div className="error-state">
      <AlertCircle size={40} className="error-state-icon" />
      <h2 className="error-state-title">{title}</h2>
      <p className="error-state-message">{message}</p>
      <div className="error-state-actions">
        {retry && (
          <button className="error-state-btn" onClick={retry}>
            Try again
          </button>
        )}
        {back && (
          <button className="error-state-btn error-state-btn--secondary" onClick={back}>
            Go back
          </button>
        )}
      </div>
    </div>
  )
}
