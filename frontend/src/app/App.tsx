import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
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
import Docs from '../pages/Docs'
import Dashboard from '../pages/Dashboard'
import IndexProgress from '../pages/IndexProgress'
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
              <Route path="/" element={<Landing />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/graph" element={<RepoGraphify />} />
              <Route path="/ask" element={<RepoAsk />} />
              <Route path="/specify" element={<SpecifyTool />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/docs" element={<Docs />} />
              <Route path="/index/:jobId" element={<IndexProgress />} />
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
