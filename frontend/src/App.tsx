import { useCallback, useEffect, useState } from 'react'
import { api, checkSearxng } from './api/client'
import type {
  Face,
  JournalEvent,
  JournalInput,
  ScreenId,
  ServiceState,
  Stats,
} from './api/types'
import { Rail } from './components/Rail'
import { ToastRegion, type ToastMessage } from './components/Toast'
import { TopBar } from './components/TopBar'
import { ComparisonScreen } from './screens/ComparisonScreen'
import { CorpusScreen } from './screens/CorpusScreen'
import { JournalScreen } from './screens/JournalScreen'
import { SearchScreen } from './screens/SearchScreen'
import { ScrapingScreen } from './screens/ScrapingScreen'
import './styles/tokens.css'
import './styles/app.css'

const JOURNAL_STORAGE_KEY = 'facelens.journal.v1'

function readJournal(): JournalEvent[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(JOURNAL_STORAGE_KEY) ?? '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export default function App() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [apiState, setApiState] = useState<ServiceState>('checking')
  const [searxState, setSearxState] = useState<ServiceState>('checking')
  const [modelState, setModelState] = useState<ServiceState>('checking')
  const [toasts, setToasts] = useState<ToastMessage[]>([])
  const [activeScreen, setActiveScreen] = useState<ScreenId>('search')
  const [faceCount, setFaceCount] = useState(0)
  const [searchSeed, setSearchSeed] = useState<File | null>(null)
  const [activeJobs, setActiveJobs] = useState(0)
  const [journal, setJournal] = useState<JournalEvent[]>(readJournal)

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

  useEffect(() => {
    localStorage.setItem(JOURNAL_STORAGE_KEY, JSON.stringify(journal))
  }, [journal])

  const addJournal = useCallback((entry: JournalInput) => {
    setJournal((current) => [{
      ...entry,
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
    }, ...current].slice(0, 500))
  }, [])

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
        activeJobs={activeJobs}
        activeScreen={activeScreen}
        onNavigate={setActiveScreen}
      />
      <main className="workspace">
        <div className="screen-stage" hidden={activeScreen !== 'search'}>
          <SearchScreen
            onToast={pushToast}
            onCorpusChanged={handleCorpusChanged}
            onJournal={addJournal}
            initialFile={searchSeed}
          />
        </div>
        <div className="screen-stage" hidden={activeScreen !== 'compare'}>
          <ComparisonScreen onToast={pushToast} onJournal={addJournal} />
        </div>
        <div className="screen-stage" hidden={activeScreen !== 'corpus'}>
          <CorpusScreen
            totalFaces={faceCount}
            sourceTypes={Object.keys(stats?.faces_by_source_type ?? {})}
            onDeleteComplete={handleCorpusChanged}
            onDomainExcluded={handleDomainExcluded}
            onSearchSimilar={searchSimilar}
            onToast={pushToast}
            onJournal={addJournal}
          />
        </div>
        <div className="screen-stage" hidden={activeScreen !== 'scraping'}>
          <ScrapingScreen
            onActiveJobsChange={setActiveJobs}
            onCorpusChanged={handleCorpusChanged}
            onJournal={addJournal}
            onToast={pushToast}
          />
        </div>
        <div className="screen-stage" hidden={activeScreen !== 'journal'}>
          <JournalScreen events={journal} onClear={() => setJournal([])} />
        </div>
      </main>
      <ToastRegion toasts={toasts} onDismiss={dismissToast} />
    </div>
  )
}
