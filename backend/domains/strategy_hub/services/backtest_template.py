"""
回测配置模板服务

提供回测配置模板的存储、加载和管理功能。
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from domains.mcp_core.paths import get_data_dir

logger = logging.getLogger(__name__)


@dataclass
class BacktestTemplate:
    """回测配置模板"""
    id: str  # 模板ID
    name: str  # 模板名称
    description: str = ""  # 模板描述
    category: str = "custom"  # 模板分类: preset(预设) / custom(自定义)

    # 策略配置
    strategy_list: List[Dict[str, Any]] = field(default_factory=list)

    # 回测参数
    leverage: float = 1.0  # 杠杆倍数
    trade_type: str = "swap"  # 交易类型
    account_type: str = "统一账户"  # 账户类型
    initial_usdt: float = 10000  # 初始资金

    # 过滤配置
    black_list: List[str] = field(default_factory=list)  # 黑名单
    white_list: List[str] = field(default_factory=list)  # 白名单
    min_kline_num: int = 168  # 最少K线数

    # 元数据
    tags: List[str] = field(default_factory=list)  # 标签
    created_at: str = ""  # 创建时间
    updated_at: str = ""  # 更新时间
    author: str = ""  # 创建者

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BacktestTemplate":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class BacktestTemplateService:
    """
    回测配置模板服务

    提供模板的CRUD操作和预设模板。
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        初始化模板服务

        Args:
            templates_dir: 模板存储目录
        """
        self.templates_dir = templates_dir or (get_data_dir() / "templates")
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # 预设模板
        self._preset_templates: Dict[str, BacktestTemplate] = {}
        self._init_preset_templates()

        logger.info(f"BacktestTemplateService 初始化，模板目录: {self.templates_dir}")

    def _init_preset_templates(self):
        """初始化预设模板"""
        # 动量策略模板
        self._preset_templates["momentum_basic"] = BacktestTemplate(
            id="momentum_basic",
            name="基础动量策略",
            description="基于多周期动量因子的选币策略，适合趋势行情",
            category="preset",
            strategy_list=[
                {
                    "strategy_name": "动量多空",
                    "offset_list": [0],
                    "long_select_coin_num": 5,
                    "short_select_coin_num": 5,
                    "factor_list": [
                        ["Bias", 1, [5, 10, 20]],
                        ["涨跌幅", 1, [24, 48, 72]],
                    ],
                    "filter_list": [],
                }
            ],
            leverage=1.0,
            trade_type="swap",
            initial_usdt=10000,
            min_kline_num=168,
            tags=["动量", "趋势", "基础"],
            author="system",
        )

        # 反转策略模板
        self._preset_templates["reversal_basic"] = BacktestTemplate(
            id="reversal_basic",
            name="基础反转策略",
            description="基于超买超卖指标的反转策略，适合震荡行情",
            category="preset",
            strategy_list=[
                {
                    "strategy_name": "反转多空",
                    "offset_list": [0],
                    "long_select_coin_num": 5,
                    "short_select_coin_num": 5,
                    "factor_list": [
                        ["Rsi", -1, [14, 21]],
                        ["Cci", -1, [20]],
                    ],
                    "filter_list": [],
                }
            ],
            leverage=1.0,
            trade_type="swap",
            initial_usdt=10000,
            min_kline_num=168,
            tags=["反转", "震荡", "基础"],
            author="system",
        )

        # 波动率策略模板
        self._preset_templates["volatility_basic"] = BacktestTemplate(
            id="volatility_basic",
            name="基础波动率策略",
            description="基于波动率因子的策略，低波动做多高波动做空",
            category="preset",
            strategy_list=[
                {
                    "strategy_name": "波动率多空",
                    "offset_list": [0],
                    "long_select_coin_num": 5,
                    "short_select_coin_num": 5,
                    "factor_list": [
                        ["Atr", -1, [14]],
                        ["波动率因子", -1, [24]],
                    ],
                    "filter_list": [],
                }
            ],
            leverage=1.0,
            trade_type="swap",
            initial_usdt=10000,
            min_kline_num=168,
            tags=["波动率", "低波做多", "基础"],
            author="system",
        )

        # 成交量策略模板
        self._preset_templates["volume_basic"] = BacktestTemplate(
            id="volume_basic",
            name="基础成交量策略",
            description="基于成交量相关因子的策略",
            category="preset",
            strategy_list=[
                {
                    "strategy_name": "成交量多空",
                    "offset_list": [0],
                    "long_select_coin_num": 5,
                    "short_select_coin_num": 5,
                    "factor_list": [
                        ["Obv", 1, [20]],
                        ["Vpt", 1, [10]],
                    ],
                    "filter_list": [],
                }
            ],
            leverage=1.0,
            trade_type="swap",
            initial_usdt=10000,
            min_kline_num=168,
            tags=["成交量", "量价", "基础"],
            author="system",
        )

        # 多因子组合模板
        self._preset_templates["multi_factor"] = BacktestTemplate(
            id="multi_factor",
            name="多因子组合策略",
            description="综合多类型因子的组合策略",
            category="preset",
            strategy_list=[
                {
                    "strategy_name": "多因子组合",
                    "offset_list": [0],
                    "long_select_coin_num": 10,
                    "short_select_coin_num": 10,
                    "factor_list": [
                        ["Bias", 1, [20]],
                        ["Rsi", -1, [14]],
                        ["Atr", -1, [14]],
                        ["Obv", 1, [20]],
                    ],
                    "filter_list": [],
                }
            ],
            leverage=1.0,
            trade_type="swap",
            initial_usdt=10000,
            min_kline_num=168,
            tags=["多因子", "组合", "进阶"],
            author="system",
        )

        # 高杠杆模板
        self._preset_templates["high_leverage"] = BacktestTemplate(
            id="high_leverage",
            name="高杠杆策略模板",
            description="2倍杠杆的策略模板，注意风险控制",
            category="preset",
            strategy_list=[
                {
                    "strategy_name": "高杠杆动量",
                    "offset_list": [0],
                    "long_select_coin_num": 3,
                    "short_select_coin_num": 3,
                    "factor_list": [
                        ["Bias", 1, [10, 20]],
                    ],
                    "filter_list": [],
                }
            ],
            leverage=2.0,
            trade_type="swap",
            initial_usdt=10000,
            min_kline_num=168,
            tags=["高杠杆", "高风险"],
            author="system",
        )

        # 纯多头模板
        self._preset_templates["long_only"] = BacktestTemplate(
            id="long_only",
            name="纯多头策略模板",
            description="只做多的策略模板",
            category="preset",
            strategy_list=[
                {
                    "strategy_name": "纯多头",
                    "offset_list": [0],
                    "long_select_coin_num": 10,
                    "short_select_coin_num": 0,
                    "factor_list": [
                        ["涨跌幅", 1, [24, 48]],
                    ],
                    "filter_list": [],
                }
            ],
            leverage=1.0,
            trade_type="swap",
            initial_usdt=10000,
            min_kline_num=168,
            tags=["纯多头", "单边"],
            author="system",
        )

        # 现货模板
        self._preset_templates["spot_basic"] = BacktestTemplate(
            id="spot_basic",
            name="现货策略模板",
            description="现货交易策略模板",
            category="preset",
            strategy_list=[
                {
                    "strategy_name": "现货策略",
                    "offset_list": [0],
                    "long_select_coin_num": 10,
                    "short_select_coin_num": 0,
                    "factor_list": [
                        ["Bias", 1, [20]],
                    ],
                    "filter_list": [],
                }
            ],
            leverage=1.0,
            trade_type="spot",
            initial_usdt=10000,
            min_kline_num=168,
            tags=["现货", "无杠杆"],
            author="system",
        )

    def get(self, template_id: str) -> Optional[BacktestTemplate]:
        """
        获取模板

        Args:
            template_id: 模板ID

        Returns:
            模板对象，不存在返回None
        """
        # 先查预设模板
        if template_id in self._preset_templates:
            return self._preset_templates[template_id]

        # 再查自定义模板
        template_file = self.templates_dir / f"{template_id}.json"
        if template_file.exists():
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return BacktestTemplate.from_dict(data)
            except Exception as e:
                logger.error(f"加载模板失败 {template_id}: {e}")
        return None

    def list_all(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[BacktestTemplate]:
        """
        列出所有模板

        Args:
            category: 按分类筛选
            tags: 按标签筛选

        Returns:
            模板列表
        """
        templates = []

        # 添加预设模板
        for template in self._preset_templates.values():
            if category and template.category != category:
                continue
            if tags and not any(t in template.tags for t in tags):
                continue
            templates.append(template)

        # 添加自定义模板
        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                template = BacktestTemplate.from_dict(data)
                if category and template.category != category:
                    continue
                if tags and not any(t in template.tags for t in tags):
                    continue
                templates.append(template)
            except Exception as e:
                logger.error(f"加载模板失败 {template_file}: {e}")

        return templates

    def create(self, template: BacktestTemplate) -> bool:
        """
        创建自定义模板

        Args:
            template: 模板对象

        Returns:
            是否创建成功
        """
        if template.id in self._preset_templates:
            logger.error(f"不能覆盖预设模板: {template.id}")
            return False

        now = datetime.now().isoformat()
        template.created_at = now
        template.updated_at = now
        template.category = "custom"

        template_file = self.templates_dir / f"{template.id}.json"
        try:
            with open(template_file, "w", encoding="utf-8") as f:
                json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"创建模板: {template.id}")
            return True
        except Exception as e:
            logger.error(f"创建模板失败 {template.id}: {e}")
            return False

    def update(self, template: BacktestTemplate) -> bool:
        """
        更新自定义模板

        Args:
            template: 模板对象

        Returns:
            是否更新成功
        """
        if template.id in self._preset_templates:
            logger.error(f"不能修改预设模板: {template.id}")
            return False

        template_file = self.templates_dir / f"{template.id}.json"
        if not template_file.exists():
            logger.error(f"模板不存在: {template.id}")
            return False

        template.updated_at = datetime.now().isoformat()

        try:
            with open(template_file, "w", encoding="utf-8") as f:
                json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"更新模板: {template.id}")
            return True
        except Exception as e:
            logger.error(f"更新模板失败 {template.id}: {e}")
            return False

    def delete(self, template_id: str) -> bool:
        """
        删除自定义模板

        Args:
            template_id: 模板ID

        Returns:
            是否删除成功
        """
        if template_id in self._preset_templates:
            logger.error(f"不能删除预设模板: {template_id}")
            return False

        template_file = self.templates_dir / f"{template_id}.json"
        if not template_file.exists():
            logger.error(f"模板不存在: {template_id}")
            return False

        try:
            template_file.unlink()
            logger.info(f"删除模板: {template_id}")
            return True
        except Exception as e:
            logger.error(f"删除模板失败 {template_id}: {e}")
            return False

    def clone(self, source_id: str, new_id: str, new_name: str) -> Optional[BacktestTemplate]:
        """
        克隆模板

        Args:
            source_id: 源模板ID
            new_id: 新模板ID
            new_name: 新模板名称

        Returns:
            新模板对象
        """
        source = self.get(source_id)
        if not source:
            logger.error(f"源模板不存在: {source_id}")
            return None

        # 创建新模板
        new_template = BacktestTemplate(
            id=new_id,
            name=new_name,
            description=f"从 {source.name} 克隆",
            category="custom",
            strategy_list=source.strategy_list.copy(),
            leverage=source.leverage,
            trade_type=source.trade_type,
            account_type=source.account_type,
            initial_usdt=source.initial_usdt,
            black_list=source.black_list.copy(),
            white_list=source.white_list.copy(),
            min_kline_num=source.min_kline_num,
            tags=source.tags.copy(),
        )

        if self.create(new_template):
            return new_template
        return None

    def get_by_tag(self, tag: str) -> List[BacktestTemplate]:
        """按标签获取模板"""
        return self.list_all(tags=[tag])

    def get_preset_templates(self) -> List[BacktestTemplate]:
        """获取所有预设模板"""
        return list(self._preset_templates.values())

    def get_custom_templates(self) -> List[BacktestTemplate]:
        """获取所有自定义模板"""
        return self.list_all(category="custom")

    def get_categories(self) -> List[str]:
        """获取所有分类"""
        categories = {"preset", "custom"}
        for template in self.list_all():
            categories.add(template.category)
        return sorted(list(categories))

    def get_all_tags(self) -> List[str]:
        """获取所有标签"""
        tags = set()
        for template in self.list_all():
            tags.update(template.tags)
        return sorted(list(tags))


# 单例实例
_template_service: Optional[BacktestTemplateService] = None


def get_backtest_template_service() -> BacktestTemplateService:
    """获取模板服务单例"""
    global _template_service
    if _template_service is None:
        _template_service = BacktestTemplateService()
    return _template_service
