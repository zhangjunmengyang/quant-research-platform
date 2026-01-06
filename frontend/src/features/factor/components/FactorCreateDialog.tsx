/**
 * Factor Create Dialog
 *
 * 用于创建新因子的对话框组件
 */

import { useState, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { factorApi } from '../api'
import type { FactorCreateRequest } from '../types'

interface FactorCreateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: (filename: string) => void
}

const DEFAULT_CODE_TEMPLATE = `# name: MyFactor
# description: 因子描述

def signal_multi_params(df, n=20):
    """
    计算因子值

    Args:
        df: K线数据，包含 open, high, low, close, volume 等字段
        n: 回看周期

    Returns:
        因子值 Series
    """
    # 在这里实现你的因子逻辑
    return df['close'].pct_change(n)
`

export function FactorCreateDialog({
  open,
  onOpenChange,
  onSuccess,
}: FactorCreateDialogProps) {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<FactorCreateRequest>({
    code_content: DEFAULT_CODE_TEMPLATE,
    filename: '',
    style: '',
    formula: '',
    description: '',
  })
  const [error, setError] = useState<string | null>(null)

  const createMutation = useMutation({
    mutationFn: factorApi.create,
    onSuccess: data => {
      queryClient.invalidateQueries({ queryKey: ['factors'] })
      queryClient.invalidateQueries({ queryKey: ['factor-stats'] })
      onOpenChange(false)
      setFormData({
        code_content: DEFAULT_CODE_TEMPLATE,
        filename: '',
        style: '',
        formula: '',
        description: '',
      })
      setError(null)
      onSuccess?.(data.filename)
    },
    onError: (err: Error) => {
      setError(err.message)
    },
  })

  const handleSubmit = useCallback(() => {
    if (!formData.code_content.includes('def signal_multi_params')) {
      setError('代码必须包含 signal_multi_params 函数')
      return
    }
    setError(null)
    createMutation.mutate(formData)
  }, [formData, createMutation])

  const handleInputChange = useCallback(
    (field: keyof FactorCreateRequest) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setFormData(prev => ({ ...prev, [field]: e.target.value }))
    },
    []
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>创建新因子</DialogTitle>
          <DialogDescription>
            输入因子代码和元数据，创建新的因子并入库。代码必须包含 signal_multi_params 函数。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="filename">因子名称 (可选)</Label>
              <Input
                id="filename"
                value={formData.filename || ''}
                onChange={handleInputChange('filename')}
                placeholder="留空则自动从代码中提取"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="style">风格分类</Label>
              <Input
                id="style"
                value={formData.style || ''}
                onChange={handleInputChange('style')}
                placeholder="如: 动量, 反转, 波动率"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="formula">核心公式</Label>
            <Input
              id="formula"
              value={formData.formula || ''}
              onChange={handleInputChange('formula')}
              placeholder="简要描述因子的计算公式"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">刻画特征</Label>
            <Input
              id="description"
              value={formData.description || ''}
              onChange={handleInputChange('description')}
              placeholder="因子刻画的市场特征"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="code_content">因子代码</Label>
            <Textarea
              id="code_content"
              value={formData.code_content}
              onChange={handleInputChange('code_content')}
              className="font-mono text-sm min-h-[400px]"
              placeholder="在这里输入因子代码..."
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={createMutation.isPending}>
            {createMutation.isPending ? '创建中...' : '创建因子'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
