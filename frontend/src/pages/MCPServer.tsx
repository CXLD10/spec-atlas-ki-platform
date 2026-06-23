import { useEffect, useState } from 'react'
import { Copy, Check, Circle } from 'lucide-react'
import { ToolCard } from '../components/mcp/ToolCard'
import { Console } from '../components/mcp/Console'
import { client, MockFallback } from '../lib/api'
import './MCPServer.css'

const MCP_TOOLS = [
  {
    name: 'search',
    signature: 'search(query: string, repo?: string) → SearchResult[]',
    description: 'Runs the full router→retriever→answerer pipeline and returns matched groups, specs and provenance.',
  },
  {
    name: 'get_spec',
    signature: 'get_spec(component_ref: string, repo?: string) → Spec',
    description: 'Fetches the current spec/card with purpose, I/O, invariants, status and citations.',
  },
  {
    name: 'get_group',
    signature: 'get_group(group_path: string, repo?: string) → Group',
    description: 'Returns a group/domain summary, child groups and member specs.',
  },
  {
    name: 'list_stale_specs',
    signature: 'list_stale_specs(repo?: string) → Spec[]',
    description: 'Lists specs whose source has drifted and need regeneration.',
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
        await client.health()
        setHealthy(true)
      } catch (err) {
        if (err instanceof MockFallback) {
          setHealthy(true) // Mock is OK
        } else {
          setHealthy(false)
        }
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
