import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { Job, JournalInput, Stats } from '../api/types'
import { AnimatedNumber } from '../components/AnimatedNumber'
import { JobCard } from '../components/JobCard'
import { SpiderIcon } from '../components/icons'
import type { ToastMessage } from '../components/Toast'

const JOBS_STORAGE_KEY = 'facelens.scrape-jobs.v1'

interface ScrapingScreenProps {
  onActiveJobsChange: (count: number) => void
  onCorpusChanged: () => void
  onJournal: (entry: JournalInput) => void
  onToast: (text: string, tone?: ToastMessage['tone']) => void
}

function readStoredJobs(): Job[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(JOBS_STORAGE_KEY) ?? '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function ScrapingScreen({
  onActiveJobsChange,
  onCorpusChanged,
  onJournal,
  onToast,
}: ScrapingScreenProps) {
  const [tab, setTab] = useState<'url' | 'search'>('url')
  const [url, setUrl] = useState('')
  const [maxImages, setMaxImages] = useState(30)
  const [sourceType, setSourceType] = useState('web')
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(10)
  const [jobs, setJobs] = useState<Job[]>(readStoredJobs)
  const [stats, setStats] = useState<Stats | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const terminalLogged = useRef(new Set<string>())

  const refreshStats = useCallback(async () => {
    try {
      setStats(await api.getStats())
    } catch (error) {
      onToast(error instanceof Error ? error.message : 'Statistiques indisponibles.', 'error')
    }
  }, [onToast])

  useEffect(() => {
    void refreshStats()
  }, [refreshStats])

  useEffect(() => {
    localStorage.setItem(JOBS_STORAGE_KEY, JSON.stringify(jobs.slice(0, 50)))
  }, [jobs])

  const activeJobIds = useMemo(
    () => jobs
      .filter((job) => job.status === 'pending' || job.status === 'running')
      .map((job) => job.job_id),
    [jobs],
  )
  const activeKey = activeJobIds.join('|')

  useEffect(() => {
    onActiveJobsChange(activeJobIds.length)
  }, [activeJobIds.length, onActiveJobsChange])

  useEffect(() => {
    if (!activeKey) return
    let cancelled = false

    const poll = async () => {
      const ids = activeKey.split('|')
      const responses = await Promise.allSettled(ids.map((id) => api.getJobStatus(id)))
      if (cancelled) return

      const updates = new Map<string, Job>()
      responses.forEach((response, index) => {
        const jobId = ids[index]
        if (response.status === 'fulfilled') {
          updates.set(jobId, response.value)
          if (
            ['completed', 'partial', 'failed'].includes(response.value.status)
            && !terminalLogged.current.has(jobId)
          ) {
            terminalLogged.current.add(jobId)
            onJournal({
              action: 'JOB TERMINÉ',
              target: response.value.target_url,
              result: `${response.value.status} · ${response.value.faces_indexed} face(s)`,
              tone: response.value.status === 'failed' ? 'error' : 'success',
            })
            onCorpusChanged()
            void refreshStats()
          }
        } else {
          setJobs((current) => current.map((job) => job.job_id === jobId
            ? { ...job, status: 'failed', updated_at: new Date().toISOString() }
            : job))
        }
      })

      if (updates.size) {
        setJobs((current) => current.map((job) => updates.get(job.job_id) ?? job))
      }
    }

    void poll()
    const interval = window.setInterval(poll, 3_000)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [activeKey, onCorpusChanged, onJournal, refreshStats])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (submitting) return

    if (tab === 'url') {
      try {
        const parsed = new URL(url)
        if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error()
      } catch {
        onToast('Saisissez une URL publique HTTP(S) valide.', 'error')
        return
      }
    } else if (!query.trim()) {
      onToast('Saisissez une requête de recherche.', 'error')
      return
    }

    setSubmitting(true)
    try {
      const response = tab === 'url'
        ? await api.startUrlJob({
          url: url.trim(),
          max_images: maxImages,
          source_type: sourceType,
          dry_run: false,
        })
        : await api.startSearchJob({
          query: query.trim(),
          engine: 'searxng',
          limit,
          dry_run: false,
        })

      const now = new Date().toISOString()
      const job: Job = {
        ...response,
        status: 'pending',
        total_images: 0,
        faces_indexed: 0,
        duplicates_skipped: 0,
        errors_by_domain: {},
        created_at: now,
        updated_at: now,
      }
      setJobs((current) => [job, ...current.filter((item) => item.job_id !== job.job_id)])
      onJournal({
        action: 'JOB CRÉÉ',
        target: response.target_url,
        result: response.job_id,
        tone: 'info',
      })
      onToast(`Job ${response.job_id} lancé.`, 'success')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Création du job impossible.'
      onJournal({
        action: 'JOB REFUSÉ',
        target: tab === 'url' ? url : query,
        result: message,
        tone: 'error',
      })
      onToast(message, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="scraping-screen">
      <header className="screen-heading">
        <div>
          <span className="eyebrow">COLLECTE PUBLIQUE / SEARXNG</span>
          <h1>Scraping contrôlé</h1>
        </div>
        <span className="case-chip">ROBOTS.TXT · 2–5 S</span>
      </header>

      <section className="scrape-stats" aria-busy={!stats}>
        <div><strong>{stats ? <AnimatedNumber value={stats.total_jobs} /> : <span className="stat-skeleton" />}</strong><span>JOBS</span></div>
        <div><strong>{stats ? <AnimatedNumber value={stats.scraped_faces} /> : <span className="stat-skeleton" />}</strong><span>FACES SCRAPÉES</span></div>
        <div><strong>{stats ? <AnimatedNumber value={stats.total_indexed_faces} /> : <span className="stat-skeleton" />}</strong><span>INDEX TOTAL</span></div>
        <div><strong>{stats ? <AnimatedNumber value={stats.excluded_domains_count} /> : <span className="stat-skeleton" />}</strong><span>DOMAINES EXCLUS</span></div>
      </section>

      <div className="scraping-layout">
        <form className="new-job-panel" onSubmit={submit}>
          <div className="job-tabs">
            <button type="button" data-active={tab === 'url'} onClick={() => setTab('url')}>URL PUBLIQUE</button>
            <button type="button" data-active={tab === 'search'} onClick={() => setTab('search')}>RECHERCHE</button>
          </div>

          {tab === 'url' ? (
            <div className="job-form-fields">
              <label>
                <span>URL CIBLE</span>
                <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.org/page-publique" />
              </label>
              <div className="job-form-row">
                <label>
                  <span>MAX IMAGES</span>
                  <input type="number" min="1" max="500" value={maxImages} onChange={(event) => setMaxImages(Number(event.target.value))} />
                </label>
                <label>
                  <span>TYPE DE SOURCE</span>
                  <select value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
                    <option value="web">Web</option>
                    <option value="presse">Presse</option>
                    <option value="forum">Forum public</option>
                  </select>
                </label>
              </div>
            </div>
          ) : (
            <div className="job-form-fields">
              <label>
                <span>REQUÊTE SEARXNG</span>
                <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="pseudo photo profil" />
              </label>
              <div className="job-form-row">
                <label>
                  <span>MOTEUR</span>
                  <input value="searxng" disabled />
                </label>
                <label>
                  <span>LIMITE</span>
                  <input type="number" min="1" max="100" value={limit} onChange={(event) => setLimit(Number(event.target.value))} />
                </label>
              </div>
            </div>
          )}

          <div className="scrape-compliance">
            Sources publiques uniquement · aucune page authentifiée, paywall ou captcha.
          </div>
          <button className="launch-job-button" type="submit" disabled={submitting}>
            {submitting ? <><span className="reticle-spinner" /> CRÉATION…</> : <><SpiderIcon /> LANCER LE JOB</>}
          </button>
        </form>

        <section className="jobs-panel">
          <div className="jobs-panel__header">
            <div>
              <span className="eyebrow">POLLING / 3 SECONDES</span>
              <h2>JOBS RÉCENTS</h2>
            </div>
            <span>{activeJobIds.length} ACTIF(S)</span>
          </div>
          <div className="jobs-list">
            {jobs.length ? jobs.map((job) => <JobCard key={job.job_id} job={job} />) : (
              <div className="jobs-empty">
                <SpiderIcon />
                <strong>Aucun job dans cette session</strong>
                <span>Les nouveaux jobs apparaîtront ici avec leur progression.</span>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
