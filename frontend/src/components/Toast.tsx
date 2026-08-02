import { useEffect } from 'react'
import { CloseIcon } from './icons'

export interface ToastMessage {
  id: number
  text: string
  tone?: 'error' | 'info' | 'success'
}

function ToastItem({ toast, onDismiss }: {
  toast: ToastMessage
  onDismiss: (id: number) => void
}) {
  useEffect(() => {
    const timeout = window.setTimeout(() => onDismiss(toast.id), 6_000)
    return () => window.clearTimeout(timeout)
  }, [toast.id, onDismiss])

  return (
    <div className="toast" data-tone={toast.tone ?? 'error'} role="status">
      <span>{toast.text}</span>
      <button type="button" aria-label="Fermer" onClick={() => onDismiss(toast.id)}>
        <CloseIcon />
      </button>
    </div>
  )
}

export function ToastRegion({ toasts, onDismiss }: {
  toasts: ToastMessage[]
  onDismiss: (id: number) => void
}) {
  return (
    <div className="toast-region">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  )
}
