/* Typed API client for Spec-Atlas backend */

const API_URL =
  ((import.meta as any).env?.VITE_API_URL as string | undefined) ||
  'http://localhost:8000'

export interface AskRequest {
  question: string
  project_id?: string
}

export interface Claim {
  text?: string
  source: string
  file?: string
  start_line?: number
  end_line?: number
  confidence?: number
}

export interface AskResponse {
  answer: string
  claims: Claim[]
  confidence?: number
  route_used?: string
  status?: 'success' | 'empty_db' | 'no_results' | 'error'
  suggestions?: string[]
}

export interface GroupNode {
  id: string
  path: string
  children?: GroupNode[]
}

export interface GroupDetail {
  id: string
  path: string
  summary_md: string
  children: GroupNode[]
  member_specs: string[]
}

export interface SpecField {
  text: string
  file?: string
  start_line?: number
  end_line?: number
}

export interface Spec {
  ref: string
  status: 'draft' | 'verified' | 'stale'
  purpose?: SpecField
  inputs?: SpecField[]
  outputs?: SpecField[]
  dependencies?: SpecField[]
  invariants?: SpecField[]
  side_effects?: SpecField[]
  failure_modes?: SpecField[]
}

export interface IngestResponse {
  job_id: string
}

export interface IngestStatus {
  job_id: string
  status: 'queued' | 'in_progress' | 'done' | 'failed'
  progress: number
  error?: string
}

export interface HealthResponse {
  status: string
  analysis_db: string
  spec_db: string
  llm: string
  embed: string
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, '') // Remove trailing slash
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`
    const opts: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    }

    if (body) {
      opts.body = JSON.stringify(body)
    }

    const response = await fetch(url, opts)

    if (!response.ok) {
      // Parse error details if available
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`
      try {
        const errorData = await response.json()
        errorMessage = errorData.detail || errorMessage
      } catch {
        // Ignore JSON parse errors
      }

      // Handle rate limiting
      if (response.status === 429) {
        const retryAfter = response.headers.get('retry-after')
        errorMessage = `Rate limited. Try again in ${retryAfter || '60'} seconds.`
      }

      throw new Error(errorMessage)
    }

    return response.json()
  }

  async ask(request: AskRequest): Promise<AskResponse> {
    return this.request('POST', '/api/ask', {
      question: request.question,
      project_id: request.project_id || 'default',
    })
  }

  async getGroups(): Promise<GroupNode[]> {
    return this.request('GET', '/api/groups')
  }

  async getGroup(id: string): Promise<GroupDetail> {
    return this.request('GET', `/api/groups/${id}`)
  }

  async getSpec(ref: string): Promise<Spec> {
    return this.request('GET', `/api/specs/${ref}`)
  }

  async getSpecVersions(ref: string): Promise<unknown> {
    return this.request('GET', `/api/specs/${ref}/versions`)
  }

  async getSpecGraph(ref: string): Promise<any> {
    return this.request('GET', `/api/specs/graph/${ref}`)
  }

  async postIngest(repoUrl: string): Promise<IngestResponse> {
    return this.request('POST', '/api/ingest', {
      repo_url: repoUrl,
    })
  }

  async getIngestStatus(jobId: string): Promise<IngestStatus> {
    return this.request('GET', `/api/ingest/${jobId}`)
  }

  async health(): Promise<HealthResponse> {
    return this.request('GET', '/health')
  }
}

export const client = new ApiClient()
