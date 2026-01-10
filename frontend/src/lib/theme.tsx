import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from 'react'

type Theme = 'light' | 'dark' | 'system'
export type FontSizeMode = 'compact' | 'standard' | 'large'

interface ThemeContextValue {
  theme: Theme
  resolvedTheme: 'light' | 'dark'
  setTheme: (theme: Theme) => void
  fontSizeMode: FontSizeMode
  setFontSizeMode: (mode: FontSizeMode) => void
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

const THEME_KEY = 'quant-platform-theme'
const FONT_SIZE_KEY = 'quant-platform-font-size'

function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function getStoredTheme(): Theme {
  if (typeof window === 'undefined') return 'system'
  const stored = localStorage.getItem(THEME_KEY)
  if (stored === 'light' || stored === 'dark' || stored === 'system') {
    return stored
  }
  return 'system'
}

function getStoredFontSizeMode(): FontSizeMode {
  if (typeof window === 'undefined') return 'standard'
  const stored = localStorage.getItem(FONT_SIZE_KEY)
  if (stored === 'compact' || stored === 'standard' || stored === 'large') {
    return stored
  }
  return 'standard'
}

interface ThemeProviderProps {
  children: ReactNode
  defaultTheme?: Theme
}

export function ThemeProvider({ children, defaultTheme = 'system' }: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>(() => getStoredTheme() || defaultTheme)
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>(() => {
    const stored = getStoredTheme() || defaultTheme
    return stored === 'system' ? getSystemTheme() : stored
  })
  const [fontSizeMode, setFontSizeModeState] = useState<FontSizeMode>(() => getStoredFontSizeMode())

  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme)
    localStorage.setItem(THEME_KEY, newTheme)
  }, [])

  const setFontSizeMode = useCallback((mode: FontSizeMode) => {
    setFontSizeModeState(mode)
    localStorage.setItem(FONT_SIZE_KEY, mode)
  }, [])

  useEffect(() => {
    const resolved = theme === 'system' ? getSystemTheme() : theme
    setResolvedTheme(resolved)

    const root = document.documentElement
    root.classList.remove('light', 'dark')
    root.classList.add(resolved)
  }, [theme])

  useEffect(() => {
    const root = document.documentElement
    root.setAttribute('data-size-mode', fontSizeMode)
  }, [fontSizeMode])

  useEffect(() => {
    if (theme !== 'system') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = (e: MediaQueryListEvent) => {
      const newResolved = e.matches ? 'dark' : 'light'
      setResolvedTheme(newResolved)
      const root = document.documentElement
      root.classList.remove('light', 'dark')
      root.classList.add(newResolved)
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme])

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme, fontSizeMode, setFontSizeMode }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
