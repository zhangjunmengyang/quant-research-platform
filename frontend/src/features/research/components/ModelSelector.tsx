/**
 * Model Selector Component
 * LLM 模型选择器组件
 */

import { useMemo } from 'react'
import { Cpu, Loader2 } from 'lucide-react'
import { useModels } from '../hooks'
import { SearchableSelect } from '@/components/ui/SearchableSelect'
import { cn } from '@/lib/utils'

interface ModelSelectorProps {
  value?: string
  onChange: (modelKey: string) => void
  className?: string
  disabled?: boolean
}

export function ModelSelector({ value, onChange, className, disabled }: ModelSelectorProps) {
  const { data: modelsData, isLoading } = useModels()

  const models = modelsData?.models ?? []
  const defaultModel = modelsData?.default_model ?? ''
  const selectedValue = value || defaultModel

  const options = useMemo(() => {
    return models.map((model) => ({
      value: model.key,
      label: model.is_default ? `${model.name} (默认)` : model.name,
      description: model.model,
    }))
  }, [models])

  if (isLoading) {
    return (
      <div className={cn('flex items-center gap-2 text-sm text-muted-foreground', className)}>
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>加载模型...</span>
      </div>
    )
  }

  if (models.length === 0) {
    return (
      <div className={cn('flex items-center gap-2 text-sm text-muted-foreground', className)}>
        <Cpu className="h-4 w-4" />
        <span>无可用模型</span>
      </div>
    )
  }

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <Cpu className="h-4 w-4 text-muted-foreground shrink-0" />
      <SearchableSelect
        options={options}
        value={selectedValue}
        onChange={onChange}
        disabled={disabled}
        placeholder="选择模型"
        size="sm"
        className="w-[130px]"
      />
    </div>
  )
}
