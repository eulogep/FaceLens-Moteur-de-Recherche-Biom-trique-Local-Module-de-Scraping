import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Match } from '../api/types'
import { Gauge } from './Gauge'
import { CompareIcon, ExternalIcon, TrashIcon } from './icons'

interface MatchCardProps {
  match: Match
  index: number
  onCompare: (match: Match) => void
  onDelete: (match: Match) => void
}

const verdictMap = {
  fort: { label: 'FORT', tone: 'signal' },
  moyen: { label: 'MOYEN', tone: 'amber' },
  sosie: { label: 'SOSIE', tone: 'coral' },
  faux_positif: { label: 'SOSIE', tone: 'coral' },
} as const

export function MatchCard({ match, index, onCompare, onDelete }: MatchCardProps) {
  const verdict = verdictMap[match.verdict]
  const date = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium' }).format(new Date(match.created_at))
  const imageKey = `${match.id}:${match.image_path}`
  const [image, setImage] = useState<{ key: string; url: string } | null>(null)

  useEffect(() => {
    let active = true
    let objectUrl = ''
    setImage(null)
    void api.imageObjectUrl(match)
      .then((url) => {
        objectUrl = url
        if (active) setImage({ key: imageKey, url })
        else URL.revokeObjectURL(url)
      })
      .catch(() => {
        if (active) setImage(null)
      })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [match.id, match.image_path, imageKey])

  return (
    <article className="match-card" data-tone={verdict.tone} style={{ animationDelay: `${index * 80}ms` }}>
      <img
        className="match-card__image"
        src={image?.key === imageKey ? image.url : undefined}
        alt={match.person_name ? `Visage de ${match.person_name}` : `Visage #${match.id}`}
      />
      <div className="match-card__body">
        <div className="match-card__headline">
          <div>
            <span className="match-card__rank">MATCH #{String(index + 1).padStart(2, '0')}</span>
            <h3>{match.person_name || 'Identité inconnue'}</h3>
          </div>
          <strong className="match-card__score">
            {(match.similarity * 100).toFixed(1)}<small>%</small>
          </strong>
        </div>
        <Gauge value={match.similarity} tone={verdict.tone} />
        <div className="match-card__meta">
          <span className="verdict" data-tone={verdict.tone}>{verdict.label}</span>
          <span>#{match.id}</span>
          <span>{match.source_type}</span>
          <span>{date}</span>
        </div>
        {match.source_url ? (
          <a className="source-link" href={match.source_url} target="_blank" rel="noopener noreferrer" title={match.source_url}>
            <ExternalIcon /> {match.source_url}
          </a>
        ) : (
          <span className="source-link source-link--empty">SOURCE NON RENSEIGNÉE</span>
        )}
      </div>
      <div className="match-card__actions">
        <button type="button" onClick={() => onCompare(match)}>
          <CompareIcon /> Comparer
        </button>
        <button type="button" className="danger" onClick={() => onDelete(match)}>
          <TrashIcon /> Supprimer
        </button>
      </div>
    </article>
  )
}
