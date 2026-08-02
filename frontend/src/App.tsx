import { useCallback, useEffect, useState } from 'react'
import { api, checkSearxng } from './api/client'
import type { Face, ScreenId, ServiceState, Stats } from './api/types'
import { Rail } from './components/Rail'
import { ToastRegion, type ToastMessage } from './components/Toast'
import { TopBar } from './components/TopBar'
import { ComparisonScreen } from './screens/ComparisonScreen'
import { CorpusScreen } from './screens/CorpusScreen'
import { SearchScreen } from './screens/SearchScreen'
import './styles/tokens.css'
import './styles/app.css'

export default function App() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [apiState, setApiState] = useState<ServiceState>('checking')
  const [searxState, setSearxState] = useState<ServiceState>('checking')
  const [modelState, setModelState] = useState<ServiceState>('checking')
  const [toasts, setToasts] = useState<ToastMessage[]>([])
  const [activeScreen, setActiveScreen] = useState<ScreenId>('search')
  const [faceCount, setFaceCount] = useState(0)
  const [searchSeed, setSearchSeed] = useState<File | null>(null)

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
    const [apiResult, searxResult, statsResult, countResult] = await Promise.allSettled([
      api.checkApi(),
      checkSearxng(),
      api.getStats(),
      api.getFaceCount(),
    ])
    setApiState(apiResult.status === 'fulfilled' ? 'healthy' : 'down')
    setSearxState(
      searxResult.status === 'fulfilled' && searxResult.value ? 'healthy' : 'down',
    )
    if (statsResult.status === 'fulfilled') {
      setStats(statsResult.value)
      setModelState(statsResult.value.integrity_verified ? 'healthy' : 'down')
      if (countResult.status !== 'fulfilled') {
        setFaceCount(statsResult.value.total_indexed_faces)
      }
    } else {
      setModelState('down')
    }
    if (countResult.status === 'fulfilled') setFaceCount(countResult.value.total)
  }, [])

  useEffect(() => {
    void refreshHealth()
    const interval = window.setInterval(refreshHealth, 15_000)
    return () => window.clearInterval(interval)
  }, [refreshHealth])

  const handleCorpusChanged = useCallback(() => {
    void refreshHealth()
  }, [refreshHealth])

  const handleDomainExcluded = useCallback(() => {
    void refreshHealth()
  }, [refreshHealth])

  const searchSimilar = useCallback(async (face: Face) => {
    try {
      const file = await api.downloadFaceImage(face)
      setSearchSeed(file)
      setActiveScreen('search')
      pushToast(`Face #${face.id} chargée comme nouvel échantillon.`, 'info')
    } catch (error) {
      pushToast(error instanceof Error ? error.message : "Chargement de l'image impossible.", 'error')
    }
  }, [pushToast])

  return (
    <div className="app-shell">
      <TopBar
        apiState={apiState}
        searxState={searxState}
        modelState={modelState}
        faceCount={faceCount}
      />
      <Rail
        corpusCount={faceCount}
        activeJobs={0}
        activeScreen={activeScreen}
        onNavigate={setActiveScreen}
        onUnavailable={(label) => pushToast(`${label} sera livré en phase 3.`, 'info')}
      />
      <main className="workspace">
        <div className="screen-stage" hidden={activeScreen !== 'search'}>
          <SearchScreen
            onToast={pushToast}
            onCorpusChanged={handleCorpusChanged}
            initialFile={searchSeed}
          />
        </div>
        <div className="screen-stage" hidden={activeScreen !== 'compare'}>
          <ComparisonScreen onToast={pushToast} />
        </div>
        <div className="screen-stage" hidden={activeScreen !== 'corpus'}>
          <CorpusScreen
            totalFaces={faceCount}
            sourceTypes={Object.keys(stats?.faces_by_source_type ?? {})}
            onDeleteComplete={handleCorpusChanged}
            onDomainExcluded={handleDomainExcluded}
            onSearchSimilar={searchSimilar}
            onToast={pushToast}
          />
        </div>
      </main>
      <ToastRegion toasts={toasts} onDismiss={dismissToast} />
    </div>
  )
}
