import { NavLink } from 'react-router-dom'
import { Menu, Zap, FileText, Network, MessageCircle, Wrench, Webhook, BookOpen } from 'lucide-react'
import { useSidebar } from './useSidebar'
import './Sidebar.css'

export function Sidebar() {
  const { collapsed, toggleCollapsed } = useSidebar()

  const navGroups = [
    {
      label: 'WORKSPACE',
      items: [
        { icon: Zap, label: 'Dashboard', path: '/' },
        { icon: FileText, label: 'Sources', path: '/sources' },
        { icon: Network, label: 'Knowledge Base', path: '/kb' },
        { icon: Network, label: 'Knowledge Graph', path: '/graph' },
        { icon: MessageCircle, label: 'Ask Atlas', path: '/ask' },
        { icon: Wrench, label: 'Specify', path: '/specify' },
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

  const railWidth = collapsed ? '64px' : '248px'

  return (
    <aside
      className="sidebar"
      style={{ '--rail': railWidth } as React.CSSProperties}
    >
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
          className={`sidebar-home ${collapsed ? 'collapsed' : ''}`}
          title="Spec-Atlas Home"
        >
          <span className="sidebar-logo">◆</span>
          {!collapsed && <span className="sidebar-wordmark">SPEC·ATLAS</span>}
        </NavLink>
      </div>

      <nav className="sidebar-nav">
        {navGroups.map((group) => (
          <div key={group.label} className="nav-group">
            <div className="nav-group-label">{group.label}</div>
            {group.items.map((item) => {
              const IconComponent = item.icon
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }: { isActive: boolean }) =>
                    `nav-item ${isActive ? 'active' : ''} ${collapsed ? 'collapsed' : ''}`
                  }
                  title={collapsed ? item.label : undefined}
                >
                  <IconComponent size={18} className="nav-icon" />
                  {!collapsed && <span className="nav-label">{item.label}</span>}
                </NavLink>
              )
            })}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        {!collapsed && <span className="footer-label">● MCP · 4 tools live</span>}
        {collapsed && <span className="footer-dot">●</span>}
      </div>
    </aside>
  )
}
