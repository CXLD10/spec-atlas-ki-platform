import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { useSidebar } from './useSidebar'
import './AppShell.css'

export function AppShell() {
  const { collapsed } = useSidebar()
  const railWidth = collapsed ? '0px' : '248px'

  return (
    <div className="app-shell" style={{ '--rail': railWidth } as React.CSSProperties}>
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
