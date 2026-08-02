export type Verdict = 'fort' | 'moyen' | 'sosie' | 'faux_positif'
export type ServiceState = 'checking' | 'healthy' | 'down'
export type Landmark = [number, number]

export interface FaceDetection {
  bbox: [number, number, number, number]
  landmarks: [Landmark, Landmark, Landmark, Landmark, Landmark]
  det_score: number
}

export interface DetectResponse {
  faces_detected: number
  faces: FaceDetection[]
}

export interface Face {
  id: number
  image_path: string
  source_url: string | null
  person_name: string | null
  source_type: string
  tags: string | null
  created_at: string
}

export interface Match extends Face {
  similarity: number
  distance: number
  verdict: Verdict
}

export interface SearchResponse {
  faces_detected: number
  results: Match[]
  disclaimer: string
}

export interface VerifyResponse {
  verified: boolean
  similarity: number
  distance: number
  threshold: number
  verdict: string
  warning?: string | null
  disclaimer: string
}

export interface Job {
  job_id: string
  target_url: string
  status: 'pending' | 'running' | 'completed' | 'partial' | 'failed'
  total_images: number
  faces_indexed: number
  duplicates_skipped: number
  errors_by_domain: Record<string, string>
  created_at: string
  updated_at: string
}

export interface Stats {
  total_jobs: number
  scraped_faces: number
  excluded_domains_count: number
  faces_by_source_type: Record<string, number>
  total_indexed_faces: number
  faiss_ntotal: number
  integrity_verified: boolean
}

export interface DeleteFaceResponse {
  success: boolean
  face_id: number
  message: string
}
