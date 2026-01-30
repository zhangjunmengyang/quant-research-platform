/**
 * Cypher 查询编辑器组件
 *
 * 基于 Monaco Editor 的 Cypher 语法编辑器，支持:
 * - 语法高亮 (基础)
 * - Ctrl/Cmd + Enter 快捷执行
 * - 执行状态和错误显示
 */

import Editor from '@monaco-editor/react'
import { useState, useCallback } from 'react'
import { Play, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface CypherEditorProps {
  onExecute: (query: string) => void
  isLoading?: boolean
  defaultValue?: string
  error?: string | null
  executionTime?: number | null
}

export function CypherEditor({
  onExecute,
  isLoading = false,
  defaultValue = 'MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100',
  error,
  executionTime,
}: CypherEditorProps) {
  const [query, setQuery] = useState(defaultValue)

  const handleExecute = useCallback(() => {
    if (query.trim() && !isLoading) {
      onExecute(query)
    }
  }, [query, isLoading, onExecute])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault()
        handleExecute()
      }
    },
    [handleExecute]
  )

  return (
    <div className="flex flex-col gap-2" onKeyDown={handleKeyDown}>
      <div className="border rounded-md overflow-hidden">
        <Editor
          height="100px"
          language="cypher"
          value={query}
          onChange={(value) => setQuery(value || '')}
          options={{
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 13,
            lineNumbers: 'off',
            folding: false,
            wordWrap: 'on',
            padding: { top: 8, bottom: 8 },
            renderLineHighlight: 'none',
            overviewRulerBorder: false,
            hideCursorInOverviewRuler: true,
            scrollbar: { vertical: 'hidden', horizontal: 'hidden' },
            automaticLayout: true,
          }}
          theme="vs-dark"
          beforeMount={(monaco) => {
            // 注册 Cypher 语言（基础语法高亮）
            if (!monaco.languages.getLanguages().some((lang: { id: string }) => lang.id === 'cypher')) {
              monaco.languages.register({ id: 'cypher' })
              monaco.languages.setMonarchTokensProvider('cypher', {
                defaultToken: '',
                ignoreCase: true,
                tokenizer: {
                  root: [
                    // 关键字
                    [
                      /\b(MATCH|OPTIONAL|WHERE|RETURN|ORDER|BY|SKIP|LIMIT|CREATE|MERGE|DELETE|DETACH|SET|REMOVE|WITH|UNWIND|CALL|YIELD|UNION|AS|DISTINCT|DESC|ASC|AND|OR|NOT|IN|IS|NULL|TRUE|FALSE|CASE|WHEN|THEN|ELSE|END)\b/,
                      'keyword',
                    ],
                    // 关系类型 [:TYPE]
                    [/\[:[A-Za-z_][A-Za-z0-9_]*\]/, 'type'],
                    // 节点标签 (:Label)
                    [/\(:[A-Za-z_][A-Za-z0-9_]*/, 'type'],
                    // 变量
                    [/\b[a-z_][a-z0-9_]*\b/, 'variable'],
                    // 字符串
                    [/"([^"\\]|\\.)*"/, 'string'],
                    [/'([^'\\]|\\.)*'/, 'string'],
                    // 数字
                    [/\b\d+(\.\d+)?\b/, 'number'],
                    // 注释
                    [/\/\/.*$/, 'comment'],
                    // 属性
                    [/\{/, { token: 'delimiter.curly', next: '@properties' }],
                  ],
                  properties: [
                    [/\}/, { token: 'delimiter.curly', next: '@pop' }],
                    [/[a-zA-Z_][a-zA-Z0-9_]*\s*:/, 'attribute.name'],
                    [/"([^"\\]|\\.)*"/, 'string'],
                    [/'([^'\\]|\\.)*'/, 'string'],
                    [/\b\d+(\.\d+)?\b/, 'number'],
                    [/,/, 'delimiter'],
                  ],
                },
              })
            }
          }}
        />
      </div>
      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground">
          {error ? (
            <span className="text-destructive">{error}</span>
          ) : executionTime != null ? (
            <span>
              执行耗时: {executionTime.toFixed(1)}ms
            </span>
          ) : (
            <span className="opacity-70">Ctrl/Cmd + Enter 执行</span>
          )}
        </div>
        <Button size="sm" onClick={handleExecute} disabled={isLoading || !query.trim()}>
          {isLoading ? (
            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
          ) : (
            <Play className="h-4 w-4 mr-1" />
          )}
          执行
        </Button>
      </div>
    </div>
  )
}
