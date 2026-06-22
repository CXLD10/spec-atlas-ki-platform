/* Layer configuration for L1-L4 build animation */
/* Extracted from prototype and design tokens */

export interface Layer {
  id: 'l1' | 'l2' | 'l3' | 'l4'
  label: string
  sublabel: string
  color: string
  depth: number
  nodeCount: number
  phaseIndex: number
}

export const LAYERS: Layer[] = [
  {
    id: 'l1',
    label: 'Code Graph',
    sublabel: 'tree-sitter → symbols+edges',
    color: 'var(--l1)',
    depth: 0,
    nodeCount: 200,
    phaseIndex: 0,
  },
  {
    id: 'l2',
    label: 'Specify',
    sublabel: 'LLM → grounded specs',
    color: 'var(--l2)',
    depth: 1,
    nodeCount: 120,
    phaseIndex: 1,
  },
  {
    id: 'l3',
    label: 'Spec Graph',
    sublabel: 'linked from real edges',
    color: 'var(--l3)',
    depth: 2,
    nodeCount: 80,
    phaseIndex: 2,
  },
  {
    id: 'l4',
    label: 'Group Tree',
    sublabel: 'summaries + embeddings',
    color: 'var(--l4)',
    depth: 3,
    nodeCount: 50,
    phaseIndex: 3,
  },
]

/* Canvas rendering parameters */
export const CANVAS_CONFIG = {
  width: 1200,
  height: 800,
  fps: 60,
  particleSize: 3,
  depth3dOffset: 200,
  cameraSpeed: 0.05,
}

/* Phase timing (exact from DESIGN-TOKENS) */
export const PHASE_DURATION = 1700 // milliseconds per phase
export const INTRO_DURATION = 1700 // milliseconds total for intro
export const PARTICLE_DURATION = 1300 // milliseconds for particle convergence
export const INTRO_TO_HERO_FADE = 400 // milliseconds for fade transition
export const QA_START_DELAY = 600 // milliseconds after build completes
