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

export interface Source {
  source_id: string
  type: 'code' | 'pdf' | 'markdown' | 'excel' | 'jira' | 'git_history'
  name: string
  status: 'queued' | 'ingesting' | 'done' | 'failed'
  progress?: number
  error?: string
}

export interface SourcesResponse {
  sources: Source[]
}

export interface GeneratedSpec {
  spec_id: string
  node_id: string
  content: string
  version: number
  status?: 'draft' | 'review' | 'approved'
  created_at?: string
  citations?: Array<{
    file: string
    start_line: number
    end_line: number
  }>
}

export interface GeneratedSpecsListResponse {
  specs: Array<{
    spec_id: string
    node_id: string
    title: string
    version: number
    created_at: string
    citations?: any[]
  }>
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

  async listSources(projectId: string): Promise<Source[]> {
    const response = await this.request<SourcesResponse>(
      'GET',
      `/api/projects/${projectId}/sources`
    )
    return response.sources
  }

  async addCodeSource(projectId: string, repoUrl: string): Promise<IngestResponse> {
    return this.request('POST', '/api/ingest', {
      project_id: projectId,
      repo_url: repoUrl,
    })
  }

  private async uploadFileSource(
    projectId: string,
    sourceType: 'pdf' | 'excel' | 'markdown',
    file: File
  ): Promise<IngestResponse> {
    const formData = new FormData()
    formData.append('project_id', projectId)
    formData.append('source_type', sourceType)
    formData.append('file', file)

    const url = `${this.baseUrl}/api/ingest`
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`
      try {
        const errorData = await response.json()
        errorMessage = errorData.detail || errorMessage
      } catch {
        // Ignore JSON parse errors
      }
      throw new Error(errorMessage)
    }

    return response.json()
  }

  async uploadPDFSource(
    projectId: string,
    file: File
  ): Promise<IngestResponse> {
    return this.uploadFileSource(projectId, 'pdf', file)
  }

  async uploadExcelSource(
    projectId: string,
    file: File
  ): Promise<IngestResponse> {
    return this.uploadFileSource(projectId, 'excel', file)
  }

  async uploadMarkdownSource(
    projectId: string,
    file: File
  ): Promise<IngestResponse> {
    return this.uploadFileSource(projectId, 'markdown', file)
  }

  async getGraphNodes(projectId: string, layers?: string[]): Promise<any[]> {
    const query = new URLSearchParams({ project_id: projectId })
    if (layers && layers.length > 0) {
      layers.forEach((layer) => query.append('layer', layer))
    }
    const path = `/api/graph/nodes?${query}`
    return this.request('GET', path)
  }

  async getGraphEdges(projectId: string, limit?: number): Promise<any[]> {
    const query = new URLSearchParams({ project_id: projectId })
    if (limit) query.append('limit', limit.toString())
    const path = `/api/graph/edges?${query}`
    return this.request('GET', path)
  }

  async getNodeNeighbors(projectId: string, nodeId: string): Promise<any> {
    const query = new URLSearchParams({ project_id: projectId })
    const path = `/api/graph/node/${nodeId}/neighbors?${query}`
    return this.request('GET', path)
  }

  async getGeneratedSpecs(projectId: string): Promise<GeneratedSpecsListResponse> {
    const path = `/api/projects/${projectId}/specs`
    return this.request('GET', path)
  }

  async getGeneratedSpec(projectId: string, specId: string): Promise<GeneratedSpec> {
    const path = `/api/projects/${projectId}/specs/${specId}`
    return this.request('GET', path)
  }
}

export const client = new ApiClient()
