/**
 * Strategy Config Card Component
 * 策略配置卡片组件
 */

import { Trash2 } from 'lucide-react'
import { SearchableSelect } from '@/components/ui/SearchableSelect'
import type { StrategyItem, FactorItem } from '@/features/strategy'
import { HOLD_PERIOD_OPTIONS, MARKET_OPTIONS, SORT_OPTIONS } from './constants'

export interface StrategyConfigCardProps {
  index: number
  strategy: StrategyItem
  availableFactors: string[]
  newFactorName: string
  onNewFactorNameChange: (name: string) => void
  onStrategyChange: (index: number, field: keyof StrategyItem, value: unknown) => void
  onRemoveStrategy: (index: number) => void
  onAddFactor: (strategyIndex: number) => void
  onRemoveFactor: (strategyIndex: number, factorIndex: number) => void
  onFactorChange: (
    strategyIndex: number,
    factorIndex: number,
    field: keyof FactorItem,
    value: unknown
  ) => void
}

export function StrategyConfigCard({
  index,
  strategy,
  availableFactors,
  newFactorName,
  onNewFactorNameChange,
  onStrategyChange,
  onRemoveStrategy,
  onAddFactor,
  onRemoveFactor,
  onFactorChange,
}: StrategyConfigCardProps) {
  return (
    <div className="rounded-md border p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-medium">策略 #{index + 1}</span>
        <button
          type="button"
          onClick={() => onRemoveStrategy(index)}
          className="text-red-500 hover:text-red-700"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs">hold_period</label>
          <SearchableSelect
            options={HOLD_PERIOD_OPTIONS}
            value={strategy.hold_period}
            onChange={(value) => onStrategyChange(index, 'hold_period', value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs">market</label>
          <SearchableSelect
            options={MARKET_OPTIONS}
            value={strategy.market}
            onChange={(value) => onStrategyChange(index, 'market', value)}
          />
        </div>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs">long_select_coin_num</label>
          <input
            type="number"
            value={strategy.long_select_coin_num}
            onChange={(e) =>
              onStrategyChange(index, 'long_select_coin_num', parseFloat(e.target.value) || 0)
            }
            className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
            min="0"
            step="any"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs">short_select_coin_num</label>
          <input
            type="text"
            value={strategy.short_select_coin_num}
            onChange={(e) => {
              const val = e.target.value
              if (val === 'long_nums' || val === '') {
                onStrategyChange(index, 'short_select_coin_num', val || 0)
              } else {
                const num = parseFloat(val)
                onStrategyChange(index, 'short_select_coin_num', isNaN(num) ? val : num)
              }
            }}
            className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
            placeholder="数字或 long_nums"
          />
        </div>
      </div>

      {/* Factor List */}
      <div className="mt-3">
        <label className="mb-1 block text-xs font-medium">factor_list *</label>
        <div className="space-y-2">
          {strategy.factor_list.map((factor, fIndex) => (
            <div key={fIndex} className="flex items-center gap-2 rounded bg-muted/50 p-2">
              <span className="min-w-[100px] text-sm font-medium">{factor.name}</span>
              <SearchableSelect
                options={SORT_OPTIONS}
                value={factor.is_sort_asc ? 'true' : 'false'}
                onChange={(value) =>
                  onFactorChange(index, fIndex, 'is_sort_asc', value === 'true')
                }
                className="w-20"
              />
              <input
                type="text"
                value={Array.isArray(factor.param) ? factor.param.join(',') : factor.param}
                onChange={(e) => {
                  const val = e.target.value
                  if (val.includes(',')) {
                    const nums = val
                      .split(',')
                      .map((s) => parseInt(s.trim()))
                      .filter((n) => !isNaN(n))
                    onFactorChange(index, fIndex, 'param', nums.length > 0 ? nums : 0)
                  } else {
                    onFactorChange(index, fIndex, 'param', val === '' ? '' : parseInt(val) || 0)
                  }
                }}
                className="w-20 rounded border border-input bg-background px-2 py-1 text-xs"
                placeholder="param"
              />
              <input
                type="number"
                value={factor.weight}
                onChange={(e) =>
                  onFactorChange(index, fIndex, 'weight', parseFloat(e.target.value) || 1)
                }
                className="w-16 rounded border border-input bg-background px-2 py-1 text-xs"
                placeholder="weight"
                step="0.1"
              />
              <button
                type="button"
                onClick={() => onRemoveFactor(index, fIndex)}
                className="text-red-500 hover:text-red-700"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          ))}
          <div className="flex gap-2">
            <SearchableSelect
              options={availableFactors.map((f) => ({ value: f, label: f }))}
              value={newFactorName}
              onChange={onNewFactorNameChange}
              placeholder="选择因子..."
              searchPlaceholder="搜索因子..."
              emptyText="无匹配因子"
              className="flex-1"
            />
            <button
              type="button"
              onClick={() => onAddFactor(index)}
              disabled={!newFactorName}
              className="rounded-md bg-secondary px-3 py-1.5 text-xs font-medium hover:bg-secondary/80 disabled:opacity-50"
            >
              添加
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
