import { useQuery, UseQueryResult } from '@tanstack/react-query'
import { client, AskResponse } from './client'

export function useAsk(
  question: string,
  repo: string = 'default'
): UseQueryResult<AskResponse, Error> {
  return useQuery({
    queryKey: ['ask', repo, question],
    queryFn: () => client.ask({ question, repo }),
    enabled: !!question && !!question.trim(),
    staleTime: 1000 * 60 * 10, // 10 minutes
  })
}
