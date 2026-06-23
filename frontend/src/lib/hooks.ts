/**
 * Data hooks for Spec-Atlas KI.
 * Wraps the API client with React Query if available, else simple useState/useEffect.
 * All hooks degrade gracefully to mock data if the API is unavailable.
 */

import { useState, useEffect } from 'react'
import {
  useQuery,
  useMutation,
} from '@tanstack/react-query'
import { client, MockFallback, Source, KnowledgeCard, JobStatus } from './api'
import { MOCK_SOURCES, MOCK_CARDS, MOCK_ANSWER } from './mock'

/**
 * Hook: List all sources (repos + documents).
 */
export function useSources() {
  return useQuery({
    queryKey: ['sources'],
    queryFn: async () => {
      try {
        return await client.listSources()
      } catch (err) {
        if (err instanceof MockFallback) {
          return MOCK_SOURCES
        }
        throw err
      }
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  })
}

/**
 * Hook: Get a single source.
 */
export function useSource(id: string) {
  return useQuery({
    queryKey: ['source', id],
    queryFn: async () => {
      try {
        return await client.getSource(id)
      } catch (err) {
        if (err instanceof MockFallback) {
          const mock = MOCK_SOURCES.find(s => s.id === id)
          if (!mock) throw new Error(`Source ${id} not found`)
          return mock
        }
        throw err
      }
    },
    enabled: !!id,
  })
}

/**
 * Hook: Ingest a repository (mutation).
 */
export function useIngestRepo() {
  return useMutation({
    mutationFn: async (repoUrl: string) => {
      try {
        return await client.ingestRepo(repoUrl)
      } catch (err) {
        if (err instanceof MockFallback) {
          // Return a mock job ID
          return {
            job_id: `mock-repo-${Date.now()}`,
            status: 'queued' as const,
            progress: 0,
          }
        }
        throw err
      }
    },
  })
}

/**
 * Hook: Upload a document (mutation).
 */
export function useUploadDocument() {
  return useMutation({
    mutationFn: async (file: File) => {
      try {
        return await client.uploadDocument(file)
      } catch (err) {
        if (err instanceof MockFallback) {
          // Return a mock job ID
          return {
            job_id: `mock-document-${Date.now()}`,
            status: 'queued' as const,
            progress: 0,
          }
        }
        throw err
      }
    },
  })
}

/**
 * Hook: Poll ingestion status.
 */
export function useIngestStatus(jobId: string, enabled: boolean = true) {
  const [mockProgress, setMockProgress] = useState(0)

  // Simulate mock progress climbing
  useEffect(() => {
    if (!jobId.startsWith('mock-') || !enabled) return

    const interval = setInterval(() => {
      setMockProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval)
          return 100
        }
        return prev + Math.random() * 20
      })
    }, 800)

    return () => clearInterval(interval)
  }, [jobId, enabled])

  return useQuery({
    queryKey: ['ingestStatus', jobId],
    queryFn: async () => {
      try {
        return await client.ingestStatus(jobId)
      } catch (err) {
        if (err instanceof MockFallback) {
          // Return a mock status that climbs toward 100
          const progress = Math.min(mockProgress, 100)
          return {
            job_id: jobId,
            status:
              progress < 100
                ? ('in_progress' as const)
                : ('done' as const),
            progress,
          }
        }
        throw err
      }
    },
    refetchInterval: enabled && !jobId.startsWith('mock-') ? 1200 : false,
    enabled,
  })
}

/**
 * Hook: List all knowledge cards.
 */
export function useCards() {
  return useQuery({
    queryKey: ['cards'],
    queryFn: async () => {
      try {
        return await client.listCards()
      } catch (err) {
        if (err instanceof MockFallback) {
          return MOCK_CARDS
        }
        throw err
      }
    },
    staleTime: 1000 * 60 * 5,
  })
}

/**
 * Hook: Get a single knowledge card.
 */
export function useCard(ref: string) {
  return useQuery({
    queryKey: ['card', ref],
    queryFn: async () => {
      try {
        return await client.getCard(ref)
      } catch (err) {
        if (err instanceof MockFallback) {
          const mock = MOCK_CARDS.find(c => c.ref === ref)
          if (!mock) throw new Error(`Card ${ref} not found`)
          return mock
        }
        throw err
      }
    },
    enabled: !!ref,
  })
}

/**
 * Hook: Ask the KI agent.
 */
export function useAsk() {
  return useMutation({
    mutationFn: async ({
      question,
      projectId,
    }: {
      question: string
      projectId?: string
    }) => {
      try {
        return await client.ask(question, projectId)
      } catch (err) {
        if (err instanceof MockFallback) {
          return MOCK_ANSWER
        }
        throw err
      }
    },
  })
}

/**
 * Hook: Check backend health.
 */
export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      try {
        return await client.health()
      } catch (err) {
        if (err instanceof MockFallback) {
          return { status: 'offline' }
        }
        throw err
      }
    },
    refetchInterval: 10000, // Every 10 seconds
  })
}

export type { Source, KnowledgeCard, JobStatus }
