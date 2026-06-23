/**
 * Data types for Spec-Atlas KI platform.
 * Unified types for repos and documents as Sources, and generated knowledge cards.
 */

export type SourceType = 'repo' | 'document'
export type SourceFormat = 'git' | 'pdf' | 'xlsx' | 'md'
export type SourceStatus = 'queued' | 'indexing' | 'ready' | 'error'
export type CardStatus = 'draft' | 'verified' | 'stale'
export type ProvenanceKind = 'code' | 'pdf' | 'xlsx' | 'md'

/**
 * Provenance: where a fact/fragment came from.
 * Examples: "auth/session.py:88" | "rfc.pdf p.12" | "service-catalog.xlsx!Sheet1!B4"
 */
export interface Provenance {
  ref: string           // e.g. "service-catalog.xlsx"
  kind: ProvenanceKind  // code|pdf|xlsx|md
  loc: string           // e.g. "Sheet1!B4" or "p.12" or "auth/session.py:88"
}

/**
 * A Source is either a repository or an uploaded document.
 */
export interface Source {
  id: string
  type: SourceType
  name: string                  // e.g. "huggingface/transformers" | "Platform RFC v3.pdf"
  subtitle?: string             // e.g. org/desc | filetype + page count
  status: SourceStatus
  progress?: number             // 0..100 for indexing
  stats: {
    entities: number            // symbols for repos, pages for docs
    cards: number               // generated knowledge cards
  }
  format?: SourceFormat
  updatedAt: string             // ISO timestamp
}

/**
 * A Knowledge Card is a generated, structured markdown page.
 * Generated from source fragments, citable and relational.
 */
export interface KnowledgeCard {
  ref: string                   // unique identifier
  title: string
  status: CardStatus
  markdown: string              // the generated knowledge page
  provenance: Provenance[]      // sources this card cites
  relations: {
    kind: string                // 'depends-on' | 'part-of' | 'references'
    ref: string                 // reference to another card
  }[]
}

/**
 * Job status for async ingestion (repo or document).
 */
export interface JobStatus {
  job_id: string
  status: 'queued' | 'in_progress' | 'done' | 'failed'
  progress: number              // 0..100
  error?: string
}

/**
 * Response from /api/ask
 */
export interface AskResponse {
  answer: string
  claims: Array<{
    text?: string
    source: string
    file?: string
    start_line?: number
    end_line?: number
    confidence?: number
  }>
  confidence?: number
  route_used?: string
  status?: 'success' | 'empty_db' | 'no_results' | 'error'
  suggestions?: string[]
}

/**
 * Health check response.
 */
export interface HealthResponse {
  status: string
  analysis_db?: string
  spec_db?: string
  llm?: string
  embed?: string
}
