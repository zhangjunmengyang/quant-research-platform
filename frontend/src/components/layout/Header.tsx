import { useLocation } from 'react-router-dom'
import { User } from 'lucide-react'

const pageTitles: Record<string, string> = {
  '/factors': '因子概览',
  '/factors/analysis': '因子分析',
  '/factors/pipeline': '数据清洗',
  '/strategies': '策略浏览',
  '/strategies/backtest': '在线回测',
  '/strategies/analysis': '策略分析',
  '/data': '数据概览',
  '/mcp': 'MCP 服务',
  '/logs': '日志中心',
}

export function Header() {
  const location = useLocation()
  const title = pageTitles[location.pathname] || '量化平台'

  return (
    <header className="flex h-16 items-center justify-between border-b bg-card px-6">
      {/* Page Title */}
      <h1 className="text-xl font-semibold">{title}</h1>

      {/* Actions */}
      <div className="flex items-center gap-4">
        {/* User */}
        <button
          type="button"
          className="flex items-center gap-2 rounded-lg p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        >
          <User className="h-5 w-5" />
        </button>
      </div>
    </header>
  )
}
