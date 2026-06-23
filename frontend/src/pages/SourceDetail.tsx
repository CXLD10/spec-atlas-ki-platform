import { useParams } from 'react-router-dom'

export function SourceDetail() {
  const { id } = useParams<{ id: string }>()

  return (
    <div style={{ padding: '2rem' }}>
      <h1>Source: {id}</h1>
      <p>Coming in Phase 1 — ingestion status, generated cards, provenance</p>
    </div>
  )
}

export default SourceDetail
