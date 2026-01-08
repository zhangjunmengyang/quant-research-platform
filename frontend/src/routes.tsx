import { createBrowserRouter, Navigate } from 'react-router-dom'
import { App } from './App'

// Lazy load pages for code splitting
const FactorsDashboard = () => import('@/pages/factors/Dashboard')
const FactorsAnalysis = () => import('@/pages/factors/Analysis')
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

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
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
