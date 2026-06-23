import { GitBranch, FileText, FileSpreadsheet, BookOpen } from 'lucide-react'
import { Source } from '../../lib/types'

export function TypeBadge({ source }: { source: Source }) {
  const isRepo = source.type === 'repo'
  const icon = isRepo ? (
    <GitBranch size={14} />
  ) : source.format === 'pdf' ? (
    <FileText size={14} />
  ) : source.format === 'xlsx' ? (
    <FileSpreadsheet size={14} />
  ) : (
    <BookOpen size={14} />
  )

  const label = isRepo ? 'Repository' : (source.format ?? 'document').toUpperCase()
  const className = `type-badge ${isRepo ? 'repo' : 'document'}`

  return (
    <div className={className}>
      {icon}
      {label}
    </div>
  )
}
