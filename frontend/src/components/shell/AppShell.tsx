import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { useSidebar } from './useSidebar'
import './AppShell.css'

export function AppShell() {
  const { collapsed, toggleCollapsed } = useSidebar()
  const railWidth = collapsed ? '50px' : '248px'

  const handleBackdropClick = () => {
    if (!collapsed) {
      toggleCollapsed()
    }
  }

  return (
    <div className="app-shell" style={{ '--rail': railWidth } as React.CSSProperties}>
      {!collapsed && (
        <div className="sidebar-backdrop" onClick={handleBackdropClick} />
      )}
      <Sidebar />
      <div className="app-shell-main">
        <Topbar />
        <div className="app-shell-content">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
