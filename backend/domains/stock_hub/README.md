# Stock Hub — A-Share Factor Research

This domain provides A-share (China mainland stock market) factor browsing, backtesting, and IC/ICIR analysis.

## Prerequisites

This module requires the **proprietary stock selection framework** which is NOT included in the open-source release.

### Required Components

1. **Stock Selection Framework** (`select-stock-pro`)
   - Contains factor library files (因子库/, 截面因子库/)
   - Contains backtest engine and analysis tools

2. **Fuel Python Environment** (Anaconda/Miniconda)
   - Python 3.11 with pandas, numba, and framework dependencies
   - Installed separately from the platform's own Python environment

3. **Market Data** (数据中心)
   - Historical A-share market data in the format expected by the framework

### Configuration

Set the following environment variables (or edit `config.py` defaults):

| Variable | Description | Example |
|----------|-------------|---------|
| `STOCK_FRAMEWORK_PATH` | Path to stock selection framework | `D:\select-stock-pro_v2.0.0` |
| `FUEL_PYTHON_PATH` | Path to Fuel Python interpreter | `C:\ProgramData\anaconda3\envs\Fuel\python.exe` |
| `DATA_CENTER_PATH` | Path to market data directory | `D:\shuju` |

### Without the Framework

If these components are not available, the Stock Hub pages will display a "Not Configured" message. All other platform features work normally.
