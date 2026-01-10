/**
 * Factor Analysis Page - Multi Factor Tab
 * 因子分析页 - 多因子分析 Tab 组件
 */

import { useState, useMemo } from 'react'
import { Loader2, Play, X, GitCompare } from 'lucide-react'
import { useFactors } from '@/features/factor'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'
import { stripPyExtension } from '@/lib/utils'
import { CorrelationMatrix } from '@/components/charts'
import {
  getCorrelationPairs,
  getCorrelationStrength,
  getCorrelationStrengthClass,
} from './utils'

export function MultiFactorTab() {
  const { data: factorsData } = useFactors({ page_size: 1000 })
  const factors = factorsData?.items || []

  const [selectedFactors, setSelectedFactors] = useState<string[]>([])
  const [correlationData, setCorrelationData] = useState<number[][] | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [factorToAdd, setFactorToAdd] = useState('')

  // 可选因子（排除已选）
  const availableFactorOptions: SelectOption[] = useMemo(
    () =>
      [...factors]
        .filter((f) => !selectedFactors.includes(f.filename))
        .sort((a, b) => stripPyExtension(a.filename).localeCompare(stripPyExtension(b.filename)))
        .map((f) => ({
          value: f.filename,
          label: stripPyExtension(f.filename),
        })),
    [factors, selectedFactors]
  )

  const handleAddFactor = (factor: string) => {
    if (!selectedFactors.includes(factor) && selectedFactors.length < 10) {
      setSelectedFactors([...selectedFactors, factor])
    }
  }

  const handleRemoveFactor = (factor: string) => {
    setSelectedFactors(selectedFactors.filter((f) => f !== factor))
  }

  const handleAnalyze = () => {
    if (selectedFactors.length < 2) return

    setIsLoading(true)
    // Simulate correlation matrix calculation
    setTimeout(() => {
      const n = selectedFactors.length
      const matrix: number[][] = []
      for (let i = 0; i < n; i++) {
        matrix[i] = []
        for (let j = 0; j < n; j++) {
          if (i === j) {
            matrix[i][j] = 1
          } else if (j < i) {
            matrix[i][j] = matrix[j][i]
          } else {
            matrix[i][j] = Math.random() * 1.6 - 0.8
          }
        }
      }
      setCorrelationData(matrix)
      setIsLoading(false)
    }, 1000)
  }

  return (
    <div className="space-y-6">
      {/* Factor Selection */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="mb-4 font-semibold">选择因子 (最多10个)</h3>

        {/* Selected Factors */}
        <div className="mb-4 flex flex-wrap gap-2">
          {selectedFactors.length === 0 ? (
            <p className="text-sm text-muted-foreground">请从下方添加因子</p>
          ) : (
            selectedFactors.map((factor) => (
              <span
                key={factor}
                className="flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1 text-sm"
              >
                {stripPyExtension(factor)}
                <button
                  onClick={() => handleRemoveFactor(factor)}
                  className="ml-1 rounded-full p-0.5 hover:bg-primary/20"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))
          )}
        </div>

        {/* Add Factor */}
        <div className="flex items-center gap-4">
          <SearchableSelect
            options={availableFactorOptions}
            value={factorToAdd}
            onChange={(value) => {
              if (value) {
                handleAddFactor(value)
                setFactorToAdd('')
              }
            }}
            placeholder="添加因子..."
            searchPlaceholder="搜索因子..."
            emptyText="无匹配因子"
            disabled={selectedFactors.length >= 10}
            className="flex-1"
          />

          <button
            onClick={handleAnalyze}
            disabled={selectedFactors.length < 2 || isLoading}
            className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                计算中...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                计算相关性
              </>
            )}
          </button>
        </div>
      </div>

      {/* Correlation Matrix */}
      {correlationData && (
        <div className="rounded-lg border bg-card p-6">
          <CorrelationMatrix
            factors={selectedFactors.map(stripPyExtension)}
            correlations={correlationData}
            title="因子相关性矩阵"
            height={Math.max(400, selectedFactors.length * 50)}
          />
        </div>
      )}

      {/* Statistics Table */}
      {correlationData && (
        <div className="rounded-lg border bg-card">
          <div className="border-b px-6 py-4">
            <h3 className="font-semibold">相关性统计</h3>
          </div>
          <div className="overflow-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-3 text-left text-sm font-medium">因子对</th>
                  <th className="px-4 py-3 text-center text-sm font-medium">相关系数</th>
                  <th className="px-4 py-3 text-center text-sm font-medium">相关强度</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {getCorrelationPairs(selectedFactors, correlationData)
                  .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
                  .map((pair, i) => (
                    <tr key={i} className="hover:bg-muted/50">
                      <td className="px-4 py-3 text-sm">
                        {stripPyExtension(pair.factor1)} - {stripPyExtension(pair.factor2)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={pair.value > 0 ? 'text-red-600' : 'text-blue-600'}>
                          {pair.value.toFixed(4)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={`rounded-full px-2 py-1 text-xs font-medium ${getCorrelationStrengthClass(
                            pair.value
                          )}`}
                        >
                          {getCorrelationStrength(pair.value)}
                        </span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!correlationData && !isLoading && (
        <div className="flex h-64 items-center justify-center rounded-lg border bg-card">
          <div className="text-center">
            <GitCompare className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-2 text-muted-foreground">
              {selectedFactors.length < 2
                ? '请至少选择2个因子进行分析'
                : '点击"计算相关性"开始分析'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
