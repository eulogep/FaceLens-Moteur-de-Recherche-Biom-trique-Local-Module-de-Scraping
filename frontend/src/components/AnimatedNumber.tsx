import { useEffect, useRef, useState } from 'react'

interface AnimatedNumberProps {
  value: number
  duration?: number
}

export function AnimatedNumber({ value, duration = 500 }: AnimatedNumberProps) {
  const [shown, setShown] = useState(0)
  const current = useRef(0)

  useEffect(() => {
    const start = current.current
    const startedAt = performance.now()
    let frame = 0

    const tick = (now: number) => {
      const progress = Math.min(1, (now - startedAt) / duration)
      const next = Math.round(start + (value - start) * progress)
      current.current = next
      setShown(next)
      if (progress < 1) frame = requestAnimationFrame(tick)
    }

    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [duration, value])

  return <>{shown}</>
}
