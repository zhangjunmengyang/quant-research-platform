"""Stock Hub 分析服务。

提供因子分析、双因子分析等能力。
安全约束:
- 使用路径白名单，禁止跨出运行缓存目录
- 长任务由 StockAnalysisRunner 异步调度
"""

import ast
import logging
import os
import subprocess
import time
from pathlib import Path

from domains.stock_hub.config import (
    ANALYSIS_TIMEOUT,
    BACKTEST_TIMEOUT,
    DATA_CENTER_PATH,
    get_framework_path,
    get_fuel_python,
)

logger = logging.getLogger(__name__)


def _is_safe_literal(value: object) -> bool:
    """递归校验 factor_config 中允许的字面量类型。"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_is_safe_literal(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_safe_literal(item)
            for key, item in value.items()
        )
    return False


def _normalize_factor_config(raw_config: str, factor_name: str) -> str:
    """将用户输入的因子配置解析为安全、规范的 Python 字面量字符串。"""
    config_text = raw_config.strip()
    if not config_text:
        return repr((factor_name, True, "", 1))

    try:
        parsed = ast.literal_eval(config_text)
    except (SyntaxError, ValueError) as exc:
        raise ValueError("因子配置格式错误，应为 Python 字面量元组") from exc

    if not isinstance(parsed, (list, tuple)) or len(parsed) != 4:
        raise ValueError("因子配置必须是长度为 4 的元组")

    config_factor_name, is_ascending, parameter, weight = parsed
    if not isinstance(config_factor_name, str) or not config_factor_name:
        raise ValueError("因子配置中的因子名必须是非空字符串")
    if config_factor_name != factor_name:
        raise ValueError("因子配置中的因子名必须与当前选择的因子一致")
    if not isinstance(is_ascending, bool):
        raise ValueError("因子配置中的排序方向必须是布尔值")
    if not _is_safe_literal(parameter):
        raise ValueError("因子配置中的参数仅支持安全字面量")
    if not isinstance(weight, (int, float)):
        raise ValueError("因子配置中的权重必须是数值")

    return repr((config_factor_name, is_ascending, parameter, weight))


def _validate_data_path(path: Path, framework: Path) -> bool:
    """校验数据路径在运行缓存白名单内。"""
    allowed_root = framework / "data" / "运行缓存"
    try:
        path.resolve().relative_to(allowed_root.resolve())
        return True
    except ValueError:
        return False


def _get_backtest_dir(
    framework: Path, backtest_name: str | None = None
) -> Path | None:
    """获取回测数据目录。"""
    cache_root = framework / "data" / "运行缓存"
    if not cache_root.is_dir():
        return None

    if backtest_name:
        target = cache_root / backtest_name
        if target.is_dir() and _validate_data_path(target, framework):
            return target
        return None

    # 默认: 优先使用 factor_hub（因子库统一回测目录）
    factor_hub_dir = cache_root / "factor_hub"
    if factor_hub_dir.is_dir() and list(factor_hub_dir.glob("factor_*.pkl")):
        return factor_hub_dir

    # 回退: 从框架 config.py 读取
    config_file = framework / "config.py"
    if config_file.exists():
        try:
            content = config_file.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines():
                if "backtest_name" in line and "=" in line:
                    val = line.split("=", 1)[1].strip().strip("'\"")
                    if val:
                        target = cache_root / val
                        if target.is_dir() and _validate_data_path(target, framework):
                            return target
        except Exception:
            pass

    return None


def _sanitize_analysis_result(result: dict) -> dict:
    """移除不应对外暴露的路径字段。"""
    cleaned = dict(result)
    cleaned.pop("html_path", None)
    return cleaned


class StockAnalysisService:
    """分析服务。"""

    def list_available_backtests(self) -> list[dict]:
        """列出所有可用的回测数据源。"""
        framework = get_framework_path()
        if not framework:
            return []

        cache_root = framework / "data" / "运行缓存"
        if not cache_root.is_dir():
            return []

        results = []
        for d in sorted(cache_root.iterdir()):
            if not d.is_dir():
                continue
            pkl_files = list(d.glob("factor_*.pkl"))
            if not pkl_files:
                continue
            latest_mtime = max(f.stat().st_mtime for f in pkl_files)
            from datetime import datetime

            results.append(
                {
                    "name": d.name,
                    "factor_count": len(pkl_files),
                    "modified_time": datetime.fromtimestamp(latest_mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                }
            )
        return results

    def list_cached_factors(
        self, backtest_name: str | None = None
    ) -> list[dict]:
        """列出回测缓存中的因子。"""
        framework = get_framework_path()
        if not framework:
            return []

        bt_dir = _get_backtest_dir(framework, backtest_name)
        if not bt_dir:
            return []

        results = []
        for pkl in sorted(bt_dir.glob("factor_*.pkl")):
            name = pkl.stem
            display = name.replace("factor_", "", 1) if name.startswith("factor_") else name
            results.append(
                {
                    "name": name,
                    "display_name": display,
                    "file_size": pkl.stat().st_size,
                }
            )
        return results

    def run_enhanced_analysis(
        self,
        factor_name: str,
        period_offset_list: list[str],
        rebalance_time: str = "0955",
        bins: int = 10,
        backtest_name: str | None = None,
    ) -> dict:
        """执行增强单因子分析。

        通过子进程调用 Fuel Python 执行分析脚本。
        """
        framework = get_framework_path()
        fuel_python = get_fuel_python()
        if not framework or not fuel_python:
            return {"error": "stock_hub 未配置"}

        script = framework / "run_enhanced_analysis.py"
        if not script.exists():
            return {"error": "分析脚本不存在"}

        bt_dir = _get_backtest_dir(framework, backtest_name)
        if not bt_dir:
            return {"error": f"回测数据不存在: {backtest_name or '默认'}"}

        import json

        args = [
            str(fuel_python),
            str(script),
            "--factor", factor_name,
            "--periods", json.dumps(period_offset_list),
            "--time", rebalance_time,
            "--bins", str(bins),
            "--cache-dir", str(bt_dir),
            "--output-format", "json",
        ]

        start = time.time()
        try:
            proc = subprocess.run(
                args,
                cwd=str(framework),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=ANALYSIS_TIMEOUT,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            elapsed = time.time() - start

            if proc.returncode != 0:
                logger.warning(
                    "分析失败 factor=%s rc=%d stderr=%s",
                    factor_name,
                    proc.returncode,
                    proc.stderr[:500],
                )
                return {"error": f"分析失败: {proc.stderr[:200]}"}

            result = _sanitize_analysis_result(json.loads(proc.stdout))
            result["elapsed_seconds"] = round(elapsed, 1)
            return result

        except subprocess.TimeoutExpired:
            return {"error": f"分析超时 ({ANALYSIS_TIMEOUT}s)"}
        except json.JSONDecodeError:
            return {"error": "分析输出格式错误"}
        except Exception as e:
            logger.exception("分析异常 factor=%s", factor_name)
            return {"error": str(e)}

    def run_dual_analysis(
        self,
        main_factor: str,
        sub_factor: str,
        period_offset_list: list[str],
        rebalance_time: str = "0955",
        bins: int = 5,
        backtest_name: str | None = None,
    ) -> dict:
        """执行双因子分析。"""
        framework = get_framework_path()
        fuel_python = get_fuel_python()
        if not framework or not fuel_python:
            return {"error": "stock_hub 未配置"}

        if main_factor == sub_factor:
            return {"error": "主因子和次因子不能相同"}

        script = framework / "run_dual_analysis.py"
        if not script.exists():
            return {"error": "双因子分析脚本不存在"}

        bt_dir = _get_backtest_dir(framework, backtest_name)
        if not bt_dir:
            return {"error": f"回测数据不存在: {backtest_name or '默认'}"}

        import json

        args = [
            str(fuel_python),
            str(script),
            "--main-factor", main_factor,
            "--sub-factor", sub_factor,
            "--periods", json.dumps(period_offset_list),
            "--time", rebalance_time,
            "--bins", str(bins),
            "--cache-dir", str(bt_dir),
            "--output-format", "json",
        ]

        start = time.time()
        try:
            proc = subprocess.run(
                args,
                cwd=str(framework),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=ANALYSIS_TIMEOUT,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            elapsed = time.time() - start

            if proc.returncode != 0:
                return {"error": f"双因子分析失败: {proc.stderr[:200]}"}

            result = _sanitize_analysis_result(json.loads(proc.stdout))
            result["elapsed_seconds"] = round(elapsed, 1)
            return result

        except subprocess.TimeoutExpired:
            return {"error": f"分析超时 ({ANALYSIS_TIMEOUT}s)"}
        except json.JSONDecodeError:
            return {"error": "分析输出格式错误"}
        except Exception as e:
            logger.exception("双因子分析异常")
            return {"error": str(e)}

    def run_factor_backtest(
        self,
        factor_name: str,
        start_date: str,
        end_date: str,
        factor_config: str = "",
        backtest_name: str | None = None,
    ) -> dict:
        """通过 Fuel Python 执行因子回测，生成 factor_*.pkl。"""
        framework = get_framework_path()
        fuel_python = get_fuel_python()
        if not framework or not fuel_python:
            return {"error": "stock_hub 未配置"}

        if not DATA_CENTER_PATH:
            return {"error": "DATA_CENTER_PATH 未配置"}

        script = Path(__file__).resolve().parent.parent / "scripts" / "run_factor_backtest.py"
        if not script.exists():
            return {"error": "回测脚本不存在"}

        if not backtest_name:
            backtest_name = "factor_hub"

        import json

        try:
            normalized_factor_config = _normalize_factor_config(
                factor_config,
                factor_name,
            )
        except ValueError as exc:
            return {"error": str(exc)}

        args = [
            str(fuel_python),
            str(script),
            "--factor", factor_name,
            "--start", start_date,
            "--end", end_date,
            "--name", backtest_name,
            "--data-path", DATA_CENTER_PATH,
            "--framework-path", str(framework),
            "--factor-config", normalized_factor_config,
        ]

        start = time.time()
        try:
            proc = subprocess.run(
                args,
                cwd=str(framework),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=BACKTEST_TIMEOUT,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            elapsed = time.time() - start

            if proc.returncode != 0:
                logger.warning(
                    "因子回测失败 factor=%s rc=%d stderr=%s",
                    factor_name,
                    proc.returncode,
                    proc.stderr[:500],
                )
                return {"error": f"因子回测失败: {proc.stderr[:200]}"}

            result = json.loads(proc.stdout)
            result["elapsed_seconds"] = round(elapsed, 1)
            return result

        except subprocess.TimeoutExpired:
            return {"error": f"因子回测超时 ({BACKTEST_TIMEOUT}s)"}
        except json.JSONDecodeError:
            return {"error": "回测输出格式错误"}
        except Exception as e:
            logger.exception("因子回测异常 factor=%s", factor_name)
            return {"error": str(e)}

    def get_status(self) -> dict:
        """检查 stock_hub 配置状态。不暴露路径信息。"""
        framework = get_framework_path()
        fuel_python = get_fuel_python()
        framework_configured = framework is not None
        fuel_python_configured = fuel_python is not None
        available = framework_configured and fuel_python_configured

        factor_lib = False
        section_lib = False
        cache_root_exists = False
        enhanced_script_exists = False
        dual_script_exists = False
        available_backtests_count = 0
        if framework:
            factor_lib = (framework / "因子库").is_dir()
            section_lib = (framework / "截面因子库").is_dir()
            cache_root = framework / "data" / "运行缓存"
            cache_root_exists = cache_root.is_dir()
            enhanced_script_exists = (framework / "run_enhanced_analysis.py").is_file()
            dual_script_exists = (framework / "run_dual_analysis.py").is_file()
            available_backtests_count = len(self.list_available_backtests())

        analysis_ready = (
            available
            and cache_root_exists
            and enhanced_script_exists
            and dual_script_exists
            and available_backtests_count > 0
        )

        return {
            "available": available,
            "analysis_ready": analysis_ready,
            "framework_configured": framework_configured,
            "fuel_python_configured": fuel_python_configured,
            "factor_lib_exists": factor_lib,
            "section_factor_lib_exists": section_lib,
            "cache_root_exists": cache_root_exists,
            "enhanced_script_exists": enhanced_script_exists,
            "dual_script_exists": dual_script_exists,
            "available_backtests_count": available_backtests_count,
        }


_service: StockAnalysisService | None = None


def get_stock_analysis_service() -> StockAnalysisService:
    """获取分析服务单例。"""
    global _service
    if _service is None:
        _service = StockAnalysisService()
    return _service
