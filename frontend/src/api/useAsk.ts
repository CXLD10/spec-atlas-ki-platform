import { useQuery, UseQueryResult } from '@tanstack/react-query'
import { client, AskResponse } from './client'

export function useAsk(
  question: string,
  projectId: string = 'default'
): UseQueryResult<AskResponse, Error> {
  return useQuery({
    queryKey: ['ask', projectId, question],
    queryFn: () => client.ask({ question, project_id: projectId }),
    enabled: !!question && !!question.trim(),
    staleTime: 1000 * 60 * 10, // 10 minutes
  })
}
