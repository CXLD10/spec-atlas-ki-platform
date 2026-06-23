/**
 * Data hooks for Spec-Atlas KI.
 * Thin React Query wrappers around the single real API client (api/client.ts).
 * No mock fallback: a failed request surfaces as a real React Query error
 * (isError/error), and callers render a real loading/error/empty state.
 */

import { useQuery, useMutation } from '@tanstack/react-query'
import { client } from '../api/client'
import type { Source, KnowledgeCard, JobStatus } from './types'

/**
 * Hook: List all sources (repos + documents).
 */
export function useSources() {
  return useQuery<Source[]>({
    queryKey: ['sources'],
    queryFn: () => client.listKnowledgeSources(),
    staleTime: 1000 * 60 * 5, // 5 minutes
    refetchInterval: 5000, // Auto-refetch every 5 seconds to show new sources
  })
}

/**
 * Hook: Get a single source.
 */
export function useSource(id: string) {
  return useQuery<Source>({
    queryKey: ['source', id],
    queryFn: () => client.getKnowledgeSource(id),
    enabled: !!id,
  })
}

/**
 * Hook: Ingest a repository (mutation).
 */
export function useIngestRepo() {
  return useMutation({
    mutationFn: (repoUrl: string) => client.postIngest(repoUrl),
  })
}

/**
 * Hook: Upload a document (mutation).
 */
export function useUploadDocument() {
  return useMutation({
    mutationFn: (file: File) => client.uploadDocument(file),
  })
}

/**
 * Hook: Poll ingestion status.
 */
export function useIngestStatus(jobId: string, enabled: boolean = true) {
  return useQuery<JobStatus>({
    queryKey: ['ingestStatus', jobId],
    queryFn: () => client.getIngestStatus(jobId),
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data || data.status === 'done' || data.status === 'failed') return false
      return 1200
    },
    enabled: enabled && !!jobId,
  })
}

/**
 * Hook: List all knowledge cards.
 */
export function useCards() {
  return useQuery<KnowledgeCard[]>({
    queryKey: ['cards'],
    queryFn: () => client.listKnowledgeCards(),
    staleTime: 1000 * 60 * 5,
  })
}

/**
 * Hook: Get a single knowledge card.
 */
export function useCard(ref: string) {
  return useQuery<KnowledgeCard>({
    queryKey: ['card', ref],
    queryFn: () => client.getKnowledgeCard(ref),
    enabled: !!ref,
  })
}

/**
 * Hook: Ask the KI agent.
 */
export function useAsk() {
  return useMutation({
    mutationFn: ({ question, projectId }: { question: string; projectId?: string }) =>
      client.ask({ question, project_id: projectId }),
  })
}

/**
 * Hook: Check backend health.
 */
export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => client.health(),
    refetchInterval: 10000, // Every 10 seconds
  })
}

export type { Source, KnowledgeCard, JobStatus }
