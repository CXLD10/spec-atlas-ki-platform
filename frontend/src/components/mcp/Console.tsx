import { useState, useRef } from 'react'
import { Copy, Check } from 'lucide-react'
import './Console.css'

const API_URL =
  ((import.meta as any).env?.VITE_API_URL as string | undefined) || 'http://localhost:8000'

// Maps frontend tool names → backend tool name + which arg key the single input maps to.
// spec_atlas_list_groups has no MCP handler so it calls /api/groups directly.
const TOOL_MAP: Record<string, { backendTool: string; argKey: string }> = {
  spec_atlas_ask:         { backendTool: 'ask_question',     argKey: 'question' },
  spec_atlas_search:      { backendTool: 'search_knowledge', argKey: 'query' },
  spec_atlas_get_spec:    { backendTool: 'get_spec',         argKey: 'component_ref' },
}

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
      let data: unknown

      if (selectedTool === 'spec_atlas_list_groups') {
        const params = new URLSearchParams({ repo: toolArg.trim() })
        const resp = await fetch(`${API_URL}/api/groups?${params.toString()}`)
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
        data = await resp.json()
      } else {
        const mapping = TOOL_MAP[selectedTool]
        if (!mapping) throw new Error(`Unknown tool: ${selectedTool}`)
        const resp = await fetch(`${API_URL}/api/mcp/call`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tool: mapping.backendTool,
            args: { [mapping.argKey]: toolArg.trim(), repo: 'default' },
          }),
        })
        if (!resp.ok) {
          const text = await resp.text().catch(() => '')
          throw new Error(`HTTP ${resp.status}: ${text}`)
        }
        data = await resp.json()
      }

      setOutput(JSON.stringify(data, null, 2))
    } catch (err) {
      setOutput(JSON.stringify({ error: err instanceof Error ? err.message : 'Unknown error' }, null, 2))
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
            placeholder='e.g. "how does auth work?" or "InferenceEngine"'
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
