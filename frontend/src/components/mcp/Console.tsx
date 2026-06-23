import { useState, useRef } from 'react'
import { Copy, Check } from 'lucide-react'
import './Console.css'

interface ConsoleProps {
  tools: Array<{ name: string; signature: string; description: string }>
}

// Simple JSON syntax highlighter
function highlightJSON(json: string): React.ReactNode {
  const regex = /("[^"]*":|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|\{|\}|\[|\]|,|:)/g
  const parts = json.split(regex)

  return (
    <>
      {parts.map((part, i) => {
        if (!part) return null

        // Keys (strings ending with :)
        if (part.match(/^"[^"]*":$/)) {
          return (
            <span key={i} className="json-key">
              {part}
            </span>
          )
        }
        // String values
        if (part.match(/^"[^"]*"$/)) {
          return (
            <span key={i} className="json-string">
              {part}
            </span>
          )
        }
        // Numbers
        if (part.match(/^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/)) {
          return (
            <span key={i} className="json-number">
              {part}
            </span>
          )
        }
        // Booleans and null
        if (/^(true|false|null)$/.test(part)) {
          return (
            <span key={i} className="json-literal">
              {part}
            </span>
          )
        }

        return part
      })}
    </>
  )
}

export function Console({ tools }: ConsoleProps) {
  const [selectedTool, setSelectedTool] = useState(tools[0]?.name || '')
  const [toolArg, setToolArg] = useState('')
  const [output, setOutput] = useState<string | null>(null)
  const [calling, setCalling] = useState(false)
  const [copied, setCopied] = useState(false)
  const outputRef = useRef<HTMLDivElement>(null)

  const handleCall = async () => {
    if (!selectedTool || !toolArg.trim()) return

    setCalling(true)
    setOutput(null)

    try {
      // Simulate API call with delay
      await new Promise((r) => setTimeout(r, 800))

      // Mock responses for each tool
      const mockResponses: Record<string, unknown> = {
        search: {
          status: 'ok',
          tool: selectedTool,
          query: toolArg,
          results: [
            {
              ref: 'hf-transformers-tokenizer',
              title: 'Tokenizer: BPE to SentencePiece',
              score: 0.94,
              source: 'huggingface/transformers',
              provenance: 'src/transformers/tokenization_utils.py:45',
            },
          ],
        },
        get_spec: {
          status: 'ok',
          ref: toolArg,
          title: 'Tokenizer Architecture',
          status_badge: 'verified',
          purpose: 'The tokenizer layer implements multiple strategies for subword segmentation.',
          inputs: ['text: str'],
          outputs: ['tokens: List[int]'],
          dependencies: ['SentencePiece'],
          provenance: [
            { ref: 'huggingface/transformers', loc: 'src/transformers/tokenization_utils.py:45' },
          ],
        },
        get_group: {
          status: 'ok',
          path: toolArg,
          summary: 'Tokenization and preprocessing layer for NLP models',
          member_count: 8,
          members: [
            { ref: 'tokenizer-bpe', title: 'BPE Tokenizer' },
            { ref: 'tokenizer-sentencepiece', title: 'SentencePiece Tokenizer' },
          ],
          children: ['tokenization/bpe', 'tokenization/wordpiece'],
        },
        list_stale_specs: {
          status: 'ok',
          stale_count: 3,
          stale_specs: [
            { ref: 'retrieval-old', title: 'Retrieval (outdated)', last_verified: '2025-04-01' },
            { ref: 'embedding-v1', title: 'Embeddings v1', last_verified: '2025-03-15' },
          ],
        },
      }

      const response = mockResponses[selectedTool] || { error: 'Unknown tool' }
      setOutput(JSON.stringify(response, null, 2))
    } catch (err) {
      setOutput(JSON.stringify({ error: 'Call failed', message: String(err) }, null, 2))
    } finally {
      setCalling(false)
    }
  }

  const handleCopyOutput = () => {
    if (output) {
      navigator.clipboard.writeText(output)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="console">
      <h2 className="console-title">Playground — try a call</h2>

      <div className="console-form">
        <div className="console-form-group">
          <label htmlFor="tool-select" className="console-label">
            Tool
          </label>
          <select
            id="tool-select"
            className="console-select"
            value={selectedTool}
            onChange={(e) => setSelectedTool(e.target.value)}
            disabled={calling}
          >
            {tools.map((t) => (
              <option key={t.name} value={t.name}>
                {t.name}
              </option>
            ))}
          </select>
        </div>

        <div className="console-form-group">
          <label htmlFor="arg-input" className="console-label">
            Argument
          </label>
          <input
            id="arg-input"
            className="console-input"
            type="text"
            placeholder='e.g. "tokenizer" or "auth/session"'
            value={toolArg}
            onChange={(e) => setToolArg(e.target.value)}
            disabled={calling}
          />
        </div>

        <button
          className="console-btn"
          onClick={handleCall}
          disabled={calling || !selectedTool || !toolArg.trim()}
        >
          {calling ? 'Calling…' : 'Call'}
        </button>
      </div>

      {output && (
        <div className="console-output">
          <div className="console-output-header">
            <span className="console-output-label">Response</span>
            <button
              className="console-output-copy"
              onClick={handleCopyOutput}
              title="Copy response"
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
          <div ref={outputRef} className="console-output-pre">
            <code>{highlightJSON(output)}</code>
          </div>
        </div>
      )}

      {!output && !calling && (
        <div className="console-empty">
          <p>Select a tool and provide an argument, then click "Call" to see the response.</p>
        </div>
      )}

      {calling && (
        <div className="console-loading">
          <div className="console-spinner" />
          <p>Calling {selectedTool}…</p>
        </div>
      )}
    </div>
  )
}
