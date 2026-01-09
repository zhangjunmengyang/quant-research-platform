import { Suspense } from 'react'
import { Outlet } from 'react-router-dom'
import { motion } from 'framer-motion'
import { MainLayout } from '@/components/layout/MainLayout'
import { FlaskConical } from 'lucide-react'

function PageLoading() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex h-64 flex-col items-center justify-center gap-4"
    >
      <motion.div
        animate={{
          scale: [1, 1.1, 1],
          rotate: [0, 5, -5, 0],
        }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-glow-md"
      >
        <FlaskConical className="h-6 w-6" />
      </motion.div>
      <div className="flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="h-2 w-2 rounded-full bg-primary"
            animate={{
              y: [0, -6, 0],
              opacity: [0.5, 1, 0.5],
            }}
            transition={{
              duration: 0.6,
              repeat: Infinity,
              delay: i * 0.15,
              ease: 'easeInOut',
            }}
          />
        ))}
      </div>
    </motion.div>
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
