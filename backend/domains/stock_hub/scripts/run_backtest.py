"""
回测执行子进程脚本
在Fuel Python环境中运行，通过subprocess调用

用法: python run_backtest.py --config <json_config_path>

输入: JSON配置文件
输出: stdout最后一行为JSON结果

关键设计: 直接替换框架的config.py（备份+恢复），
         使用文件锁防止并发回测冲突。
         这样多进程子进程也能正确import config。
"""
import sys
import os
import json
import argparse
import traceback
import shutil
from pathlib import Path


def generate_config_py(params: dict, output_dir: Path) -> Path:
    """根据JSON参数生成一个真实的config.py文件"""
    config_path = output_dir / "config.py"

    # 构建strategy_list的Python源码
    strategies = params.get("strategies", [])
    strategy_list_code = "[\n"
    for s in strategies:
        factor_list_code = "[\n"
        for f in s.get("factor_list", []):
            name = f["name"]
            asc = f.get("ascending", True)
            param = f.get("param", "")
            weight = f.get("weight", 1)
            factor_list_code += f'            ("{name}", {asc}, "{param}", {weight}),\n'
        factor_list_code += "        ]"

        filter_list_code = "[\n"
        for fl in s.get("filter_list", []):
            name = fl["name"]
            param = repr(fl.get("param"))
            cond = fl["condition"]
            keep = fl.get("keep", True)
            filter_list_code += f'            ("{name}", {param}, "{cond}", {keep}),\n'
        filter_list_code += "        ]"

        strategy_list_code += f"""    {{
        "name": "{s.get("name", "默认策略")}",
        "hold_period": "{s.get("hold_period", "W")}",
        "offset_list": {s.get("offset_list", [0])},
        "select_num": {s.get("select_num", 3)},
        "cap_weight": {s.get("cap_weight", 1)},
        "rebalance_time": "{s.get("rebalance_time", "open")}",
        "factor_list": {factor_list_code},
        "filter_list": {filter_list_code},
    }},\n"""
    strategy_list_code += "]"

    # 性能模式
    pm = params.get("performance_mode", "ECO")
    if pm in ("BAL", "EQUAL"):
        n_jobs = int(os.cpu_count() / 2)
        fcl = 8
    elif pm in ("MAX", "PERFORMANCE"):
        n_jobs = int(os.cpu_count() - 1)
        fcl = 12
    else:
        n_jobs = int(os.cpu_count() / 4)
        fcl = 6
    n_jobs = max(n_jobs, 4)
    if os.name == "nt":
        n_jobs = min(n_jobs, 61)

    data_center = params.get("data_center_path", r"D:\shuju").replace("\\", "\\\\")
    stock_fw = params.get("stock_framework_path", r"D:\select-stock-pro_v2.0.0").replace("\\", "\\\\")

    code = f'''"""Auto-generated config by stock_hub"""
import os
from pathlib import Path
import sys

# 确保选股框架在路径中
_fw = r"{stock_fw}"
if _fw not in sys.path:
    sys.path.insert(0, _fw)

from core.utils.path_kit import get_folder_path

# 1. 回测配置
start_date = "{params.get("start_date", "2024-01-01")}"
end_date = {repr(params.get("end_date"))}
performance_mode = "{pm}"
stay_real = {params.get("stay_real", True)}

# 2. 数据配置
data_center_path = r"{data_center}"
runtime_data_path = get_folder_path("data")
clean_result_folder = False

# 3. 策略配置
backtest_name = "{params.get("backtest_name", "AI框架回测")}"
strategy_list = {strategy_list_code}
excluded_boards = {params.get("excluded_boards", ["bj"])}
days_listed = {params.get("days_listed", 250)}
total_cap_usage = {params.get("total_cap_usage", 1.0)}
initial_cash = {params.get("initial_cash", 100000000)}
c_rate = {params.get("c_rate", 1.2 / 10000)}
t_rate = {params.get("t_rate", 1 / 1000)}
stock_timing_order_price = {params.get("stock_timing_order_price", 5)}

# 4. 性能配置
n_jobs = {n_jobs}
factor_col_limit = {fcl}

# 5. 运行时路径
runtime_folder = get_folder_path(runtime_data_path, "运行缓存")
if not Path(data_center_path).exists():
    print(f"数据中心路径不存在：{{data_center_path}}，请检查配置或联系助教，程序退出")
    exit()

data_center_path = Path(data_center_path)
runtime_data_path = Path(runtime_data_path)
'''

    config_path.write_text(code, encoding="utf-8")
    return config_path


def _acquire_config_lock(lock_path: Path):
    """获取config.py文件锁（防止并发回测冲突）"""
    lock_file = open(lock_path, "w")
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
    return lock_file


def _release_config_lock(lock_file):
    """释放config.py文件锁"""
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    finally:
        try:
            lock_file.close()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="JSON配置文件路径")
    args = parser.parse_args()

    result = {"status": "error", "message": "", "result_path": None}
    stock_framework_path = r"D:\select-stock-pro_v2.0.0"
    lock_file = None

    try:
        config_json_path = Path(args.config)
        params = json.loads(config_json_path.read_text(encoding="utf-8"))

        stock_framework_path = params.get("stock_framework_path", r"D:\select-stock-pro_v2.0.0")

        # 获取文件锁（防止并发回测互相覆盖config.py）
        lock_path = Path(stock_framework_path) / "config.py.lock"
        lock_file = _acquire_config_lock(lock_path)

        # 直接替换框架的config.py（多进程唯一可靠方案）
        original_config = Path(stock_framework_path) / "config.py"
        backup_config = Path(stock_framework_path) / "config.py._stock_hub_backup"

        # 备份原始config
        if original_config.exists():
            shutil.copy2(original_config, backup_config)

        # 生成新config.py覆盖原文件
        generate_config_py(params, Path(stock_framework_path))

        # 切换到选股框架目录
        os.chdir(stock_framework_path)
        if stock_framework_path not in sys.path:
            sys.path.insert(0, stock_framework_path)

        # 导入config验证
        import config
        if not config.data_center_path.exists():
            result["message"] = f"数据中心路径不存在: {config.data_center_path}"
            print(f"\n__RESULT_JSON__:{json.dumps(result, ensure_ascii=False)}")
            sys.exit(1)

        import warnings
        warnings.filterwarnings("ignore")

        # 导入并执行回测
        from core.backtest import run_backtest
        from core.model.backtest_config import load_config

        conf = load_config()
        run_backtest(conf)

        # 查找结果路径
        result_path = config.runtime_data_path / "回测结果"
        if result_path.exists():
            subdirs = [d for d in result_path.iterdir() if d.is_dir()]
            if subdirs:
                latest = max(subdirs, key=lambda d: d.stat().st_mtime)
                result["result_path"] = str(latest)

        result["status"] = "ok"
        result["message"] = "回测完成"

    except Exception as e:
        result["status"] = "error"
        result["message"] = f"{type(e).__name__}: {str(e)}"
        traceback.print_exc(file=sys.stderr)
    finally:
        # 恢复原始config.py（无论成功/失败/超时都执行）
        try:
            backup = Path(stock_framework_path) / "config.py._stock_hub_backup"
            original = Path(stock_framework_path) / "config.py"
            if backup.exists():
                shutil.copy2(backup, original)
                backup.unlink()
        except Exception:
            pass

        # 释放文件锁
        if lock_file:
            _release_config_lock(lock_file)

    print(f"\n__RESULT_JSON__:{json.dumps(result, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
