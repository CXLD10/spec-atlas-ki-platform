/**
 * Typed API client for Spec-Atlas backend.
 * Provides a mock fallback when VITE_API_URL is not set or backend is unavailable.
 */

import {
  Source,
  KnowledgeCard,
  JobStatus,
  AskResponse,
  HealthResponse,
  MockFallback,
} from './types'

const API_URL =
  ((import.meta as any).env?.VITE_API_URL as string | undefined) ||
  'http://localhost:8000'

/**
 * Generic request wrapper: throws MockFallback if no base URL or request fails.
 */
async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options?: { headers?: Record<string, string> }
): Promise<T> {
  if (!API_URL || API_URL === '') {
    throw new MockFallback('No API URL configured')
  }

  try {
    const url = new URL(path, API_URL).toString()
    const fetchOpts: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    }

    if (body && method !== 'GET') {
      fetchOpts.body = JSON.stringify(body)
    }

    const res = await fetch(url, fetchOpts)
    if (!res.ok) {
      throw new MockFallback(`API error: ${res.status} ${res.statusText}`)
    }

    return await res.json()
  } catch (err) {
    if (err instanceof MockFallback) throw err
    throw new MockFallback(`Request failed: ${err instanceof Error ? err.message : String(err)}`)
  }
}

/**
 * Multipart file upload wrapper.
 */
async function uploadFile<T>(
  path: string,
  file: File
): Promise<T> {
  if (!API_URL || API_URL === '') {
    throw new MockFallback('No API URL configured')
  }

  try {
    const url = new URL(path, API_URL).toString()
    const formData = new FormData()
    formData.append('file', file)

    const res = await fetch(url, {
      method: 'POST',
      body: formData,
    })

    if (!res.ok) {
      throw new MockFallback(`Upload error: ${res.status} ${res.statusText}`)
    }

    return await res.json()
  } catch (err) {
    if (err instanceof MockFallback) throw err
    throw new MockFallback(`Upload failed: ${err instanceof Error ? err.message : String(err)}`)
  }
}

/**
 * Spec-Atlas API client.
 */
export const client = {
  /**
   * List all sources (repos + documents).
   * BACKEND-DEP: GET /api/sources or merge /api/documents + repo list
   */
  async listSources(): Promise<Source[]> {
    return request<Source[]>('GET', '/api/sources')
  },

  /**
   * Get a single source.
   * BACKEND-DEP: GET /api/sources/:id
   */
  async getSource(id: string): Promise<Source> {
    return request<Source>('GET', `/api/sources/${id}`)
  },

  /**
   * Start a repo ingestion.
   * Live: POST /api/ingest
   */
  async ingestRepo(repoUrl: string): Promise<JobStatus> {
    return request<JobStatus>('POST', '/api/ingest', { repo_url: repoUrl })
  },

  /**
   * Upload a document (PDF/XLSX/Markdown).
   * BACKEND-DEP: POST /api/documents (multipart)
   */
  async uploadDocument(file: File): Promise<JobStatus> {
    return uploadFile<JobStatus>('/api/documents', file)
  },

  /**
   * Get ingestion job status.
   * Live: GET /api/ingest/:jobId/status
   */
  async ingestStatus(jobId: string): Promise<JobStatus> {
    return request<JobStatus>('GET', `/api/ingest/${jobId}/status`)
  },

  /**
   * List all knowledge cards.
   * BACKEND-DEP: GET /api/kb (may map to /api/specs listing)
   */
  async listCards(): Promise<KnowledgeCard[]> {
    return request<KnowledgeCard[]>('GET', '/api/kb')
  },

  /**
   * Get a single knowledge card.
   * BACKEND-DEP: GET /api/kb/:ref (may map to /api/specs/:ref)
   */
  async getCard(ref: string): Promise<KnowledgeCard> {
    return request<KnowledgeCard>('GET', `/api/kb/${ref}`)
  },

  /**
   * Ask a question to the KI agent.
   * Live: POST /api/ask
   */
  async ask(question: string, projectId?: string): Promise<AskResponse> {
    return request<AskResponse>('POST', '/api/ask', {
      question,
      project_id: projectId || 'default',
    })
  },

  /**
   * Check backend health.
   * Live: GET /health
   */
  async health(): Promise<HealthResponse> {
    return request<HealthResponse>('GET', '/health')
  },

  /**
   * Get source preview (for citations).
   * BACKEND-DEP: GET /api/source-snippet?doc=:id&page=:n
   */
  async getSourceSnippet(docId: string, page?: number): Promise<{ snippet: string }> {
    const params = new URLSearchParams()
    params.append('doc', docId)
    if (page) params.append('page', String(page))
    return request<{ snippet: string }>('GET', `/api/source-snippet?${params.toString()}`)
  },

  /**
   * Get a subgraph of nodes and edges.
   * BACKEND-DEP: GET /api/graph/subgraph?node_id=&max_depth=2
   */
  async getSubgraph(nodeId?: string, maxDepth: number = 2): Promise<{
    nodes: Array<{ id: string; label: string; layer: string; _x: number; _y: number; _z: number }>
    edges: Array<{ s: string; d: string; kind: string; layer: string; inter?: boolean }>
  }> {
    const params = new URLSearchParams()
    if (nodeId) params.append('node_id', nodeId)
    params.append('max_depth', String(maxDepth))
    return request(
      'GET',
      `/api/graph/subgraph?${params.toString()}`
    )
  },

  /**
   * Generate a structured Knowledge Card from an entity name.
   * BACKEND-DEP: POST /api/specs {repo, entity_name}
   */
  async generateSpec(repo: string, entityName: string): Promise<KnowledgeCard> {
    return request<KnowledgeCard>('POST', '/api/specs', {
      repo,
      entity_name: entityName,
    })
  },
}

export type { Source, KnowledgeCard, JobStatus, AskResponse }
export { MockFallback }
