import type { ServiceState } from '../api/types'

interface StatusLEDProps {
  label: string
  state: ServiceState
  detail: string
}

export function StatusLED({ label, state, detail }: StatusLEDProps) {
  return (
    <div className="status-led" data-state={state} title={detail}>
      <span className="status-led__dot" />
      <span>{label}</span>
    </div>
  )
}
