import { useLocation, useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import './Topbar.css'

const routeTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/sources': 'Sources',
  '/kb': 'Knowledge Base',
  '/graph': 'Knowledge Graph',
  '/ask': 'Ask Atlas',
  '/specify': 'Specify',
  '/mcp': 'MCP Server',
  '/docs': 'Docs',
}

export function Topbar() {
  const location = useLocation()
  const navigate = useNavigate()

  const getTitle = (pathname: string): string => {
    return routeTitles[pathname] || 'Spec-Atlas'
  }

  const title = getTitle(location.pathname)

  return (
    <header className="topbar">
      <button
        className="topbar-home"
        onClick={() => navigate('/')}
        title="Go to Dashboard"
      >
        <span className="breadcrumb-text">spec-atlas</span>
        {location.pathname !== '/' && (
          <>
            <span className="breadcrumb-separator">/</span>
            <span className="breadcrumb-title">{title}</span>
          </>
        )}
      </button>
      <div className="topbar-search">
        <Search size={16} className="search-icon" />
        <input
          type="text"
          placeholder="Search sources, cards, symbols…"
          className="search-input"
        />
      </div>
    </header>
  )
}
