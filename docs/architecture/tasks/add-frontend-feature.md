# 任务: 添加前端功能模块

## 完整流程

```
1. 创建 feature 目录结构
2. 定义类型（镜像后端 Schema）
3. 实现 API 客户端
4. 实现 React Query Hooks
5. 创建页面组件
6. 配置路由
```

## 目录结构

```bash
mkdir -p frontend/src/features/new/{components}
touch frontend/src/features/new/{types,api,hooks,store,index}.ts
```

## 实现示例

### 1. 类型定义

```typescript
// frontend/src/features/new/types.ts
export interface NewEntity {
  id: string
  name: string
  // 镜像后端 Pydantic 模型
}

export interface NewEntityListParams {
  page?: number
  page_size?: number
  search?: string
}
```

### 2. API 客户端

```typescript
// frontend/src/features/new/api.ts
import { apiClient, type ApiResponse, type PaginatedResponse } from '@/lib/api/client'
import type { NewEntity, NewEntityListParams } from './types'

export const newApi = {
  list: async (params: NewEntityListParams = {}) => {
    const { data } = await apiClient.get<ApiResponse<PaginatedResponse<NewEntity>>>(
      '/new',  // 注意: 不带尾部斜杠
      { params }
    )
    if (!data.success) throw new Error(data.error)
    return data.data
  },

  get: async (id: string) => {
    const { data } = await apiClient.get<ApiResponse<NewEntity>>(`/new/${id}`)
    if (!data.success) throw new Error(data.error)
    return data.data
  },
}
```

### 3. React Query Hooks

```typescript
// frontend/src/features/new/hooks.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { newApi } from './api'

export function useNewEntities(params = {}) {
  return useQuery({
    queryKey: ['new-entities', params],
    queryFn: () => newApi.list(params),
  })
}

export function useNewEntity(id: string) {
  return useQuery({
    queryKey: ['new-entity', id],
    queryFn: () => newApi.get(id),
    enabled: !!id,
  })
}
```

### 4. 页面组件

```typescript
// frontend/src/pages/new/List.tsx
import { useNewEntities } from '@/features/new/hooks'

export function Component() {
  const { data, isLoading, error } = useNewEntities()

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error: {error.message}</div>

  return (
    <div>
      {data?.items.map(item => (
        <div key={item.id}>{item.name}</div>
      ))}
    </div>
  )
}
```

### 5. 路由配置

```typescript
// frontend/src/routes.tsx
const NewList = () => import('@/pages/new/List')

// 在 children 中添加
{
  path: 'new',
  children: [
    { index: true, lazy: NewList },
  ],
}
```

## 关键规范

- **API 路径**: 不使用尾部斜杠
- **类型**: 避免 any，镜像后端模型
- **ECharts**: 禁止 ResizeObserver，用 window.resize
