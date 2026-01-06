import { Suspense } from 'react'
import { Outlet } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { Loader2 } from 'lucide-react'

// 页面加载占位组件
function PageLoading() {
  return (
    <div className="flex h-64 items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  )
}

export function App() {
  return (
    <MainLayout>
      <Suspense fallback={<PageLoading />}>
        <Outlet />
      </Suspense>
    </MainLayout>
  )
}
