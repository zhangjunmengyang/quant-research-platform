# 量化研究知识与经验管理体系

本文档阐述量化研究平台的知识管理架构设计，包括理论基础、分层模型和实现方案。

## 目录

1. [设计背景与动机](#设计背景与动机)
2. [理论基础](#理论基础)
3. [知识分层架构](#知识分层架构)
4. [各层职责详解](#各层职责详解)
5. [experience-hub 设计](#experience-hub-设计)
6. [数据流与交互](#数据流与交互)
7. [实现路线](#实现路线)

---

## 设计背景与动机

### 当前系统的不足

现有系统包含 data-hub、factor-hub、strategy-hub、note-hub、research-hub 五个知识库，覆盖了从原始数据到研究记录的多个层次。但存在一个关键缺失：

**缺少"经验层"** —— 即可迁移、可复用的研究智慧。

当前的问题：
- note-hub 定位模糊，混杂临时记录和重要结论
- 研究过程中的成功/失败经验没有结构化存储
- Agent 无法查询历史研究中的教训和规律
- 知识停留在"信息"层面，未能提炼为"智慧"

### 核心诉求

1. **避免重复踩坑**：Agent 能查询历史失败案例
2. **复用成功经验**：Agent 能参考历史成功模式
3. **理解因果关系**：不只是"是什么"，还有"为什么"
4. **长期记忆**：经验能跨研究会话持久化

---

## 理论基础

### DIKW 知识金字塔

DIKW 模型是知识管理的经典框架，描述了从数据到智慧的演进过程：

```
          ┌───────┐
          │Wisdom │  智慧：可迁移的原则和判断力
         ┌┴───────┴┐
         │Knowledge│  知识：结构化的理解和结论
        ┌┴─────────┴┐
        │Information│  信息：有意义的数据组合
       ┌┴───────────┴┐
       │    Data     │  数据：原始的事实和数字
       └─────────────┘
```

**映射到量化研究：**

| DIKW 层级 | 量化研究对应 | 示例 |
|----------|-------------|------|
| Data | K线、成交量 | BTC-USDT 的小时收盘价序列 |
| Information | 因子值、回测指标 | Momentum_5d 的 IC 是 0.03 |
| Knowledge | 研究结论 | Bias_20 在 2024Q1 牛市表现优异 |
| Wisdom | 研究原则 | 均值回归因子在高波动期普遍失效 |

### 经验的本质特征

经验不同于信息，它具有以下核心特征：

1. **可迁移性**（Transferability）
   - 能应用到新的、未见过的情境
   - 不局限于特定因子或策略

2. **因果性**（Causality）
   - 包含"为什么"的理解
   - 不只是相关性，而是因果推断

3. **抽象性**（Abstraction）
   - 超越具体案例的模式识别
   - 从个例提炼出规律

4. **时效性**（Temporality）
   - 可能随市场演变而失效
   - 需要持续验证和更新

### PARL 经验框架

为了结构化存储经验，采用 PARL 框架：

```
┌─────────────────────────────────────────────────┐
│                  PARL Framework                  │
├─────────────┬───────────────────────────────────┤
│  Problem    │ 面临的问题或挑战是什么？          │
├─────────────┼───────────────────────────────────┤
│  Approach   │ 采用了什么方法或策略？            │
├─────────────┼───────────────────────────────────┤
│  Result     │ 得到了什么结果？                  │
├─────────────┼───────────────────────────────────┤
│  Lesson     │ 总结出什么教训或规律？            │
└─────────────┴───────────────────────────────────┘
```

**示例：**

```yaml
problem: 动量因子在某些时期表现极差，导致策略大幅回撤
approach: 分析动量因子失效的市场环境特征
result: 发现在 VIX 指数超过 30 的高波动期，动量因子 IC 转负
lesson: 动量因子需要结合波动率过滤，高波动期应降低仓位或暂停交易
```

### 经验的生命周期

经验不是静态的，它有完整的生命周期：

```
  ┌─────────┐     验证成功     ┌───────────┐
  │  Draft  │ ───────────────→ │ Validated │
  │ (草稿)  │                  │  (已验证)  │
  └─────────┘                  └───────────┘
                                    │
                               证伪/过时
                                    │
                                    ▼
                              ┌───────────┐
                              │Deprecated │
                              │  (已废弃)  │
                              └───────────┘
```

- **Draft**：新记录的经验，待验证
- **Validated**：经过后续研究验证的经验，置信度提升
- **Deprecated**：被证伪或已过时的经验，保留历史但降低检索权重

---

## 知识分层架构

### 完整架构图

```
┌────────────────────────────────────────────────────────────┐
│                    Wisdom Layer (智慧层)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  experience-hub (经验知识库)                          │  │
│  │                                                      │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ Strategic (战略级)                              │  │  │
│  │  │ • 研究原则：长期有效的方法论                    │  │  │
│  │  │ • 设计模式：经验证的因子/策略设计范式          │  │  │
│  │  │ • 风险警示：必须避免的陷阱                     │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ Tactical (战术级)                               │  │  │
│  │  │ • 场景结论：特定市场环境下的研究发现           │  │  │
│  │  │ • 参数建议：经验证的参数范围                   │  │  │
│  │  │ • 组合策略：因子/策略的有效组合方式            │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ Operational (操作级)                            │  │  │
│  │  │ • 成功实验：具体的成功案例详情                 │  │  │
│  │  │ • 失败实验：具体的失败案例教训                 │  │  │
│  │  │ • 研究观察：过程中的重要发现                   │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ▲                                  │
│            提炼 (curate)  │  参考 (reference)              │
│                          │                                  │
├───────────────────────────┼────────────────────────────────┤
│                 Knowledge Layer (知识层)                    │
│                                                            │
│  ┌─────────────────────┐    ┌─────────────────────┐       │
│  │      note-hub       │    │    research-hub     │       │
│  │    (研究笔记库)      │    │   (外部研究库)      │       │
│  │                     │    │                     │       │
│  │  • 研究轨迹         │    │  • 外部研报         │       │
│  │  • 临时发现         │    │  • 学术论文         │       │
│  │  • 待验证假设       │    │  • 市场分析         │       │
│  │  • 研究草稿         │    │  • RAG 检索         │       │
│  └─────────────────────┘    └─────────────────────┘       │
│           ▲                          ▲                     │
│           │ 记录                     │ 输入                │
├───────────┼──────────────────────────┼─────────────────────┤
│                 Artifact Layer (产出层)                     │
│                                                            │
│  ┌─────────────────────┐    ┌─────────────────────┐       │
│  │    strategy-hub     │    │     factor-hub      │       │
│  │    (策略知识库)      │    │    (因子知识库)     │       │
│  │                     │    │                     │       │
│  │  • 策略配置         │    │  • 因子代码         │       │
│  │  • 回测结果         │    │  • IC/IR 指标       │       │
│  │  • 实盘记录         │    │  • 元数据           │       │
│  │  • 参数遍历         │    │  • 分组分析         │       │
│  └─────────────────────┘    └─────────────────────┘       │
│           ▲                          ▲                     │
│           │ 构建                     │ 计算                │
├───────────┼──────────────────────────┼─────────────────────┤
│                   Data Layer (数据层)                       │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                      data-hub                         │  │
│  │                    (市场数据库)                        │  │
│  │                                                      │  │
│  │  • K线数据 (OHLCV)                                   │  │
│  │  • 成交量、持仓量                                    │  │
│  │  • 资金费率                                          │  │
│  │  • 市场概览                                          │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### 层级关系说明

| 层级 | 职责 | 内容特征 | 时效性 | 可迁移性 |
|------|------|---------|--------|---------|
| **Wisdom** | 研究智慧 | 抽象、可复用、经验证 | 长期 | 高 |
| **Knowledge** | 研究过程 | 临时、待整理、外部输入 | 短-中期 | 中 |
| **Artifact** | 研究产出 | 结构化、可执行、可验证 | 中期 | 低 |
| **Data** | 市场数据 | 事实、客观、原始 | 实时 | 无 |

### 依赖方向

```
Wisdom Layer
    │
    │ 提炼自 / 指导
    ▼
Knowledge Layer
    │
    │ 记录 / 参考
    ▼
Artifact Layer
    │
    │ 基于
    ▼
Data Layer
```

**关键原则：上层依赖下层，下层不依赖上层。**

---

## 各层职责详解

### Data Layer: data-hub

**定位**：市场原始数据的唯一来源

**职责**：
- 提供 K线、成交量、资金费率等市场数据
- 支持多币种、多周期查询
- 提供市场概览和排名

**不变性**：data-hub 存储的是客观事实，不包含任何主观判断。

### Artifact Layer: factor-hub & strategy-hub

**factor-hub 定位**：因子的结构化存储

**职责**：
- 存储因子代码和元数据
- 记录 IC、RankIC、ICIR 等统计指标
- 支持因子检索、对比、相关性分析
- 管理因子生命周期（验证、排除）

**strategy-hub 定位**：策略的结构化存储

**职责**：
- 存储策略配置
- 管理回测任务和结果
- 支持参数遍历和分析
- 记录实盘表现

### Knowledge Layer: note-hub & research-hub

**note-hub 定位**：研究过程的临时记录（重新定位）

**职责**：
- 记录研究轨迹（Research Trail）
- 存储临时发现和观察
- 保存待验证的假设
- 作为 experience-hub 的"原材料"

**与 experience-hub 的关系**：
```
note-hub (草稿/临时) ──提炼──→ experience-hub (结构化/持久)
```

**research-hub 定位**：外部知识的输入通道

**职责**：
- 存储外部研报、论文
- 提供 RAG 检索能力
- 作为研究的参考输入

### Wisdom Layer: experience-hub

**定位**：可迁移的研究智慧，Agent 的长期记忆

**职责**：
- 存储结构化的研究经验
- 支持语义检索
- 管理经验生命周期
- 支持经验的验证和提炼

**详细设计见下一章节。**

---

## experience-hub 设计

### 经验分类体系

```
experience_level
│
├── strategic (战略级)
│   │
│   │   长期有效的研究原则，跨因子/策略/市场通用
│   │
│   ├── market_regime_principle
│   │   示例："均值回归因子在高波动期普遍失效"
│   │
│   ├── factor_design_principle
│   │   示例："多因子组合前必须检查相关性矩阵"
│   │
│   └── risk_management_principle
│       示例："新因子上线前必须经历完整牛熊周期验证"
│
├── tactical (战术级)
│   │
│   │   特定场景下的研究结论，有明确的适用边界
│   │
│   ├── factor_performance
│   │   示例："Bias_20 在震荡市 IC 稳定在 0.03 左右"
│   │
│   ├── strategy_optimization
│   │   示例："合约市场最优持仓周期为 4H"
│   │
│   └── param_sensitivity
│       示例："动量周期在 5-20 日范围内敏感度较低"
│
└── operational (操作级)
    │
    │   具体的研究记录，详细的案例
    │
    ├── successful_experiment
    │   示例："2024-03-15 动量+波动率过滤组合回测，夏普2.1"
    │
    ├── failed_experiment
    │   示例："2024-03-10 纯动量策略在震荡市大幅回撤"
    │
    └── research_observation
        示例："发现 BTC 主导率下降时山寨币动量因子更有效"
```

### 数据模型

```python
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ExperienceContext(BaseModel):
    """经验的上下文信息"""

    # 市场环境
    market_regime: Optional[str] = None
    """市场状态：牛市/熊市/震荡"""

    # 相关因子风格
    factor_styles: List[str] = Field(default_factory=list)
    """相关的因子风格：动量/反转/波动性/流动性等"""

    # 时间范围
    time_horizon: Optional[str] = None
    """适用的时间范围：短期/中期/长期"""

    # 资产类别
    asset_class: Optional[str] = None
    """资产类别：BTC/ETH/山寨币/全市场"""

    # 自由标签
    tags: List[str] = Field(default_factory=list)
    """自定义标签"""


class ExperienceContent(BaseModel):
    """经验的核心内容（PARL框架）"""

    problem: str
    """Problem: 面临的问题或挑战"""

    approach: str
    """Approach: 采用的方法或策略"""

    result: str
    """Result: 得到的结果"""

    lesson: str
    """Lesson: 总结的教训或规律"""


class Experience(BaseModel):
    """经验实体"""

    # === 基础信息 ===
    id: str
    """唯一标识"""

    title: str
    """经验标题"""

    experience_level: Literal["strategic", "tactical", "operational"]
    """经验层级"""

    category: str
    """分类：如 market_regime_principle, factor_performance 等"""

    # === 核心内容 ===
    content: ExperienceContent
    """PARL 结构化内容"""

    # === 上下文 ===
    context: ExperienceContext
    """经验的上下文信息"""

    # === 来源追溯 ===
    source_type: Literal["research", "backtest", "live_trade", "external", "manual"]
    """来源类型"""

    source_ref: Optional[str] = None
    """来源引用：research_id, strategy_id, note_id 等"""

    # === 置信度与验证 ===
    confidence: float = Field(ge=0, le=1, default=0.5)
    """置信度 0-1"""

    validation_count: int = Field(ge=0, default=0)
    """被验证次数"""

    last_validated: Optional[datetime] = None
    """最后验证时间"""

    # === 生命周期 ===
    status: Literal["draft", "validated", "deprecated"] = "draft"
    """状态"""

    deprecated_reason: Optional[str] = None
    """废弃原因（如果 status=deprecated）"""

    # === 时间戳 ===
    created_at: datetime
    """创建时间"""

    updated_at: datetime
    """更新时间"""

    # === 语义检索 ===
    embedding: Optional[List[float]] = None
    """向量化表示，用于语义检索"""
```

### 核心工具设计

#### store_experience - 存储经验

```python
def store_experience(
    experience_level: Literal["strategic", "tactical", "operational"],
    category: str,
    title: str,
    content: ExperienceContent,
    context: ExperienceContext,
    source_type: Literal["research", "backtest", "live_trade", "external", "manual"],
    source_ref: Optional[str] = None,
    confidence: float = 0.5,
) -> dict:
    """
    存储新经验

    Args:
        experience_level: 经验层级
        category: 分类
        title: 标题
        content: PARL 结构化内容
        context: 上下文信息
        source_type: 来源类型
        source_ref: 来源引用
        confidence: 初始置信度

    Returns:
        {"experience_id": str, "status": "created"}
    """
```

#### query_experiences - 检索经验

```python
def query_experiences(
    query: str,
    experience_level: Optional[str] = None,
    category: Optional[str] = None,
    market_regime: Optional[str] = None,
    factor_styles: Optional[List[str]] = None,
    min_confidence: float = 0.0,
    include_deprecated: bool = False,
    top_k: int = 5,
) -> List[Experience]:
    """
    语义检索经验

    Args:
        query: 自然语言查询
        experience_level: 过滤层级
        category: 过滤分类
        market_regime: 过滤市场环境
        factor_styles: 过滤因子风格
        min_confidence: 最低置信度
        include_deprecated: 是否包含已废弃经验
        top_k: 返回数量

    Returns:
        匹配的经验列表，按相关性排序
    """
```

#### validate_experience - 验证经验

```python
def validate_experience(
    experience_id: str,
    validation_note: Optional[str] = None,
    confidence_delta: float = 0.1,
) -> dict:
    """
    验证/增强经验

    当后续研究证实了某条经验时调用，会：
    1. 增加 validation_count
    2. 更新 last_validated
    3. 提升 confidence（不超过 1.0）
    4. 如果是 draft 状态，更新为 validated

    Args:
        experience_id: 经验 ID
        validation_note: 验证说明
        confidence_delta: 置信度增量

    Returns:
        {"experience_id": str, "new_confidence": float, "validation_count": int}
    """
```

#### deprecate_experience - 废弃经验

```python
def deprecate_experience(
    experience_id: str,
    reason: str,
) -> dict:
    """
    废弃经验

    当经验被证伪或已过时时调用，会：
    1. 将 status 更新为 deprecated
    2. 记录废弃原因
    3. 保留历史记录但降低检索权重

    Args:
        experience_id: 经验 ID
        reason: 废弃原因

    Returns:
        {"experience_id": str, "status": "deprecated"}
    """
```

#### curate_experience - 提炼经验

```python
def curate_experience(
    source_experience_ids: List[str],
    target_level: Literal["tactical", "strategic"],
    title: str,
    content: ExperienceContent,
    context: ExperienceContext,
) -> dict:
    """
    从低层经验提炼高层经验

    例如：
    - 从多个 operational 经验总结为一个 tactical 结论
    - 从多个 tactical 结论抽象为一个 strategic 原则

    Args:
        source_experience_ids: 源经验 ID 列表
        target_level: 目标层级（必须高于源经验）
        title: 新经验标题
        content: PARL 内容
        context: 上下文

    Returns:
        {"experience_id": str, "source_count": int}
    """
```

#### link_experience - 关联经验

```python
def link_experience(
    experience_id: str,
    entity_type: Literal["factor", "strategy", "note", "research"],
    entity_id: str,
    relation: str = "related",
) -> dict:
    """
    关联经验与其他实体

    建立经验与因子、策略、笔记、研报的关联关系。

    Args:
        experience_id: 经验 ID
        entity_type: 实体类型
        entity_id: 实体 ID
        relation: 关系类型（related, derived_from, applied_to 等）

    Returns:
        {"link_id": str, "experience_id": str, "entity_type": str, "entity_id": str}
    """
```

### 语义检索设计

#### Embedding 策略

经验的语义表示需要捕获其核心含义。Embedding 的生成策略：

```python
def generate_experience_embedding(experience: Experience) -> List[float]:
    """
    生成经验的向量表示

    组合以下内容生成 embedding：
    1. title（标题）
    2. content.problem（问题）
    3. content.lesson（教训）

    这三个字段最能代表经验的核心语义。
    """
    text = f"{experience.title}\n{experience.content.problem}\n{experience.content.lesson}"
    return embed_text(text)  # 使用 mcp_core/llm 的 embedding 能力
```

#### 混合检索

检索时采用 语义相似度 + 结构化过滤 的混合方式：

```
用户查询
    │
    ├──→ 生成 query embedding
    │         │
    │         ▼
    │    向量相似度检索 ──→ 候选集 A
    │
    └──→ 结构化条件过滤
              │
              ▼
         过滤后候选集 B
              │
              ▼
         A ∩ B = 最终结果
              │
              ▼
         按相似度排序返回
```

---

## 数据流与交互

### 研究全流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        研究生命周期                              │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Phase 1: 研究启动                                         │  │
│  │                                                           │  │
│  │  "我要研究动量因子在震荡市的表现"                         │  │
│  │                    │                                      │  │
│  │                    ▼                                      │  │
│  │  query_experiences("动量因子 震荡市")                     │  │
│  │                    │                                      │  │
│  │                    ▼                                      │  │
│  │  参考历史经验，避免已知陷阱                               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Phase 2: 研究进行                                         │  │
│  │                                                           │  │
│  │  执行因子分析、回测等                                     │  │
│  │                    │                                      │  │
│  │                    ▼                                      │  │
│  │  create_note() ──→ 记录临时发现到 note-hub               │  │
│  │                                                           │  │
│  │  "发现 Momentum_5d 在最近3个月 IC 急剧下降"              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Phase 3: 研究完成                                         │  │
│  │                                                           │  │
│  │  总结研究结论                                             │  │
│  │                    │                                      │  │
│  │                    ▼                                      │  │
│  │  store_experience() ──→ 结构化存储到 experience-hub      │  │
│  │                                                           │  │
│  │  {                                                        │  │
│  │    experience_level: "tactical",                          │  │
│  │    category: "factor_performance",                        │  │
│  │    content: {                                             │  │
│  │      problem: "动量因子在震荡市表现不稳定",              │  │
│  │      approach: "分析不同市场环境下的 IC 变化",           │  │
│  │      result: "震荡市 IC 方差是趋势市的 3 倍",            │  │
│  │      lesson: "震荡市需要降低动量因子权重或加入过滤"      │  │
│  │    }                                                      │  │
│  │  }                                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Phase 4: 后续验证                                         │  │
│  │                                                           │  │
│  │  后续研究证实了这个结论                                   │  │
│  │                    │                                      │  │
│  │                    ▼                                      │  │
│  │  validate_experience(experience_id)                       │  │
│  │                    │                                      │  │
│  │                    ▼                                      │  │
│  │  置信度提升，validation_count++                           │  │
│  │                                                           │  │
│  │  ─────────────── 或者 ───────────────                     │  │
│  │                                                           │  │
│  │  发现这个结论不再成立（市场变化）                         │  │
│  │                    │                                      │  │
│  │                    ▼                                      │  │
│  │  deprecate_experience(experience_id, "市场结构改变")      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Phase 5: 经验提炼                                         │  │
│  │                                                           │  │
│  │  积累了多个类似的 tactical 经验                           │  │
│  │                    │                                      │  │
│  │                    ▼                                      │  │
│  │  curate_experience(                                       │  │
│  │    source_ids=[exp1, exp2, exp3],                        │  │
│  │    target_level="strategic",                              │  │
│  │    content={                                              │  │
│  │      problem: "因子在不同市场环境表现差异大",            │  │
│  │      approach: "研究多个因子在多种市场环境的表现",       │  │
│  │      result: "总结出因子-环境适配规律",                  │  │
│  │      lesson: "任何因子策略都需要市场环境适配机制"        │  │
│  │    }                                                      │  │
│  │  )                                                        │  │
│  │                    │                                      │  │
│  │                    ▼                                      │  │
│  │  生成 strategic 级别的研究原则                            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Hub 间交互关系

```
                    ┌─────────────┐
                    │ experience  │
                    │    hub      │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │  note-hub  │  │research-hub│  │  外部输入  │
    │  (草稿)    │  │ (外部研报) │  │  (手动)    │
    └─────┬──────┘  └─────┬──────┘  └────────────┘
          │               │
          │    研究过程    │    参考输入
          ▼               ▼
    ┌────────────────────────────────────┐
    │         研究活动 (Agent)            │
    └────────────────┬───────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
  ┌────────────┐          ┌────────────┐
  │factor-hub  │          │strategy-hub│
  │ (因子产出) │          │ (策略产出) │
  └─────┬──────┘          └─────┬──────┘
        │                       │
        └───────────┬───────────┘
                    │
                    ▼
             ┌────────────┐
             │  data-hub  │
             │ (市场数据) │
             └────────────┘
```

### 关联关系

```
experience-hub
     │
     ├── link_experience ──→ factor-hub
     │   "这条经验涉及 Momentum_5d 因子"
     │
     ├── link_experience ──→ strategy-hub
     │   "这条经验来自某策略的回测"
     │
     ├── link_experience ──→ note-hub
     │   "这条经验提炼自某条笔记"
     │
     └── link_experience ──→ research-hub
         "这条经验参考了某篇外部研报"
```

---

## 实现路线

### Phase 1: 核心功能 (已完成)

**目标**：实现 experience-hub 的基本存取能力

**已实现**：
1. 创建 `backend/domains/experience_hub/` 目录结构
2. 实现数据模型和数据库表
3. 实现 `store_experience` 工具
4. 实现 `query_experiences` 工具（结构化过滤）
5. 创建 MCP Server

**代码路径**：
- 数据模型: `backend/domains/experience_hub/core/models.py`
- 存储层: `backend/domains/experience_hub/core/store.py`
- 数据库表: `backend/domains/experience_hub/core/schema.sql`
- MCP 服务器: `backend/domains/experience_hub/api/mcp/server.py`
- MCP 工具: `backend/domains/experience_hub/api/mcp/tools/experience_tools.py`

**服务端口**: 6794

### Phase 2: 语义检索 (已完成)

**目标**：支持自然语言查询经验

**已实现**：
1. 集成 embedding 生成
2. 实现向量存储（PostgreSQL pgvector）
3. 实现混合检索逻辑

**代码路径**：
- 向量检索: `backend/domains/experience_hub/core/store.py` (`vector_search`, `store_embedding` 方法)
- 向量表: `backend/domains/experience_hub/core/schema.sql` (`experience_embeddings` 表)

### Phase 3: 生命周期管理 (已完成)

**目标**：支持经验的完整生命周期

**已实现**：
1. 实现 `validate_experience` 工具
2. 实现 `deprecate_experience` 工具

**代码路径**：
- 验证/废弃: `backend/domains/experience_hub/core/store.py` (`validate`, `deprecate` 方法)
- 工具实现: `backend/domains/experience_hub/api/mcp/tools/experience_tools.py`

### Phase 4: 提炼与关联 (已完成)

**目标**：支持经验的提炼和关联

**已实现**：
1. 实现 `curate_experience` 工具
2. 实现 `link_experience` 工具
3. 创建关联关系表
4. 实现关联查询

**代码路径**：
- 关联表: `backend/domains/experience_hub/core/schema.sql` (`experience_links`, `experience_curation_sources` 表)
- 关联管理: `backend/domains/experience_hub/core/store.py` (`add_link`, `get_links`, `get_experiences_by_entity` 方法)
- 提炼任务: `backend/domains/experience_hub/tasks/curate.py`

### Phase 5: 集成优化 (已完成)

**目标**：与现有系统深度集成

**已实现**：
1. 优化 note-hub，明确其作为"草稿"的定位
   - 新增字段: note_type, promoted_to_experience_id, is_archived
2. 实现 Edge 系统管理实体关系
   - 核心实现: `backend/domains/mcp_core/edge/`
   - 支持任意实体间的关系建立（note-note, note-factor, note-coin 等）
   - 关系类型: derived_from, verifies, references, summarizes, has_tag, related

**Edge 系统替代 linked_note_id**：
- 旧方案: 使用 `linked_note_id` 字段关联验证笔记与假设笔记
- 新方案: 使用 `link_note(note_id, "note", hypothesis_id, "verifies")` 建立关系
- 优势: 支持任意实体间的多对多关系，可追溯完整知识谱系

**待完成**：
- 在研究流程中自动触发经验查询
- 实现经验的可视化展示
- 性能优化和监控

### 数据库迁移

执行顺序：
1. `backend/domains/experience_hub/core/schema.sql` - 创建 experience_hub 表
2. `scripts/migrations/note_hub_enhance.sql` - 增强 note_hub 表
3. `scripts/migrations/knowledge_graph_tables.sql` - 创建知识图谱表

详细迁移说明见 [数据库迁移文档](../database-migrations.md)

---

## 附录

### A. 经验分类参考

| experience_level | category | 说明 | 示例 |
|-----------------|----------|------|------|
| strategic | market_regime_principle | 市场环境原则 | 均值回归因子在高波动期失效 |
| strategic | factor_design_principle | 因子设计原则 | 多因子组合前检查相关性 |
| strategic | risk_management_principle | 风险管理原则 | 新因子需完整周期验证 |
| tactical | factor_performance | 因子表现结论 | Bias_20 震荡市 IC 稳定 |
| tactical | strategy_optimization | 策略优化结论 | 合约最优持仓周期 4H |
| tactical | param_sensitivity | 参数敏感性结论 | 动量周期 5-20 敏感度低 |
| operational | successful_experiment | 成功实验 | 某次回测夏普 2.1 |
| operational | failed_experiment | 失败实验 | 某策略震荡市大幅回撤 |
| operational | research_observation | 研究观察 | BTC 主导率与山寨动量关系 |

### B. 置信度评估参考

| 置信度范围 | 含义 | 来源 |
|-----------|------|------|
| 0.0 - 0.3 | 初步假设 | 单次观察、直觉推测 |
| 0.3 - 0.5 | 待验证结论 | 单次回测、初步分析 |
| 0.5 - 0.7 | 较可信结论 | 多次回测、交叉验证 |
| 0.7 - 0.9 | 高可信结论 | 实盘验证、长期跟踪 |
| 0.9 - 1.0 | 经典规律 | 广泛验证、业界共识 |

### C. 相关文档

- [添加业务域指南](tasks/add-domain.md)
- [添加 MCP 工具指南](tasks/add-mcp-tool.md)
- [架构参考](reference.md)
