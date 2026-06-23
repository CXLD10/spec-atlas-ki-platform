import { useLocation } from 'react-router-dom'
import { Menu, Search } from 'lucide-react'
import { useSidebar } from './useSidebar'
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
  const { isMobile, openMobile } = useSidebar()
  const location = useLocation()

  const getTitle = (pathname: string): string => {
    return routeTitles[pathname] || 'Spec-Atlas'
  }

  const title = getTitle(location.pathname)

  return (
    <header className="topbar">
      {isMobile && (
        <button
          className="topbar-hamburger"
          aria-label="Open navigation"
          onClick={openMobile}
        >
          <Menu size={20} />
        </button>
      )}
      <div className="topbar-breadcrumb">
        <span className="breadcrumb-text">spec-atlas</span>
        <span className="breadcrumb-separator">/</span>
        <span className="breadcrumb-title">{title}</span>
      </div>
      <div className="topbar-search">
        <Search size={16} className="search-icon" />
        <input
          type="text"
          placeholder="Search sources, cards, symbols…"
          className="search-input"
          disabled
        />
      </div>
    </header>
  )
}
