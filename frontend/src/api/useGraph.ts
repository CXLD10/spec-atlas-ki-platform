import { useQuery } from '@tanstack/react-query'
import { client } from './client'

export interface GraphNode {
  id: string
  label: string
  kind: string
  layer: 'L1' | 'L3' | 'L4'
  file_path?: string
  qualified_name?: string
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  kind: string
  confidence?: number
}

export function useGraphNodes(projectId: string, layers?: string[]) {
  return useQuery({
    queryKey: ['graph-nodes', projectId, layers],
    queryFn: () => client.getGraphNodes(projectId, layers),
    enabled: !!projectId,
    staleTime: Infinity,
    refetchInterval: false,
  })
}

export function useGraphEdges(projectId: string) {
  return useQuery({
    queryKey: ['graph-edges', projectId],
    queryFn: () => client.getGraphEdges(projectId),
    enabled: !!projectId,
    staleTime: Infinity,
    refetchInterval: false,
  })
}

/** Real L1+L3+L4 layered graph for a repo (GET /api/graph/layered). */
export function useLayeredGraph(repo: string | undefined) {
  return useQuery({
    queryKey: ['layered-graph', repo],
    queryFn: () => client.getLayeredGraph(repo as string),
    enabled: !!repo,
    staleTime: 1000 * 30,
  })
}
