import { useEffect, useState } from 'react'

interface GaugeProps {
  value: number
  threshold?: number
  tone?: 'signal' | 'amber' | 'coral'
}

export function Gauge({ value, threshold = 0.7, tone = 'signal' }: GaugeProps) {
  const [animated, setAnimated] = useState(0)
  const clamped = Math.max(0, Math.min(1, value))

  useEffect(() => {
    setAnimated(0)
    const frame = requestAnimationFrame(() => setAnimated(clamped))
    return () => cancelAnimationFrame(frame)
  }, [clamped])

  return (
    <div className="gauge" aria-label={`Score ${(clamped * 100).toFixed(1)} %`}>
      <span
        className="gauge__fill"
        data-tone={tone}
        style={{ width: `${animated * 100}%` }}
      />
      <span
        className="gauge__threshold"
        style={{ left: `${threshold * 100}%` }}
        title={`Seuil ${threshold}`}
      />
    </div>
  )
}
