import { sceneEvents } from '../scene/sceneEvents'
import './CitationChip.css'

interface CitationChipProps {
  file: string
  startLine: number
  endLine?: number
  layer?: 0 | 1 | 2 | 3 // L1-L4 for styling
  onClick?: () => void
}

const LAYER_COLORS = ['--l1', '--l2', '--l3', '--l4']
const DEFAULT_LAYER = 2 // L3 (amber)

export function CitationChip({
  file,
  startLine,
  endLine,
  layer = DEFAULT_LAYER,
  onClick,
}: CitationChipProps) {
  const handleClick = () => {
    onClick?.()
    sceneEvents.emit('fly-to-node', `${file}:${startLine}`)
  }

  const displayText = endLine && endLine !== startLine
    ? `${file}:${startLine}-${endLine}`
    : `${file}:${startLine}`

  const colorVar = LAYER_COLORS[layer]

  return (
    <button
      className="citation-chip"
      onClick={handleClick}
      title={`Jump to ${displayText}`}
      style={{
        '--chip-color': `var(${colorVar})`,
      } as React.CSSProperties}
    >
      <span className="chip-marker" aria-hidden="true">◆</span>
      <span className="chip-text">{displayText}</span>
    </button>
  )
}
