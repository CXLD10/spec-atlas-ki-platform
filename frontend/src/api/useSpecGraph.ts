import { useQuery, UseQueryResult } from '@tanstack/react-query'
import { client } from './client'

export interface SpecGraphData {
  spec: any
  dependencies: any[]
  dependents: any[]
}

export function useSpecGraph(ref: string): UseQueryResult<SpecGraphData, Error> {
  return useQuery({
    queryKey: ['specGraph', ref],
    queryFn: () => client.getSpecGraph(ref),
    enabled: !!ref,
    staleTime: 1000 * 60 * 30, // 30 minutes
  })
}
