import { useParams } from 'react-router-dom'

export function KnowledgeCard() {
  const { ref } = useParams<{ ref: string }>()

  return (
    <div style={{ padding: '2rem' }}>
      <h1>Knowledge Card: {ref}</h1>
      <p>Coming in Phase 1 — markdown + citations + relations</p>
    </div>
  )
}

export default KnowledgeCard
