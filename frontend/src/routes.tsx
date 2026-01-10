import { createBrowserRouter, Navigate } from 'react-router-dom'
import { App } from './App'
import { AlertCircle, RefreshCw } from 'lucide-react'

// Lazy load pages for code splitting
const FactorsDashboard = () => import('@/pages/factors/Dashboard')
const FactorsAnalysis = () => import('@/pages/factors/analysis')
const FactorsPipeline = () => import('@/pages/factors/Pipeline')

const StrategiesBrowser = () => import('@/pages/strategies/Browser')
const StrategiesDetail = () => import('@/pages/strategies/Detail')
const StrategiesBacktest = () => import('@/pages/strategies/Backtest')
const StrategiesAnalysis = () => import('@/pages/strategies/Analysis')

const DataOverview = () => import('@/pages/data/Overview')

const MCPDashboard = () => import('@/pages/mcp/Dashboard')
const MCPDetail = () => import('@/pages/mcp/Detail')

const NotesList = () => import('@/pages/notes/List')
const NotesDetail = () => import('@/pages/notes/Detail')

const ResearchList = () => import('@/pages/research/List')
const ResearchDetail = () => import('@/pages/research/Detail')
const ResearchSearch = () => import('@/pages/research/Search')

const ExperiencesDashboard = () => import('@/pages/experiences/Dashboard')

const LogsExplorer = () => import('@/pages/logs/Explorer')

// Error element for routes
function ErrorBoundaryElement() {
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-4 text-destructive">
      <AlertCircle className="h-12 w-12" />
      <div className="text-center">
        <p className="font-medium">出现错误</p>
        <p className="text-sm text-muted-foreground">页面加载失败</p>
      </div>
      <button
        onClick={() => window.location.reload()}
        className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
      >
        <RefreshCw className="h-4 w-4" />
        重新加载
      </button>
    </div>
  )
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    errorElement: ErrorBoundaryElement(),
    children: [
      // Default redirect to data overview
      {
        index: true,
        element: <Navigate to="/data" replace />,
      },
      // Data Hub
      {
        path: 'data',
        children: [{ index: true, lazy: DataOverview }],
      },
      // Factor Hub
      {
        path: 'factors',
        children: [
          { index: true, lazy: FactorsDashboard },
          { path: 'analysis', lazy: FactorsAnalysis },
          { path: 'pipeline', lazy: FactorsPipeline },
        ],
      },
      // Strategy Hub
      {
        path: 'strategies',
        children: [
          { index: true, lazy: StrategiesBrowser },
          { path: ':id', lazy: StrategiesDetail },
          { path: 'backtest', lazy: StrategiesBacktest },
          { path: 'analysis', lazy: StrategiesAnalysis },
        ],
      },
      // MCP Management
      {
        path: 'mcp',
        children: [
          { index: true, lazy: MCPDashboard },
          { path: ':name', lazy: MCPDetail },
        ],
      },
      // Research Hub
      {
        path: 'research',
        children: [
          { index: true, lazy: ResearchList },
          { path: 'search', lazy: ResearchSearch },
          { path: ':id', lazy: ResearchDetail },
        ],
      },
      // Notes Hub
      {
        path: 'notes',
        children: [
          { index: true, lazy: NotesList },
          { path: ':id', lazy: NotesDetail },
        ],
      },
      // Experience Hub
      {
        path: 'experiences',
        children: [{ index: true, lazy: ExperiencesDashboard }],
      },
      // Logs Hub
      {
        path: 'logs',
        children: [{ index: true, lazy: LogsExplorer }],
      },
    ],
  },
])
