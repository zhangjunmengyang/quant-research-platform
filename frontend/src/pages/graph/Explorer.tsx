/**
 * Graph Explorer Page
 * 知识图谱探索页面
 */

import { GraphExplorer } from '@/features/graph'

export function Component() {
  return (
    <div className="h-[calc(100vh-theme(spacing.14)-theme(spacing.6))]">
      <GraphExplorer className="h-full" />
    </div>
  )
}
