/**
 * Strategy Module Exports
 */

// Types
export * from './types'

// API
export { strategyApi, backtestApi, taskApi, analysisApi } from './api'

// Hooks
export {
  // Strategy hooks
  strategyKeys,
  backtestKeys,
  useStrategies,
  useStrategy,
  useStrategyStats,
  useStrategyMutations,
  useBacktestConfig,
  useBacktestTemplates,
  useBacktest,
  useBacktestResult,
  useBatchBacktest,
  // Task management hooks
  taskKeys,
  useTasks,
  useTask,
  useTaskStats,
  useTaskExecutions,
  useExecution,
  useTaskMutations,
  useTaskExecution,
  useExecutionMutations,
  // Strategy analysis hooks
  useParamSearch,
  useParamAnalysis,
  useBacktestComparison,
  useFactorComparison,
  useCoinSimilarity,
  useEquityCorrelation,
} from './hooks'

// Store
export { useStrategyStore, DEFAULT_STRATEGY_FILTERS } from './store'
