import { useCallback, useEffect, useState } from 'react'
import { api, checkSearxng } from './api/client'
import type { ServiceState, Stats } from './api/types'
import { Rail } from './components/Rail'
import { ToastRegion, type ToastMessage } from './components/Toast'
import { TopBar } from './components/TopBar'
import { SearchScreen } from './screens/SearchScreen'
import './styles/tokens.css'
import './styles/app.css'

export default function App() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [apiState, setApiState] = useState<ServiceState>('checking')
  const [searxState, setSearxState] = useState<ServiceState>('checking')
  const [modelState, setModelState] = useState<ServiceState>('checking')
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const pushToast = useCallback((
    text: string,
    tone: ToastMessage['tone'] = 'error',
  ) => {
    setToasts((current) => [
      ...current,
      { id: Date.now() + Math.random(), text, tone },
    ])
  }, [])

  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const refreshHealth = useCallback(async () => {
    const [apiResult, searxResult, statsResult] = await Promise.allSettled([
      api.checkApi(),
      checkSearxng(),
      api.getStats(),
    ])
    setApiState(apiResult.status === 'fulfilled' ? 'healthy' : 'down')
    setSearxState(
      searxResult.status === 'fulfilled' && searxResult.value ? 'healthy' : 'down',
    )
    if (statsResult.status === 'fulfilled') {
      setStats(statsResult.value)
      setModelState(statsResult.value.integrity_verified ? 'healthy' : 'down')
    } else {
      setModelState('down')
    }
  }, [])

  useEffect(() => {
    void refreshHealth()
    const interval = window.setInterval(refreshHealth, 15_000)
    return () => window.clearInterval(interval)
  }, [refreshHealth])

  return (
    <div className="app-shell">
      <TopBar
        apiState={apiState}
        searxState={searxState}
        modelState={modelState}
        faceCount={stats?.total_indexed_faces ?? 0}
      />
      <Rail
        corpusCount={stats?.total_indexed_faces ?? 0}
        activeJobs={0}
        onUnavailable={(label) => pushToast(`${label} sera livré dans la phase suivante.`, 'info')}
      />
      <main className="workspace">
        <SearchScreen onToast={pushToast} onCorpusChanged={refreshHealth} />
      </main>
      <ToastRegion toasts={toasts} onDismiss={dismissToast} />
    </div>
  )
}
