import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import type { ExcludedDomain, Face } from '../api/types'
import { CorpusCard } from '../components/CorpusCard'
import { CloseIcon, CorpusIcon, TrashIcon } from '../components/icons'
import type { ToastMessage } from '../components/Toast'

const PAGE_SIZE = 24

interface CorpusScreenProps {
  totalFaces: number
  sourceTypes: string[]
  onDeleteComplete: () => void
  onDomainExcluded: () => void
  onSearchSimilar: (face: Face) => void
  onToast: (text: string, tone?: ToastMessage['tone']) => void
}

type SortMode = 'date-desc' | 'date-asc' | 'source'

function normalizeDomain(value: string) {
  const trimmed = value.trim().toLowerCase()
  if (!trimmed) return ''
  try {
    const url = new URL(trimmed.includes('://') ? trimmed : `https://${trimmed}`)
    return url.hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}

export function CorpusScreen({
  totalFaces,
  sourceTypes,
  onDeleteComplete,
  onDomainExcluded,
  onSearchSimilar,
  onToast,
}: CorpusScreenProps) {
  const [faces, setFaces] = useState<Face[]>([])
  const [listTotal, setListTotal] = useState(0)
  const [query, setQuery] = useState('')
  const [sourceFilter, setSourceFilter] = useState('all')
  const [sort, setSort] = useState<SortMode>('date-desc')
  const [page, setPage] = useState(0)
  const [reloadToken, setReloadToken] = useState(0)
  const [loading, setLoading] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<Face | null>(null)
  const [removingId, setRemovingId] = useState<number | null>(null)
  const [domainInput, setDomainInput] = useState('')
  const [domainTarget, setDomainTarget] = useState<string | null>(null)
  const [excludedDomains, setExcludedDomains] = useState<ExcludedDomain[]>([])
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    const timer = window.setTimeout(async () => {
      try {
        const response = await api.listFaces({
          limit: PAGE_SIZE,
          offset: page * PAGE_SIZE,
          sourceType: sourceFilter === 'all' ? '' : sourceFilter,
          q: query.trim(),
        })
        if (!cancelled) {
          setFaces(response.items)
          setListTotal(response.total)
        }
      } catch (error) {
        if (!cancelled) {
          onToast(error instanceof Error ? error.message : 'Lecture du corpus impossible.', 'error')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 180)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [onToast, page, query, reloadToken, sourceFilter])

  useEffect(() => {
    let cancelled = false
    api.getExcludedDomains()
      .then((response) => {
        if (!cancelled) setExcludedDomains(response.domains)
      })
      .catch((error) => {
        if (!cancelled) {
          onToast(error instanceof Error ? error.message : 'Lecture des domaines impossible.', 'error')
        }
      })
    return () => { cancelled = true }
  }, [onToast, reloadToken])

  const visibleFaces = useMemo(() => [...faces].sort((a, b) => {
    if (sort === 'source') return a.source_type.localeCompare(b.source_type)
    const delta = new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    return sort === 'date-desc' ? delta : -delta
  }), [faces, sort])

  const totalPages = Math.max(1, Math.ceil(listTotal / PAGE_SIZE))

  const refreshLists = () => setReloadToken((current) => current + 1)

  const confirmDelete = async () => {
    if (!deleteTarget || busy) return
    const faceId = deleteTarget.id
    setBusy(true)
    try {
      await api.deleteFace(faceId)
      setRemovingId(faceId)
      window.setTimeout(() => {
        setFaces((current) => current.filter((face) => face.id !== faceId))
        setListTotal((current) => Math.max(0, current - 1))
        setRemovingId(null)
        if (faces.length === 1 && page > 0) setPage((current) => current - 1)
        else refreshLists()
        onDeleteComplete()
      }, 260)
      onToast(`Face #${faceId} supprimée du corpus.`, 'success')
    } catch (error) {
      onToast(error instanceof Error ? error.message : 'Suppression impossible.', 'error')
    } finally {
      setBusy(false)
      setDeleteTarget(null)
    }
  }

  const prepareDomain = () => {
    const domain = normalizeDomain(domainInput)
    if (!domain) {
      onToast('Saisissez un domaine valide.', 'error')
      return
    }
    setDomainTarget(domain)
  }

  const confirmDomain = async () => {
    if (!domainTarget || busy) return
    setBusy(true)
    try {
      const result = await api.deleteDomain(domainTarget)
      setDomainInput('')
      setPage(0)
      refreshLists()
      onDomainExcluded()
      onToast(
        `${domainTarget} exclu · ${result.deleted_faces_count} visage(s) supprimé(s).`,
        'success',
      )
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Exclusion du domaine impossible.", 'error')
    } finally {
      setBusy(false)
      setDomainTarget(null)
    }
  }

  return (
    <div className="corpus-screen">
      <header className="screen-heading">
        <div>
          <span className="eyebrow">INDEX SQLITE + FAISS</span>
          <h1>Corpus facial</h1>
        </div>
        <div className="corpus-total">
          <strong>{totalFaces}</strong>
          <span>FACES INDEXÉES</span>
        </div>
      </header>

      <div className="corpus-index-state">
        <CorpusIcon />
        <span>
          INDEX COMPLET · {listTotal} RÉSULTAT(S) · PAGE {page + 1}/{totalPages}
        </span>
        <button type="button" onClick={refreshLists}>ACTUALISER</button>
      </div>

      <section className="corpus-toolbar">
        <label className="corpus-search">
          <span>RECHERCHE</span>
          <input
            type="search"
            value={query}
            onChange={(event) => { setQuery(event.target.value); setPage(0) }}
            placeholder="Nom, pseudo, URL ou ID…"
          />
        </label>
        <div className="source-filters" aria-label="Filtrer par source">
          {['all', ...sourceTypes].map((source) => (
            <button
              type="button"
              key={source}
              data-active={sourceFilter === source}
              onClick={() => { setSourceFilter(source); setPage(0) }}
            >
              {source === 'all' ? 'TOUTES' : source.toUpperCase()}
            </button>
          ))}
        </div>
        <label className="corpus-sort">
          <span>TRI</span>
          <select value={sort} onChange={(event) => setSort(event.target.value as SortMode)}>
            <option value="date-desc">Date · récent</option>
            <option value="date-asc">Date · ancien</option>
            <option value="source">Type de source</option>
          </select>
        </label>
      </section>

      {loading ? (
        <section className="corpus-grid" aria-label="Chargement du corpus">
          {Array.from({ length: 8 }, (_, index) => (
            <div className="corpus-skeleton" key={index} />
          ))}
        </section>
      ) : visibleFaces.length ? (
        <section className="corpus-grid">
          {visibleFaces.map((face) => (
            <CorpusCard
              key={face.id}
              face={face}
              removing={removingId === face.id}
              onSearchSimilar={onSearchSimilar}
              onDelete={setDeleteTarget}
            />
          ))}
        </section>
      ) : (
        <section className="corpus-empty">
          <CorpusIcon />
          <strong>Aucune face ne correspond aux filtres</strong>
          <span>Modifiez la recherche ou le type de source.</span>
        </section>
      )}

      <nav className="corpus-pagination" aria-label="Pagination du corpus">
        <button
          type="button"
          disabled={page === 0 || loading}
          onClick={() => setPage((current) => Math.max(0, current - 1))}
        >
          ← PRÉCÉDENT
        </button>
        <span>
          {page * PAGE_SIZE + (visibleFaces.length ? 1 : 0)}
          –{Math.min((page + 1) * PAGE_SIZE, listTotal)} / {listTotal}
        </span>
        <button
          type="button"
          disabled={page + 1 >= totalPages || loading}
          onClick={() => setPage((current) => current + 1)}
        >
          SUIVANT →
        </button>
      </nav>

      <section className="excluded-domains">
        <div className="excluded-domains__heading">
          <div>
            <span className="eyebrow">PÉRIMÈTRE D'EXCLUSION</span>
            <h2>Domaines exclus</h2>
          </div>
          <span>{excludedDomains.length} ENREGISTRÉ(S)</span>
        </div>
        <div className="domain-form">
          <input
            value={domainInput}
            onChange={(event) => setDomainInput(event.target.value)}
            placeholder="example.org"
            aria-label="Domaine à exclure"
          />
          <button type="button" onClick={prepareDomain} disabled={!domainInput.trim() || busy}>
            EXCLURE LE DOMAINE
          </button>
        </div>
        {excludedDomains.length > 0 && (
          <div className="domain-chips">
            {excludedDomains.map((entry) => (
              <span key={entry.domain} title={entry.created_at}>
                {entry.domain} · {new Date(entry.created_at).toLocaleDateString('fr-FR')}
              </span>
            ))}
          </div>
        )}
      </section>

      {(deleteTarget || domainTarget) && (
        <div className="modal-backdrop" role="presentation">
          <div className="confirm-modal" role="alertdialog" aria-modal="true">
            <button
              className="modal-close"
              type="button"
              aria-label="Fermer"
              onClick={() => { setDeleteTarget(null); setDomainTarget(null) }}
            >
              <CloseIcon />
            </button>
            <span className="modal-icon"><TrashIcon /></span>
            <span className="eyebrow">ACTION IRRÉVERSIBLE</span>
            {deleteTarget ? (
              <>
                <h2>Supprimer la face #{deleteTarget.id} ?</h2>
                <p>Le vecteur FAISS et les métadonnées SQLite seront supprimés atomiquement.</p>
              </>
            ) : (
              <>
                <h2>Exclure {domainTarget} ?</h2>
                <p>Toutes les faces associées seront purgées et le domaine sera placé sur liste d’exclusion.</p>
              </>
            )}
            <div className="modal-actions">
              <button type="button" onClick={() => { setDeleteTarget(null); setDomainTarget(null) }}>ANNULER</button>
              <button
                type="button"
                className="danger"
                disabled={busy}
                onClick={deleteTarget ? confirmDelete : confirmDomain}
              >
                {busy ? 'TRAITEMENT…' : 'CONFIRMER'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
