import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import type { LayeredGraphNode, LayeredGraphEdge } from '../../api/client'
import './GraphCanvas3D.css'

// Adapted from pages/RepoGraphify.tsx's scene (the only place in this
// codebase that actually used THREE.js + raycasting against real data) —
// extracted into a reusable, prop-driven component for the primary /graph
// route, decoupled from RepoGraphify's repo-scoped data fetching.

class OrbitControls {
  constructor(camera: THREE.Camera, domElement: HTMLElement) {
    this.camera = camera
    this.domElement = domElement
    domElement.addEventListener('mousedown', this.onMouseDown)
    domElement.addEventListener('mousemove', this.onMouseMove)
    domElement.addEventListener('mouseup', this.onMouseUp)
    domElement.addEventListener('wheel', this.onMouseWheel, { passive: false })
  }

  camera: THREE.Camera
  domElement: HTMLElement
  isPanning = false
  isRotating = false
  previousMousePosition = { x: 0, y: 0 }

  onMouseDown = (event: MouseEvent) => {
    if (event.button === 2) this.isPanning = true
    if (event.button === 0) this.isRotating = true
    this.previousMousePosition = { x: event.clientX, y: event.clientY }
  }

  onMouseMove = (event: MouseEvent) => {
    const deltaX = event.clientX - this.previousMousePosition.x
    const deltaY = event.clientY - this.previousMousePosition.y

    if (this.isRotating) {
      const speed = 0.002
      const cam = this.camera as THREE.PerspectiveCamera
      const pos = new THREE.Vector3().copy(cam.position)
      const theta = Math.atan2(pos.z, pos.x) + deltaX * speed
      const phi = Math.acos(pos.y / pos.length()) + deltaY * speed
      const radius = pos.length()
      cam.position.x = radius * Math.sin(phi) * Math.cos(theta)
      cam.position.y = radius * Math.cos(phi)
      cam.position.z = radius * Math.sin(phi) * Math.sin(theta)
      cam.lookAt(0, 0, 0)
    }

    if (this.isPanning) {
      const speed = 0.1
      const cam = this.camera as THREE.PerspectiveCamera
      cam.position.x -= deltaX * speed
      cam.position.y += deltaY * speed
    }

    this.previousMousePosition = { x: event.clientX, y: event.clientY }
  }

  onMouseUp = () => {
    this.isPanning = false
    this.isRotating = false
  }

  onMouseWheel = (event: WheelEvent) => {
    event.preventDefault()
    const speed = 1.05
    const cam = this.camera as THREE.PerspectiveCamera
    const direction = new THREE.Vector3().copy(cam.position).normalize()
    const distance = cam.position.length()
    const newDistance = event.deltaY > 0 ? distance * speed : distance / speed
    cam.position.copy(direction.multiplyScalar(newDistance))
  }
}

const LAYER_COLORS: Record<string, number> = {
  L1: 0x58a6ff, // blue — code
  L3: 0x3fb950, // green — specs
  L4: 0x7c8bff, // purple — groups/domains
}

const EDGE_COLORS: Record<string, number> = {
  imports: 0x58a6ff,
  calls: 0x3fb950,
  defines: 0xd291f2,
  inherits: 0xd29922,
  documents: 0x3fb950,
  contains: 0x7c8bff,
  'part-of': 0x7c8bff,
  uses: 0x3fb950,
  'depends-on': 0xd29922,
}

interface GraphCanvas3DProps {
  nodes: LayeredGraphNode[]
  edges: LayeredGraphEdge[]
  onSelectNode: (node: LayeredGraphNode | null) => void
  selectedNodeId?: string | null
}

export function GraphCanvas3D({ nodes, edges, onSelectNode, selectedNodeId }: GraphCanvas3DProps) {
  const mountRef = useRef<HTMLDivElement>(null)
  // animate()'s rAF closure is only rebuilt when nodes/edges change (full
  // scene rebuild is expensive); selection changes far more often, so it's
  // read from a ref each frame instead of being a useEffect dependency.
  const selectedNodeIdRef = useRef<string | null | undefined>(selectedNodeId)
  useEffect(() => {
    selectedNodeIdRef.current = selectedNodeId
  }, [selectedNodeId])

  useEffect(() => {
    const mount = mountRef.current
    if (!mount || nodes.length === 0) return

    const width = mount.clientWidth
    const height = mount.clientHeight

    const visibleNodeIds = new Set(nodes.map((n) => n.id))
    const visibleEdges = edges.filter(
      (e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)
    )

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0d1117)

    const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 10000)
    camera.position.z = Math.max(50, nodes.length * 0.6)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(window.devicePixelRatio)
    mount.appendChild(renderer.domElement)

    interface PhysicsNode {
      position: THREE.Vector3
      velocity: THREE.Vector3
      mesh: THREE.Mesh
    }

    const physicsNodes: Record<string, PhysicsNode> = {}
    const nodeMeshes: Record<string, THREE.Mesh> = {}

    nodes.forEach((node) => {
      const color = LAYER_COLORS[node.layer] ?? 0x6b7280
      const radius = node.layer === 'L4' ? 3 : node.layer === 'L3' ? 2.4 : 1.8
      const material = new THREE.MeshPhongMaterial({ color, emissive: 0x000000, shininess: 100 })
      const geometry = new THREE.SphereGeometry(radius, 24, 24)
      const mesh = new THREE.Mesh(geometry, material)

      // Layer-separated initial layout: each layer on its own ring/depth band.
      const layerDepth = { L1: 0, L3: -40, L4: -80 }[node.layer] ?? 0
      const angle = Math.random() * Math.PI * 2
      const ring = 30 + Math.random() * 25
      mesh.position.set(Math.cos(angle) * ring, (Math.random() - 0.5) * 40, layerDepth + Math.sin(angle) * ring)
      mesh.userData = { node }

      scene.add(mesh)
      nodeMeshes[node.id] = mesh
      physicsNodes[node.id] = { position: mesh.position.clone(), velocity: new THREE.Vector3(), mesh }
    })

    const edgeGroup = new THREE.Group()
    const edgeMaterialCache: Record<string, THREE.LineBasicMaterial> = {}
    const defaultEdgeMaterial = new THREE.LineBasicMaterial({
      color: 0x30363d,
      opacity: 0.2,
      transparent: true,
    })

    function materialFor(kind: string, inter: boolean): THREE.LineBasicMaterial {
      const key = `${kind}:${inter}`
      if (!edgeMaterialCache[key]) {
        const color = EDGE_COLORS[kind] ?? 0x30363d
        edgeMaterialCache[key] = new THREE.LineBasicMaterial({
          color,
          opacity: inter ? 0.35 : 0.25,
          transparent: true,
        })
      }
      return edgeMaterialCache[key]
    }

    visibleEdges.forEach((edge) => {
      const source = nodeMeshes[edge.source]
      const target = nodeMeshes[edge.target]
      if (!source || !target) return

      const geometry = new THREE.BufferGeometry()
      geometry.setAttribute(
        'position',
        new THREE.BufferAttribute(
          new Float32Array([
            source.position.x,
            source.position.y,
            source.position.z,
            target.position.x,
            target.position.y,
            target.position.z,
          ]),
          3
        )
      )
      const material = materialFor(edge.kind, edge.inter) ?? defaultEdgeMaterial
      edgeGroup.add(new THREE.Line(geometry, material))
    })
    scene.add(edgeGroup)

    scene.add(new THREE.AmbientLight(0xffffff, 0.5))
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
    directionalLight.position.set(50, 50, 50)
    scene.add(directionalLight)

    const controls = new OrbitControls(camera, renderer.domElement)

    const raycaster = new THREE.Raycaster()
    const mouse = new THREE.Vector2()
    let isInteracting = false

    const resetMeshColors = () => {
      Object.values(nodeMeshes).forEach((mesh) => {
        const node = mesh.userData.node as LayeredGraphNode
        const color = LAYER_COLORS[node.layer] ?? 0x6b7280
        ;(mesh.material as THREE.MeshPhongMaterial).color.setHex(color)
        ;(mesh.material as THREE.MeshPhongMaterial).emissive.setHex(0x000000)
      })
    }

    const onMouseMove = (event: MouseEvent) => {
      if (isInteracting) return
      const rect = renderer.domElement.getBoundingClientRect()
      mouse.x = ((event.clientX - rect.left) / width) * 2 - 1
      mouse.y = -((event.clientY - rect.top) / height) * 2 + 1
      raycaster.setFromCamera(mouse, camera)
      const intersects = raycaster.intersectObjects(Object.values(nodeMeshes))
      renderer.domElement.style.cursor = intersects.length > 0 ? 'pointer' : 'grab'
    }

    const onMouseDown = (event: MouseEvent) => {
      if (event.button === 0 || event.button === 2) isInteracting = true
    }
    const onMouseUp = () => {
      isInteracting = false
    }

    const onMouseUp = () => {
      dragDistance = 0
    }

    const onClick = (event: MouseEvent) => {
      if (isInteracting) return
      const rect = renderer.domElement.getBoundingClientRect()
      mouse.x = ((event.clientX - rect.left) / width) * 2 - 1
      mouse.y = -((event.clientY - rect.top) / height) * 2 + 1
      raycaster.setFromCamera(mouse, camera)
      const intersects = raycaster.intersectObjects(Object.values(nodeMeshes))
      if (intersects.length > 0) {
        const node = (intersects[0].object as THREE.Mesh).userData.node as LayeredGraphNode
        onSelectNode(node)
      } else {
        onSelectNode(null)
      }
    }

    renderer.domElement.addEventListener('mousemove', onMouseMove)
    renderer.domElement.addEventListener('mousedown', onMouseDown)
    renderer.domElement.addEventListener('mouseup', onMouseUp)
    renderer.domElement.addEventListener('click', onClick)
    renderer.domElement.style.cursor = 'grab'

    let animationFrameId: number
    let frameCount = 0

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate)
      frameCount++

      if (frameCount % 2 === 0) {
        Object.values(physicsNodes).forEach((p) => {
          Object.values(physicsNodes).forEach((other) => {
            if (other === p) return
            const diff = new THREE.Vector3().subVectors(p.position, other.position)
            const distance = diff.length()
            if (distance > 0.1 && distance < 60) {
              diff.normalize().multiplyScalar(0.015)
              p.velocity.add(diff)
            }
          })

          visibleEdges.forEach((edge) => {
            if (edge.source === p.mesh.userData.node.id && physicsNodes[edge.target]) {
              const diff = new THREE.Vector3()
                .subVectors(physicsNodes[edge.target].position, p.position)
                .multiplyScalar(-0.0015)
              p.velocity.add(diff)
            }
          })

          p.velocity.multiplyScalar(0.95)
          p.position.add(p.velocity)
          p.mesh.position.copy(p.position)
        })

        // Re-draw edge lines each physics tick to track moving nodes.
        edgeGroup.children.forEach((obj, i) => {
          const edge = visibleEdges[i]
          if (!edge) return
          const source = nodeMeshes[edge.source]
          const target = nodeMeshes[edge.target]
          if (!source || !target) return
          const line = obj as THREE.Line
          const positions = (line.geometry.getAttribute('position') as THREE.BufferAttribute).array as Float32Array
          positions[0] = source.position.x
          positions[1] = source.position.y
          positions[2] = source.position.z
          positions[3] = target.position.x
          positions[4] = target.position.y
          positions[5] = target.position.z
          line.geometry.getAttribute('position').needsUpdate = true
        })
      }

      // Selection highlight (reads the ref, not the closed-over prop).
      resetMeshColors()
      const selected = selectedNodeIdRef.current
      if (selected && nodeMeshes[selected]) {
        const mat = nodeMeshes[selected].material as THREE.MeshPhongMaterial
        mat.emissive.setHex(0xffffff)
        mat.emissive.multiplyScalar(0.5)
      }

      renderer.render(scene, camera)
    }
    animate()

    const onResize = () => {
      const w = mount.clientWidth
      const h = mount.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', onResize)

    return () => {
      window.removeEventListener('resize', onResize)
      renderer.domElement.removeEventListener('mousemove', onMouseMove)
      renderer.domElement.removeEventListener('mousedown', onMouseDown)
      renderer.domElement.removeEventListener('mouseup', onMouseUp)
      renderer.domElement.removeEventListener('click', onClick)
      renderer.domElement.removeEventListener('wheel', controls.onMouseWheel)
      renderer.domElement.removeEventListener('mousedown', controls.onMouseDown)
      renderer.domElement.removeEventListener('mousemove', controls.onMouseMove)
      renderer.domElement.removeEventListener('mouseup', controls.onMouseUp)
      cancelAnimationFrame(animationFrameId)
      mount.removeChild(renderer.domElement)
      renderer.dispose()

      Object.values(nodeMeshes).forEach((mesh) => {
        mesh.geometry.dispose()
        if (mesh.material instanceof THREE.Material) mesh.material.dispose()
      })
      edgeGroup.children.forEach((line) => {
        if (line instanceof THREE.Line) {
          line.geometry.dispose()
          if (line.material instanceof THREE.Material) line.material.dispose()
        }
      })
    }
    // selectedNodeId intentionally excluded: handled per-frame inside animate()
    // so selection doesn't tear down and rebuild the whole WebGL scene.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges, onSelectNode])

  return <div ref={mountRef} className="graph-canvas-3d" role="img" aria-label="Knowledge graph" />
}
