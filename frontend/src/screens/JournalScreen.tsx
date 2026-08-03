import { useState } from 'react'
import type { JournalEvent } from '../api/types'
import { CloseIcon, JournalIcon, TrashIcon } from '../components/icons'

interface JournalScreenProps {
  events: JournalEvent[]
  onClear: () => void
}

export function JournalScreen({ events, onClear }: JournalScreenProps) {
  const [confirmClear, setConfirmClear] = useState(false)

  const exportEvents = () => {
    const blob = new Blob([JSON.stringify(events, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `facelens-journal-${new Date().toISOString().slice(0, 10)}.json`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="journal-screen">
      <header className="screen-heading">
        <div>
          <span className="eyebrow">TRACE LOCALE / LOCALSTORAGE</span>
          <h1>Journal d’investigation</h1>
        </div>
        <span className="case-chip">{events.length} ÉVÉNEMENT(S)</span>
      </header>

      <div className="journal-toolbar">
        <span>Les événements restent dans ce navigateur et ne sont jamais envoyés au serveur.</span>
        <div>
          <button type="button" onClick={exportEvents} disabled={!events.length}>EXPORTER JSON</button>
          <button type="button" className="danger" onClick={() => setConfirmClear(true)} disabled={!events.length}>VIDER</button>
        </div>
      </div>

      <section className="journal-table-wrap">
        {events.length ? (
          <table className="journal-table">
            <thead>
              <tr><th>DATE</th><th>ACTION</th><th>CIBLE</th><th>RÉSULTAT</th></tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id} data-tone={event.tone}>
                  <td>{new Date(event.timestamp).toLocaleString('fr-FR')}</td>
                  <td>{event.action}</td>
                  <td title={event.target}>{event.target}</td>
                  <td>{event.result}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="journal-empty">
            <JournalIcon />
            <strong>Journal vide</strong>
            <span>Les recherches, suppressions et jobs seront consignés ici.</span>
          </div>
        )}
      </section>

      {confirmClear && (
        <div className="modal-backdrop" role="presentation">
          <div className="confirm-modal" role="alertdialog" aria-modal="true">
            <button className="modal-close" type="button" aria-label="Fermer" onClick={() => setConfirmClear(false)}>
              <CloseIcon />
            </button>
            <span className="modal-icon"><TrashIcon /></span>
            <span className="eyebrow">JOURNAL LOCAL</span>
            <h2>Vider tout le journal ?</h2>
            <p>Cette action supprime définitivement les événements stockés dans ce navigateur.</p>
            <div className="modal-actions">
              <button type="button" onClick={() => setConfirmClear(false)}>ANNULER</button>
              <button type="button" className="danger" onClick={() => { onClear(); setConfirmClear(false) }}>VIDER</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
