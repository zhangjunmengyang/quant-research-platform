/**
 * MainLayout Component
 * Design System: Main application layout with sidebar and header
 *
 * Note: Removed page transition animations to avoid visual delay
 * The content should appear immediately for better UX
 */

import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { Toaster } from '@/components/ui/toast'

interface MainLayoutProps {
  children: ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col min-w-0">
        <Header />
        <main className="flex-1 overflow-y-auto p-6 bg-background-subtle">
          {children}
        </main>
      </div>
      <Toaster />
    </div>
  )
}
