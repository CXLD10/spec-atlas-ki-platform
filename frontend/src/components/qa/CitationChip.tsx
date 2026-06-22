import './CitationChip.css'

interface CitationChipProps {
  source: string // "file:line" or "document:page"
  onClick?: () => void
}

export function CitationChip({ source, onClick }: CitationChipProps) {
  const isDocCitation = source.includes(':p.')
  const isCodeCitation = source.includes(':') && !isDocCitation

  const handleClick = () => {
    onClick?.()
  }

  const chipClass = isDocCitation
    ? 'citation-chip citation-chip--doc'
    : isCodeCitation
      ? 'citation-chip citation-chip--code'
      : 'citation-chip citation-chip--unknown'

  const icon = isDocCitation ? '📄' : isCodeCitation ? '💻' : '•'

  return (
    <button
      className={chipClass}
      onClick={handleClick}
      title={`Citation: ${source}`}
    >
      <span className="chip-icon" aria-hidden="true">
        {icon}
      </span>
      <span className="chip-text">{source}</span>
    </button>
  )
}
