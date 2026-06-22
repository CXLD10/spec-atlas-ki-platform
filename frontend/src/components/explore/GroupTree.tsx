import { useState } from 'react'
import { GroupNode } from '../../api/client'
import './GroupTree.css'

interface GroupTreeProps {
  groups: GroupNode[]
  activeId?: string
  onSelect: (id: string) => void
}

export function GroupTree({ groups, activeId, onSelect }: GroupTreeProps) {
  return (
    <nav className="group-tree" role="navigation" aria-label="Group tree">
      <ol className="tree-list">
        {groups.map((group) => (
          <TreeNode
            key={group.id}
            node={group}
            activeId={activeId}
            onSelect={onSelect}
            level={0}
          />
        ))}
      </ol>
    </nav>
  )
}

interface TreeNodeProps {
  node: GroupNode
  activeId?: string
  onSelect: (id: string) => void
  level: number
}

function TreeNode({ node, activeId, onSelect, level }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = node.children && node.children.length > 0
  const isActive = node.id === activeId

  const handleClick = () => {
    onSelect(node.id)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    switch (e.key) {
      case 'Enter':
      case ' ':
        e.preventDefault()
        onSelect(node.id)
        break
      case 'ArrowRight':
        e.preventDefault()
        if (hasChildren) setExpanded(true)
        break
      case 'ArrowLeft':
        e.preventDefault()
        if (hasChildren) setExpanded(false)
        break
    }
  }

  return (
    <li className="tree-node">
      <div
        className={`tree-item ${isActive ? 'active' : ''}`}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={isActive ? 0 : -1}
        aria-selected={isActive}
      >
        {hasChildren && (
          <button
            className="expand-toggle"
            onClick={(e) => {
              e.stopPropagation()
              setExpanded(!expanded)
            }}
            aria-expanded={expanded}
            aria-label={`${expanded ? 'Collapse' : 'Expand'} ${node.id}`}
          >
            {expanded ? '▾' : '▸'}
          </button>
        )}
        {!hasChildren && <span className="expand-spacer" />}
        <span className="tree-label mono">{node.id}</span>
      </div>

      {expanded && hasChildren && (
        <ol className="tree-list">
          {node.children!.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              activeId={activeId}
              onSelect={onSelect}
              level={level + 1}
            />
          ))}
        </ol>
      )}
    </li>
  )
}
