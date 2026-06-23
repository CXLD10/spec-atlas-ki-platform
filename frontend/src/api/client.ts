/* Typed API client for Spec-Atlas backend */

import type { Source as KISource, KnowledgeCard } from '../lib/types'

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

// Shape returned by GET /api/graph/subgraph (graph.py's NodeDetail/EdgeDetail):
// a single L1 node's immediate neighborhood. For the full L1/L3/L4 graph used
// by the /graph page, see getLayeredGraph (GET /api/graph/layered) below.
export interface SubgraphNode {
  id: string
  label: string
  layer: 'L1' | 'L3' | 'L4'
  _x: number
  _y: number
  _z: number
}

export interface SubgraphEdge {
  s: string
  d: string
  kind: string
  layer: 'L1' | 'L3' | 'L4'
  inter?: boolean
}

export interface SubgraphResult {
  nodes: SubgraphNode[]
  edges: SubgraphEdge[]
}

// Real shape of POST /api/specs/generate/{component_ref}?repo=... (specs.py
// GenerateSpecResponse). Not the KnowledgeCard shape yet — Specify.tsx adapts
// it client-side until the backend/Specify rewiring lands (Phase 1).
export interface GeneratedSpecResult {
  component_ref: string
  version: number
  status: string
  content: Record<string, unknown>
  provenance: unknown[]
  created_at: string
}

// GET /api/graph/layered?repo=... — L1 code + L3 specs + L4 groups, tagged
// by layer, with inter-layer edges (group contains node, spec documents
// node). Note: this interface is intentionally identical in shape to
// api/useGraph.ts's GraphNode/GraphEdge (kept separate to avoid a circular
// import — useGraph.ts already imports `client` from this module).
export interface LayeredGraphNode {
  id: string
  label: string
  kind: string
  layer: 'L1' | 'L3' | 'L4'
  file_path?: string
  qualified_name?: string
}

export interface LayeredGraphEdge {
  id: string
  source: string
  target: string
  kind: string
  confidence?: number
  inter: boolean
}

export interface LayeredGraphResult {
  nodes: LayeredGraphNode[]
  edges: LayeredGraphEdge[]
}

// GET /api/reports/verification, /verification/issues, /verification/confidence
export interface VerificationReport {
  total_specs: number
  verified_count: number
  review_count: number
  draft_count: number
  avg_confidence: number
  verification_rate: number
  specs_needing_review: number
}

export interface VerificationIssuesReport {
  issues: Array<{ reason: string; count: number }>
  count: number
}

export interface ConfidenceDistribution {
  bins: string[]
  counts: number[]
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

  // ── Unified IA: subgraph, knowledge sources/cards, document upload ──────
  // These back the new IA pages (Dashboard/Sources/KnowledgeBase/Graph).
  // listKnowledgeSources/listKnowledgeCards are real (Phase 1: GET /api/sources,
  // /api/kb). getSourceSnippet/uploadDocument still hit routes that don't exist
  // yet (/api/documents, /api/source-snippet — Phase 2 document ingestion);
  // calling them surfaces a real error, never mock data.

  async getSubgraph(nodeId?: string, maxDepth: number = 2): Promise<SubgraphResult> {
    const params = new URLSearchParams()
    if (nodeId) params.append('node_id', nodeId)
    params.append('max_depth', String(maxDepth))
    const raw = await this.request<{
      nodes: Array<{ id: string; qualified_name: string; kind: string }>
      edges: Array<{ src_node_id: string; dst_node_id: string; kind: string }>
    }>('GET', `/api/graph/subgraph?${params.toString()}`)

    return {
      nodes: raw.nodes.map((n) => ({
        id: n.id,
        label: n.qualified_name,
        layer: 'L1',
        _x: 0,
        _y: 0,
        _z: 0,
      })),
      edges: raw.edges.map((e) => ({
        s: e.src_node_id,
        d: e.dst_node_id,
        kind: e.kind,
        layer: 'L1',
      })),
    }
  }

  async listKnowledgeSources(): Promise<KISource[]> {
    return this.request('GET', '/api/sources')
  }

  async getKnowledgeSource(id: string): Promise<KISource> {
    return this.request('GET', `/api/sources/${id}`)
  }

  async uploadDocument(file: File): Promise<IngestResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const url = `${this.baseUrl}/api/documents`
    const response = await fetch(url, { method: 'POST', body: formData })

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

  async listKnowledgeCards(): Promise<KnowledgeCard[]> {
    return this.request('GET', '/api/kb')
  }

  async getKnowledgeCard(ref: string): Promise<KnowledgeCard> {
    return this.request('GET', `/api/kb/${ref}`)
  }

  async getSourceSnippet(docId: string, page?: number): Promise<{ snippet: string }> {
    const params = new URLSearchParams()
    params.append('doc', docId)
    if (page) params.append('page', String(page))
    return this.request('GET', `/api/source-snippet?${params.toString()}`)
  }

  async generateSpec(repo: string, componentRef: string): Promise<GeneratedSpecResult> {
    const params = new URLSearchParams({ repo })
    return this.request(
      'POST',
      `/api/specs/generate/${encodeURIComponent(componentRef)}?${params.toString()}`
    )
  }

  async getSpecDetail(repo: string, componentRef: string): Promise<GeneratedSpecResult> {
    const params = new URLSearchParams({ repo })
    return this.request(
      'GET',
      `/api/specs/${encodeURIComponent(componentRef)}?${params.toString()}`
    )
  }

  async verifySpec(
    repo: string,
    componentRef: string,
    version: number
  ): Promise<{ component_ref: string; version: number; status: string; confidence: number; is_grounded: boolean; issues: Array<{ claim: string; reason: string; severity: string }> }> {
    const params = new URLSearchParams({ repo, version: String(version) })
    return this.request(
      'POST',
      `/api/specs/${encodeURIComponent(componentRef)}/verify?${params.toString()}`
    )
  }

  async getLayeredGraph(repo: string): Promise<LayeredGraphResult> {
    const params = new URLSearchParams({ repo })
    return this.request('GET', `/api/graph/layered?${params.toString()}`)
  }

  async getVerificationReport(repo: string): Promise<VerificationReport> {
    const params = new URLSearchParams({ repo })
    return this.request('GET', `/api/reports/verification?${params.toString()}`)
  }

  async getVerificationIssues(repo: string, limit: number = 10): Promise<VerificationIssuesReport> {
    const params = new URLSearchParams({ repo, limit: String(limit) })
    return this.request('GET', `/api/reports/verification/issues?${params.toString()}`)
  }

  async getConfidenceDistribution(repo: string, bins: number = 5): Promise<ConfidenceDistribution> {
    const params = new URLSearchParams({ repo, bins: String(bins) })
    return this.request('GET', `/api/reports/verification/confidence?${params.toString()}`)
  }
}

export const client = new ApiClient()
