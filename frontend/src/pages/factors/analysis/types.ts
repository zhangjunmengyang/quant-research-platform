/**
 * Factor Analysis Page - Type Definitions
 * 因子分析页 - 类型定义
 */

import type { FactorGroupAnalysisResponse, DataType, BinMethod } from '@/features/factor'

export type TabType = 'calculator' | 'single' | 'multi' | 'grouping'

// ============================================================================
// 因子计算 Tab 类型
// ============================================================================

export interface FactorConfig {
  id: string
  factor: string
  params: number[]
}

export interface CalculationResult {
  symbol: string
  data_type: string
  factors: Array<{
    name: string
    param: number
    data: Array<{ time: string; value: number | null }>
    stats: {
      count?: number
      mean?: number | null
      std?: number | null
      min?: number | null
      max?: number | null
      latest?: number | null
    }
  }>
}

// ============================================================================
// 单因子分析 Tab 类型
// ============================================================================

export interface SingleAnalysisResult {
  ic: Array<{ time: string; ic: number; rankIC?: number }>
  groupReturns: {
    groups: string[]
    returns: number[]
  }
  distribution: {
    bins: string[]
    counts: number[]
  }
  stats: {
    ic_mean: number
    ic_std: number
    ic_ir: number
    rank_ic_mean: number
    positive_ratio: number
  }
}

// ============================================================================
// 因子分箱 Tab 类型
// ============================================================================

export interface FactorGroupConfig {
  id: string
  factor: string
  params: number[]
}

export type { FactorGroupAnalysisResponse, DataType, BinMethod }
