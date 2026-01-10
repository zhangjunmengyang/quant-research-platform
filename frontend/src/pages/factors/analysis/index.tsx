/**
 * Factor Analysis Page - Main Component
 * 因子分析页 - 主组件 (只包含 tab 切换逻辑)
 */

import { useState } from 'react'
import {
  Calculator,
  BarChart3,
  GitCompare,
  Layers,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { CalculatorTab } from './CalculatorTab'
import { SingleFactorTab } from './SingleFactorTab'
import { MultiFactorTab } from './MultiFactorTab'
import { GroupingTab } from './GroupingTab'
import type { TabType } from './types'

export function Component() {
  const [activeTab, setActiveTab] = useState<TabType>('calculator')

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex items-center gap-4 border-b">
        <button
          onClick={() => setActiveTab('calculator')}
          className={cn(
            'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
            activeTab === 'calculator'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          <Calculator className="h-4 w-4" />
          因子计算
        </button>
        <button
          onClick={() => setActiveTab('single')}
          className={cn(
            'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
            activeTab === 'single'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          <BarChart3 className="h-4 w-4" />
          单因子分析
        </button>
        <button
          onClick={() => setActiveTab('multi')}
          className={cn(
            'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
            activeTab === 'multi'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          <GitCompare className="h-4 w-4" />
          多因子分析
        </button>
        <button
          onClick={() => setActiveTab('grouping')}
          className={cn(
            'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
            activeTab === 'grouping'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          <Layers className="h-4 w-4" />
          因子分箱
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'calculator' && <CalculatorTab />}
      {activeTab === 'single' && <SingleFactorTab />}
      {activeTab === 'multi' && <MultiFactorTab />}
      {activeTab === 'grouping' && <GroupingTab />}
    </div>
  )
}
