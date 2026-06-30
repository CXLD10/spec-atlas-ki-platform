import { useEffect, useRef, useState } from 'react'
import './PipelineHUD.css'

const PHASES = [
  { id: 'inventory', label: 'Inventory',  sublabel: 'Scanning files',          threshold: 0  },
  { id: 'parse',     label: 'Parse',      sublabel: 'Extracting symbols',      threshold: 16 },
  { id: 'graph',     label: 'Graph',      sublabel: 'Building edges',          threshold: 32 },
  { id: 'cluster',   label: 'Cluster',    sublabel: 'Grouping components',     threshold: 50 },
  { id: 'spec',      label: 'Spec',       sublabel: 'Generating knowledge',    threshold: 68 },
  { id: 'embed',     label: 'Embed',      sublabel: 'Vectorising',             threshold: 85 },
]

interface PipelineHUDProps {
  progress: number // 0–100
}

function useAnimatedCounter(target: number, speed = 40): number {
  const [value, setValue] = useState(0)
  const ref = useRef(0)
  useEffect(() => {
    const step = Math.max(1, Math.ceil((target - ref.current) / speed))
    if (ref.current >= target) return
    const id = setInterval(() => {
      ref.current = Math.min(ref.current + step, target)
      setValue(ref.current)
      if (ref.current >= target) clearInterval(id)
    }, 30)
    return () => clearInterval(id)
  }, [target, speed])
  return value
}

export function PipelineHUD({ progress }: PipelineHUDProps) {
  const activePhaseIndex = PHASES.reduce((acc, p, i) => progress >= p.threshold ? i : acc, 0)

  // Derive counter targets from progress
  const fileTarget    = Math.floor((progress / 100) * 412)
  const symbolTarget  = Math.floor((progress / 100) * 3840)
  const edgeTarget    = Math.floor((progress / 100) * 1240)

  const files   = useAnimatedCounter(fileTarget)
  const symbols = useAnimatedCounter(symbolTarget)
  const edges   = useAnimatedCounter(edgeTarget)

  return (
    <div className="phud">
      <div className="phud-phases">
        {PHASES.map((phase, i) => {
          const state = i < activePhaseIndex ? 'done' : i === activePhaseIndex ? 'active' : 'pending'
          return (
            <div key={phase.id} className={`phud-phase phud-phase--${state}`}>
              <div className="phud-dot">
                {state === 'done' && <span className="phud-check">✓</span>}
                {state === 'active' && <span className="phud-pulse" />}
              </div>
              <div className="phud-phase-text">
                <span className="phud-phase-name">{phase.label}</span>
                <span className="phud-phase-sub">{phase.sublabel}</span>
              </div>
              {i < PHASES.length - 1 && <div className={`phud-connector ${state === 'done' ? 'phud-connector--lit' : ''}`} />}
            </div>
          )
        })}
      </div>

      <div className="phud-counters">
        <div className="phud-counter">
          <span className="phud-counter-val">{files.toLocaleString()}</span>
          <span className="phud-counter-lbl">files</span>
        </div>
        <div className="phud-counter-divider" />
        <div className="phud-counter">
          <span className="phud-counter-val">{symbols.toLocaleString()}</span>
          <span className="phud-counter-lbl">symbols</span>
        </div>
        <div className="phud-counter-divider" />
        <div className="phud-counter">
          <span className="phud-counter-val">{edges.toLocaleString()}</span>
          <span className="phud-counter-lbl">edges</span>
        </div>
      </div>
    </div>
  )
}
