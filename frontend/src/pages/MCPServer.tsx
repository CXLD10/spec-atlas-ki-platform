import { useEffect, useState } from 'react'
import { Copy, Check, Circle } from 'lucide-react'
import { ToolCard } from '../components/mcp/ToolCard'
import { Console } from '../components/mcp/Console'
import { client } from '../api/client'
import './MCPServer.css'

const MCP_TOOLS = [
  {
    name: 'spec_atlas_ask',
    signature: 'spec_atlas_ask(question: string, repo?: string, strategy?: "vector"|"graph"|"hybrid") → Answer',
    description: 'Answer a natural-language question using the full knowledge graph. Returns a grounded answer with source citations and a confidence score.',
    params: [
      { name: 'question', type: 'string', required: true,  desc: 'The question to answer' },
      { name: 'repo',     type: 'string', required: false, desc: 'Repository name to scope the search (defaults to all)' },
      { name: 'strategy', type: '"vector"|"graph"|"hybrid"', required: false, desc: 'Retrieval strategy — defaults to "hybrid"' },
    ],
  },
  {
    name: 'spec_atlas_search',
    signature: 'spec_atlas_search(query: string, repo?: string, limit?: number) → SearchResult[]',
    description: 'Semantic search across all indexed sources. Runs the full router → retriever pipeline and returns matched groups and source units with relevance scores.',
    params: [
      { name: 'query', type: 'string', required: true,  desc: 'Natural-language or keyword search query' },
      { name: 'repo',  type: 'string', required: false, desc: 'Repository name to restrict search scope' },
      { name: 'limit', type: 'number', required: false, desc: 'Max results to return (default 10)' },
    ],
  },
  {
    name: 'spec_atlas_get_spec',
    signature: 'spec_atlas_get_spec(component_ref: string, repo?: string, version?: number) → Spec',
    description: 'Retrieve a structured spec for any component. Returns the knowledge card with purpose, inputs, outputs, invariants, and provenance citations.',
    params: [
      { name: 'component_ref', type: 'string', required: true,  desc: 'Qualified component name (e.g. "InferenceEngine")' },
      { name: 'repo',          type: 'string', required: false, desc: 'Repository name (defaults to first indexed repo)' },
      { name: 'version',       type: 'number', required: false, desc: 'Spec version to retrieve (defaults to latest)' },
    ],
  },
  {
    name: 'spec_atlas_list_groups',
    signature: 'spec_atlas_list_groups(repo?: string, include_summary?: boolean) → Group[]',
    description: 'List all knowledge groups with summaries. Returns semantic clusters auto-generated from the codebase with member counts and purpose summaries.',
    params: [
      { name: 'repo',            type: 'string',  required: false, desc: 'Repository to list groups for' },
      { name: 'include_summary', type: 'boolean', required: false, desc: 'Include full group summary text (default true)' },
    ],
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
