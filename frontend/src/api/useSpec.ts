import { useQuery, UseQueryResult } from '@tanstack/react-query'
import { client, Spec } from './client'

export function useSpec(ref: string): UseQueryResult<Spec, Error> {
  return useQuery({
    queryKey: ['spec', ref],
    queryFn: () => client.getSpec(ref),
    enabled: !!ref,
    staleTime: 1000 * 60 * 30, // 30 minutes
  })
}
