import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { TopBar } from '../components/layout/TopBar'
import './Docs.css'

interface DocSection {
  id: string
  title: string
  icon?: string
  subsections?: DocSection[]
}

const docSections: DocSection[] = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    subsections: [
      { id: 'intro', title: 'What is Spec-Atlas?' },
      { id: 'install', title: 'Installation' },
      { id: 'first-index', title: 'Your First Index' },
    ],
  },
  {
    id: 'graph-explorer',
    title: 'Graph Explorer',
    subsections: [
      { id: 'graph-overview', title: 'Overview' },
      { id: 'layers', title: 'Understanding Layers' },
      { id: 'graph-navigation', title: 'Navigation & Controls' },
      { id: 'graph-examples', title: 'Examples' },
    ],
  },
  {
    id: 'specify-tool',
    title: 'Specify Tool',
    subsections: [
      { id: 'what-is-spec', title: 'What is a Spec?' },
      { id: 'why-specs', title: 'Why Specs Matter' },
      { id: 'creating-specs', title: 'Creating Specs' },
      { id: 'spec-format', title: 'Spec Format Reference' },
    ],
  },
  {
    id: 'architecture',
    title: 'Architecture',
    subsections: [
      { id: 'four-layers', title: 'Four-Layer Model' },
      { id: 'data-flow', title: 'Data Flow' },
      { id: 'components', title: 'Core Components' },
    ],
  },
  {
    id: 'faq',
    title: 'FAQ',
    subsections: [
      { id: 'common-questions', title: 'Common Questions' },
      { id: 'troubleshooting', title: 'Troubleshooting' },
      { id: 'performance', title: 'Performance Tips' },
    ],
  },
]

const docContent: { [key: string]: { title: string; content: string } } = {
  intro: {
    title: 'What is Spec-Atlas?',
    content: `Spec-Atlas is a tool that transforms your codebase into a living knowledge graph. It automatically extracts code structure, generates specifications, and creates an interactive visualization of your architecture.

Instead of maintaining outdated documentation, Spec-Atlas keeps your specs in sync with your code. Ask questions about your codebase and get grounded answers with exact source citations.`,
  },
  install: {
    title: 'Installation',
    content: `Spec-Atlas is available as a web application. No installation required!

1. Open the Spec-Atlas interface in your browser
2. Enter your repository URL (GitHub, GitLab, Gitea, or Codeberg)
3. Click "Index Repository"
4. Wait 2–5 minutes for indexing to complete
5. Explore your code structure using the three main tools

Supported repositories:
• GitHub (public and private with token)
• GitLab
• Gitea
• Codeberg

No special setup or credentials required for public repositories.`,
  },
  'first-index': {
    title: 'Your First Index',
    content: `Getting started is simple:

1. Go to the Spec-Atlas home page
2. Paste your repository URL (e.g., \`https://github.com/username/repo\`)
3. Click "Index Repository"
4. Watch the progress page as Spec-Atlas:
   - Clones your repository
   - Parses all source files
   - Extracts symbols and relationships
   - Generates specifications
   - Builds the graph

Once complete, you'll have access to:
• Graph Explorer: Visualize your code structure
• Specify Tool: Browse and edit specifications
• Q&A: Ask questions about your code

Start with a small repository (< 10k LOC) to see the full pipeline in ~2 minutes.`,
  },
  'graph-overview': {
    title: 'Graph Explorer Overview',
    content: `The Graph Explorer visualizes your code as an interactive 3D graph. Each node represents a code symbol (function, class, module), and edges represent relationships (imports, calls, defines).

Features:
• Interactive 3D visualization
• Color-coded nodes by type
• Real-time node selection
• Relationship visualization
• Statistics panel

The visualization shows how your code components connect and depend on each other. Use it to:
• Understand architecture
• Identify circular dependencies
• Find cross-file relationships
• Plan refactoring`,
  },
  layers: {
    title: 'Understanding Layers',
    content: `Spec-Atlas organizes knowledge into four layers:

**L1 – Code Graph**
The raw code structure extracted from your repository. Every function, class, module, and their relationships.
Color: Cyan (#58a6ff)

**L2 – Specs**
Human-written specifications for code components. Purpose, inputs, outputs, dependencies, failure modes.
Color: Green (#3fb950)

**L3 – Spec Graph**
Relationships between specs. How specifications cross-reference each other.
Color: Purple (#d291f2)

**L4 – Groups**
Higher-level clusters of related components. Teams, modules, features.
Color: Orange

Each layer builds on the previous one, creating a complete knowledge map of your codebase.`,
  },
  'graph-navigation': {
    title: 'Navigation & Controls',
    content: `Using the Graph Explorer:

**Mouse Interaction:**
• Hover over nodes to inspect them
• Click nodes to see details
• Scroll to zoom in/out
• Drag to rotate the view

**Left Panel (Controls):**
• Filter by layer (L1, L3, L4)
• Search nodes by name
• View layer statistics

**Right Panel (Info):**
• Graph statistics
• Node type legend
• Selected node details
• Relationship information

Tips:
• Start with fewer nodes (100–200) for clarity
• Use filters to focus on specific layers
• Zoom in on clusters to see relationships clearly
• Select nodes to view metadata`,
  },
  'graph-examples': {
    title: 'Examples',
    content: `Example: Exploring an API Layer

1. Index your web application repository
2. In Graph Explorer, filter to show only "module" and "class" nodes
3. Hover over the "api" module node
4. See all classes that import from api
5. Select a class to view its file path and connections
6. Use this to understand API surface and dependencies

Example: Finding Circular Dependencies

1. In the graph, look for nodes with bidirectional edges
2. Hover over clusters of tightly connected nodes
3. These often indicate circular dependencies
4. Plan refactoring to break cycles

Example: Understanding a New Module

1. Search for the module name in Graph Explorer
2. See all components that depend on it (inbound edges)
3. See all components it depends on (outbound edges)
4. This shows you the module's role in the architecture`,
  },
  'what-is-spec': {
    title: 'What is a Spec?',
    content: `A specification (spec) is a structured description of what a code component does. Instead of relying on comments or documentation, specs are explicit, queryable, and version-controlled.

A spec includes:
• **Purpose**: What does this component do?
• **Inputs**: What does it accept?
• **Outputs**: What does it return?
• **Dependencies**: What does it rely on?
• **Invariants**: What must always be true?
• **Side Effects**: What does it change?
• **Failure Modes**: How can it fail?

Example spec for a function:

\`\`\`json
{
  "component_ref": "auth/tokens/RefreshToken",
  "purpose": "Refresh an expired access token",
  "inputs": [
    {"name": "token", "type": "string", "description": "Expired token"}
  ],
  "outputs": [
    {"name": "new_token", "type": "string", "description": "Fresh token"}
  ],
  "dependencies": ["Token", "HashUtil"],
  "invariants": ["Token is always valid for 1 hour"],
  "failure_modes": ["Token is invalid", "Rate limit exceeded"]
}
\`\`\``,
  },
  'why-specs': {
    title: 'Why Specs Matter',
    content: `Specs provide multiple benefits:

**For Developers:**
• Know exactly what a function does without reading code
• Understand expected inputs and outputs
• Find failure modes before you hit them
• Save time on code review

**For Teams:**
• Living documentation that never goes out of date
• Clear interface contracts between components
• Easier onboarding for new team members
• Better architectural discussions

**For AI Agents:**
• More accurate code generation
• Better understanding of constraints
• Fewer hallucinations and errors
• Faster task completion

Specs are the bridge between code structure and human understanding.`,
  },
  'creating-specs': {
    title: 'Creating Specs',
    content: `Using the Specify Tool:

1. Navigate to the "Specify Tool" from the home page
2. Browse the hierarchical tree of your code components
3. Select a component to view its details
4. Click "View Full Spec" to edit or create a spec
5. Fill in each field:
   - Purpose (one sentence)
   - Inputs (array of parameters)
   - Outputs (array of return values)
   - Dependencies (other components used)
   - Invariants (constraints that must hold)
   - Side Effects (state changes)
   - Failure Modes (error cases)
6. Click "Save" to store the spec in the database

**Spec Status:**
• Draft: Work in progress
• Review: Ready for team review
• Approved: Accepted and in use

Start with high-level components (modules, classes) before detailing every function.`,
  },
  'spec-format': {
    title: 'Spec Format Reference',
    content: `Spec JSON Schema:

\`\`\`json
{
  "component_ref": "string (required)",
  "purpose": "string (required)",
  "inputs": [
    {
      "name": "string",
      "type": "string",
      "description": "string",
      "optional": "boolean"
    }
  ],
  "outputs": [
    {
      "name": "string",
      "type": "string",
      "description": "string"
    }
  ],
  "dependencies": ["string"],
  "invariants": ["string"],
  "side_effects": ["string"],
  "failure_modes": ["string"],
  "status": "draft | review | approved",
  "version": "integer",
  "created_at": "ISO8601 timestamp"
}
\`\`\`

**Best Practices:**
• Keep purposes concise (1–2 sentences)
• List all inputs and outputs, even if obvious
• Include at least 2–3 failure modes
• Use consistent terminology across specs
• Review specs before marking approved
• Update specs when code behavior changes`,
  },
  'four-layers': {
    title: 'Four-Layer Model',
    content: `Spec-Atlas organizes knowledge in layers, each building on the previous:

**Layer 1: Code (L1)**
Raw source code extracted via tree-sitter. Symbols, relationships, imports, definitions. Fully automated.

**Layer 2: Specs (L2)**
Human-written specifications describing what code does. Purpose, inputs, outputs, dependencies. Manually created.

**Layer 3: Spec Graph (L3)**
Relationships between specs. How specifications reference each other. Built from L1 + L2.

**Layer 4: Groups (L4)**
High-level clusters. Teams, modules, features. Automatically formed from code structure.

Each layer serves a different purpose:
• L1: "What is the code structure?"
• L2: "What does this component do?"
• L3: "How do specifications relate?"
• L4: "What are the major components?"

Use these layers together to understand your codebase at every level of abstraction.`,
  },
  'data-flow': {
    title: 'Data Flow',
    content: `How Spec-Atlas processes your code:

1. **Ingest**: Repository cloned, files extracted
2. **Parse**: tree-sitter extracts symbols, signatures
3. **Analyze**: Relationships identified (imports, calls, inherits)
4. **Store (L1)**: Code graph saved to analysis database
5. **Generate (L2)**: LLM generates initial specs from code
6. **Store (L2)**: Specs stored in spec database
7. **Link (L3)**: Relationships between specs identified
8. **Cluster (L4)**: Groups formed from directory structure
9. **Embed**: All specs embedded for semantic search
10. **Query**: API serves all layers for UI and agents

The entire pipeline is idempotent: re-indexing the same repo produces the same results.`,
  },
  components: {
    title: 'Core Components',
    content: `**Frontend (React + TypeScript)**
• Landing Page: Hero and repository indexing
• Graph Explorer: Interactive 3D visualization
• Specify Tool: Hierarchical spec browser
• Documentation: This guide

**Backend (Python + FastAPI)**
• Parser: tree-sitter multi-language support
• Analyzer: Edge detection and relationship analysis
• LLM Integration: Spec generation and summarization
• Vector Store: pgvector for semantic search
• API: RESTful endpoints for all operations

**Data Layer**
• Analysis DB: Code structure (PostgreSQL)
• Spec DB: Specifications and metadata (PostgreSQL)
• Vector Store: Embeddings for search (pgvector)

All components are open-source and self-contained.`,
  },
  'common-questions': {
    title: 'Common Questions',
    content: `**Q: How long does indexing take?**
A: Typically 2–5 minutes depending on repository size. Larger repos (100k+ LOC) may take longer.

**Q: Does Spec-Atlas support my language?**
A: We support Python, TypeScript, JavaScript, Go, Rust, and more via tree-sitter. Check the docs for the full list.

**Q: Are my specs private?**
A: Yes. All data stays in your instance. No external calls or uploads.

**Q: Can I edit specs after creating them?**
A: Yes. Specs are versioned. Every edit creates a new version while preserving history.

**Q: What if my repo is huge?**
A: Try indexing a subdirectory or single module first. The graph can handle 10k+ nodes smoothly.

**Q: Can I integrate this with my CI/CD?**
A: Yes. Spec-Atlas has an MCP server for Claude Code and other agents.`,
  },
  troubleshooting: {
    title: 'Troubleshooting',
    content: `**Indexing fails**
• Check repository URL format (\`https://github.com/user/repo\`)
• Ensure repository is public or token is valid
• Check internet connection
• Try a smaller repository first

**Graph doesn't display**
• Ensure indexing completed successfully
• Check browser console for errors
• Try refreshing the page
• Ensure WebGL is enabled in browser

**Specs not generating**
• LLM provider may be overloaded
• Check that backend is running
• Re-index the repository
• Check logs for API errors

**Slow visualization**
• Reduce node count (use filters)
• Close other browser tabs
• Use Chrome for best performance
• Update graphics drivers`,
  },
  'performance': {
    title: 'Performance Tips',
    content: `**For Indexing:**
• Start with small repos (< 10k LOC)
• Public repositories are faster than private
• Run during off-peak hours for large repos
• Use a wired connection for faster cloning

**For Graph Exploration:**
• Filter by layer to reduce visible nodes
• Search instead of browsing large graphs
• Use the info panel instead of hovering for details
• Zoom out before rotating the view

**For Query Performance:**
• Use specific search terms
• Limit time range when searching
• Index only active branches
• Archive old data periodically

**Hardware Recommendations:**
• 8GB+ RAM for indexing large repos
• GPU acceleration recommended for 3D visualization
• Broadband internet connection
• SSD for faster file operations`,
  },
}

export function Docs() {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['getting-started', 'graph-explorer', 'specify-tool'])
  )
  const [selectedDoc, setSelectedDoc] = useState<string>('intro')
  const [searchQuery, setSearchQuery] = useState('')

  const toggleSection = (id: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedSections(newExpanded)
  }

  const currentDoc = docContent[selectedDoc]

  const renderNavItem = (section: DocSection, level = 0): JSX.Element => {
    const isExpanded = expandedSections.has(section.id)
    const hasSubsections = section.subsections && section.subsections.length > 0
    const isSelected = selectedDoc === section.id

    return (
      <div key={section.id}>
        <button
          className={`nav-item ${isSelected ? 'selected' : ''}`}
          style={{ paddingLeft: `${level * 16}px` }}
          onClick={() => {
            setSelectedDoc(section.id)
            if (hasSubsections) toggleSection(section.id)
          }}
        >
          {hasSubsections ? (
            <span className="nav-toggle">
              {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </span>
          ) : (
            <span className="nav-toggle-placeholder" />
          )}
          <span className="nav-label">{section.title}</span>
        </button>

        {hasSubsections && isExpanded && section.subsections && (
          <div className="nav-subsections">
            {section.subsections.map((subsection) =>
              renderNavItem(subsection, level + 1)
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="docs-page">
      <TopBar variant="workspace" />

      <div className="docs-container">
        {/* Sidebar */}
        <aside className="docs-sidebar">
          <div className="sidebar-header">
            <h2>Documentation</h2>
            <input
              type="text"
              placeholder="Search docs..."
              className="sidebar-search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <nav className="docs-nav">
            {docSections.map((section) => renderNavItem(section))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="docs-content">
          {currentDoc ? (
            <article className="doc-article">
              <h1>{currentDoc.title}</h1>
              <div className="doc-body">
                {currentDoc.content.split('\n\n').map((paragraph, idx) => {
                  // Handle code blocks
                  if (paragraph.includes('```')) {
                    const parts = paragraph.split('```')
                    return (
                      <div key={idx}>
                        {parts[0] && <p>{parts[0]}</p>}
                        {parts[1] && (
                          <pre className="code-block">
                            <code>{parts[1].trim()}</code>
                          </pre>
                        )}
                        {parts[2] && <p>{parts[2]}</p>}
                      </div>
                    )
                  }

                  // Handle lists
                  if (paragraph.includes('•')) {
                    const items = paragraph.split('\n').filter((line) => line.includes('•'))
                    return (
                      <ul key={idx} className="doc-list">
                        {items.map((item, i) => (
                          <li key={i}>{item.replace('•', '').trim()}</li>
                        ))}
                      </ul>
                    )
                  }

                  // Handle numbered lists
                  if (paragraph.match(/^\d\./m)) {
                    const items = paragraph.split('\n').filter((line) => line.match(/^\d\./))
                    return (
                      <ol key={idx} className="doc-list">
                        {items.map((item, i) => (
                          <li key={i}>{item.replace(/^\d\.\s*/, '').trim()}</li>
                        ))}
                      </ol>
                    )
                  }

                  // Regular paragraph
                  return (
                    <p key={idx} className="doc-paragraph">
                      {paragraph}
                    </p>
                  )
                })}
              </div>
            </article>
          ) : (
            <div className="doc-empty">
              <p>Select a topic from the sidebar to get started</p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default Docs
