import { useRef, useState, type KeyboardEvent, type ReactNode } from 'react'

interface DropzoneProps {
  onFile: (file: File) => void
  children: ReactNode
  disabled?: boolean
}

export function Dropzone({ onFile, children, disabled }: DropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const accept = (file?: File) => {
    if (file?.type.startsWith('image/')) onFile(file)
  }
  const openPicker = () => !disabled && inputRef.current?.click()
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      openPicker()
    }
  }

  return (
    <div
      className="dropzone"
      data-dragging={dragging}
      data-disabled={disabled}
      role="button"
      tabIndex={disabled ? -1 : 0}
      onKeyDown={onKeyDown}
      onClick={openPicker}
      onDragEnter={(event) => {
        event.preventDefault()
        setDragging(true)
      }}
      onDragOver={(event) => event.preventDefault()}
      onDragLeave={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false)
      }}
      onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        accept(event.dataTransfer.files[0])
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        hidden
        onChange={(event) => accept(event.target.files?.[0])}
      />
      {children}
    </div>
  )
}
