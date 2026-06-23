import { CheckCircle, Circle, Loader } from 'lucide-react'
import './TraceSteps.css'

export type StepStatus = 'queued' | 'running' | 'done'

export interface Step {
  id: string
  icon: React.ReactNode
  title: string
  detail: string
  status: StepStatus
}

interface TraceStepsProps {
  steps: Step[]
}

export function TraceSteps({ steps }: TraceStepsProps) {
  return (
    <div className="trace-steps">
      {steps.map((step, idx) => (
        <div key={step.id} className="trace-step">
          {/* Step connector (vertical line between steps) */}
          {idx < steps.length - 1 && (
            <div className={`trace-connector trace-connector--${step.status}`} />
          )}

          {/* Step content */}
          <div className={`trace-step-content trace-step--${step.status}`}>
            <div className="trace-step-icon">
              {step.status === 'done' && <CheckCircle size={20} />}
              {step.status === 'running' && <Loader size={20} className="trace-spinner" />}
              {step.status === 'queued' && <Circle size={20} />}
            </div>

            <div className="trace-step-text">
              <h3 className="trace-step-title">{step.title}</h3>
              <p className="trace-step-detail">{step.detail}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
