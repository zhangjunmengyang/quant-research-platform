"""
数据层配置加载器

支持从配置文件加载数据层相关配置。
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from .models import DataConfig
from domains.mcp_core.paths import get_project_root, get_config_dir, get_factors_dir, get_sections_dir


class DataHubConfig:
    """
    数据层配置加载器

    负责加载数据层相关配置，包括回测配置和数据源配置。
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置加载器

        Args:
            config_dir: 配置文件目录，默认为项目根目录下的 config/
        """
        if config_dir is None:
            config_dir = get_config_dir()
        self.config_dir = Path(config_dir)
        self.project_root = get_project_root()

        # 缓存
        self._data_config: Optional[DataConfig] = None
        self._backtest_config_cache: Optional[Dict[str, Any]] = None

    def load_backtest_config(self, reload: bool = False) -> Dict[str, Any]:
        """
        加载回测配置

        从 config/backtest_config.py 读取配置变量。
        使用 exec 直接执行配置文件，避免导入依赖问题。

        Args:
            reload: 是否强制重新加载

        Returns:
            回测配置字典
        """
        if self._backtest_config_cache is not None and not reload:
            return self._backtest_config_cache

        config_file = self.config_dir / "backtest_config.py"

        if not config_file.exists():
            self._backtest_config_cache = {}
            return self._backtest_config_cache

        # 使用 exec 执行配置文件，提取需要的变量
        # 这样可以避免 import 带来的依赖问题
        config_vars = {}
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 创建一个受限的执行环境
            exec_globals = {
                '__builtins__': {
                    'Path': Path,
                    'len': len,
                    'print': lambda *args, **kwargs: None,  # 禁止打印
                    'exit': lambda *args, **kwargs: None,   # 禁止退出
                },
                'os': os,
                'Path': Path,
            }

            # 执行配置文件
            exec(content, exec_globals, config_vars)

        except Exception as e:
            # 如果 exec 失败，尝试直接解析关键变量
            config_vars = self._parse_config_file(config_file)

        self._backtest_config_cache = {
            'pre_data_path': config_vars.get('pre_data_path', ''),
            'start_date': config_vars.get('start_date', ''),
            'end_date': config_vars.get('end_date', ''),
            'black_list': config_vars.get('black_list', []),
            'white_list': config_vars.get('white_list', []),
            'min_kline_num': config_vars.get('min_kline_num', 168),
            'stable_symbol': config_vars.get('stable_symbol', []),
            'spot_path': config_vars.get('spot_path', None),
            'swap_path': config_vars.get('swap_path', None),
            'data_source_dict': config_vars.get('data_source_dict', {}),
        }

        return self._backtest_config_cache

    def _parse_config_file(self, config_file: Path) -> Dict[str, Any]:
        """
        备用方法：直接解析配置文件中的关键变量

        Args:
            config_file: 配置文件路径

        Returns:
            解析出的配置字典
        """
        import re

        result = {}

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析 pre_data_path
            match = re.search(r"pre_data_path\s*=\s*['\"]([^'\"]+)['\"]", content)
            if match:
                result['pre_data_path'] = match.group(1)

            # 解析 start_date
            match = re.search(r"start_date\s*=\s*['\"]([^'\"]+)['\"]", content)
            if match:
                result['start_date'] = match.group(1)

            # 解析 end_date
            match = re.search(r"end_date\s*=\s*['\"]([^'\"]+)['\"]", content)
            if match:
                result['end_date'] = match.group(1)

            # 解析 min_kline_num
            match = re.search(r"min_kline_num\s*=\s*(\d+)", content)
            if match:
                result['min_kline_num'] = int(match.group(1))

            # 解析 black_list 和 white_list (简单解析空列表)
            result['black_list'] = []
            result['white_list'] = []

            # 解析 stable_symbol
            match = re.search(r"stable_symbol\s*=\s*\[([^\]]*)\]", content)
            if match:
                items = re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))
                result['stable_symbol'] = items

        except Exception:
            pass

        return result

    def get_data_config(self, reload: bool = False) -> DataConfig:
        """
        获取数据配置

        将回测配置转换为 DataConfig 对象。

        Args:
            reload: 是否强制重新加载

        Returns:
            DataConfig 实例
        """
        if self._data_config is not None and not reload:
            return self._data_config

        backtest_cfg = self.load_backtest_config(reload)

        self._data_config = DataConfig(
            pre_data_path=backtest_cfg.get('pre_data_path', ''),
            start_date=backtest_cfg.get('start_date', ''),
            end_date=backtest_cfg.get('end_date', ''),
            black_list=backtest_cfg.get('black_list', []),
            white_list=backtest_cfg.get('white_list', []),
            min_kline_num=backtest_cfg.get('min_kline_num', 168),
            stable_symbols=backtest_cfg.get('stable_symbol', []),
        )

        return self._data_config

    @property
    def spot_path(self) -> Optional[Path]:
        """获取现货数据路径"""
        cfg = self.load_backtest_config()
        path = cfg.get('spot_path')
        return Path(path) if path else None

    @property
    def swap_path(self) -> Optional[Path]:
        """获取合约数据路径"""
        cfg = self.load_backtest_config()
        path = cfg.get('swap_path')
        return Path(path) if path else None

    @property
    def factors_dir(self) -> Path:
        """获取因子代码目录"""
        return get_factors_dir()

    @property
    def sections_dir(self) -> Path:
        """获取截面因子目录"""
        return get_sections_dir()


# 单例实例
_data_hub_config: Optional[DataHubConfig] = None


def get_data_hub_config() -> DataHubConfig:
    """获取数据层配置加载器单例"""
    global _data_hub_config
    if _data_hub_config is None:
        _data_hub_config = DataHubConfig()
    return _data_hub_config


def reset_data_hub_config():
    """重置配置加载器单例（用于测试）"""
    global _data_hub_config
    _data_hub_config = None
