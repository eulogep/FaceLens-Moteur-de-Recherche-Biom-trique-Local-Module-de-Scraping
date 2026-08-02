import { useEffect, useRef, useState } from 'react'
import type { FaceDetection } from '../api/types'
import { Dropzone } from './Dropzone'
import { ReticleIcon, UploadIcon } from './icons'

interface ScanViewportProps {
  file: File | null
  previewUrl: string | null
  scanning: boolean
  detections: FaceDetection[]
  onFile: (file: File) => void
}

function drawDetections(
  context: CanvasRenderingContext2D,
  detections: FaceDetection[],
  scale: number,
  offsetX: number,
  offsetY: number,
) {
  detections.forEach((detection, index) => {
    const [x1, y1, x2, y2] = detection.bbox
    const left = offsetX + x1 * scale
    const top = offsetY + y1 * scale
    const width = (x2 - x1) * scale
    const height = (y2 - y1) * scale

    context.save()
    context.strokeStyle = '#46e0c0'
    context.lineWidth = 2
    context.shadowColor = 'rgba(70, 224, 192, 0.75)'
    context.shadowBlur = 10
    context.strokeRect(left, top, width, height)
    context.shadowBlur = 0

    detection.landmarks.forEach(([x, y]) => {
      context.beginPath()
      context.arc(offsetX + x * scale, offsetY + y * scale, 4, 0, Math.PI * 2)
      context.fillStyle = '#46e0c0'
      context.fill()
      context.lineWidth = 1
      context.strokeStyle = '#050a0c'
      context.stroke()
    })

    const label = `FACE ${String(index + 1).padStart(2, '0')} · ${(
      detection.det_score * 100
    ).toFixed(1)}%`
    context.font = '600 11px "JetBrains Mono", monospace'
    const labelWidth = context.measureText(label).width + 12
    const labelTop = Math.max(0, top - 21)
    context.fillStyle = '#46e0c0'
    context.fillRect(left, labelTop, labelWidth, 21)
    context.fillStyle = '#050a0c'
    context.fillText(label, left + 6, labelTop + 14)
    context.restore()
  })
}

export function ScanViewport(props: ScanViewportProps) {
  const { file, previewUrl, scanning, detections, onFile } = props
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
      const offsetX = (canvas.width - width) / 2
      const offsetY = (canvas.height - height) / 2
      context?.clearRect(0, 0, canvas.width, canvas.height)
      context?.drawImage(
        image,
        offsetX,
        offsetY,
        width,
        height,
      )
      if (context) drawDetections(context, detections, scale, offsetX, offsetY)
    }
    image.src = previewUrl
  }, [previewUrl, detections])

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
              <canvas
                ref={canvasRef}
                width="960"
                height="720"
                aria-label={`${detections.length} visage(s) détecté(s)`}
              />
              {scanning && <span className="scan-line" key={Date.now()} />}
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
