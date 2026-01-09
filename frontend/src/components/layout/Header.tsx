/**
 * Header Component
 * Design System: Unified header with consistent spacing and interactions
 */

import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { Check, Globe, Moon, Sun, Monitor, User } from 'lucide-react'
import { useTheme } from '@/lib/theme'
import { cn } from '@/lib/utils'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu'

const pageTitles: Record<string, string> = {
  '/factors': 'page.factorOverview',
  '/factors/analysis': 'page.factorAnalysis',
  '/factors/pipeline': 'page.dataCleaning',
  '/strategies': 'page.strategyBrowser',
  '/strategies/backtest': 'page.onlineBacktest',
  '/strategies/analysis': 'page.strategyAnalysis',
  '/data': 'page.dataOverview',
  '/mcp': 'page.mcpService',
  '/logs': 'page.logCenter',
  '/research': 'page.researchOverview',
  '/notes': 'page.noteOverview',
  '/experiences': 'page.experienceOverview',
}

const languages = [
  { code: 'zh-CN', label: '简体中文', flag: '🇨🇳' },
  { code: 'en-US', label: 'English', flag: '🇺🇸' },
]

export function Header() {
  const location = useLocation()
  const { t, i18n } = useTranslation()
  const { theme, setTheme } = useTheme()

  const titleKey = pageTitles[location.pathname] || 'page.quantPlatform'
  const title = t(titleKey)

  const currentLanguage = languages.find((l) => l.code === i18n.language) || languages[0]

  const handleLanguageChange = (langCode: string) => {
    i18n.changeLanguage(langCode)
  }

  // 点击切换主题：light -> dark -> system -> light
  const handleThemeToggle = () => {
    if (theme === 'light') {
      setTheme('dark')
    } else if (theme === 'dark') {
      setTheme('system')
    } else {
      setTheme('light')
    }
  }

  // 获取当前主题的提示文本
  const getThemeTitle = () => {
    if (theme === 'light') return t('header.themeDark')
    if (theme === 'dark') return t('header.themeSystem')
    return t('header.themeLight')
  }

  return (
    <header className="flex h-14 items-center justify-between border-b bg-card px-5 shadow-depth-1">
      {/* Page Title */}
      <motion.h1
        key={titleKey}
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="text-base font-semibold tracking-tight"
      >
        {title}
      </motion.h1>

      {/* Actions */}
      <div className="flex items-center gap-1">
        {/* Theme Toggle - Direct click to cycle: light -> dark -> system */}
        <button
          type="button"
          onClick={handleThemeToggle}
          className={cn(
            'flex h-8 w-8 items-center justify-center rounded-md transition-colors',
            'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
          )}
          aria-label={t('header.theme')}
          title={getThemeTitle()}
        >
          {theme === 'system' ? (
            <Monitor className="h-4 w-4" />
          ) : (
            <>
              <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            </>
          )}
        </button>

        {/* Language Switcher */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className={cn(
                'flex h-8 items-center gap-1.5 rounded-md px-2 transition-colors',
                'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
              aria-label={t('header.language')}
            >
              <Globe className="h-4 w-4" />
              <span className="text-sm">{currentLanguage.flag}</span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-36">
            <DropdownMenuLabel className="text-xs font-medium text-muted-foreground">
              {t('header.language')}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            {languages.map((lang) => (
              <DropdownMenuItem
                key={lang.code}
                onClick={() => handleLanguageChange(lang.code)}
                className="flex items-center justify-between text-sm"
              >
                <div className="flex items-center gap-2">
                  <span>{lang.flag}</span>
                  <span>{lang.label}</span>
                </div>
                {i18n.language === lang.code && <Check className="h-4 w-4 text-primary" />}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className={cn(
                'flex h-8 w-8 items-center justify-center rounded-md transition-colors',
                'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
              aria-label={t('header.user')}
            >
              <User className="h-4 w-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-44">
            <DropdownMenuLabel className="text-xs font-medium text-muted-foreground">
              {t('header.user')}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled className="text-sm">
              <span className="text-muted-foreground">{t('common.developing')}</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
