import { useEffect, useState } from 'react'
import './ChatMessage.css'

interface Claim {
  text?: string
  source: string
  file?: string
  start_line?: number
  end_line?: number
  confidence?: number
}

interface ChatMessageProps {
  role: 'user' | 'assistant'
  text: string
  streaming?: boolean
  claims?: Claim[]
  confidence?: number
  route?: string
}

export function ChatMessage({ role, text, streaming, claims, confidence, route }: ChatMessageProps) {
  const [displayText, setDisplayText] = useState(streaming ? '' : text)

  useEffect(() => {
    if (!streaming) {
      setDisplayText(text)
      return
    }

    let idx = 0
    const interval = setInterval(() => {
      if (idx < text.length) {
        setDisplayText(text.slice(0, ++idx))
      } else {
        clearInterval(interval)
      }
    }, 20)

    return () => clearInterval(interval)
  }, [text, streaming])

  return (
    <div className={`chat-message chat-message--${role}`}>
      <div className="chat-message-avatar">
        <span className={`chat-avatar chat-avatar--${role}`}>
          {role === 'user' ? '👤' : '⚛️'}
        </span>
      </div>
      <div className="chat-message-content">
        <p className="chat-text">{displayText}</p>
        {streaming && <span className="chat-cursor" />}

        {!streaming && claims && claims.length > 0 && (
          <div className="chat-citations">
            <span className="chat-citations-label">Sources</span>
            <div className="chat-citations-list">
              {claims.map((c, i) => (
                <span key={i} className={`chat-claim chat-claim--${c.source.split('/').pop()?.split('.').pop() || 'text'}`}>
                  <code className="chat-claim-ref">{c.source}</code>
                  {c.file && <span className="chat-claim-loc">{c.file}</span>}
                  {c.start_line && (
                    <span className="chat-claim-line">
                      L{c.start_line}
                      {c.end_line && c.end_line !== c.start_line ? `-${c.end_line}` : ''}
                    </span>
                  )}
                </span>
              ))}
            </div>
          </div>
        )}

        {!streaming && confidence !== undefined && (
          <div className={`chat-footer ${confidence < 0.5 ? 'chat-footer--low-confidence' : ''}`}>
            {confidence < 0.5 && <span className="chat-warning">⚠️ Low confidence</span>}
            {route && <span className="chat-route">{route}</span>}
            <span className="chat-confidence">{(confidence * 100).toFixed(0)}%</span>
          </div>
        )}
      </div>
    </div>
  )
}
