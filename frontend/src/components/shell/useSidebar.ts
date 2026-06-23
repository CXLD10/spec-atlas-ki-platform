import { useState, useEffect, useCallback } from 'react'

const STORAGE_KEY = 'sa.sidebar.collapsed'

interface UseSidebarReturn {
  collapsed: boolean
  toggleCollapsed: () => void
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

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(collapsed))
  }, [collapsed])

  const toggleCollapsed = useCallback(() => {
    setCollapsed(prev => !prev)
  }, [])

  return {
    collapsed,
    toggleCollapsed,
  }
}
