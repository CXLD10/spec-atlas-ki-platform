import { useQuery } from '@tanstack/react-query'
import { client } from './client'

export function useVerificationReport(repo: string | undefined) {
  return useQuery({
    queryKey: ['verification-report', repo],
    queryFn: () => client.getVerificationReport(repo as string),
    enabled: !!repo,
  })
}

export function useVerificationIssues(repo: string | undefined, limit = 10) {
  return useQuery({
    queryKey: ['verification-issues', repo, limit],
    queryFn: () => client.getVerificationIssues(repo as string, limit),
    enabled: !!repo,
  })
}

export function useConfidenceDistribution(repo: string | undefined, bins = 5) {
  return useQuery({
    queryKey: ['confidence-distribution', repo, bins],
    queryFn: () => client.getConfidenceDistribution(repo as string, bins),
    enabled: !!repo,
  })
}
