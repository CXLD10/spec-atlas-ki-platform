import { useState } from 'react'
import './MCPServer.css'

const MCP_TOOLS = [
  {
    name: 'search',
    signature: 'search(query: string, repo?: string) → SearchResult[]',
    description: 'Semantic search across all indexed sources and knowledge cards.',
  },
  {
    name: 'get_spec',
    signature: 'get_spec(component_ref: string, repo?: string) → Spec',
    description: 'Retrieve the full knowledge card for a specific component by reference.',
  },
  {
    name: 'get_group',
    signature: 'get_group(group_path: string, repo?: string) → Group',
    description: 'Get a domain group with its member cards and summary.',
  },
  {
    name: 'list_stale_specs',
    signature: 'list_stale_specs(repo?: string) → Spec[]',
    description: 'List all knowledge cards that are stale and need regeneration.',
  },
]

const MCP_CONFIG = `{
  "mcpServers": {
    "spec-atlas": {
      "command": "uvx",
      "args": ["spec-atlas-mcp"],
      "env": {
        "SPEC_ATLAS_URL": "http://localhost:8000"
      }
    }
  }
}`

export function MCPServer() {
  const [selectedTool, setSelectedTool] = useState(MCP_TOOLS[0].name)
  const [toolArg, setToolArg] = useState('')
  const [output, setOutput] = useState<string | null>(null)
  const [calling, setCalling] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCall = async () => {
    setCalling(true)
    setOutput(null)
    await new Promise((r) => setTimeout(r, 800))
    setOutput(
      JSON.stringify(
        {
          status: 'ok',
          tool: selectedTool,
          result: [
            {
              ref: 'hf-transformers-tokenizer',
              title: 'Tokenizer: BPE to SentencePiece',
              score: 0.94,
              source: 'huggingface/transformers',
            },
          ],
        },
        null,
        2
      )
    )
    setCalling(false)
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(MCP_CONFIG)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="mcp-page">
      <div className="mcp-header">
        <div>
          <h1 className="mcp-title">MCP Server</h1>
          <p className="mcp-subtitle">
            Connect Claude Code and other MCP-compatible agents to your knowledge base.
          </p>
        </div>
        <div className="mcp-status healthy">
          <span className="status-dot" />
          MCP · 4 tools live
        </div>
      </div>

      <div className="mcp-layout">
        <div className="mcp-tools">
          <h2 className="section-title">Available Tools</h2>
          <div className="tool-grid">
            {MCP_TOOLS.map((tool) => (
              <div key={tool.name} className="tool-card">
                <div className="tool-header">
                  <span className="tool-name">{tool.name}</span>
                  <span className="tool-badge">FROZEN</span>
                </div>
                <code className="tool-signature">{tool.signature}</code>
                <p className="tool-desc">{tool.description}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="mcp-sidebar">
          <div className="mcp-console">
            <h2 className="section-title">Playground — try a call</h2>
            <div className="console-form">
              <label className="console-label">Tool</label>
              <select
                className="console-select"
                value={selectedTool}
                onChange={(e) => setSelectedTool(e.target.value)}
              >
                {MCP_TOOLS.map((t) => (
                  <option key={t.name} value={t.name}>
                    {t.name}
                  </option>
                ))}
              </select>

              <label className="console-label">Argument</label>
              <input
                className="console-input"
                type="text"
                placeholder='e.g. "tokenizer" or "auth/session"'
                value={toolArg}
                onChange={(e) => setToolArg(e.target.value)}
              />

              <button
                className="console-call-btn"
                onClick={handleCall}
                disabled={calling}
              >
                {calling ? 'Calling...' : 'Call'}
              </button>
            </div>

            {output && (
              <div className="console-output">
                <pre className="output-pre">{output}</pre>
              </div>
            )}
          </div>

          <div className="mcp-config-block">
            <div className="config-header">
              <h3 className="config-title">claude_desktop_config.json</h3>
              <button className="copy-btn" onClick={handleCopy}>
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <pre className="config-pre">{MCP_CONFIG}</pre>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MCPServer
