import type { ScreenId } from '../api/types'
import { CompareIcon, CorpusIcon, JournalIcon, ReticleIcon, SpiderIcon } from './icons'

interface RailProps {
  corpusCount: number
  activeJobs: number
  activeScreen: ScreenId
  onNavigate: (screen: ScreenId) => void
  onUnavailable: (label: string) => void
}

export function Rail({
  corpusCount,
  activeJobs,
  activeScreen,
  onNavigate,
  onUnavailable,
}: RailProps) {
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
          data-active={id === activeScreen}
          data-tooltip={
            id === 'scraping' || id === 'journal'
              ? `${label} · phase 3`
              : label
          }
          aria-label={label}
          onClick={() => {
            const screen = id as ScreenId
            if (screen === 'scraping' || screen === 'journal') onUnavailable(label)
            else onNavigate(screen)
          }}
        >
          <Icon />
          {badge > 0 && <span className="rail__badge">{badge > 99 ? '99+' : badge}</span>}
        </button>
      ))}
    </nav>
  )
}
