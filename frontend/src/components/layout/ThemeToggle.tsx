import { useTheme } from '../../app/theme/ThemeProvider'
import './ThemeToggle.css'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()

  return (
    <button
      className="theme-toggle"
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      title={`Current theme: ${theme}`}
    >
      <span className="toggle-icon" aria-hidden="true">
        {theme === 'dark' ? '◐' : '◑'}
      </span>
    </button>
  )
}
