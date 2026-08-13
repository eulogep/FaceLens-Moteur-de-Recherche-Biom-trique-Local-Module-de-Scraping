import type {
  DetectResponse,
  DeleteFaceResponse,
  DeleteDomainResponse,
  ExcludedDomainListResponse,
  Face,
  FaceCountResponse,
  FaceListResponse,
  Job,
  ScrapeJobResponse,
  ScrapeSearchPayload,
  ScrapeUrlPayload,
  SearchResponse,
  Stats,
  VerifyResponse,
} from './types'

export const API = (
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
).replace(/\/$/, '')

export const SEARXNG = (
  import.meta.env.VITE_SEARXNG_URL ?? 'http://localhost:8080'
).replace(/\/$/, '')

const API_KEY = String(import.meta.env.VITE_FACELENS_API_KEY ?? '').trim()

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status = 0,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function authenticatedHeaders(init?: HeadersInit): Headers {
  if (API_KEY.length < 32) {
    throw new ApiError(
      'VITE_FACELENS_API_KEY est absente ou trop courte. Configurez le client local avant utilisation.',
      401,
    )
  }
  const headers = new Headers(init)
  headers.set('X-FaceLens-API-Key', API_KEY)
  return headers
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 30_000)

  try {
    const response = await fetch(`${API}${path}`, {
      ...init,
      headers: authenticatedHeaders(init.headers),
      signal: controller.signal,
    })
    const contentType = response.headers.get('content-type') ?? ''
    const payload = contentType.includes('application/json')
      ? await response.json()
      : await response.text()

    if (!response.ok) {
      const detail =
        typeof payload === 'object' && payload && 'detail' in payload
          ? String(payload.detail)
          : `Erreur HTTP ${response.status}`
      throw new ApiError(detail, response.status)
    }
    return payload as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('La requête a dépassé le délai de 30 secondes.')
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Erreur réseau inconnue.',
    )
  } finally {
    window.clearTimeout(timeout)
  }
}

async function faceImageBlob(imagePath: string): Promise<Blob> {
  if (!imagePath.startsWith('/api/faces/')) {
    throw new ApiError('Référence d’image biométrique invalide.', 400)
  }
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 30_000)
  try {
    const response = await fetch(`${API}${imagePath}`, {
      headers: authenticatedHeaders(),
      signal: controller.signal,
    })
    if (!response.ok) {
      throw new ApiError(`Image indisponible · HTTP ${response.status}`, response.status)
    }
    return response.blob()
  } finally {
    window.clearTimeout(timeout)
  }
}

export const api = {
  async checkApi(): Promise<boolean> {
    await request<Record<string, unknown>>('/')
    return true
  },

  getStats: () => request<Stats>('/api/scrape/stats'),
  getFaceCount: () => request<FaceCountResponse>('/api/faces/count'),

  listFaces({
    limit = 24,
    offset = 0,
    sourceType = '',
    q = '',
  }: {
    limit?: number
    offset?: number
    sourceType?: string
    q?: string
  } = {}) {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
    if (sourceType) params.set('source_type', sourceType)
    if (q) params.set('q', q)
    return request<FaceListResponse>(`/api/faces?${params.toString()}`)
  },

  getExcludedDomains: () => request<ExcludedDomainListResponse>('/api/scrape/domains'),
  startUrlJob: (payload: ScrapeUrlPayload) =>
    request<ScrapeJobResponse>('/api/scrape/url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  startSearchJob: (payload: ScrapeSearchPayload) =>
    request<ScrapeJobResponse>('/api/scrape/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  getJobStatus: (jobId: string) => request<Job>(`/api/scrape/status/${encodeURIComponent(jobId)}`),

  searchFaces(file: File, topK = 15, minSimilarity = 0) {
    const form = new FormData()
    form.append('file', file)
    return request<SearchResponse>(
      `/api/faces/search?top_k=${topK}&min_similarity=${minSimilarity}`,
      { method: 'POST', body: form },
    )
  },
  detectFaces(file: File) {
    const form = new FormData()
    form.append('file', file)
    return request<DetectResponse>('/api/faces/detect', { method: 'POST', body: form })
  },
  verifyFaces(imageA: File, imageB: File) {
    const form = new FormData()
    form.append('image_a', imageA)
    form.append('image_b', imageB)
    return request<VerifyResponse>('/api/faces/verify', { method: 'POST', body: form })
  },
  deleteFace: (faceId: number) => request<DeleteFaceResponse>(`/api/faces/${faceId}`, { method: 'DELETE' }),
  deleteDomain: (domain: string) =>
    request<DeleteDomainResponse>(`/api/scrape/source/${encodeURIComponent(domain)}`, { method: 'DELETE' }),

  async imageObjectUrl(face: Face): Promise<string> {
    return URL.createObjectURL(await faceImageBlob(face.image_path))
  },

  async downloadFaceImage(face: Face) {
    const blob = await faceImageBlob(face.image_path)
    const extension = blob.type.split('/')[1] || 'jpg'
    return new File([blob], face.person_name || `face-${face.id}.${extension}`, {
      type: blob.type || 'image/jpeg',
    })
  },
}

export async function checkSearxng(): Promise<boolean> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 5_000)
  try {
    await fetch(`${SEARXNG}/healthz`, { mode: 'no-cors', cache: 'no-store', signal: controller.signal })
    return true
  } catch {
    return false
  } finally {
    window.clearTimeout(timeout)
  }
}
