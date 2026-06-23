import { useState, useEffect, useCallback } from 'react'

const STORAGE_KEY = 'sa.sidebar'

interface UseSidebarReturn {
  collapsed: boolean
  toggleCollapsed: () => void
  mobileOpen: boolean
  openMobile: () => void
  closeMobile: () => void
  isMobile: boolean
}

export function useSidebar(): UseSidebarReturn {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      return stored ? JSON.parse(stored) : false
    } catch {
      return false
    }
  })

  const [mobileOpen, setMobileOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 768)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(collapsed))
  }, [collapsed])

  const toggleCollapsed = useCallback(() => {
    setCollapsed(prev => !prev)
  }, [])

  const openMobile = useCallback(() => {
    setMobileOpen(true)
  }, [])

  const closeMobile = useCallback(() => {
    setMobileOpen(false)
  }, [])

  useEffect(() => {
    const handleMediaChange = (e: MediaQueryListEvent) => {
      setIsMobile(e.matches)
    }

    const mediaQuery = window.matchMedia('(max-width: 767px)')
    mediaQuery.addEventListener('change', handleMediaChange)
    // Set initial state from media query to ensure accuracy
    setIsMobile(mediaQuery.matches)

    return () => {
      mediaQuery.removeEventListener('change', handleMediaChange)
    }
  }, [])

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && mobileOpen) {
        closeMobile()
      }
    }

    if (mobileOpen) {
      document.addEventListener('keydown', handleEscape)
      return () => {
        document.removeEventListener('keydown', handleEscape)
      }
    }
  }, [mobileOpen, closeMobile])

  return {
    collapsed,
    toggleCollapsed,
    mobileOpen,
    openMobile,
    closeMobile,
    isMobile,
  }
}
