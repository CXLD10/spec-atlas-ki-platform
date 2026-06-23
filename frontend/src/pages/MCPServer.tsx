import { useEffect, useState } from 'react'
import { Copy, Check, Circle } from 'lucide-react'
import { ToolCard } from '../components/mcp/ToolCard'
import { Console } from '../components/mcp/Console'
import { client } from '../api/client'
import './MCPServer.css'

const MCP_TOOLS = [
  {
    name: 'search_knowledge',
    signature: 'search_knowledge(query: string, repo?: string, limit?: number) → SearchResult[]',
    description: 'Runs the full router→retriever pipeline and returns matched groups and source units with relevance scores.',
  },
  {
    name: 'get_spec',
    signature: 'get_spec(component_ref: string, repo?: string, version?: number) → Spec',
    description: 'Fetches the current spec/card with purpose, I/O, status and citations.',
  },
  {
    name: 'get_graph',
    signature: 'get_graph(repo?: string, layer?: string, limit?: number) → Graph',
    description: 'Returns graph nodes and edges for the requested layer (source/group/all).',
  },
  {
    name: 'ask_question',
    signature: 'ask_question(question: string, repo?: string) → Answer',
    description: 'Answers a natural-language question using retrieval + LLM with real confidence scoring.',
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

export default function MCPServer() {
  const [healthy, setHealthy] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const result = await client.health()
        setHealthy(result.status === 'ok')
      } catch {
        setHealthy(false)
      }
    }

    checkHealth()
    const interval = setInterval(checkHealth, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleCopyConfig = () => {
    navigator.clipboard.writeText(MCP_CONFIG)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="mcp-page">
      {/* Header */}
      <header className="mcp-header">
        <div className="mcp-header-content">
          <h1 className="mcp-title">MCP Server</h1>
          <p className="mcp-subtitle">
            Connect Claude Code and other MCP-compatible agents to your knowledge base. Four frozen tools provide stable schemas for retrieval and exploration.
          </p>
        </div>

        <div className={`mcp-status ${healthy ? 'mcp-status--healthy' : 'mcp-status--offline'}`}>
          <Circle size={10} fill="currentColor" />
          <span>{healthy ? 'MCP · backend ready' : 'MCP · offline'}</span>
        </div>
      </header>

      {/* Layout */}
      <div className="mcp-layout">
        {/* Tools section */}
        <section className="mcp-tools">
          <h2 className="mcp-section-title">Available Tools</h2>
          <div className="mcp-tool-grid">
            {MCP_TOOLS.map((tool) => (
              <ToolCard key={tool.name} {...tool} />
            ))}
          </div>
        </section>

        {/* Sidebar */}
        <aside className="mcp-sidebar">
          {/* Console */}
          <Console tools={MCP_TOOLS} />

          {/* Config block */}
          <div className="mcp-config">
            <div className="mcp-config-header">
              <h3 className="mcp-config-title">claude_desktop_config.json</h3>
              <button
                className="mcp-config-copy"
                onClick={handleCopyConfig}
                title="Copy config"
              >
                {copied ? (
                  <>
                    <Check size={14} />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy size={14} />
                    Copy
                  </>
                )}
              </button>
            </div>
            <pre className="mcp-config-pre">{MCP_CONFIG}</pre>
          </div>
        </aside>
      </div>
    </div>
  )
}
