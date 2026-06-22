import { useState, useEffect, useCallback } from 'react'
import { PHASE_DURATION } from './layerConfig'

export interface GraphNode {
  id: string
  x: number
  y: number
  z: number
  layer: 'l1' | 'l2' | 'l3' | 'l4'
  radius: number
}

export interface GraphEdge {
  from: string
  to: string
  layer: 'l1' | 'l2' | 'l3' | 'l4'
}

export interface GraphBuildState {
  phase: number // 0-4 (4 = complete)
  progress: number // 0-100 for current phase
  camTargetZ: number // camera depth target
  nodes: GraphNode[]
  edges: GraphEdge[]
  interactive: boolean
}

interface UseGraphBuildOptions {
  mode: 'timer' | 'live'
  jobId?: string
  progressPct?: number // For live mode: 0-100 from backend
  onPhaseComplete?: (phase: number) => void
}

export function useGraphBuild(
  options: UseGraphBuildOptions = { mode: 'timer' }
): GraphBuildState {
  const [state, setState] = useState<GraphBuildState>({
    phase: 0,
    progress: 0,
    camTargetZ: 0,
    nodes: [],
    edges: [],
    interactive: false,
  })

  // Check for prefers-reduced-motion
  const prefersReducedMotion = useCallback(() => {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }, [])

  // Timer-driven demo mode (Landing page)
  useEffect(() => {
    if (options.mode !== 'timer') return

    const reducedMotion = prefersReducedMotion()

    if (reducedMotion) {
      // Skip animation, go straight to final state
      setState({
        phase: 4,
        progress: 100,
        camTargetZ: 3,
        nodes: generateNodes(4),
        edges: generateEdges(4),
        interactive: true,
      })
      options.onPhaseComplete?.(4)
      return
    }

    const startTime = Date.now()
    let animationId: number

    const updateAnimation = () => {
      const elapsed = Date.now() - startTime
      const totalDuration = PHASE_DURATION * 4

      if (elapsed >= totalDuration) {
        // Animation complete
        setState({
          phase: 4,
          progress: 100,
          camTargetZ: 3,
          nodes: generateNodes(4),
          edges: generateEdges(4),
          interactive: true,
        })
        options.onPhaseComplete?.(4)
        return
      }

      const currentPhase = Math.floor(elapsed / PHASE_DURATION)
      const phaseProgress = (elapsed % PHASE_DURATION) / PHASE_DURATION

      setState((prev) => ({
        ...prev,
        phase: currentPhase,
        progress: Math.min(phaseProgress * 100, 100),
        camTargetZ: currentPhase,
        nodes: generateNodes(currentPhase + 1),
        edges: generateEdges(currentPhase + 1),
      }))

      if (currentPhase > 0 && Math.floor((elapsed - PHASE_DURATION) / PHASE_DURATION) < currentPhase) {
        // Phase transition happened
        options.onPhaseComplete?.(currentPhase)
      }

      animationId = requestAnimationFrame(updateAnimation)
    }

    animationId = requestAnimationFrame(updateAnimation)

    return () => cancelAnimationFrame(animationId)
  }, [options.mode, options.onPhaseComplete, prefersReducedMotion])

  // Live mode: driven by backend progress percentage (polling fallback)
  useEffect(() => {
    if (options.mode !== 'live' || options.progressPct === undefined) return

    const reducedMotion = prefersReducedMotion()
    const progressPct = Math.min(options.progressPct, 100)

    if (reducedMotion) {
      // Skip animation, show current phase based on progress
      const phase = Math.floor((progressPct / 100) * 4)
      setState({
        phase,
        progress: progressPct,
        camTargetZ: phase,
        nodes: generateNodes(phase + 1),
        edges: generateEdges(phase + 1),
        interactive: progressPct === 100,
      })
      if (progressPct === 100) {
        options.onPhaseComplete?.(4)
      }
      return
    }

    // Map progress percentage to phase (0-25% = phase 0, 25-50% = phase 1, etc.)
    const phase = Math.min(Math.floor((progressPct / 100) * 4), 4)
    const phaseProgress = ((progressPct % 25) / 25) * 100

    setState({
      phase,
      progress: phaseProgress,
      camTargetZ: phase,
      nodes: generateNodes(Math.min(phase + 1, 4)),
      edges: generateEdges(Math.min(phase + 1, 4)),
      interactive: progressPct === 100,
    })

    if (progressPct === 100) {
      options.onPhaseComplete?.(4)
    }
  }, [options.mode, options.progressPct, options.onPhaseComplete, prefersReducedMotion])

  return state
}

function generateNodes(maxPhase: number): GraphNode[] {
  const nodes: GraphNode[] = []
  const nodeCounts = [200, 120, 80, 50]

  for (let phase = 0; phase < Math.min(maxPhase, 4); phase++) {
    const count = nodeCounts[phase]
    const z = phase

    for (let i = 0; i < count; i++) {
      nodes.push({
        id: `${phase}-${i}`,
        x: Math.random() * 800 - 400,
        y: Math.random() * 600 - 300,
        z,
        layer: ['l1', 'l2', 'l3', 'l4'][phase] as 'l1' | 'l2' | 'l3' | 'l4',
        radius: 2 + Math.random() * 2,
      })
    }
  }

  return nodes
}

function generateEdges(maxPhase: number): GraphEdge[] {
  const edges: GraphEdge[] = []
  const nodeCounts = [200, 120, 80, 50]

  for (let phase = 0; phase < Math.min(maxPhase, 4); phase++) {
    const count = nodeCounts[phase]

    for (let i = 0; i < Math.min(count * 0.5, count - 1); i++) {
      const from = Math.floor(Math.random() * count)
      const to = Math.floor(Math.random() * count)

      if (from !== to) {
        edges.push({
          from: `${phase}-${from}`,
          to: `${phase}-${to}`,
          layer: ['l1', 'l2', 'l3', 'l4'][phase] as 'l1' | 'l2' | 'l3' | 'l4',
        })
      }
    }
  }

  return edges
}
