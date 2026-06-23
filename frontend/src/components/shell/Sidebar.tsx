import { useState, useEffect, useRef } from 'react'
import { NavLink } from 'react-router-dom'
import { Menu, Zap, FileText, Network, BookOpen, MessageCircle, Wrench, Webhook, Library, ShieldCheck } from 'lucide-react'
import { useSidebar } from './useSidebar'
import { ThemeToggle } from './ThemeToggle'
import './Sidebar.css'

export function Sidebar() {
  const { collapsed, toggleCollapsed } = useSidebar()
  const [mcpHealthy, setMcpHealthy] = useState(true)
  const sidebarRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/health')
        setMcpHealthy(res.ok)
      } catch {
        setMcpHealthy(false)
      }
    }
    checkHealth()
  }, [])

  // Close sidebar when clicking outside of it
  useEffect(() => {
    if (collapsed) return

    const handleClickOutside = (e: MouseEvent) => {
      if (sidebarRef.current && !sidebarRef.current.contains(e.target as Node)) {
        toggleCollapsed()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [collapsed, toggleCollapsed])

  const navGroups = [
    {
      label: 'WORKSPACE',
      items: [
        { icon: Zap, label: 'Dashboard', path: '/' },
        { icon: FileText, label: 'Sources', path: '/sources' },
        { icon: Library, label: 'Knowledge Base', path: '/kb' },
        { icon: Network, label: 'Knowledge Graph', path: '/graph' },
        { icon: MessageCircle, label: 'Ask Atlas', path: '/ask' },
        { icon: Wrench, label: 'Specify', path: '/specify' },
        { icon: ShieldCheck, label: 'Verification', path: '/reports' },
      ],
    },
    {
      label: 'INTEGRATE',
      items: [
        { icon: Webhook, label: 'MCP Server', path: '/mcp' },
        { icon: BookOpen, label: 'Docs', path: '/docs' },
      ],
    },
  ]

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`} ref={sidebarRef}>
      <div className="sidebar-header">
        <button
          className="sidebar-hamburger"
          aria-label="Toggle sidebar"
          aria-expanded={!collapsed}
          onClick={toggleCollapsed}
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          <Menu size={20} />
        </button>

        <NavLink
          to="/"
          className="sidebar-home"
          title="Spec-Atlas Home"
        >
          <span className="sidebar-logo">◆</span>
          {!collapsed && <span className="sidebar-wordmark">SPEC·ATLAS</span>}
        </NavLink>
      </div>

      <nav className="sidebar-nav">
        {navGroups.map((group) => (
          <div key={group.label} className="nav-group">
            {!collapsed && <div className="nav-group-label">{group.label}</div>}
            {collapsed && <div className="nav-group-divider" />}
            {group.items.map((item) => {
              const IconComponent = item.icon
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }: { isActive: boolean }) =>
                    `nav-item ${isActive ? 'active' : ''}`
                  }
                  aria-label={item.label}
                  title={item.label}
                >
                  <IconComponent size={20} className="nav-icon" />
                  {!collapsed && <span className="nav-label">{item.label}</span>}
                </NavLink>
              )
            })}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="footer-content">
          <div className={`footer-label ${mcpHealthy ? 'healthy' : 'unhealthy'}`}>
            <div className={`footer-dot ${mcpHealthy ? 'healthy' : 'unhealthy'}`} />
            {!collapsed && (mcpHealthy ? 'MCP ready' : 'MCP offline')}
          </div>
        </div>
        <ThemeToggle />
      </div>
    </aside>
  )
}
