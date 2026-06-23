import { Menu } from 'lucide-react'
import { useSidebar } from './useSidebar'
import './Topbar.css'

export function Topbar() {
  const { isMobile, openMobile } = useSidebar()

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
      <div className="topbar-breadcrumb">Spec-Atlas</div>
    </header>
  )
}
