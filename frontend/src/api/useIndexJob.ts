import { useQuery, UseQueryResult } from '@tanstack/react-query'
import { client, IngestStatus } from './client'

export function useIndexJob(jobId: string): UseQueryResult<IngestStatus, Error> {
  // Poll every 1 second while job is in progress
  return useQuery({
    queryKey: ['ingest', jobId],
    queryFn: () => client.getIngestStatus(jobId),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data as IngestStatus | undefined
      // Stop polling when job is done or errored
      if (!data || data.status === 'done' || data.status === 'failed') {
        return false
      }
      return 1000 // Poll every 1 second
    },
    staleTime: 0, // Always refetch
  })
}
