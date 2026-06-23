import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { X } from 'lucide-react'
import { ChatMessage } from '../components/ask/ChatMessage'
import { Composer } from '../components/ask/Composer'
import { client, MockFallback } from '../lib/api'
import { MOCK_ANSWER } from '../lib/mock'
import './Ask.css'

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
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
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

    try {
      const data = await client.ask(question, scope || undefined)

      const assistantMsg: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        text: data.answer || 'No response',
        streaming: true,
        claims: data.claims || [],
        confidence: data.confidence,
        route: data.route_used,
      }

      setMessages((prev) => [...prev, assistantMsg])

      // Wait for streaming to complete (text length * 20ms per char)
      await new Promise((r) => setTimeout(r, (data.answer?.length || 0) * 20 + 100))

      // Mark as done streaming
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantMsg.id ? { ...m, streaming: false } : m))
      )
    } catch (err) {
      if (err instanceof MockFallback) {
        const assistantMsg: Message = {
          id: `msg-${Date.now() + 1}`,
          role: 'assistant',
          text: MOCK_ANSWER.answer,
          streaming: true,
          claims: MOCK_ANSWER.claims,
          confidence: MOCK_ANSWER.confidence,
          route: MOCK_ANSWER.route_used,
        }

        setMessages((prev) => [...prev, assistantMsg])
        await new Promise((r) => setTimeout(r, (MOCK_ANSWER.answer?.length || 0) * 20 + 100))
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsg.id ? { ...m, streaming: false } : m))
        )
      } else {
        const errorMsg: Message = {
          id: `msg-${Date.now() + 1}`,
          role: 'assistant',
          text: `Error: ${err instanceof Error ? err.message : 'Unknown error'}`,
        }
        setMessages((prev) => [...prev, errorMsg])
      }
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
