import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from './theme/ThemeProvider'
import { AppShell } from '../components/shell/AppShell'
import Landing from '../pages/Landing'
import Projects from '../pages/Projects'
import Ask from '../pages/Ask'
import RepoAsk from '../pages/RepoAsk'
import RepoExplore from '../pages/RepoExplore'
import RepoSpec from '../pages/RepoSpec'
import RepoGraphify from '../pages/RepoGraphify'
import SpecifyTool from '../pages/SpecifyTool'
import SpecView from '../pages/SpecView'
import Docs from '../pages/Docs'
import Dashboard from '../pages/Dashboard'
import Graph from '../pages/Graph'
import IndexProgress from '../pages/IndexProgress'
import Sources from '../pages/Sources'
import SourceDetail from '../pages/SourceDetail'
import KnowledgeBase from '../pages/KnowledgeBase'
import KnowledgeCard from '../pages/KnowledgeCard'
import MCPServer from '../pages/MCPServer'
import '../styles/global.css'

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
              <Route path="/kb" element={<KnowledgeBase />} />
              <Route path="/kb/:ref" element={<KnowledgeCard />} />
              <Route path="/graph" element={<Graph />} />
              <Route path="/ask" element={<Ask />} />
              <Route path="/specify" element={<SpecifyTool />} />
              <Route path="/mcp" element={<MCPServer />} />
              <Route path="/docs" element={<Docs />} />
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
