import { useEffect, useRef, useState } from 'react'
import { Dropzone } from './Dropzone'
import { ReticleIcon, UploadIcon } from './icons'

interface ScanViewportProps {
  file: File | null
  previewUrl: string | null
  scanning: boolean
  faceDetected: boolean
  onFile: (file: File) => void
}

export function ScanViewport(props: ScanViewportProps) {
  const { file, previewUrl, scanning, faceDetected, onFile } = props
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !previewUrl) return
    const context = canvas.getContext('2d')
    const image = new Image()
    image.onload = () => {
      setDimensions({ width: image.naturalWidth, height: image.naturalHeight })
      const scale = Math.min(canvas.width / image.width, canvas.height / image.height)
      const width = image.width * scale
      const height = image.height * scale
      context?.clearRect(0, 0, canvas.width, canvas.height)
      context?.drawImage(
        image,
        (canvas.width - width) / 2,
        (canvas.height - height) / 2,
        width,
        height,
      )
    }
    image.src = previewUrl
  }, [previewUrl])

  return (
    <section className="scan-shell">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">ENTRÉE / SOURCE 01</span>
          <h1>Analyse faciale</h1>
        </div>
        <span className="case-chip">LOCAL · CPU</span>
      </div>

      <div className="scan-frame">
        <Dropzone onFile={onFile} disabled={scanning}>
          {!file || !previewUrl ? (
            <div className="scan-idle">
              <ReticleIcon className="scan-idle__reticle" />
              <strong>Déposez un visage à analyser</strong>
              <span>Glissez une image ici ou cliquez pour parcourir</span>
              <span className="scan-idle__formats">JPG · PNG · WEBP</span>
            </div>
          ) : (
            <div className="scan-canvas-wrap">
              <canvas ref={canvasRef} width="960" height="720" />
              {scanning && <span className="scan-line" key={Date.now()} />}
              {faceDetected && (
                <div className="face-overlay" aria-label="Visage détecté">
                  <i className="bracket bracket--tl" />
                  <i className="bracket bracket--tr" />
                  <i className="bracket bracket--bl" />
                  <i className="bracket bracket--br" />
                  <span className="landmark landmark--eye-a" />
                  <span className="landmark landmark--eye-b" />
                  <span className="landmark landmark--nose" />
                  <span className="landmark landmark--mouth-a" />
                  <span className="landmark landmark--mouth-b" />
                  <span className="face-overlay__label">VISAGE DÉTECTÉ</span>
                </div>
              )}
              <span className="scan-corner-label">FL / OPTICAL INPUT</span>
              <span className="scan-change"><UploadIcon /> Remplacer</span>
            </div>
          )}
        </Dropzone>
      </div>

      <div className="image-meta">
        <span><b>FICHIER</b>{file?.name ?? '—'}</span>
        <span><b>DIMENSIONS</b>{dimensions ? `${dimensions.width} × ${dimensions.height}` : '—'}</span>
        <span><b>POIDS</b>{file ? `${(file.size / 1024).toFixed(1)} Ko` : '—'}</span>
      </div>
    </section>
  )
}
