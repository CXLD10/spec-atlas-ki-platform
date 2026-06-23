import { useState, useEffect, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Search, X } from 'lucide-react'
import { useSources, useCards } from '../../lib/hooks'
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

interface SearchResult {
  id: string
  type: 'source' | 'card'
  title: string
  subtitle?: string
  path: string
}

export function Topbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { data: sources = [] } = useSources()
  const { data: cards = [] } = useCards()

  const [searchQuery, setSearchQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [showResults, setShowResults] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)

  const getTitle = (pathname: string): string => {
    return routeTitles[pathname] || 'Spec-Atlas'
  }

  const title = getTitle(location.pathname)

  // Search logic
  useEffect(() => {
    if (!searchQuery.trim()) {
      setResults([])
      setShowResults(false)
      return
    }

    const query = searchQuery.toLowerCase()
    const searchResults: SearchResult[] = []

    // Search sources
    sources.forEach((source) => {
      if (source.name.toLowerCase().includes(query)) {
        searchResults.push({
          id: source.id,
          type: 'source',
          title: source.name,
          subtitle: source.subtitle,
          path: `/sources/${source.id}`,
        })
      }
    })

    // Search knowledge cards
    cards.forEach((card) => {
      if (
        card.title.toLowerCase().includes(query) ||
        card.markdown.toLowerCase().includes(query)
      ) {
        searchResults.push({
          id: card.ref,
          type: 'card',
          title: card.title,
          subtitle: `Status: ${card.status}`,
          path: `/kb/${card.ref}`,
        })
      }
    })

    setResults(searchResults.slice(0, 8))
    setShowResults(searchResults.length > 0)
  }, [searchQuery, sources, cards])

  // Close results when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowResults(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleResultClick = (result: SearchResult) => {
    navigate(result.path)
    setSearchQuery('')
    setShowResults(false)
  }

  return (
    <header className="topbar">
      <button
        className="topbar-home"
        onClick={() => navigate('/')}
        title="Go to Dashboard"
      >
        <img src="/spec-atlas-logo.png" alt="Spec-Atlas" className="topbar-logo" />
        <span className="breadcrumb-text">spec-atlas</span>
        {location.pathname !== '/' && (
          <>
            <span className="breadcrumb-separator">/</span>
            <span className="breadcrumb-title">{title}</span>
          </>
        )}
      </button>
      <div className="topbar-search-wrapper" ref={searchRef}>
        <div className="topbar-search">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder="Search sources, cards, symbols…"
            className="search-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => {
              if (searchQuery.trim() && results.length > 0) {
                setShowResults(true)
              }
            }}
          />
          {searchQuery && (
            <button
              className="search-clear"
              onClick={() => {
                setSearchQuery('')
                setShowResults(false)
              }}
              aria-label="Clear search"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {showResults && results.length > 0 && (
          <div className="search-results">
            {results.map((result) => (
              <button
                key={`${result.type}-${result.id}`}
                className={`search-result-item search-result--${result.type}`}
                onClick={() => handleResultClick(result)}
              >
                <div className="result-content">
                  <div className="result-title">{result.title}</div>
                  {result.subtitle && (
                    <div className="result-subtitle">{result.subtitle}</div>
                  )}
                </div>
                <span className="result-type">{result.type === 'source' ? '📁' : '📄'}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </header>
  )
}
