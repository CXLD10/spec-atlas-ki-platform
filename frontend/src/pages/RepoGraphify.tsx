import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import * as THREE from 'three'
import { TopBar } from '../components/layout/TopBar'
import { useGraphNodes, useGraphEdges } from '../api/useGraph'
import './RepoGraphify.css'

// OrbitControls for camera manipulation
class OrbitControls {
  constructor(camera: THREE.Camera, domElement: HTMLElement) {
    this.camera = camera
    this.domElement = domElement
    this.isPanning = false
    this.isRotating = false
    this.previousMousePosition = { x: 0, y: 0 }

    domElement.addEventListener('mousedown', this.onMouseDown)
    domElement.addEventListener('mousemove', this.onMouseMove)
    domElement.addEventListener('mouseup', this.onMouseUp)
    domElement.addEventListener('wheel', this.onMouseWheel, false)
  }

  camera: THREE.Camera
  domElement: HTMLElement
  isPanning = false
  isRotating = false
  previousMousePosition = { x: 0, y: 0 }

  onMouseDown = (event: MouseEvent) => {
    if (event.button === 2) this.isPanning = true // Right mouse
    if (event.button === 0) this.isRotating = true // Left mouse
    this.previousMousePosition = { x: event.clientX, y: event.clientY }
  }

  onMouseMove = (event: MouseEvent) => {
    const deltaX = event.clientX - this.previousMousePosition.x
    const deltaY = event.clientY - this.previousMousePosition.y

    if (this.isRotating) {
      const speed = 0.002
      const cam = this.camera as THREE.PerspectiveCamera
      const pos = new THREE.Vector3().copy(cam.position)

      // Rotate around center
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

interface GraphNode {
  id: string
  label: string
  kind: string
  file_path: string
  layer?: 'L1' | 'L3' | 'L4' // L1=code, L3=spec, L4=groups
}

interface GraphEdge {
  id: string
  source: string
  target: string
  kind: string
  confidence: number
  layer?: 'L1' | 'L3' | 'L4'
}

// Color scheme for layers
const LAYER_COLORS: { [key: string]: number } = {
  L1: 0x6b7280,        // Gray - Code/Sources
  L3: 0x10b981,        // Green - Specs
  L4: 0x3b82f6,        // Blue - Groups
}

const DEFAULT_NODE_COLOR = 0x6b7280 // Gray for unknown

// Fallback for kind-based colors if layer is not set
const NODE_COLORS: { [key: string]: number } = {
  module: 0x58a6ff,
  class: 0x79c0ff,
  function: 0x58a6ff,
  method: 0x3fb950,
  interface: 0xd291f2,
}

export default function RepoGraphify() {
  const { repoId = 'default' } = useParams<{ repoId: string }>()
  const mountRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)

  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [stats, setStats] = useState({ nodes: 0, edges: 0 })
  const [layerVisibility, setLayerVisibility] = useState({
    L1: true,
    L3: true,
    L4: true,
  })

  // Fetch graph data using hooks
  const visibleLayers = Object.entries(layerVisibility)
    .filter(([_, visible]) => visible)
    .map(([layer]) => layer)

  const {
    data: nodesData = [],
    isLoading: nodesLoading,
    error: nodesError,
  } = useGraphNodes(repoId, visibleLayers)

  const {
    data: edgesData = [],
    isLoading: edgesLoading,
    error: edgesError,
  } = useGraphEdges(repoId)

  const loading = nodesLoading || edgesLoading
  const error = nodesError?.message || edgesError?.message || null

  const nodes = nodesData
  const edges = edgesData

  // Update stats when layer visibility changes
  useEffect(() => {
    const visibleNodes = nodes.filter((node) => {
      const layer = node.layer || 'L1'
      return layerVisibility[layer as keyof typeof layerVisibility]
    })
    const visibleNodeIds = new Set(visibleNodes.map((n) => n.id))
    const visibleEdges = edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target))
    setStats({ nodes: visibleNodes.length, edges: visibleEdges.length })
  }, [nodes, edges, layerVisibility])

  // Initialize Three.js scene
  useEffect(() => {
    if (!mountRef.current || nodes.length === 0 || loading) return

    const width = mountRef.current.clientWidth
    const height = mountRef.current.clientHeight

    // Filter nodes based on layer visibility
    const visibleNodes = nodes.filter((node) => {
      const layer = node.layer || 'L1'
      return layerVisibility[layer as keyof typeof layerVisibility]
    })

    const visibleNodeIds = new Set(visibleNodes.map((n) => n.id))

    // Filter edges based on visible nodes
    const visibleEdges = edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target))

    // Scene setup
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0d1117)
    sceneRef.current = scene

    // Camera
    const camera = new THREE.PerspectiveCamera(
      75,
      width / height,
      0.1,
      10000
    )
    camera.position.z = Math.max(50, nodes.length * 0.3)
    cameraRef.current = camera

    // Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
    })
    renderer.setSize(width, height)
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.shadowMap.enabled = true
    rendererRef.current = renderer
    mountRef.current.appendChild(renderer.domElement)

    // Force-directed layout simulation
    interface PhysicsNode {
      position: THREE.Vector3
      velocity: THREE.Vector3
      mesh?: THREE.Mesh
    }

    const physicsNodes: { [key: string]: PhysicsNode } = {}
    const nodeMeshes: { [key: string]: THREE.Mesh } = {}

    // Initialize nodes with force-directed layout
    visibleNodes.forEach((node) => {
      // Use layer-based colors, fall back to kind-based colors
      const layer = node.layer || 'L1'
      const color = LAYER_COLORS[layer] || NODE_COLORS[node.kind] || DEFAULT_NODE_COLOR
      const material = new THREE.MeshPhongMaterial({
        color,
        emissive: 0x000000,
        shininess: 100,
      })

      const geometry = new THREE.SphereGeometry(2, 32, 32)
      const mesh = new THREE.Mesh(geometry, material)

      // Random initial position
      const angle = Math.random() * Math.PI * 2
      const radius = 30 + Math.random() * 20
      const x = Math.cos(angle) * radius
      const y = (Math.random() - 0.5) * 40
      const z = Math.sin(angle) * radius

      mesh.position.set(x, y, z)
      mesh.castShadow = true
      mesh.receiveShadow = true
      mesh.userData = { node }

      scene.add(mesh)
      nodeMeshes[node.id] = mesh
      physicsNodes[node.id] = {
        position: mesh.position.clone(),
        velocity: new THREE.Vector3(),
        mesh,
      }
    })

    // Create edges with better styling
    const edgeLines = new THREE.Group()
    const edgeMaterials: { [key: string]: THREE.LineBasicMaterial } = {
      imports: new THREE.LineBasicMaterial({ color: 0x58a6ff, opacity: 0.3, transparent: true }),
      calls: new THREE.LineBasicMaterial({ color: 0x3fb950, opacity: 0.3, transparent: true }),
      defines: new THREE.LineBasicMaterial({ color: 0xd291f2, opacity: 0.3, transparent: true }),
      inherits: new THREE.LineBasicMaterial({ color: 0xd29922, opacity: 0.3, transparent: true }),
    }

    const defaultMaterial = new THREE.LineBasicMaterial({
      color: 0x30363d,
      opacity: 0.2,
      transparent: true,
    })

    visibleEdges.forEach((edge) => {
      const source = nodeMeshes[edge.source]
      const target = nodeMeshes[edge.target]

      if (source && target) {
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

        const material =
          edgeMaterials[edge.kind] || defaultMaterial
        const line = new THREE.Line(geometry, material)
        edgeLines.add(line)
      }
    })

    scene.add(edgeLines)

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5)
    scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
    directionalLight.position.set(50, 50, 50)
    directionalLight.castShadow = true
    directionalLight.shadow.mapSize.width = 2048
    directionalLight.shadow.mapSize.height = 2048
    scene.add(directionalLight)

    // Initialize OrbitControls for camera interaction
    const controls = new OrbitControls(camera, renderer.domElement)

    // Mouse interaction - Hover and click
    const raycaster = new THREE.Raycaster()
    const mouse = new THREE.Vector2()
    let isInteractingWithControls = false

    const onMouseMove = (event: MouseEvent) => {
      // Don't do hover detection if user is rotating/panning
      if (isInteractingWithControls) return

      const rect = renderer.domElement.getBoundingClientRect()
      mouse.x = ((event.clientX - rect.left) / width) * 2 - 1
      mouse.y = -((event.clientY - rect.top) / height) * 2 + 1

      raycaster.setFromCamera(mouse, camera)
      const intersects = raycaster.intersectObjects(Object.values(nodeMeshes))

      // Reset colors
      Object.values(nodeMeshes).forEach((mesh) => {
        const layer = mesh.userData.node.layer || 'L1'
        const color = LAYER_COLORS[layer] || NODE_COLORS[mesh.userData.node.kind] || DEFAULT_NODE_COLOR
        ;(mesh.material as THREE.MeshPhongMaterial).color.setHex(color)
        ;(mesh.material as THREE.MeshPhongMaterial).emissive.setHex(0x000000)
      })

      if (intersects.length > 0) {
        const closestObject = intersects[0].object as THREE.Mesh
        if (closestObject.userData?.node) {
          ;(closestObject.material as THREE.MeshPhongMaterial).emissive.setHex(0xffffff)
          ;(closestObject.material as THREE.MeshPhongMaterial).emissive.multiplyScalar(
            0.5
          )
          setSelectedNode(closestObject.userData.node)
          renderer.domElement.style.cursor = 'pointer'
          return
        }
      }

      setSelectedNode(null)
      renderer.domElement.style.cursor = 'default'
    }

    const onMouseDown = (event: MouseEvent) => {
      // Track that user is interacting with camera controls
      if (event.button === 0 || event.button === 2) {
        isInteractingWithControls = true
      }
    }

    const onMouseUp = () => {
      isInteractingWithControls = false
    }

    const onClick = (event: MouseEvent) => {
      // Ignore if user was dragging
      if (isInteractingWithControls) return

      const rect = renderer.domElement.getBoundingClientRect()
      mouse.x = ((event.clientX - rect.left) / width) * 2 - 1
      mouse.y = -((event.clientY - rect.top) / height) * 2 + 1

      raycaster.setFromCamera(mouse, camera)
      const intersects = raycaster.intersectObjects(Object.values(nodeMeshes))

      if (intersects.length > 0) {
        const clickedObject = intersects[0].object as THREE.Mesh
        if (clickedObject.userData?.node) {
          setSelectedNode(clickedObject.userData.node)
        }
      }
    }

    renderer.domElement.addEventListener('mousemove', onMouseMove)
    renderer.domElement.addEventListener('mousedown', onMouseDown)
    renderer.domElement.addEventListener('mouseup', onMouseUp)
    renderer.domElement.addEventListener('click', onClick)
    renderer.domElement.style.cursor = 'grab'

    // Animation loop with physics
    let animationFrameId: number
    let frameCount = 0

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate)
      frameCount++

      // Apply force-directed layout (simplified)
      if (frameCount % 2 === 0) {
        Object.values(physicsNodes).forEach((physicsNode) => {
          if (!physicsNode.mesh) return

          // Repulsive forces from other nodes
          Object.values(physicsNodes).forEach((otherNode) => {
            if (otherNode === physicsNode || !otherNode.mesh) return

            const diff = new THREE.Vector3().subVectors(
              physicsNode.position,
              otherNode.position
            )
            const distance = diff.length()

            if (distance > 0.1) {
              diff.normalize()
              diff.multiplyScalar(0.01)
              physicsNode.velocity.add(diff)
            }
          })

          // Attractive forces from connected edges
          visibleEdges.forEach((edge) => {
            if (
              edge.source === physicsNode.mesh?.userData.node.id &&
              physicsNodes[edge.target]?.mesh
            ) {
              const target = physicsNodes[edge.target].position
              const diff = new THREE.Vector3().subVectors(
                target,
                physicsNode.position
              )
              diff.multiplyScalar(-0.001)
              physicsNode.velocity.add(diff)
            }
          })

          // Damping
          physicsNode.velocity.multiplyScalar(0.95)

          // Update position
          physicsNode.position.add(physicsNode.velocity)
          if (physicsNode.mesh) {
            physicsNode.mesh.position.copy(physicsNode.position)
          }
        })
      }

      renderer.render(scene, camera)
    }

    animate()

    // Handle window resize
    const onWindowResize = () => {
      const newWidth = mountRef.current?.clientWidth || width
      const newHeight = mountRef.current?.clientHeight || height

      camera.aspect = newWidth / newHeight
      camera.updateProjectionMatrix()
      renderer.setSize(newWidth, newHeight)
    }

    window.addEventListener('resize', onWindowResize)

    // Cleanup
    return () => {
      window.removeEventListener('resize', onWindowResize)
      renderer.domElement.removeEventListener('mousemove', onMouseMove)
      renderer.domElement.removeEventListener('mousedown', onMouseDown)
      renderer.domElement.removeEventListener('mouseup', onMouseUp)
      renderer.domElement.removeEventListener('click', onClick)
      renderer.domElement.removeEventListener('wheel', controls.onMouseWheel)
      renderer.domElement.removeEventListener('mousedown', controls.onMouseDown)
      renderer.domElement.removeEventListener('mousemove', controls.onMouseMove)
      renderer.domElement.removeEventListener('mouseup', controls.onMouseUp)
      cancelAnimationFrame(animationFrameId)
      mountRef.current?.removeChild(renderer.domElement)
      renderer.dispose()

      // Dispose all node meshes
      Object.values(nodeMeshes).forEach((mesh) => {
        if (mesh.geometry) mesh.geometry.dispose()
        if (mesh.material instanceof THREE.Material) {
          mesh.material.dispose()
        }
      })

      // Dispose edge lines
      edgeLines.children.forEach((line: THREE.Object3D) => {
        if (line instanceof THREE.Line) {
          if (line.geometry) line.geometry.dispose()
          if (line.material instanceof THREE.Material) {
            line.material.dispose()
          }
        }
      })
    }
  }, [nodes, edges, loading, layerVisibility])

  return (
    <div className="repo-graphify-page">
      <TopBar variant="workspace" />

      <div className="graphify-container">
        {/* Canvas */}
        <div
          ref={mountRef}
          className="graph-canvas"
          style={{
            width: '100%',
            height: '100%',
            backgroundColor: 'var(--bg)',
          }}
        >
          {loading && (
            <div className="graph-loading">
              <div className="loading-spinner" />
              <p>Loading graph visualization...</p>
            </div>
          )}

          {error && (
            <div className="graph-error">
              <p>Error: {error}</p>
              <small>Make sure the backend is running and has indexed data</small>
            </div>
          )}

          {!loading && !error && nodes.length === 0 && (
            <div className="graph-empty">
              <p>No graph data available</p>
              <small>Index a repository to view the code graph</small>
            </div>
          )}
        </div>

        {/* Stats and Controls */}
        <div className="graph-info-panel">
          <div className="info-header">
            <h3>Graph Statistics</h3>
          </div>

          <div className="info-stats">
            <div className="stat-item">
              <span className="stat-label">Nodes:</span>
              <span className="stat-value">{stats.nodes}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Edges:</span>
              <span className="stat-value">{stats.edges}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Repo:</span>
              <span className="stat-value code">{repoId}</span>
            </div>
          </div>

          <div className="info-layers">
            <h4>Layers</h4>
            <div className="layer-toggles">
              <label className="layer-toggle">
                <input
                  type="checkbox"
                  checked={layerVisibility.L1}
                  onChange={(e) =>
                    setLayerVisibility({ ...layerVisibility, L1: e.target.checked })
                  }
                />
                <span>L1 Code Graph</span>
              </label>
              <label className="layer-toggle">
                <input
                  type="checkbox"
                  checked={layerVisibility.L3}
                  onChange={(e) =>
                    setLayerVisibility({ ...layerVisibility, L3: e.target.checked })
                  }
                />
                <span>L3 Spec Graph</span>
              </label>
              <label className="layer-toggle">
                <input
                  type="checkbox"
                  checked={layerVisibility.L4}
                  onChange={(e) =>
                    setLayerVisibility({ ...layerVisibility, L4: e.target.checked })
                  }
                />
                <span>L4 Groups</span>
              </label>
            </div>
          </div>

          <div className="info-legend">
            <h4>Layers</h4>
            <div className="legend-items">
              <div className="legend-item">
                <div className="legend-color" style={{ backgroundColor: '#6b7280' }} />
                <span>L1 Code Graph (Sources)</span>
              </div>
              <div className="legend-item">
                <div className="legend-color" style={{ backgroundColor: '#10b981' }} />
                <span>L3 Spec Graph</span>
              </div>
              <div className="legend-item">
                <div className="legend-color" style={{ backgroundColor: '#3b82f6' }} />
                <span>L4 Groups</span>
              </div>
              <div className="legend-item">
                <div className="legend-color" style={{ backgroundColor: '#6b7280' }} />
                <span>Unknown</span>
              </div>
            </div>
          </div>

          {selectedNode && (
            <div className="info-selected">
              <h4>Selected Node</h4>
              <div className="selected-content">
                <p className="selected-name">{selectedNode.label}</p>
                <div className="selected-meta">
                  <div>
                    <span className="meta-label">Type:</span>
                    <span className="meta-value">{selectedNode.kind}</span>
                  </div>
                  <div>
                    <span className="meta-label">File:</span>
                    <span className="meta-value code">{selectedNode.file_path}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="info-help">
            <p className="help-text">Left-click + drag to rotate • Right-click + drag to pan • Scroll to zoom • Hover to inspect</p>
          </div>
        </div>
      </div>
    </div>
  )
}
