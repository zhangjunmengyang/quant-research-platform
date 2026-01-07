import { memo, useMemo } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  BarChart3,
  BookOpen,
  Database,
  FileText,
  FileTextIcon,
  FlaskConical,
  Play,
  Server,
  Sparkles,
  Target,
  TrendingUp,
} from 'lucide-react'

interface NavItem {
  label: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  disabled?: boolean
}

interface NavGroup {
  title: string
  items: NavItem[]
}

const navigation: NavGroup[] = [
  {
    title: '数据库',
    items: [{ label: '数据概览', href: '/data', icon: Database }],
  },
  {
    title: '因子库',
    items: [
      { label: '因子概览', href: '/factors', icon: FlaskConical },
      { label: '因子分析', href: '/factors/analysis', icon: BarChart3 },
      { label: '数据清洗', href: '/factors/pipeline', icon: Sparkles },
    ],
  },
  {
    title: '策略库',
    items: [
      { label: '策略概览', href: '/strategies', icon: Target },
      { label: '回测队列', href: '/strategies/backtest', icon: Play },
      { label: '策略分析', href: '/strategies/analysis', icon: BarChart3 },
    ],
  },
  {
    title: '研报库',
    items: [
      { label: '研报概览', href: '/research', icon: FileTextIcon },
    ],
  },
  {
    title: '经验库',
    items: [
      { label: '经验概览', href: '/notes', icon: BookOpen },
    ],
  },
  {
    title: '实盘分析',
    items: [
      { label: '实盘监控', href: '/live', icon: TrendingUp, disabled: true },
    ],
  },
  {
    title: '系统',
    items: [
      { label: 'MCP 服务', href: '/mcp', icon: Server },
      { label: '日志浏览', href: '/logs', icon: FileText },
    ],
  },
]

// 预计算所有 href 列表（只计算一次）
const allHrefs = navigation.flatMap((g) => g.items.map((i) => i.href))

// 检查是否有更精确的匹配
function checkHasMoreSpecificMatch(itemHref: string, pathname: string): boolean {
  return allHrefs.some(
    (href) =>
      href !== itemHref &&
      href.startsWith(itemHref + '/') &&
      pathname.startsWith(href)
  )
}

// 使用 memo 优化的导航项组件
const NavItemComponent = memo(function NavItemComponent({
  item,
  isActive,
}: {
  item: NavItem
  isActive: boolean
}) {
  if (item.disabled) {
    return (
      <li>
        <span className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground/50 cursor-not-allowed">
          <item.icon className="h-4 w-4" />
          {item.label}
          <span className="ml-auto text-xs">(开发中)</span>
        </span>
      </li>
    )
  }

  return (
    <li>
      <NavLink
        to={item.href}
        className={cn(
          'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
        )}
      >
        <item.icon className="h-4 w-4" />
        {item.label}
      </NavLink>
    </li>
  )
})

export function Sidebar() {
  const location = useLocation()

  // 缓存当前路径的活动状态计算
  const activeStates = useMemo(() => {
    const states = new Map<string, boolean>()
    for (const href of allHrefs) {
      const hasMoreSpecificMatch = checkHasMoreSpecificMatch(href, location.pathname)
      const isActive =
        location.pathname === href ||
        (!hasMoreSpecificMatch && location.pathname.startsWith(href + '/'))
      states.set(href, isActive)
    }
    return states
  }, [location.pathname])

  return (
    <aside className="flex h-full w-64 flex-col border-r bg-card">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 border-b px-6">
        <FlaskConical className="h-6 w-6 text-primary" />
        <span className="text-lg font-semibold">Quant Platform</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-auto p-4">
        {navigation.map((group) => (
          <div key={group.title} className="mb-6">
            <h3 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {group.title}
            </h3>
            <ul className="space-y-1">
              {group.items.map((item) => (
                <NavItemComponent
                  key={item.href}
                  item={item}
                  isActive={activeStates.get(item.href) ?? false}
                />
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t p-4">
        <div className="text-xs text-muted-foreground">
          <p>Version 2.0.0</p>
        </div>
      </div>
    </aside>
  )
}
