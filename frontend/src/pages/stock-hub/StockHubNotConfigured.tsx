import { useTranslation } from 'react-i18next'
import { AlertCircle } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import type { StockHubStatus } from '@/features/stock-hub'

export function StockHubNotConfigured({ status }: { status: StockHubStatus }) {
  const { t } = useTranslation()
  return (
    <Card>
      <CardContent className="py-12 text-center">
        <AlertCircle className="mx-auto h-12 w-12 mb-3 text-amber-500" />
        <h2 className="text-lg font-semibold mb-2">{t('stockHub.notConfigured')}</h2>
        <p className="text-sm text-muted-foreground max-w-md mx-auto mb-4">
          {t('stockHub.notConfiguredHint')}
        </p>
        <div className="text-xs text-muted-foreground space-y-1">
          <p>STOCK_FRAMEWORK_PATH: {status.stock_framework_path} ({status.stock_framework_exists ? '\u2713' : '\u2717'})</p>
          <p>FUEL_PYTHON_PATH: {status.fuel_python_exists ? '\u2713' : '\u2717'}</p>
          <p>Factor Library: {status.factor_lib_exists ? '\u2713' : '\u2717'}</p>
        </div>
      </CardContent>
    </Card>
  )
}
