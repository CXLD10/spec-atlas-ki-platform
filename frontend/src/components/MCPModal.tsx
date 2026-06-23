import { X } from 'lucide-react'
import './MCPModal.css'

interface MCPModalProps {
  onClose: () => void
}

export default function MCPModal({ onClose }: MCPModalProps) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>
          <X size={20} />
        </button>

        <h2>MCP Server</h2>
        <p className="modal-subtitle">
          Spec-Atlas exposes a Model Context Protocol (MCP) server for external AI agents.
        </p>

        <div className="mcp-tools">
          <h3>Available Tools</h3>
          <ul>
            <li>
              <code>search_knowledge</code> — Search across code, docs, specs
            </li>
            <li>
              <code>get_spec</code> — Retrieve a spec by component
            </li>
            <li>
              <code>get_graph</code> — Get graph structure and relationships
            </li>
            <li>
              <code>ask_question</code> — Ask a question and get grounded answers
            </li>
          </ul>
        </div>

        <div className="mcp-usage">
          <h3>How to Use</h3>
          <p>Connect Claude Code, Codex, or other MCP-compatible agents:</p>
          <code className="code-block">
            spec-atlas-mcp --host=localhost --port=8001
          </code>
        </div>

        <p className="modal-note">
          🎯 Agents can fetch specs instead of re-reading your entire codebase.
        </p>

        <button className="btn btn-primary" onClick={onClose}>
          Got it
        </button>
      </div>
    </div>
  )
}
