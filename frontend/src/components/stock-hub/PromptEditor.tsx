import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { X, Save, RotateCcw, Loader2 } from 'lucide-react'
import { stockApi } from '@/features/stock-hub'
import type { EvaluationType, PromptConfig } from '@/features/stock-hub'

interface PromptEditorProps {
  evalType: EvaluationType | null // null = closed
  onClose: () => void
  onSaved?: () => void // optional callback after save
}

const EVAL_TYPE_LABELS: Record<string, string> = {
  comprehensive: '综合评估',
  ic_performance: 'IC表现',
  grouping_ability: '分组能力',
  style_profile: '风格画像',
  market_cap: '市值分析',
}

export function PromptEditor({ evalType, onClose, onSaved }: PromptEditorProps) {
  const { t } = useTranslation()

  const [system, setSystem] = useState('')
  const [user, setUser] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadPrompt = useCallback(async (type: EvaluationType) => {
    setLoading(true)
    setError(null)
    try {
      const config: PromptConfig = await stockApi.getPrompt(type)
      setSystem(config.system)
      setUser(config.user)
      setDescription(config.description)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prompt')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (evalType) {
      loadPrompt(evalType)
    }
  }, [evalType, loadPrompt])

  const handleSave = async () => {
    if (!evalType) return
    setSaving(true)
    setError(null)
    try {
      await stockApi.updatePrompt(evalType, system, user)
      onSaved?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save prompt')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    if (evalType) {
      loadPrompt(evalType)
    }
  }

  if (!evalType) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-lg border bg-background p-6 shadow-lg">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">
              {EVAL_TYPE_LABELS[evalType] ?? evalType} - {t('stockHub.promptEditor', '提示词编辑')}
            </h2>
            {description && (
              <p className="mt-1 text-sm text-muted-foreground">{description}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 hover:bg-muted"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">{t('common.loading', '加载中...')}</span>
          </div>
        ) : (
          <div className="space-y-4">
            {/* System Prompt */}
            <div>
              <label className="mb-1 block text-sm font-medium">
                System Prompt
              </label>
              <textarea
                value={system}
                onChange={(e) => setSystem(e.target.value)}
                rows={8}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            {/* User Prompt */}
            <div>
              <label className="mb-1 block text-sm font-medium">
                User Prompt
              </label>
              <textarea
                value={user}
                onChange={(e) => setUser(e.target.value)}
                rows={8}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={handleReset}
                disabled={saving}
                className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm hover:bg-muted disabled:opacity-50"
              >
                <RotateCcw className="h-4 w-4" />
                {t('common.reset', '重置')}
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {saving ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                {t('common.save', '保存')}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
