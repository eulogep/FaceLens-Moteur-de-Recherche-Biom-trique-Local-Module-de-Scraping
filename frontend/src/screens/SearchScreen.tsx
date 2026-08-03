import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { FaceDetection, JournalInput, Match, SearchResponse } from '../api/types'
import { MatchCard } from '../components/MatchCard'
import { ScanViewport } from '../components/ScanViewport'
import { CloseIcon, ReticleIcon, TrashIcon } from '../components/icons'
import type { ToastMessage } from '../components/Toast'

const DISCLAIMER = "La similarité faciale n'est pas une preuve d'identité. Vérifiez les sources avant toute conclusion."

interface SearchScreenProps {
  onToast: (text: string, tone?: ToastMessage['tone']) => void
  onCorpusChanged: (faceId?: number) => void
  onJournal: (entry: JournalInput) => void
  initialFile?: File | null
}

export function SearchScreen({
  onToast,
  onCorpusChanged,
  onJournal,
  initialFile,
}: SearchScreenProps) {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [detections, setDetections] = useState<FaceDetection[]>([])
  const [minSimilarity, setMinSimilarity] = useState(0)
  const [deleteTarget, setDeleteTarget] = useState<Match | null>(null)

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
  }, [previewUrl])

  const selectFile = useCallback((nextFile: File) => {
    setFile(nextFile)
    setPreviewUrl(URL.createObjectURL(nextFile))
    setResponse(null)
    setDetections([])
  }, [])

  useEffect(() => {
    if (initialFile) selectFile(initialFile)
  }, [initialFile, selectFile])

  const analyze = async () => {
    if (!file || loading) return
    setLoading(true)
    setResponse(null)
    setDetections([])
    try {
      const [result, detection] = await Promise.all([
        api.searchFaces(file, 15, minSimilarity),
        api.detectFaces(file),
        new Promise((resolve) => window.setTimeout(resolve, 1_200)),
      ])
      setResponse(result)
      setDetections(detection.faces)
      onJournal({
        action: 'RECHERCHE 1:N',
        target: file.name,
        result: `${detection.faces.length} visage(s) · ${result.results.length} résultat(s)`,
        tone: 'success',
      })
      if (!detection.faces_detected) onToast("Aucun visage détecté dans cette image.", 'error')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Recherche impossible.'
      onJournal({ action: 'RECHERCHE 1:N', target: file.name, result: message, tone: 'error' })
      onToast(message, 'error')
    } finally {
      setLoading(false)
    }
  }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    try {
      await api.deleteFace(deleteTarget.id)
      setResponse((current) => current ? {
        ...current,
        results: current.results.filter((match) => match.id !== deleteTarget.id),
      } : current)
      onToast(`Face #${deleteTarget.id} supprimée du corpus.`, 'success')
      onJournal({
        action: 'SUPPRESSION FACE',
        target: `Face #${deleteTarget.id}`,
        result: 'SQLite + FAISS supprimés',
        tone: 'success',
      })
      onCorpusChanged(deleteTarget.id)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Suppression impossible.'
      onJournal({
        action: 'SUPPRESSION FACE',
        target: `Face #${deleteTarget.id}`,
        result: message,
        tone: 'error',
      })
      onToast(message, 'error')
    } finally {
      setDeleteTarget(null)
    }
  }

  const matches = response?.results ?? []

  return (
    <>
      <div className="search-layout">
        <div className="search-input-column">
          <ScanViewport
            file={file}
            previewUrl={previewUrl}
            scanning={loading}
            detections={detections}
            onFile={selectFile}
          />
          <div className="analysis-controls">
            <label>
              <span>SEUIL D'AFFICHAGE</span>
              <strong>{minSimilarity.toFixed(2)}</strong>
              <input
                type="range"
                min="0"
                max="0.9"
                step="0.05"
                value={minSimilarity}
                onChange={(event) => setMinSimilarity(Number(event.target.value))}
              />
            </label>
            <button
              className="analyze-button"
              type="button"
              disabled={!file || loading}
              onClick={analyze}
            >
              {loading ? (
                <><span className="reticle-spinner" /> ANALYSE EN COURS</>
              ) : (
                <><ReticleIcon /> ANALYSER</>
              )}
            </button>
          </div>
        </div>

        <section className="results-panel" aria-busy={loading}>
          <div className="results-header">
            <div>
              <span className="eyebrow">INDEX FAISS / TOP 15</span>
              <h2>CORRESPONDANCES <b>({matches.length})</b></h2>
            </div>
            <div className="threshold-readout">
              <span>SEUIL FORT</span>
              <strong>0.70</strong>
            </div>
          </div>

          <div className="results-stream">
            {loading ? (
              <div className="skeleton-list">
                {[0, 1, 2].map((item) => <div className="match-skeleton" key={item} />)}
              </div>
            ) : matches.length ? (
              matches.map((match, index) => (
                <MatchCard
                  key={match.id}
                  match={match}
                  index={index}
                  onCompare={() => onToast('Comparaison disponible en phase 2.', 'info')}
                  onDelete={setDeleteTarget}
                />
              ))
            ) : (
              <div className="results-empty">
                <ReticleIcon />
                <strong>
                  {response
                    ? 'Aucune correspondance au seuil choisi'
                    : 'Lancez une analyse pour voir les correspondances'}
                </strong>
                <span>
                  {response?.faces_detected
                    ? 'Réduisez le seuil ou alimentez le corpus.'
                    : 'Le flux affichera les résultats classés par similarité.'}
                </span>
              </div>
            )}
          </div>
          <footer className="results-disclaimer">⚠ {DISCLAIMER}</footer>
        </section>
      </div>

      {deleteTarget && (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={(event) => event.target === event.currentTarget && setDeleteTarget(null)}
        >
          <div className="confirm-modal" role="alertdialog" aria-modal="true" aria-labelledby="delete-title">
            <button
              className="modal-close"
              type="button"
              aria-label="Fermer"
              onClick={() => setDeleteTarget(null)}
            >
              <CloseIcon />
            </button>
            <span className="modal-icon"><TrashIcon /></span>
            <span className="eyebrow">ACTION IRRÉVERSIBLE</span>
            <h2 id="delete-title">Supprimer la face #{deleteTarget.id} ?</h2>
            <p>Le vecteur FAISS et les métadonnées SQLite seront supprimés atomiquement.</p>
            <div className="modal-actions">
              <button type="button" onClick={() => setDeleteTarget(null)}>ANNULER</button>
              <button type="button" className="danger" onClick={confirmDelete}>SUPPRIMER</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
