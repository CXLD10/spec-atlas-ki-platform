import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Suspense, lazy } from 'react'
import { ThemeProvider } from './theme/ThemeProvider'
import { AppShell } from '../components/shell/AppShell'
import Landing from '../pages/Landing'
import Projects from '../pages/Projects'
import RepoAsk from '../pages/RepoAsk'
import RepoExplore from '../pages/RepoExplore'
import RepoSpec from '../pages/RepoSpec'
import RepoGraphify from '../pages/RepoGraphify'
import SpecifyTool from '../pages/SpecifyTool'
import SpecView from '../pages/SpecView'
import IndexProgress from '../pages/IndexProgress'
import Dashboard from '../pages/Dashboard'
import Sources from '../pages/Sources'
import SourceDetail from '../pages/SourceDetail'
import '../styles/global.css'

// Code-split heavy routes
const Ask = lazy(() => import('../pages/Ask'))
const Specify = lazy(() => import('../pages/Specify'))
const Docs = lazy(() => import('../pages/Docs'))
const Graph = lazy(() => import('../pages/Graph'))
const KnowledgeBase = lazy(() => import('../pages/KnowledgeBase'))
const KnowledgeCard = lazy(() => import('../pages/KnowledgeCard'))
const MCPServer = lazy(() => import('../pages/MCPServer'))

const PageLoader = () => (
  <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--mid)' }}>
    Loading…
  </div>
)

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 10,   // 10 minutes
    },
  },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              {/* New IA routes */}
              <Route path="/" element={<Dashboard />} />
              <Route path="/sources" element={<Sources />} />
              <Route path="/sources/:id" element={<SourceDetail />} />
              <Route path="/kb" element={<Suspense fallback={<PageLoader />}><KnowledgeBase /></Suspense>} />
              <Route path="/kb/:ref" element={<Suspense fallback={<PageLoader />}><KnowledgeCard /></Suspense>} />
              <Route path="/graph" element={<Suspense fallback={<PageLoader />}><Graph /></Suspense>} />
              <Route path="/ask" element={<Suspense fallback={<PageLoader />}><Ask /></Suspense>} />
              <Route path="/specify" element={<Suspense fallback={<PageLoader />}><Specify /></Suspense>} />
              <Route path="/mcp" element={<Suspense fallback={<PageLoader />}><MCPServer /></Suspense>} />
              <Route path="/docs" element={<Suspense fallback={<PageLoader />}><Docs /></Suspense>} />
              <Route path="/index/:jobId" element={<IndexProgress />} />

              {/* Backward compatibility / old repo-scoped routes */}
              <Route path="/landing" element={<Landing />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/repo/:repoId/ask" element={<RepoAsk />} />
              <Route path="/repo/:repoId/graphify" element={<RepoGraphify />} />
              <Route path="/repo/:repoId/specify" element={<SpecifyTool />} />
              <Route path="/repo/:repoId/specify/:specId" element={<SpecView />} />
              <Route path="/repo/:repoId/explore" element={<RepoExplore />} />
              <Route path="/repo/:repoId/explore/specs/:specRef" element={<RepoSpec />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App
