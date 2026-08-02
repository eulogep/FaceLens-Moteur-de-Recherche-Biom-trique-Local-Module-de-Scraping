import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { VerifyResponse } from '../api/types'
import { Dropzone } from '../components/Dropzone'
import { Gauge } from '../components/Gauge'
import { CompareIcon, UploadIcon } from '../components/icons'
import type { ToastMessage } from '../components/Toast'

const DISCLAIMER = "La similarité faciale n'est pas une preuve d'identité. Vérifiez les sources avant toute conclusion."

interface ComparisonScreenProps {
  onToast: (text: string, tone?: ToastMessage['tone']) => void
}

function usePreview(file: File | null) {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!file) {
      setUrl(null)
      return
    }
    const nextUrl = URL.createObjectURL(file)
    setUrl(nextUrl)
    return () => URL.revokeObjectURL(nextUrl)
  }, [file])

  return url
}

function ComparisonSlot({
  label,
  file,
  onFile,
  disabled,
}: {
  label: string
  file: File | null
  onFile: (file: File) => void
  disabled: boolean
}) {
  const preview = usePreview(file)

  return (
    <div className="comparison-slot">
      <div className="comparison-slot__header">
        <span className="eyebrow">ÉCHANTILLON / {label}</span>
        <span>{file ? 'PRÊT' : 'EN ATTENTE'}</span>
      </div>
      <Dropzone onFile={onFile} disabled={disabled}>
        {preview ? (
          <div className="comparison-preview">
            <img src={preview} alt={`Échantillon ${label}`} />
            <span><UploadIcon /> REMPLACER</span>
          </div>
        ) : (
          <div className="comparison-idle">
            <UploadIcon />
            <strong>IMAGE {label}</strong>
            <span>Déposer ou parcourir</span>
          </div>
        )}
      </Dropzone>
      <div className="comparison-slot__meta">
        <span>{file?.name ?? 'AUCUN FICHIER'}</span>
        <span>{file ? `${(file.size / 1024).toFixed(1)} KO` : '—'}</span>
      </div>
    </div>
  )
}

function resultTone(result: VerifyResponse): 'signal' | 'amber' | 'coral' {
  if (result.similarity >= result.threshold) return 'signal'
  if (result.similarity >= 0.5) return 'amber'
  return 'coral'
}

export function ComparisonScreen({ onToast }: ComparisonScreenProps) {
  const [imageA, setImageA] = useState<File | null>(null)
  const [imageB, setImageB] = useState<File | null>(null)
  const [result, setResult] = useState<VerifyResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const verify = async () => {
    if (!imageA || !imageB || loading) return
    setLoading(true)
    setResult(null)
    try {
      const [response] = await Promise.all([
        api.verifyFaces(imageA, imageB),
        new Promise((resolve) => window.setTimeout(resolve, 700)),
      ])
      setResult(response)
    } catch (error) {
      onToast(error instanceof Error ? error.message : 'Comparaison impossible.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const tone = result ? resultTone(result) : 'signal'

  return (
    <div className="comparison-screen">
      <header className="screen-heading">
        <div>
          <span className="eyebrow">VÉRIFICATION BIOMÉTRIQUE / 1:1</span>
          <h1>Comparaison faciale</h1>
        </div>
        <span className="case-chip">ARCFACE · 512-D</span>
      </header>

      <section className="comparison-bench">
        <ComparisonSlot label="A" file={imageA} onFile={(file) => { setImageA(file); setResult(null) }} disabled={loading} />
        <div className="versus-block" aria-hidden="true">
          <span />
          <b>VS</b>
          <span />
        </div>
        <ComparisonSlot label="B" file={imageB} onFile={(file) => { setImageB(file); setResult(null) }} disabled={loading} />
      </section>

      <button
        className="verify-button"
        type="button"
        disabled={!imageA || !imageB || loading}
        onClick={verify}
      >
        {loading ? <><span className="reticle-spinner" /> VÉRIFICATION EN COURS</> : <><CompareIcon /> VÉRIFIER</>}
      </button>

      <section className="verification-result" data-tone={tone} aria-busy={loading}>
        {loading ? (
          <div className="verification-loading">
            <span className="reticle-spinner" />
            <strong>CALCUL DE L'EMBEDDING</strong>
            <span>Comparaison des vecteurs biométriques…</span>
          </div>
        ) : result ? (
          <>
            <div className="verification-result__header">
              <div>
                <span className="eyebrow">VERDICT</span>
                <h2>{result.verified ? 'CORRESPONDANCE' : 'NON CORRESPONDANT'}</h2>
              </div>
              <div className="verification-score">
                <strong>{(result.similarity * 100).toFixed(1)}%</strong>
                <span>SIMILARITÉ</span>
              </div>
            </div>
            <Gauge value={result.similarity} threshold={result.threshold} tone={tone} />
            <div className="verification-metrics">
              <span><b>DISTANCE</b>{result.distance.toFixed(4)}</span>
              <span><b>SEUIL</b>{result.threshold.toFixed(2)}</span>
              <span><b>CLASSE</b>{result.verdict.toUpperCase()}</span>
            </div>
            {result.warning && <p className="verification-warning">⚠ {result.warning}</p>}
          </>
        ) : (
          <div className="verification-empty">
            <CompareIcon />
            <strong>Deux échantillons requis</strong>
            <span>Le verdict et les métriques apparaîtront ici.</span>
          </div>
        )}
        <footer className="comparison-disclaimer">⚠ {DISCLAIMER}</footer>
      </section>
    </div>
  )
}
