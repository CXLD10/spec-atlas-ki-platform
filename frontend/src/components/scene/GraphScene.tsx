import { useRef, useEffect, useState } from 'react'
import { useGraphBuild } from './useGraphBuild'
import { LAYERS } from './layerConfig'
import './GraphScene.css'

interface GraphSceneProps {
  mode?: 'timer' | 'live'
  jobId?: string
  progressPct?: number // For live mode
  onPhaseComplete?: (phase: number) => void
}

export function GraphScene({
  mode = 'timer',
  jobId,
  progressPct,
  onPhaseComplete,
}: GraphSceneProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [context, setContext] = useState<CanvasRenderingContext2D | null>(null)
  const [isHovering, setIsHovering] = useState(false)
  const state = useGraphBuild({ mode, jobId, progressPct, onPhaseComplete })

  // Initialize canvas context
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    // Set canvas size to match window
    const updateSize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    updateSize()
    window.addEventListener('resize', updateSize)

    const ctx = canvas.getContext('2d')
    if (ctx) setContext(ctx)

    // Mouse hover effects
    const handleMouseEnter = () => setIsHovering(true)
    const handleMouseLeave = () => setIsHovering(false)

    canvas.addEventListener('mouseenter', handleMouseEnter)
    canvas.addEventListener('mouseleave', handleMouseLeave)

    return () => {
      window.removeEventListener('resize', updateSize)
      canvas.removeEventListener('mouseenter', handleMouseEnter)
      canvas.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [])

  // Render animation
  useEffect(() => {
    if (!context) return

    const canvas = canvasRef.current
    if (!canvas) return

    let animationId: number
    const startTime = Date.now()

    const render = () => {
      const elapsed = (Date.now() - startTime) / 1000 // Time in seconds

      // Clear canvas
      context.fillStyle = 'var(--bg)'
      context.fillRect(0, 0, canvas.width, canvas.height)

      const centerX = canvas.width / 2
      const centerY = canvas.height / 2

      // Draw edges first (so they appear behind nodes)
      context.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--cyan-glow')
      context.lineWidth = 1.2
      state.edges.slice(0, Math.max(20, state.edges.length * 0.4)).forEach((edge) => {
        const fromNode = state.nodes.find((n) => n.id === edge.from)
        const toNode = state.nodes.find((n) => n.id === edge.to)
        if (!fromNode || !toNode) return

        // Static positions with very subtle depth
        const x1 = centerX + fromNode.x * (1 - fromNode.z * 0.05)
        const y1 = centerY + fromNode.y * (1 - fromNode.z * 0.05)
        const x2 = centerX + toNode.x * (1 - toNode.z * 0.05)
        const y2 = centerY + toNode.y * (1 - toNode.z * 0.05)

        context.globalAlpha = Math.max(0.15, 0.4 - fromNode.z * 0.08)
        context.beginPath()
        context.moveTo(x1, y1)
        context.lineTo(x2, y2)
        context.stroke()
      })
      context.globalAlpha = 1

      // Draw nodes with visible dots
      const hoverBrightness = isHovering ? 1.3 : 1
      state.nodes.forEach((node) => {
        const layer = LAYERS.find((l) => l.id === node.layer)
        if (!layer) return

        // Very subtle pulsing (just opacity, no movement)
        const pulse = 0.9 + Math.sin(elapsed * 2) * 0.1

        const screenX = centerX + node.x * (1 - node.z * 0.05)
        const screenY = centerY + node.y * (1 - node.z * 0.05)

        // Glow effect
        context.fillStyle = layer.color
        context.globalAlpha = Math.max(0.08, (0.25 - node.z * 0.05) * pulse * hoverBrightness)
        context.beginPath()
        context.arc(screenX, screenY, node.radius * 2.5, 0, Math.PI * 2)
        context.fill()

        // Core node dot (visible, solid)
        context.fillStyle = layer.color
        context.globalAlpha = Math.max(0.6, (0.9 - node.z * 0.1) * pulse * hoverBrightness)
        context.beginPath()
        context.arc(screenX, screenY, node.radius, 0, Math.PI * 2)
        context.fill()
      })
      context.globalAlpha = 1

      animationId = requestAnimationFrame(render)
    }

    animationId = requestAnimationFrame(render)

    return () => cancelAnimationFrame(animationId)
  }, [context, state.nodes, state.edges, isHovering])

  return (
    <canvas
      ref={canvasRef}
      className="graph-scene"
      role="img"
      aria-label="Build animation graph"
    />
  )
}
