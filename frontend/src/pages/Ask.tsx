import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { X } from 'lucide-react'
import { ChatMessage } from '../components/ask/ChatMessage'
import { Composer } from '../components/ask/Composer'
import './Ask.css'

const API_URL =
  ((import.meta as any).env?.VITE_API_URL as string | undefined) || 'http://localhost:8000'

/** POST /api/ask/stream — consumes the SSE response token-by-token.
 *  Calls onToken for each incremental word; resolves with the final payload. */
async function streamAsk(
  question: string,
  onToken: (token: string) => void,
): Promise<{ answer: string; claims: any[]; confidence: number; strategy: string; status: string }> {
  const resp = await fetch(`${API_URL}/api/ask/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, repo: 'default' }),
  })

  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    throw new Error(`HTTP ${resp.status}: ${text}`)
  }

  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalPayload: any = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE lines end with \n\n; process complete events
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      for (const line of part.split('\n')) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6))
          if (event.type === 'token') {
            onToken(event.token as string)
          } else if (event.type === 'done') {
            finalPayload = event
          }
        } catch { /* malformed JSON — skip */ }
      }
    }
  }

  return finalPayload ?? { answer: '', claims: [], confidence: 0, strategy: '', status: 'error' }
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  streaming?: boolean
  claims?: any[]
  confidence?: number
  route?: string
}

const SUGGESTIONS = [
  'What are the main features?',
  'How does authentication work?',
  'What are the dependencies?',
  'Explain the data flow.',
]

export default function Ask() {
  const [searchParams, setSearchParams] = useSearchParams()
  const scope = searchParams.get('scope')

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const scrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    // Scroll to bottom when new messages arrive or streaming state changes
    setTimeout(() => {
      scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, 0)
  }, [messages, streaming])

  const clearScope = () => {
    const newParams = new URLSearchParams(searchParams)
    newParams.delete('scope')
    setSearchParams(newParams)
  }

  const handleSubmit = async () => {
    if (!input.trim() || streaming) return

    const userMsg: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      text: input,
    }

    setMessages((prev) => [...prev, userMsg])
    const question = input
    setInput('')
    setStreaming(true)

    const assistantId = `msg-${Date.now() + 1}`

    // Add a streaming placeholder immediately so the loading dots disappear
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: 'assistant', text: '', streaming: true },
    ])

    try {
      const final = await streamAsk(question, (token) => {
        // Append each token to the assistant message in-place
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, text: m.text + token } : m,
          ),
        )
      })

      // Replace placeholder with the final complete message
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                text: final.answer || m.text || 'No response',
                streaming: false,
                claims: final.claims || [],
                confidence: final.confidence,
                route: final.strategy,
              }
            : m,
        ),
      )
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                text: `Error: ${err instanceof Error ? err.message : 'Unknown error'}`,
                streaming: false,
              }
            : m,
        ),
      )
    } finally {
      setStreaming(false)
    }
  }

  const handleSuggestion = (suggestion: string) => {
    setInput(suggestion)
  }

  return (
    <div className="ask-page">
      {/* Scope pill */}
      {scope && (
        <div className="ask-scope">
          <div className="ask-scope-content">
            <span className="ask-scope-label">Scoped to</span>
            <code className="ask-scope-value">{scope}</code>
            <button
              className="ask-scope-clear"
              onClick={clearScope}
              title="Clear scope"
              aria-label="Clear scope"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="ask-messages">
        {messages.length === 0 ? (
          <div className="ask-welcome">
            <h1 className="ask-welcome-title">Ask Atlas</h1>
            <p className="ask-welcome-desc">
              {scope
                ? `Ask about ${scope}`
                : 'Ask questions about your code and get grounded answers with exact source citations.'}
            </p>

            <div className="ask-suggestions">
              <p className="ask-suggestions-label">Try asking:</p>
              <div className="ask-suggestions-grid">
                {SUGGESTIONS.map((s, i) => (
                  <button
                    key={i}
                    className="ask-suggestion-btn"
                    onClick={() => handleSuggestion(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="ask-messages-inner">
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                role={msg.role}
                text={msg.text}
                streaming={msg.streaming}
                claims={msg.claims}
                confidence={msg.confidence}
                route={msg.route}
              />
            ))}
            {streaming && (
              <div className="ask-loading">
                <div className="ask-loading-dots">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            )}
            <div ref={scrollRef} />
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="ask-footer">
        <Composer
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          disabled={streaming}
          placeholder={scope ? `Ask about ${scope}…` : undefined}
        />
      </div>
    </div>
  )
}
