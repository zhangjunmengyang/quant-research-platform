"""
数据模型定义

定义因子知识库的核心数据结构。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class FactorType:
    """因子类型枚举常量"""
    TIME_SERIES = "time_series"  # 时序因子
    CROSS_SECTION = "cross_section"  # 截面因子


class VerificationStatus:
    """验证状态枚举常量"""
    UNVERIFIED = 0  # 未验证
    PASSED = 1  # 通过
    FAILED = 2  # 废弃（失败研究）


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
        verification_status: 验证状态 (0=未验证, 1=通过, 2=废弃)
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
    llm_score: float | None = None
    ic: float | None = None
    rank_ic: float | None = None
    verification_status: int = VerificationStatus.UNVERIFIED  # 0=未验证, 1=通过, 2=废弃
    verify_note: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # 新增回测指标
    backtest_sharpe: float | None = None
    backtest_ic: float | None = None
    backtest_ir: float | None = None
    turnover: float | None = None
    decay: int | None = None  # IC半衰期（周期数）
    # 新增分类标签
    market_regime: str = ""  # 牛市/熊市/震荡
    best_holding_period: int | None = None  # 最佳持仓周期（小时）
    tags: str = ""  # 逗号分隔的标签列表
    # 新增代码质量
    code_complexity: float | None = None  # 代码复杂度评分
    last_backtest_date: str | None = None  # 最后回测日期
    # 排除状态
    excluded: int = 0  # 是否被排除
    exclude_reason: str = ""  # 排除原因
    # 参数分析结果 (JSON 字符串)
    param_analysis: str = ""

    def to_dict(self) -> dict[str, Any]:
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
            'verification_status': self.verification_status,
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
            'param_analysis': self.param_analysis,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Factor':
        """从字典创建因子实例"""
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)

    @property
    def is_passed(self) -> bool:
        """是否验证通过"""
        return self.verification_status == VerificationStatus.PASSED

    @property
    def is_failed(self) -> bool:
        """是否废弃（失败研究）"""
        return self.verification_status == VerificationStatus.FAILED

    @property
    def is_unverified(self) -> bool:
        """是否未验证"""
        return self.verification_status == VerificationStatus.UNVERIFIED

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
    def styles_list(self) -> list[str]:
        """获取风格列表（逗号分隔的风格字符串转为列表）"""
        if not self.style:
            return []
        return [s.strip() for s in self.style.split(',') if s.strip()]

    @property
    def tags_list(self) -> list[str]:
        """获取标签列表（逗号分隔的字符串转为列表）"""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def set_tags(self, tags: list[str]):
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
    def icir(self) -> float | None:
        """计算ICIR（如果有数据）"""
        if self.backtest_ic and self.backtest_ir:
            return self.backtest_ir
        return None

    @property
    def has_param_analysis(self) -> bool:
        """是否有参数分析数据"""
        return bool(self.param_analysis)

    def get_param_analysis(self) -> dict[str, Any] | None:
        """获取参数分析数据（解析 JSON）"""
        if not self.param_analysis:
            return None
        try:
            return json.loads(self.param_analysis)
        except json.JSONDecodeError:
            return None

    def set_param_analysis(self, data: dict[str, Any]):
        """设置参数分析数据"""
        self.param_analysis = json.dumps(data, ensure_ascii=False)


@dataclass
class FactorStats:
    """
    因子库统计信息

    包含因子库的各类统计数据。
    """
    total: int = 0
    scored: int = 0
    unscored: int = 0
    passed: int = 0  # 验证通过数量
    failed: int = 0  # 废弃（失败研究）数量
    score_distribution: dict[str, int] = field(default_factory=dict)
    style_distribution: dict[str, int] = field(default_factory=dict)
    input_field_distribution: dict[str, int] = field(default_factory=dict)
    score_stats: dict[str, float] = field(default_factory=dict)
    ic_stats: dict[str, Any] = field(default_factory=dict)
    rank_ic_stats: dict[str, Any] = field(default_factory=dict)
    time_distribution: dict[str, int] = field(default_factory=dict)
    score_histogram: list[float] = field(default_factory=list)
