import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client, IngestResponse } from './client'

export function useSources(projectId: string) {
  return useQuery({
    queryKey: ['sources', projectId],
    queryFn: () => client.listSources(projectId),
    enabled: !!projectId,
    refetchInterval: 2000,
    staleTime: 0,
  })
}

export function useAddSource(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: {
      type: 'code' | 'pdf'
      url?: string
      file?: File
    }): Promise<IngestResponse> => {
      if (data.type === 'code' && data.url) {
        return client.addCodeSource(projectId, data.url)
      } else if (data.type === 'pdf' && data.file) {
        return client.uploadPDFSource(projectId, data.file)
      }
      throw new Error('Invalid source data')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', projectId] })
    },
  })
}
