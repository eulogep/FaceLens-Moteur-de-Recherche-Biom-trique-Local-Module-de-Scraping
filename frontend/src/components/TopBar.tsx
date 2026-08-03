import type { ServiceState } from '../api/types'
import { AnimatedNumber } from './AnimatedNumber'
import { ReticleIcon } from './icons'
import { StatusLED } from './StatusLED'

interface TopBarProps {
  apiState: ServiceState
  searxState: ServiceState
  modelState: ServiceState
  faceCount: number
}

export function TopBar(props: TopBarProps) {
  return (
    <header className="topbar">
      <div className="brand">
        <ReticleIcon />
        <span>FACERLENS</span>
        <small>CONSOLE</small>
      </div>
      <div className="service-cluster">
        <StatusLED label="API" state={props.apiState} detail="FastAPI · localhost:8000" />
        <StatusLED label="SEARXNG" state={props.searxState} detail="Méta-moteur · localhost:8080" />
        <StatusLED
          label="MODÈLE"
          state={props.modelState}
          detail="buffalo_l · ArcFace 512-d · CPU"
        />
      </div>
      <div className="topbar__right">
        <div className="face-count">
          <span>FACES INDEXÉES</span>
          <strong><AnimatedNumber value={props.faceCount} /></strong>
        </div>
        <div className="disclaimer-badge">⚠ Similarité ≠ identité</div>
      </div>
    </header>
  )
}
