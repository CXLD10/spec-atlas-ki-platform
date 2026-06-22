import { LAYERS } from '../scene/layerConfig'
import './PipelineHUD.css'

interface PipelineHUDProps {
  activePhase: number // 0-4
}

export function PipelineHUD({ activePhase }: PipelineHUDProps) {
  return (
    <aside className="pipeline-hud" role="region" aria-label="Build progress stages">
      <ol className="stages-list">
        {LAYERS.map((layer) => (
          <li
            key={layer.id}
            className={`stage ${activePhase > layer.phaseIndex ? 'done' : activePhase === layer.phaseIndex ? 'active' : ''}`}
            style={{
              '--stage-color': layer.color,
            } as React.CSSProperties}
          >
            <span className="stage-indicator" aria-hidden="true">
              {activePhase > layer.phaseIndex ? '●' : '○'}
            </span>
            <span className="stage-label mono">{layer.label}</span>
          </li>
        ))}
      </ol>
    </aside>
  )
}
