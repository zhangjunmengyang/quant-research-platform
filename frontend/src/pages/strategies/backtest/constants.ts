/**
 * Backtest Page Constants
 * 回测页面常量定义
 */

import type { SelectOption } from '@/components/ui/SearchableSelect'

// 账户类型选项
export const ACCOUNT_TYPE_OPTIONS: SelectOption[] = [
  { value: '统一账户', label: '统一账户' },
  { value: '普通账户', label: '普通账户' },
]

// hold_period 选项
export const HOLD_PERIOD_OPTIONS: SelectOption[] = [
  { value: '1H', label: '1H' },
  { value: '2H', label: '2H' },
  { value: '4H', label: '4H' },
  { value: '6H', label: '6H' },
  { value: '8H', label: '8H' },
  { value: '12H', label: '12H' },
  { value: '1D', label: '1D' },
  { value: '3D', label: '3D' },
  { value: '7D', label: '7D' },
]

// market 选项
export const MARKET_OPTIONS: SelectOption[] = [
  { value: 'swap_swap', label: 'swap_swap' },
  { value: 'spot_spot', label: 'spot_spot' },
  { value: 'spot_swap', label: 'spot_swap' },
  { value: 'mix_swap', label: 'mix_swap' },
  { value: 'mix_spot', label: 'mix_spot' },
]

// 排序方向选项
export const SORT_OPTIONS: SelectOption[] = [
  { value: 'true', label: 'Asc' },
  { value: 'false', label: 'Desc' },
]
