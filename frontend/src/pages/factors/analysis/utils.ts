/**
 * Factor Analysis Page - Utility Functions
 * 因子分析页 - 辅助函数
 */

export function generateMockICData(): Array<{ time: string; ic: number; rankIC: number }> {
  const data: Array<{ time: string; ic: number; rankIC: number }> = []
  const startDate = new Date('2023-01-01')

  for (let i = 0; i < 52; i++) {
    const date = new Date(startDate)
    date.setDate(date.getDate() + i * 7)
    data.push({
      time: date.toISOString().slice(0, 10),
      ic: (Math.random() - 0.4) * 0.3,
      rankIC: (Math.random() - 0.4) * 0.25,
    })
  }

  return data
}

export interface CorrelationPair {
  factor1: string
  factor2: string
  value: number
}

export function getCorrelationPairs(factors: string[], matrix: number[][]): CorrelationPair[] {
  const pairs: CorrelationPair[] = []
  for (let i = 0; i < factors.length; i++) {
    for (let j = i + 1; j < factors.length; j++) {
      pairs.push({
        factor1: factors[i] ?? '',
        factor2: factors[j] ?? '',
        value: matrix[i]?.[j] ?? 0,
      })
    }
  }
  return pairs
}

export function getCorrelationStrength(value: number): string {
  const abs = Math.abs(value)
  if (abs >= 0.8) return '非常强'
  if (abs >= 0.6) return '强'
  if (abs >= 0.4) return '中等'
  if (abs >= 0.2) return '弱'
  return '非常弱'
}

export function getCorrelationStrengthClass(value: number): string {
  const abs = Math.abs(value)
  if (abs >= 0.8) return 'bg-red-100 text-red-800'
  if (abs >= 0.6) return 'bg-orange-100 text-orange-800'
  if (abs >= 0.4) return 'bg-yellow-100 text-yellow-800'
  if (abs >= 0.2) return 'bg-green-100 text-green-800'
  return 'bg-gray-100 text-gray-600'
}
