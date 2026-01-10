/**
 * Font Size Selector Component
 * 字号档位选择器 - 点击循环切换，T 图标 + 右下角角标
 */

import { Type } from 'lucide-react'
import { useTheme } from '@/lib/theme'

export type FontSizeMode = 'compact' | 'standard' | 'large'

const MODE_ORDER: FontSizeMode[] = ['standard', 'large', 'compact']

export function FontSizeSelector() {
  const { fontSizeMode, setFontSizeMode } = useTheme()

  const handleClick = () => {
    const currentIndex = MODE_ORDER.indexOf(fontSizeMode)
    const nextIndex = (currentIndex + 1) % MODE_ORDER.length
    const nextMode = MODE_ORDER[nextIndex]
    if (nextMode) {
      setFontSizeMode(nextMode)
    }
  }

  const getBadgeText = (): string => {
    switch (fontSizeMode) {
      case 'compact':
        return '小'
      case 'large':
        return '大'
      default:
        return '中'
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className="relative flex h-8 w-8 items-center justify-center rounded-md transition-colors text-muted-foreground hover:bg-accent hover:text-accent-foreground focus-visible:outline-none"
      aria-label="字号设置"
    >
      <Type className="h-4 w-4" />
      <span className="absolute -bottom-0.5 -right-0.5 text-[10px] font-medium text-muted-foreground">
        {getBadgeText()}
      </span>
    </button>
  )
}
