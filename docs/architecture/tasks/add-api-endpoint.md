# 任务: 添加 API 端点

## 完整流程

```
1. backend/app/schemas/    -> 定义 Pydantic 模型
2. backend/domains/*/services/ -> 实现业务逻辑
3. backend/app/routes/v1/  -> 创建路由
4. frontend/src/features/*/types.ts -> 镜像类型
5. frontend/src/features/*/api.ts   -> API 客户端
6. frontend/src/features/*/hooks.ts -> React Query Hooks
7. frontend/src/features/*/components/ -> UI 组件
```

## 后端实现

### 1. Schema 定义

```python
# backend/app/schemas/analysis.py
from pydantic import BaseModel
from typing import Optional

class FactorAnalysisRequest(BaseModel):
    factor_name: str
    param: Optional[str] = None
    n_groups: int = 5

class FactorAnalysisResponse(BaseModel):
    factor_name: str
    ic_mean: float
    ic_std: float
    rank_ic: float
    sharpe: float
```

### 2. 服务层

```python
# backend/domains/factor_hub/services/factor_analysis.py
class FactorAnalysisService:
    def analyze(self, factor_name: str, param: str = None, n_groups: int = 5):
        # 业务逻辑
        return AnalysisResult(...)
```

### 3. 路由

```python
# backend/app/routes/v1/analysis.py
from fastapi import APIRouter, Depends
from app.schemas.analysis import FactorAnalysisRequest, FactorAnalysisResponse

router = APIRouter()

@router.post("/factors/{filename}/analyze")
async def analyze_factor(
    filename: str,
    request: FactorAnalysisRequest,
):
    service = get_factor_analysis_service()
    result = service.analyze(filename, request.param, request.n_groups)
    return success_response(FactorAnalysisResponse.from_result(result))
```

**路径规范**: 不使用尾部斜杠（`/factors` 而非 `/factors/`）

## 前端实现

### 4. 类型定义

```typescript
// frontend/src/features/factor/types.ts
export interface FactorAnalysisRequest {
  factor_name: string
  param?: string
  n_groups?: number
}

export interface FactorAnalysisResponse {
  factor_name: string
  ic_mean: number
  ic_std: number
  rank_ic: number
  sharpe: number
}
```

### 5. API 客户端

```typescript
// frontend/src/features/factor/api.ts
export const factorApi = {
  analyze: async (filename: string, request: FactorAnalysisRequest) => {
    const { data } = await apiClient.post<ApiResponse<FactorAnalysisResponse>>(
      `/factors/${filename}/analyze`,
      request
    )
    return data.data
  },
}
```

### 6. React Query Hook

```typescript
// frontend/src/features/factor/hooks.ts
export function useFactorAnalysis(filename: string) {
  return useMutation({
    mutationFn: (request: FactorAnalysisRequest) =>
      factorApi.analyze(filename, request),
  })
}
```

## 命名规范

- **Schema 文件**: 复数命名（`strategies.py`）
- **Service 文件**: 单数命名（`backtest.py`）
- **前端类型**: 镜像后端 Pydantic 模型，日期用 ISO 8601 字符串
