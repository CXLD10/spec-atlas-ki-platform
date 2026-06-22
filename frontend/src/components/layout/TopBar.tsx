import { Link } from 'react-router-dom'
import { ThemeToggle } from './ThemeToggle'
import './TopBar.css'

interface TopBarProps {
  variant?: 'marketing' | 'workspace'
}

export function TopBar({ variant = 'marketing' }: TopBarProps) {
  return (
    <header className="top-bar">
      <div className="top-bar-content">
        <Link to="/" className="brand">
          <span className="brand-mark">◆</span>
          <span className="brand-text">SPEC·ATLAS</span>
        </Link>

        <nav className="top-nav">
          {variant === 'marketing' && (
            <>
              <Link to={`/repo/default/graphify`}>Graph Explorer</Link>
              <Link to={`/repo/default/specify`}>Specify Tool</Link>
              <Link to={`/docs`}>Docs</Link>
              <a href="https://github.com/anthropics/spec-atlas" target="_blank" rel="noreferrer">
                GitHub
              </a>
            </>
          )}
          {variant === 'workspace' && (
            <>
              <Link to={`/repo/default/ask`}>Ask</Link>
              <Link to={`/repo/default/explore`}>Explore</Link>
            </>
          )}
        </nav>

        <ThemeToggle />
      </div>
    </header>
  )
}
