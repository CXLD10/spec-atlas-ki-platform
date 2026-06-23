import { Lock } from 'lucide-react'
import './ToolCard.css'

interface ToolCardProps {
  name: string
  signature: string
  description: string
}

export function ToolCard({ name, signature, description }: ToolCardProps) {
  return (
    <div className="tool-card">
      <div className="tool-card-header">
        <code className="tool-card-name">{name}</code>
        <span className="tool-card-badge">
          <Lock size={12} />
          FROZEN
        </span>
      </div>
      <code className="tool-card-signature">{signature}</code>
      <p className="tool-card-desc">{description}</p>
    </div>
  )
}
