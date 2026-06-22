import { ReactNode } from 'react'
import './AnswerDock.css'

interface AnswerDockProps {
  question?: string
  answer?: ReactNode
  confidence?: number // 0-1
  isLoading?: boolean
}

export function AnswerDock({
  question,
  answer,
  confidence = 0,
  isLoading = false,
}: AnswerDockProps) {
  if (!question && !answer && !isLoading) {
    return null
  }

  return (
    <div className="answer-dock glass-panel">
      <div className="dock-header">
        <span className="dock-title">◆ Grounded Answer</span>
      </div>

      {question && (
        <div className="question-section">
          <p className="question-text">{question}</p>
        </div>
      )}

      {isLoading ? (
        <div className="answer-loading">
          <div className="spinner" aria-hidden="true" />
          <span className="sr-only">Loading answer...</span>
        </div>
      ) : answer ? (
        <div className="answer-section">
          <div className="answer-text">{answer}</div>

          {confidence > 0 && (
            <div className="confidence-bar-container">
              <label htmlFor="confidence" className="confidence-label mono">
                CONFIDENCE
              </label>
              <div className="confidence-bar">
                <div
                  id="confidence"
                  className="confidence-fill"
                  style={{ width: `${confidence * 100}%` }}
                  role="progressbar"
                  aria-valuenow={Math.round(confidence * 100)}
                  aria-valuemin={0}
                  aria-valuemax={100}
                />
              </div>
              <span className="confidence-value">{Math.round(confidence * 100)}%</span>
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}
