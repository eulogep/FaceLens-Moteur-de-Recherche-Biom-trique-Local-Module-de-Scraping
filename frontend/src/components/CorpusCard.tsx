import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Face } from '../api/types'
import { ReticleIcon, TrashIcon } from './icons'

interface CorpusCardProps {
  face: Face
  removing: boolean
  onSearchSimilar: (face: Face) => void
  onDelete: (face: Face) => void
}

function sourceLabel(url: string | null, sourceType: string) {
  if (!url) return sourceType
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return sourceType
  }
}

export function CorpusCard({ face, removing, onSearchSimilar, onDelete }: CorpusCardProps) {
  const ref = useRef<HTMLElement>(null)
  const [revealed, setRevealed] = useState(false)
  const [imageUrl, setImageUrl] = useState('')

  useEffect(() => {
    let active = true
    let objectUrl = ''
    void api.imageObjectUrl(face)
      .then((url) => {
        objectUrl = url
        if (active) setImageUrl(url)
        else URL.revokeObjectURL(url)
      })
      .catch(() => {
        if (active) setImageUrl('')
      })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [face.id, face.image_path])

  useEffect(() => {
    const node = ref.current
    if (!node || !('IntersectionObserver' in window)) {
      setRevealed(true)
      return
    }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setRevealed(true)
        observer.disconnect()
      }
    }, { threshold: 0.12 })
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  return (
    <article ref={ref} className="corpus-card" data-revealed={revealed} data-removing={removing}>
      <img
        src={imageUrl || undefined}
        alt={face.person_name ?? `Face #${face.id}`}
        loading="lazy"
      />
      <div className="corpus-card__id">ID #{face.id}</div>
      <div className="corpus-card__overlay">
        <div>
          <strong>{face.person_name ?? 'Sujet non identifié'}</strong>
          <span>{sourceLabel(face.source_url, face.source_type)}</span>
        </div>
        <div className="corpus-card__actions">
          <button type="button" onClick={() => onSearchSimilar(face)}>
            <ReticleIcon /> SIMILAIRES
          </button>
          <button type="button" className="danger" onClick={() => onDelete(face)}>
            <TrashIcon /> SUPPRIMER
          </button>
        </div>
      </div>
      <footer>
        <span>{face.source_type.toUpperCase()}</span>
        <time>{new Date(face.created_at).toLocaleDateString('fr-FR')}</time>
      </footer>
    </article>
  )
}
