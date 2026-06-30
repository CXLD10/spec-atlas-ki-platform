import { Lock } from 'lucide-react'
import './ToolCard.css'

interface Param {
  name: string
  type: string
  required: boolean
  desc: string
}

interface ToolCardProps {
  name: string
  signature: string
  description: string
  params?: Param[]
}

export function ToolCard({ name, signature, description, params }: ToolCardProps) {
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
      {params && params.length > 0 && (
        <div className="tool-card-params">
          {params.map(p => (
            <div key={p.name} className="tool-param">
              <span className="tool-param-name">{p.name}</span>
              <span className="tool-param-type">{p.type}</span>
              {p.required && <span className="tool-param-required">required</span>}
              <span className="tool-param-desc">{p.desc}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
