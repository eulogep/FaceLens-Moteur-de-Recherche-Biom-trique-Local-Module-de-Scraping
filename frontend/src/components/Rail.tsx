import { CompareIcon, CorpusIcon, JournalIcon, ReticleIcon, SpiderIcon } from './icons'

interface RailProps {
  corpusCount: number
  activeJobs: number
  onUnavailable: (label: string) => void
}

export function Rail({ corpusCount, activeJobs, onUnavailable }: RailProps) {
  const items = [
    { id: 'search', label: 'Recherche', icon: ReticleIcon, badge: 0 },
    { id: 'compare', label: 'Comparaison', icon: CompareIcon, badge: 0 },
    { id: 'corpus', label: 'Corpus', icon: CorpusIcon, badge: corpusCount },
    { id: 'scraping', label: 'Scraping', icon: SpiderIcon, badge: activeJobs },
    { id: 'journal', label: 'Journal', icon: JournalIcon, badge: 0 },
  ]

  return (
    <nav className="rail" aria-label="Navigation principale">
      {items.map(({ id, label, icon: Icon, badge }) => (
        <button
          key={id}
          className="rail__item"
          data-active={id === 'search'}
          data-tooltip={id === 'search' ? label : `${label} · phase suivante`}
          aria-label={label}
          onClick={() => id !== 'search' && onUnavailable(label)}
        >
          <Icon />
          {badge > 0 && <span className="rail__badge">{badge > 99 ? '99+' : badge}</span>}
        </button>
      ))}
    </nav>
  )
}
