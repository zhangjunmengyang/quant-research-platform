"""Stock Hub 配置"""
import os
from pathlib import Path

# 选股框架路径
STOCK_FRAMEWORK_PATH = Path(os.environ.get(
    "STOCK_FRAMEWORK_PATH",
    r"D:\select-stock-pro_v2.0.0"
))

# Fuel Python 解释器路径
FUEL_PYTHON_PATH = Path(os.environ.get(
    "FUEL_PYTHON_PATH",
    r"C:\ProgramData\anaconda3\envs\Fuel\python.exe"
))

# 数据中心路径
DATA_CENTER_PATH = Path(os.environ.get(
    "DATA_CENTER_PATH",
    r"D:\shuju"
))

# 因子库目录
FACTOR_LIB_PATH = STOCK_FRAMEWORK_PATH / "因子库"
SECTION_FACTOR_LIB_PATH = STOCK_FRAMEWORK_PATH / "截面因子库"

# 缓存目录
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# 因子元数据缓存文件
FACTOR_META_CACHE = CACHE_DIR / "factor_meta.json"

# MCP服务器端口
MCP_SERVER_PORT = int(os.environ.get("STOCK_HUB_MCP_PORT", "6795"))

# 子进程超时（秒）
BACKTEST_TIMEOUT = int(os.environ.get("STOCK_HUB_BACKTEST_TIMEOUT", "1800"))  # 30分钟
ANALYSIS_TIMEOUT = int(os.environ.get("STOCK_HUB_ANALYSIS_TIMEOUT", "600"))  # 10分钟


def is_stock_framework_available() -> bool:
    """Check if the proprietary stock framework is installed and accessible."""
    return (
        STOCK_FRAMEWORK_PATH.exists()
        and FUEL_PYTHON_PATH.exists()
        and (FACTOR_LIB_PATH.exists() or SECTION_FACTOR_LIB_PATH.exists())
    )
