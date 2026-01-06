"""
回测引擎配置桥接

engine/core 是外部引入的回测引擎，它使用根目录 config 作为配置入口。
此文件提供向后兼容，将实际配置从 config/backtest_config.py 导出。

注意: engine/core 核心逻辑禁止修改，因此需要保留此桥接文件。
"""

from config.backtest_config import *
