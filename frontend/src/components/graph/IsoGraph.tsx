import { useEffect, useRef, useState } from 'react'
import './IsoGraph.css'

export interface GraphNode {
  id: string
  label: string
  layer: 'L1' | 'L3' | 'L4'
  _x: number
  _y: number
  _z: number
}

export interface GraphEdge {
  s: string
  d: string
  kind: string
  layer: 'L1' | 'L3' | 'L4'
  inter?: boolean
}

interface IsoGraphProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  active: { L1: boolean; L3: boolean; L4: boolean }
  selected?: GraphNode | null
  onNodeClick: (node: GraphNode) => void
}

const LAYER_COLORS = {
  L1: 'rgb(88, 166, 255)',  // --l1 (blue)
  L3: 'rgb(63, 185, 80)',   // --l3 (green)
  L4: 'rgb(124, 139, 255)', // --l4 (purple)
}

export function IsoGraph({ nodes, edges, active, selected, onNodeClick }: IsoGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [yaw, setYaw] = useState(0)
  const [pitch, setPitch] = useState(0.3)
  const [zoom, setZoom] = useState(1)
  const [dragging, setDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [hovered, setHovered] = useState<string | null>(null)

  // Simple 3D isometric projection
  const project3D = (
    x: number,
    y: number,
    z: number,
    centerX: number,
    centerY: number
  ): { x: number; y: number } => {
    // Rotate around Y axis (yaw)
    const cosY = Math.cos(yaw)
    const sinY = Math.sin(yaw)
    let rx = x * cosY - z * sinY
    let ry = y
    let rz = x * sinY + z * cosY

    // Rotate around X axis (pitch)
    const cosX = Math.cos(pitch)
    const sinX = Math.sin(pitch)
    let rx2 = rx
    let ry2 = ry * cosX - rz * sinX
    let rz2 = ry * sinX + rz * cosX

    // Isometric projection: x2 = x - z/2, y2 = y - z/4
    const iso2dx = rx2 - rz2 * 0.5
    const iso2dy = ry2 - rz2 * 0.25

    // Scale by zoom and translate to center
    return {
      x: centerX + iso2dx * zoom,
      y: centerY + iso2dy * zoom,
    }
  }

  const drawGraph = () => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height
    const centerX = width / 2
    const centerY = height / 2

    // Clear canvas
    ctx.fillStyle = 'var(--bg)'
    ctx.fillRect(0, 0, width, height)

    // Filter active nodes
    const activeNodes = nodes.filter((n) => active[n.layer])
    const activeNodeIds = new Set(activeNodes.map((n) => n.id))
    const activeEdges = edges.filter((e) => activeNodeIds.has(e.s) && activeNodeIds.has(e.d))

    // Draw edges first (so they appear behind nodes)
    activeEdges.forEach((edge) => {
      const source = nodes.find((n) => n.id === edge.s)
      const target = nodes.find((n) => n.id === edge.d)

      if (!source || !target) return

      const p1 = project3D(source._x, source._y, source._z, centerX, centerY)
      const p2 = project3D(target._x, target._y, target._z, centerX, centerY)

      const isInter = source.layer !== target.layer

      if (isInter) {
        // Inter-layer beam: gradient, thicker
        const gradient = ctx.createLinearGradient(p1.x, p1.y, p2.x, p2.y)
        gradient.addColorStop(0, LAYER_COLORS[source.layer])
        gradient.addColorStop(1, LAYER_COLORS[target.layer])

        ctx.strokeStyle = gradient
        ctx.globalAlpha = 0.4
        ctx.lineWidth = 2.5
      } else {
        // Intra-layer edge: solid, thin
        ctx.strokeStyle = LAYER_COLORS[source.layer]
        ctx.globalAlpha = 0.2
        ctx.lineWidth = 1
      }

      ctx.beginPath()
      ctx.moveTo(p1.x, p1.y)
      ctx.lineTo(p2.x, p2.y)
      ctx.stroke()
    })

    ctx.globalAlpha = 1

    // Draw nodes
    activeNodes.forEach((node) => {
      const p = project3D(node._x, node._y, node._z, centerX, centerY)
      const isHovered = node.id === hovered
      const isSelected = selected?.id === node.id
      const radius = isHovered || isSelected ? 8 : 6
      const color = LAYER_COLORS[node.layer]

      // Selected ring (outer, solid)
      if (isSelected) {
        ctx.strokeStyle = color
        ctx.globalAlpha = 0.9
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.arc(p.x, p.y, radius + 5, 0, Math.PI * 2)
        ctx.stroke()
      }

      // Glow halo for hover or selected
      if (isHovered || isSelected) {
        ctx.fillStyle = color
        ctx.globalAlpha = isSelected ? 0.25 : 0.15
        ctx.beginPath()
        ctx.arc(p.x, p.y, radius + (isSelected ? 8 : 6), 0, Math.PI * 2)
        ctx.fill()
      }

      // Node circle
      ctx.fillStyle = color
      ctx.globalAlpha = 1
      ctx.beginPath()
      ctx.arc(p.x, p.y, radius, 0, Math.PI * 2)
      ctx.fill()

      // Label: always show for selected, only on hover otherwise
      if (isHovered || isSelected) {
        ctx.fillStyle = isSelected ? '#ffffff' : 'rgba(255,255,255,0.8)'
        ctx.font = `${isSelected ? '600 ' : ''}11px var(--mono, monospace)`
        ctx.globalAlpha = 1
        ctx.fillText(node.label, p.x + radius + 8, p.y + 4)
      }
    })

    // Store node positions for hit detection
    ;(canvas as any).nodePositions = activeNodes.map((node) => ({
      id: node.id,
      pos: project3D(node._x, node._y, node._z, centerX, centerY),
      radius: 8,
    }))
  }

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    let animFrameId: number
    const animate = () => {
      animFrameId = requestAnimationFrame(animate)
      drawGraph()
    }

    animate()

    return () => cancelAnimationFrame(animFrameId)
  }, [nodes, edges, active, yaw, pitch, zoom, hovered, selected])

  // Mouse events
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const onMouseDown = (e: MouseEvent) => {
      setDragging(true)
      setDragStart({ x: e.clientX, y: e.clientY })
    }

    const onMouseMove = (e: MouseEvent) => {
      if (dragging) {
        const deltaX = e.clientX - dragStart.x
        const deltaY = e.clientY - dragStart.y
        setYaw((y) => y + deltaX * 0.01)
        setPitch((p) => Math.max(-Math.PI / 2, Math.min(Math.PI / 2, p + deltaY * 0.01)))
        setDragStart({ x: e.clientX, y: e.clientY })
      } else {
        // Hover detection
        const rect = canvas.getBoundingClientRect()
        const x = e.clientX - rect.left
        const y = e.clientY - rect.top

        let hoveredId: string | null = null
        const nodePositions = (canvas as any).nodePositions || []

        for (const { id, pos, radius } of nodePositions) {
          const dx = x - pos.x
          const dy = y - pos.y
          if (dx * dx + dy * dy < radius * radius) {
            hoveredId = id
            break
          }
        }

        setHovered(hoveredId)
        canvas.style.cursor = hoveredId ? 'pointer' : 'grab'
      }
    }

    const onMouseUp = () => {
      setDragging(false)
    }

    const onClick = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top

      const nodePositions = (canvas as any).nodePositions || []
      for (const { id, pos, radius } of nodePositions) {
        const dx = x - pos.x
        const dy = y - pos.y
        if (dx * dx + dy * dy < radius * radius) {
          const node = nodes.find((n) => n.id === id)
          if (node) onNodeClick(node)
          break
        }
      }
    }

    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      setZoom((z) => Math.max(0.1, Math.min(3, z - e.deltaY * 0.001)))
    }

    canvas.addEventListener('mousedown', onMouseDown)
    canvas.addEventListener('mousemove', onMouseMove)
    canvas.addEventListener('mouseup', onMouseUp)
    canvas.addEventListener('click', onClick)
    canvas.addEventListener('wheel', onWheel, { passive: false })

    return () => {
      canvas.removeEventListener('mousedown', onMouseDown)
      canvas.removeEventListener('mousemove', onMouseMove)
      canvas.removeEventListener('mouseup', onMouseUp)
      canvas.removeEventListener('click', onClick)
      canvas.removeEventListener('wheel', onWheel)
    }
  }, [nodes, dragging, dragStart, onNodeClick])

  // Handle resize via ResizeObserver (more accurate than window resize)
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const setSize = () => {
      const parent = canvas.parentElement
      if (!parent) return
      canvas.width = parent.clientWidth
      canvas.height = parent.clientHeight
    }

    setSize()

    const ro = new ResizeObserver(setSize)
    if (canvas.parentElement) ro.observe(canvas.parentElement)

    return () => ro.disconnect()
  }, [])

  return <canvas ref={canvasRef} className="iso-graph-canvas" />
}
