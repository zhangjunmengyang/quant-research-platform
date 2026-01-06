"""
数据模型定义

定义因子知识库的核心数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List


class FactorType:
    """因子类型枚举常量"""
    TIME_SERIES = "time_series"  # 时序因子
    CROSS_SECTION = "cross_section"  # 截面因子


@dataclass
class Factor:
    """
    因子数据类

    表示一个量化因子的完整信息，包括元数据、代码、评分和状态。

    Attributes:
        filename: 因子文件名（主键）
        factor_type: 因子类型（time_series/cross_section）
        uuid: 因子唯一标识符
        style: 因子风格分类（如动量、反转、波动率等）
        formula: 核心公式描述
        input_data: 输入数据字段
        value_range: 因子值域
        description: 因子刻画特征描述
        analysis: 因子详细分析
        code_path: 代码文件路径
        code_content: 完整代码内容
        llm_score: LLM 评分 (0-5)
        ic: IC 值
        rank_ic: RankIC 值
        verified: 是否已人工验证
        verify_note: 验证备注
        created_at: 创建时间
        updated_at: 更新时间
    """
    filename: str
    factor_type: str = FactorType.TIME_SERIES  # 默认为时序因子
    uuid: str = ""
    style: str = ""
    formula: str = ""
    input_data: str = ""
    value_range: str = ""
    description: str = ""
    analysis: str = ""
    code_path: str = ""
    code_content: str = ""
    llm_score: Optional[float] = None
    ic: Optional[float] = None
    rank_ic: Optional[float] = None
    verified: int = 0
    verify_note: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 新增回测指标
    backtest_sharpe: Optional[float] = None
    backtest_ic: Optional[float] = None
    backtest_ir: Optional[float] = None
    turnover: Optional[float] = None
    decay: Optional[int] = None  # IC半衰期（周期数）
    # 新增分类标签
    market_regime: str = ""  # 牛市/熊市/震荡
    best_holding_period: Optional[int] = None  # 最佳持仓周期（小时）
    tags: str = ""  # 逗号分隔的标签列表
    # 新增代码质量
    code_complexity: Optional[float] = None  # 代码复杂度评分
    last_backtest_date: Optional[str] = None  # 最后回测日期
    # 排除状态
    excluded: int = 0  # 是否被排除
    exclude_reason: str = ""  # 排除原因

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'filename': self.filename,
            'factor_type': self.factor_type,
            'uuid': self.uuid,
            'style': self.style,
            'formula': self.formula,
            'input_data': self.input_data,
            'value_range': self.value_range,
            'description': self.description,
            'analysis': self.analysis,
            'code_path': self.code_path,
            'code_content': self.code_content,
            'llm_score': self.llm_score,
            'ic': self.ic,
            'rank_ic': self.rank_ic,
            'verified': self.verified,
            'verify_note': self.verify_note,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            # 新增字段
            'backtest_sharpe': self.backtest_sharpe,
            'backtest_ic': self.backtest_ic,
            'backtest_ir': self.backtest_ir,
            'turnover': self.turnover,
            'decay': self.decay,
            'market_regime': self.market_regime,
            'best_holding_period': self.best_holding_period,
            'tags': self.tags,
            'code_complexity': self.code_complexity,
            'last_backtest_date': self.last_backtest_date,
            'excluded': self.excluded,
            'exclude_reason': self.exclude_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Factor':
        """从字典创建因子实例"""
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)

    @property
    def is_verified(self) -> bool:
        """是否已验证"""
        return bool(self.verified)

    @property
    def is_excluded(self) -> bool:
        """是否被排除"""
        return bool(self.excluded)

    @property
    def is_time_series(self) -> bool:
        """是否为时序因子"""
        return self.factor_type == FactorType.TIME_SERIES

    @property
    def is_cross_section(self) -> bool:
        """是否为截面因子"""
        return self.factor_type == FactorType.CROSS_SECTION

    @property
    def has_score(self) -> bool:
        """是否有评分"""
        return self.llm_score is not None

    @property
    def styles_list(self) -> List[str]:
        """获取风格列表（逗号分隔的风格字符串转为列表）"""
        if not self.style:
            return []
        return [s.strip() for s in self.style.split(',') if s.strip()]

    @property
    def tags_list(self) -> List[str]:
        """获取标签列表（逗号分隔的字符串转为列表）"""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def set_tags(self, tags: List[str]):
        """设置标签列表"""
        self.tags = ','.join(tags)

    def add_tag(self, tag: str):
        """添加标签"""
        tags = self.tags_list
        if tag not in tags:
            tags.append(tag)
            self.set_tags(tags)

    def remove_tag(self, tag: str):
        """移除标签"""
        tags = self.tags_list
        if tag in tags:
            tags.remove(tag)
            self.set_tags(tags)

    @property
    def has_backtest(self) -> bool:
        """是否有回测数据"""
        return self.backtest_sharpe is not None or self.backtest_ic is not None

    @property
    def icir(self) -> Optional[float]:
        """计算ICIR（如果有数据）"""
        if self.backtest_ic and self.backtest_ir:
            return self.backtest_ir
        return None


@dataclass
class FactorStats:
    """
    因子库统计信息

    包含因子库的各类统计数据。
    """
    total: int = 0
    scored: int = 0
    unscored: int = 0
    verified: int = 0
    score_distribution: Dict[str, int] = field(default_factory=dict)
    style_distribution: Dict[str, int] = field(default_factory=dict)
    input_field_distribution: Dict[str, int] = field(default_factory=dict)
    score_stats: Dict[str, float] = field(default_factory=dict)
    ic_stats: Dict[str, Any] = field(default_factory=dict)
    rank_ic_stats: Dict[str, Any] = field(default_factory=dict)
    time_distribution: Dict[str, int] = field(default_factory=dict)
    score_histogram: List[float] = field(default_factory=list)
