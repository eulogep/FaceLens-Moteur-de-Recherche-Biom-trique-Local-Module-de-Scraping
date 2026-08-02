import type {
  DetectResponse,
  DeleteFaceResponse,
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

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status = 0,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 30_000)

  try {
    const response = await fetch(`${API}${path}`, {
      ...init,
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

export const api = {
  async checkApi(): Promise<boolean> {
    await request<string>('/docs')
    return true
  },

  getStats: () => request<Stats>('/api/scrape/stats'),

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
    return request<DetectResponse>('/api/faces/detect', {
      method: 'POST',
      body: form,
    })
  },

  verifyFaces(imageA: File, imageB: File) {
    const form = new FormData()
    form.append('image_a', imageA)
    form.append('image_b', imageB)
    return request<VerifyResponse>('/api/faces/verify', {
      method: 'POST',
      body: form,
    })
  },

  deleteFace: (faceId: number) =>
    request<DeleteFaceResponse>(`/api/faces/${faceId}`, {
      method: 'DELETE',
    }),
}

export async function checkSearxng(): Promise<boolean> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 5_000)
  try {
    await fetch(`${SEARXNG}/healthz`, {
      mode: 'no-cors',
      cache: 'no-store',
      signal: controller.signal,
    })
    return true
  } catch {
    return false
  } finally {
    window.clearTimeout(timeout)
  }
}

export function faceImageUrl(imagePath: string): string {
  if (/^https?:\/\//i.test(imagePath)) return imagePath
  const normalized = imagePath.replace(/\\/g, '/')
  const filename = normalized.split('/').pop()
  return `${API}/static/images/${encodeURIComponent(filename ?? '')}`
}
