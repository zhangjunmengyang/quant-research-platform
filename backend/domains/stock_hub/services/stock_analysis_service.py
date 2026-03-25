"""A股因子分析服务"""
import json
import logging
import os
import subprocess
import time
from typing import Optional, Dict, Any, List
from pathlib import Path

from domains.stock_hub.config import (
    STOCK_FRAMEWORK_PATH,
    FUEL_PYTHON_PATH,
    CACHE_DIR,
    ANALYSIS_TIMEOUT,
)

logger = logging.getLogger(__name__)

TMP_DIR = CACHE_DIR / "tmp"
TMP_DIR.mkdir(exist_ok=True)

# 增强分析结果目录
ANALYSIS_RESULT_DIR = STOCK_FRAMEWORK_PATH / "data" / "分析结果"


class StockAnalysisService:
    """因子分析服务 - IC/ICIR/分组收益"""

    def __init__(self):
        self.script_path = Path(__file__).parent.parent / "scripts" / "run_factor_analysis.py"
        self.enhanced_script_path = Path(__file__).parent.parent / "scripts" / "run_enhanced_analysis.py"
        self.dual_script_path = Path(__file__).parent.parent / "scripts" / "run_dual_analysis.py"

    # ========== 原有基础分析 ==========

    def analyze_factor(
        self,
        result_path: str,
        factor_name: str,
        hold_period: str = "W",
        group_num: int = 10,
    ) -> Dict[str, Any]:
        """对回测结果中的因子进行IC/分组分析（基础版）"""
        from domains.stock_hub.config import is_stock_framework_available

        if not is_stock_framework_available():
            return {
                "status": "error",
                "message": "Stock framework not configured.",
            }

        config = {
            "stock_framework_path": str(STOCK_FRAMEWORK_PATH),
            "result_path": result_path,
            "factor_name": factor_name,
            "hold_period": hold_period,
            "group_num": group_num,
        }

        config_path = TMP_DIR / f"analysis_{int(time.time() * 1000)}.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        try:
            return self._run_subprocess(self.script_path, config_path)
        finally:
            try:
                config_path.unlink()
            except Exception:
                pass

    # ========== 增强因子分析（早盘换仓 + 全offset） ==========

    def list_available_backtests(self) -> Dict[str, Any]:
        """列出运行缓存中所有可用的回测数据源（直接扫目录，无需subprocess）"""
        runtime_cache = STOCK_FRAMEWORK_PATH / "data" / "运行缓存"
        if not runtime_cache.exists():
            return {"status": "ok", "data": {"backtests": [], "total": 0}}

        backtests = []
        for d in sorted(runtime_cache.iterdir()):
            if not d.is_dir():
                continue
            factor_files = [f for f in d.iterdir() if f.name.startswith("factor_") and f.name.endswith(".pkl")]
            if not factor_files:
                continue
            mtime = max(f.stat().st_mtime for f in factor_files)
            backtests.append({
                "name": d.name,
                "factor_count": len(factor_files),
                "modified_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)),
            })

        # 按修改时间倒序
        backtests.sort(key=lambda x: x["modified_time"], reverse=True)
        return {"status": "ok", "data": {"backtests": backtests, "total": len(backtests)}}

    def enhanced_analyze(
        self,
        factor_name: str,
        period_offset_list: List[str] = None,
        rebalance_time: str = "0955",
        bins: int = 10,
        backtest_name: str = None,
    ) -> Dict[str, Any]:
        """增强单因子分析 — 支持早盘换仓 + 全offset"""
        from domains.stock_hub.config import is_stock_framework_available

        if not is_stock_framework_available():
            return {"status": "error", "message": "Stock framework not configured."}

        if period_offset_list is None:
            period_offset_list = ["5_0"]

        config = {
            "stock_framework_path": str(STOCK_FRAMEWORK_PATH),
            "mode": "single",
            "factor_name": factor_name,
            "period_offset_list": period_offset_list,
            "rebalance_time": rebalance_time,
            "bins": bins,
            "limit": 100,
            "force_read": False,
        }
        if backtest_name:
            config["backtest_name"] = backtest_name

        config_path = TMP_DIR / f"enhanced_{int(time.time() * 1000)}.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        try:
            return self._run_subprocess(self.enhanced_script_path, config_path, timeout=ANALYSIS_TIMEOUT)
        finally:
            try:
                config_path.unlink()
            except Exception:
                pass

    def list_cached_factors(self, backtest_name: str = None) -> Dict[str, Any]:
        """列出运行缓存中的可用因子"""
        from domains.stock_hub.config import is_stock_framework_available

        if not is_stock_framework_available():
            return {"status": "error", "message": "Stock framework not configured."}

        config = {
            "stock_framework_path": str(STOCK_FRAMEWORK_PATH),
            "mode": "list_factors",
        }
        if backtest_name:
            config["backtest_name"] = backtest_name

        config_path = TMP_DIR / f"list_{int(time.time() * 1000)}.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        try:
            return self._run_subprocess(self.enhanced_script_path, config_path, timeout=60)
        finally:
            try:
                config_path.unlink()
            except Exception:
                pass

    def batch_analyze(
        self,
        period_offset_list: List[str] = None,
        rebalance_time: str = "0955",
        bins: int = 10,
        max_workers: int = 3,
        skip_existing: bool = True,
        backtest_name: str = None,
    ) -> Dict[str, Any]:
        """批量分析所有因子"""
        from domains.stock_hub.config import is_stock_framework_available

        if not is_stock_framework_available():
            return {"status": "error", "message": "Stock framework not configured."}

        if period_offset_list is None:
            period_offset_list = ["5_0"]

        config = {
            "stock_framework_path": str(STOCK_FRAMEWORK_PATH),
            "mode": "batch",
            "period_offset_list": period_offset_list,
            "rebalance_time": rebalance_time,
            "bins": bins,
            "limit": 100,
            "batch_max_workers": max_workers,
            "skip_existing": skip_existing,
            "force_read": False,
        }
        if backtest_name:
            config["backtest_name"] = backtest_name

        config_path = TMP_DIR / f"batch_{int(time.time() * 1000)}.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        try:
            # 批量分析超时更长
            return self._run_subprocess(self.enhanced_script_path, config_path, timeout=7200)
        finally:
            try:
                config_path.unlink()
            except Exception:
                pass

    def dual_analyze(
        self,
        main_factor: str,
        sub_factor: str,
        period_offset_list: List[str] = None,
        rebalance_time: str = "0955",
        bins: int = 5,
        backtest_name: str = None,
    ) -> Dict[str, Any]:
        """双因子分析 — 热力图 + 风格暴露"""
        from domains.stock_hub.config import is_stock_framework_available

        if not is_stock_framework_available():
            return {"status": "error", "message": "Stock framework not configured."}

        if period_offset_list is None:
            period_offset_list = ["5_0"]

        config = {
            "stock_framework_path": str(STOCK_FRAMEWORK_PATH),
            "main_factor": main_factor,
            "sub_factor": sub_factor,
            "period_offset_list": period_offset_list,
            "rebalance_time": rebalance_time,
            "bins": bins,
            "limit": 100,
            "force_read": False,
        }
        if backtest_name:
            config["backtest_name"] = backtest_name

        config_path = TMP_DIR / f"dual_{int(time.time() * 1000)}.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        try:
            return self._run_subprocess(self.dual_script_path, config_path, timeout=ANALYSIS_TIMEOUT)
        finally:
            try:
                config_path.unlink()
            except Exception:
                pass

    def get_analysis_report_path(self, factor_name: str, cfg_str: str = None) -> Optional[Path]:
        """获取因子分析HTML报告路径"""
        html_dir = ANALYSIS_RESULT_DIR / "单因子分析"
        if not html_dir.exists():
            return None

        # 查找匹配的HTML文件
        pattern = f"*{factor_name}*"
        if cfg_str:
            pattern = f"*{factor_name}*{cfg_str}*"

        matches = list(html_dir.glob(f"{pattern}.html"))
        if matches:
            return matches[0]
        return None

    def list_analysis_results(self, cfg_str: str = None) -> List[Dict[str, Any]]:
        """列出已有的分析结果（从PKL目录扫描）"""
        results = []
        if not ANALYSIS_RESULT_DIR.exists():
            return results

        # 扫描所有PKL目录
        for pkl_dir in ANALYSIS_RESULT_DIR.glob("单因子_*_pkl"):
            dir_name = pkl_dir.name
            if cfg_str and cfg_str not in dir_name:
                continue

            for pkl_file in sorted(pkl_dir.glob("*.pkl")):
                try:
                    import pickle
                    with open(pkl_file, 'rb') as f:
                        data = pickle.load(f)
                    results.append({
                        "factor_name": data.get("name", pkl_file.stem),
                        "score": float(data.get("score", 0)),
                        "ic_mean": float(data.get("ic_mean", 0)),
                        "icir": float(data.get("icir", 0)),
                        "ic_ratio": str(data.get("ic_ratio", "")),
                        "config": dir_name,
                    })
                except Exception:
                    continue

        return results

    # ========== 通用子进程执行 ==========

    def _run_subprocess(self, script_path: Path, config_path: Path, timeout: int = None) -> Dict[str, Any]:
        """执行分析子进程"""
        if timeout is None:
            timeout = ANALYSIS_TIMEOUT

        cmd = [
            str(FUEL_PYTHON_PATH),
            "-X", "utf8",
            str(script_path),
            "--config", str(config_path),
        ]

        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                cwd=str(STOCK_FRAMEWORK_PATH),
                timeout=timeout,
            )

            stdout = proc.stdout or ""
            for line in stdout.split("\n"):
                if line.startswith("__RESULT_JSON__:"):
                    try:
                        return json.loads(line[len("__RESULT_JSON__:"):])
                    except json.JSONDecodeError:
                        pass

            # 如果没找到 JSON 结果，返回错误
            error_msg = proc.stderr[-2000:] if proc.stderr else "No result"
            # 也包含 stdout 的最后几行作为调试信息
            stdout_tail = "\n".join(stdout.split("\n")[-5:])
            return {
                "status": "error",
                "message": f"{error_msg}\n--- stdout tail ---\n{stdout_tail}",
            }

        except subprocess.TimeoutExpired:
            return {"status": "error", "message": f"分析超时（{timeout}秒）"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


_service: Optional[StockAnalysisService] = None


def get_stock_analysis_service() -> StockAnalysisService:
    global _service
    if _service is None:
        _service = StockAnalysisService()
    return _service
