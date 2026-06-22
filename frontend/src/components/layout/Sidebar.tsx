import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { FileText, GitBranch, Settings, MessageSquare, Book, Github } from 'lucide-react'
import MCPModal from '../MCPModal'
import './Sidebar.css'

export function Sidebar() {
  const location = useLocation()
  const [showMCPModal, setShowMCPModal] = useState(false)

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path + '/')
  }

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>Spec-Atlas</h2>
      </div>
      <nav className="sidebar-nav">
        <Link
          to="/projects"
          className={`nav-link ${isActive('/projects') ? 'active' : ''}`}
        >
          <FileText size={18} />
          <span>Projects</span>
        </Link>
        <Link
          to="/graph"
          className={`nav-link ${isActive('/graph') ? 'active' : ''}`}
        >
          <GitBranch size={18} />
          <span>Graph Explorer</span>
        </Link>
        <Link
          to="/specify"
          className={`nav-link ${isActive('/specify') ? 'active' : ''}`}
        >
          <Settings size={18} />
          <span>Specify Tool</span>
        </Link>
        <Link
          to="/ask"
          className={`nav-link ${isActive('/ask') ? 'active' : ''}`}
        >
          <MessageSquare size={18} />
          <span>Ask</span>
        </Link>
        <Link
          to="/docs"
          className={`nav-link ${isActive('/docs') ? 'active' : ''}`}
        >
          <Book size={18} />
          <span>Docs</span>
        </Link>
        <a
          href="https://github.com/CXLD10/spec-atlas-ki-platform"
          target="_blank"
          rel="noopener noreferrer"
          className="nav-link"
        >
          <Github size={18} />
          <span>GitHub</span>
        </a>
      </nav>

      {/* MCP section */}
      <div className="mcp-section">
        <button
          className="btn-mcp"
          onClick={() => setShowMCPModal(true)}
        >
          🤖 MCP Server
        </button>
      </div>

      {/* MCP Modal */}
      {showMCPModal && <MCPModal onClose={() => setShowMCPModal(false)} />}
    </div>
  )
}
