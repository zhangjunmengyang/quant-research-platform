/**
 * Sidebar Component
 * Design System: Unified sidebar with consistent spacing and interactions
 *
 * Note: Removed page-load animations to avoid visual delay
 * Only keeping expand/collapse animations which provide value
 */

import { memo, useMemo, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AnimatePresence, motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import {
  BarChart3,
  BookOpen,
  ChevronDown,
  Database,
  Eye,
  FileText,
  FileTextIcon,
  FlaskConical,
  Lightbulb,
  Network,
  Server,
  Sparkles,
  Target,
} from 'lucide-react'

interface NavItem {
  labelKey: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  disabled?: boolean
}

interface NavGroup {
  titleKey: string
  items: NavItem[]
  defaultOpen?: boolean
}

const navigation: NavGroup[] = [
  // Data Layer
  {
    titleKey: 'nav.data',
    defaultOpen: true,
    items: [
      { labelKey: 'nav.dataOverview', href: '/data', icon: Database },
      { labelKey: 'nav.dataMonitor', href: '/data/monitor', icon: Eye },
    ],
  },
  // Information Layer (Factor + Strategy)
  {
    titleKey: 'nav.information',
    defaultOpen: true,
    items: [
      { labelKey: 'nav.factorOverview', href: '/factors', icon: FlaskConical },
      { labelKey: 'nav.factorAnalysis', href: '/factors/analysis', icon: BarChart3 },
      { labelKey: 'nav.factorPipeline', href: '/factors/pipeline', icon: Sparkles },
      { labelKey: 'nav.strategyOverview', href: '/strategies', icon: Target },
      { labelKey: 'nav.strategyAnalysis', href: '/strategies/analysis', icon: BarChart3 },
    ],
  },
  // Knowledge Layer
  {
    titleKey: 'nav.knowledge',
    defaultOpen: true,
    items: [
      { labelKey: 'nav.researchOverview', href: '/research', icon: FileTextIcon },
      { labelKey: 'nav.noteOverview', href: '/notes', icon: BookOpen },
    ],
  },
  // Wisdom Layer
  {
    titleKey: 'nav.wisdom',
    defaultOpen: true,
    items: [
      { labelKey: 'nav.experienceOverview', href: '/experiences', icon: Lightbulb },
      { labelKey: 'nav.graphExplorer', href: '/graph', icon: Network },
    ],
  },
  // System
  {
    titleKey: 'nav.system',
    defaultOpen: true,
    items: [
      { labelKey: 'nav.mcpService', href: '/mcp', icon: Server },
      { labelKey: 'nav.logBrowser', href: '/logs', icon: FileText },
    ],
  },
]

const allHrefs = navigation.flatMap((g) => g.items.map((i) => i.href))

function checkHasMoreSpecificMatch(itemHref: string, pathname: string): boolean {
  return allHrefs.some(
    (href) => href !== itemHref && href.startsWith(itemHref + '/') && pathname.startsWith(href)
  )
}

const NavItemComponent = memo(function NavItemComponent({
  item,
  isActive,
}: {
  item: NavItem
  isActive: boolean
}) {
  const { t } = useTranslation()

  if (item.disabled) {
    return (
      <li>
        <span className="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-sidebar-foreground/40 cursor-not-allowed">
          <item.icon className="h-4 w-4" />
          <span className="flex-1">{t(item.labelKey)}</span>
          <span className="text-2xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
            {t('common.developing')}
          </span>
        </span>
      </li>
    )
  }

  return (
    <li>
      <NavLink
        to={item.href}
        className={cn(
          'group flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium transition-all duration-150',
          isActive
            ? 'bg-sidebar-primary text-sidebar-primary-foreground shadow-glow-sm'
            : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
        )}
      >
        <item.icon
          className={cn(
            'h-4 w-4 transition-transform duration-150',
            !isActive && 'group-hover:scale-110'
          )}
        />
        <span className="flex-1">{t(item.labelKey)}</span>
        {isActive && (
          <span className="w-1.5 h-1.5 rounded-full bg-sidebar-primary-foreground" />
        )}
      </NavLink>
    </li>
  )
})

const NavGroupComponent = memo(function NavGroupComponent({
  group,
  activeStates,
}: {
  group: NavGroup
  activeStates: Map<string, boolean>
}) {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(group.defaultOpen ?? true)
  const hasActiveItem = group.items.some((item) => activeStates.get(item.href))

  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex w-full items-center gap-2 px-2.5 py-1.5 text-xs font-semibold uppercase tracking-wider transition-colors',
          hasActiveItem ? 'text-sidebar-accent-foreground' : 'text-sidebar-foreground/50',
          'hover:text-sidebar-accent-foreground'
        )}
      >
        <span className="flex-1 text-left">{t(group.titleKey)}</span>
        <ChevronDown
          className={cn(
            'h-3 w-3 transition-transform duration-150',
            isOpen ? 'rotate-0' : '-rotate-90'
          )}
        />
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.ul
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15, ease: 'easeInOut' }}
            className="mt-1 space-y-0.5 overflow-hidden"
          >
            {group.items.map((item) => (
              <NavItemComponent
                key={item.href}
                item={item}
                isActive={activeStates.get(item.href) ?? false}
              />
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  )
})

export function Sidebar() {
  const { t } = useTranslation()
  const location = useLocation()

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
    <aside className="flex h-full w-60 flex-col border-r border-sidebar-border bg-sidebar">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 border-b border-sidebar-border px-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground shadow-glow-sm">
          <FlaskConical className="h-4 w-4" />
        </div>
        <span className="text-base font-bold tracking-tight text-foreground">
          {t('nav.platformName')}
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-auto px-2.5 py-3">
        {navigation.map((group) => (
          <NavGroupComponent
            key={group.titleKey}
            group={group}
            activeStates={activeStates}
          />
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border px-4 py-3">
        <div className="text-2xs text-sidebar-foreground/50">
          <p>
            {t('common.version')} 2.0.0
          </p>
        </div>
      </div>
    </aside>
  )
}
