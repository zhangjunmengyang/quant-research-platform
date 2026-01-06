"""
数据层数据模型

定义数据层的核心数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

import pandas as pd


@dataclass
class DataConfig:
    """
    数据配置

    存储数据加载和处理所需的配置信息。

    Attributes:
        pre_data_path: 预处理数据路径
        start_date: 开始日期
        end_date: 结束日期
        black_list: 黑名单币种
        white_list: 白名单币种
        min_kline_num: 最小K线数量
        stable_symbols: 稳定币列表
    """
    pre_data_path: str
    start_date: str = ""
    end_date: str = ""
    black_list: List[str] = field(default_factory=list)
    white_list: List[str] = field(default_factory=list)
    min_kline_num: int = 168
    stable_symbols: List[str] = field(default_factory=lambda: [
        'BKRW', 'USDC', 'USDP', 'TUSD', 'BUSD', 'FDUSD', 'DAI',
        'EUR', 'GBP', 'USBP', 'SUSD', 'PAXG', 'AEUR', 'EURI'
    ])

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'pre_data_path': self.pre_data_path,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'black_list': self.black_list,
            'white_list': self.white_list,
            'min_kline_num': self.min_kline_num,
            'stable_symbols': self.stable_symbols,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataConfig':
        """从字典创建配置实例"""
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


@dataclass
class KlineData:
    """
    K线数据

    表示单条K线的完整数据。

    Attributes:
        symbol: 交易对
        candle_begin_time: K线开始时间
        open: 开盘价
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 成交量
        quote_volume: 成交额
        trade_num: 成交笔数
        taker_buy_base_asset_volume: 主动买入成交量
        taker_buy_quote_asset_volume: 主动买入成交额
        is_spot: 是否为现货
    """
    symbol: str
    candle_begin_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    quote_volume: float = 0.0
    trade_num: int = 0
    taker_buy_base_asset_volume: float = 0.0
    taker_buy_quote_asset_volume: float = 0.0
    is_spot: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'symbol': self.symbol,
            'candle_begin_time': self.candle_begin_time,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'quote_volume': self.quote_volume,
            'trade_num': self.trade_num,
            'taker_buy_base_asset_volume': self.taker_buy_base_asset_volume,
            'taker_buy_quote_asset_volume': self.taker_buy_quote_asset_volume,
            'is_spot': self.is_spot,
        }


@dataclass
class FactorResult:
    """
    因子计算结果

    存储单个因子在单个币种上的计算结果。

    Attributes:
        factor_name: 因子名称
        param: 因子参数
        symbol: 交易对
        data: 因子值序列 (index=candle_begin_time)
    """
    factor_name: str
    param: Any
    symbol: str
    data: pd.Series

    @property
    def column_name(self) -> str:
        """获取因子列名"""
        return f"{self.factor_name}_{self.param}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（不包含 data）"""
        return {
            'factor_name': self.factor_name,
            'param': self.param,
            'symbol': self.symbol,
            'column_name': self.column_name,
            'length': len(self.data) if self.data is not None else 0,
        }


@dataclass
class SymbolInfo:
    """
    币种信息

    Attributes:
        symbol: 交易对名称
        has_spot: 是否有现货
        has_swap: 是否有合约
        first_candle_time: 第一根K线时间
        last_candle_time: 最后一根K线时间
        kline_count: K线数量
    """
    symbol: str
    has_spot: bool = False
    has_swap: bool = False
    first_candle_time: Optional[datetime] = None
    last_candle_time: Optional[datetime] = None
    kline_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'symbol': self.symbol,
            'has_spot': self.has_spot,
            'has_swap': self.has_swap,
            'first_candle_time': self.first_candle_time,
            'last_candle_time': self.last_candle_time,
            'kline_count': self.kline_count,
        }


@dataclass
class FactorInfo:
    """
    因子信息

    Attributes:
        name: 因子名称
        is_cross: 是否为截面因子
        has_extra_data: 是否需要额外数据
        extra_data_dict: 额外数据配置
    """
    name: str
    is_cross: bool = False
    has_extra_data: bool = False
    extra_data_dict: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'is_cross': self.is_cross,
            'has_extra_data': self.has_extra_data,
            'extra_data_dict': self.extra_data_dict,
        }
