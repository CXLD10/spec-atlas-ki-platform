import { useQuery, UseQueryResult } from '@tanstack/react-query'
import { client, GroupNode, GroupDetail } from './client'

export function useGroups(): UseQueryResult<GroupNode[], Error> {
  return useQuery({
    queryKey: ['groups'],
    queryFn: () => client.getGroups(),
    staleTime: 1000 * 60 * 30, // 30 minutes
  })
}

export function useGroup(id: string): UseQueryResult<GroupDetail, Error> {
  return useQuery({
    queryKey: ['group', id],
    queryFn: () => client.getGroup(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 30, // 30 minutes
  })
}
