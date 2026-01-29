/**
 * Graph 图表样式工具函数
 *
 * 提供现代化的节点和边样式，使用发光效果替代生硬边框。
 * 设计风格：Luminous Network（发光网络）
 *
 * 注意：本模块不依赖 ECharts 类型，使用自定义类型以确保类型兼容性。
 */

/**
 * 节点样式类型定义
 * 支持径向渐变和发光效果
 */
interface RadialGradientColor {
  type: 'radial'
  x: number
  y: number
  r: number
  colorStops: Array<{ offset: number; color: string }>
}

interface ItemStyleOption {
  color?: string | RadialGradientColor
  borderWidth?: number
  borderColor?: string
  shadowBlur?: number
  shadowColor?: string
  shadowOffsetX?: number
  shadowOffsetY?: number
}

/**
 * 将 hex 颜色转换为 rgba
 */
function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

/**
 * 调整颜色亮度
 * @param hex - 十六进制颜色
 * @param percent - 正值变亮，负值变暗
 */
function adjustBrightness(hex: string, percent: number): string {
  const num = parseInt(hex.slice(1), 16)
  const r = Math.min(
    255,
    Math.max(0, (num >> 16) + Math.round(2.55 * percent))
  )
  const g = Math.min(
    255,
    Math.max(0, ((num >> 8) & 0x00ff) + Math.round(2.55 * percent))
  )
  const b = Math.min(
    255,
    Math.max(0, (num & 0x0000ff) + Math.round(2.55 * percent))
  )
  return `#${(0x1000000 + (r << 16) + (g << 8) + b).toString(16).slice(1)}`
}

/**
 * 创建节点样式
 *
 * 使用径向渐变和发光阴影替代传统边框，营造现代感。
 */
export function createNodeStyle(
  baseColor: string,
  options: {
    isCenter?: boolean
    isFocused?: boolean
  } = {}
): ItemStyleOption {
  const { isCenter = false, isFocused = false } = options

  // 中心节点或聚焦节点 - 强发光效果
  if (isCenter || isFocused) {
    return {
      color: {
        type: 'radial',
        x: 0.5,
        y: 0.5,
        r: 0.8,
        colorStops: [
          { offset: 0, color: adjustBrightness(baseColor, 30) },
          { offset: 0.6, color: baseColor },
          { offset: 1, color: adjustBrightness(baseColor, -15) },
        ],
      },
      borderWidth: 0,
      shadowBlur: 20,
      shadowColor: hexToRgba(baseColor, 0.55),
      shadowOffsetX: 0,
      shadowOffsetY: 0,
    }
  }

  // 普通节点 - 轻微发光效果
  return {
    color: {
      type: 'radial',
      x: 0.35,
      y: 0.35,
      r: 0.9,
      colorStops: [
        { offset: 0, color: adjustBrightness(baseColor, 25) },
        { offset: 1, color: baseColor },
      ],
    },
    borderWidth: 0,
    shadowBlur: 6,
    shadowColor: hexToRgba(baseColor, 0.25),
  }
}

/**
 * 简单的边样式类型（color 只支持字符串）
 */
interface SimpleLinkStyle {
  color?: string
  width?: number
  curveness?: number
}

/**
 * 创建连线样式
 *
 * 使用半透明柔和颜色，配合轻微弧度。
 */
export function createLinkStyle(options?: {
  color?: string
  width?: number
  curveness?: number
}): SimpleLinkStyle {
  return {
    color: options?.color ?? 'rgba(148, 163, 184, 0.45)',
    width: options?.width ?? 1.5,
    curveness: options?.curveness ?? 0.15,
  }
}

