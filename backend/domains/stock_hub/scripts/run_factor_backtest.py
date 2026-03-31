"""Factor backtest wrapper — generates a temporary config and runs factor calculation.

Executed by Fuel Python as a subprocess. Outputs JSON to stdout.

Usage:
    python run_factor_backtest.py \
        --factor "市值" --start "2020-01-01" --end "2024-12-31" \
        --name "pf_市值_2020_2024" \
        --data-path "D:/shuju" --framework-path "D:/select-stock-pro_v2.0.0"
"""

import argparse
import ast
import io
import json
import os
import sys
import tempfile
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# Preserve original stdout for final JSON output, then redirect stdout→stderr
# so framework log_kit.py print() calls don't pollute JSON.

_real_stdout = sys.stdout.buffer if hasattr(sys.stdout, "buffer") else sys.stdout

if os.name == "nt":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Redirect stdout to stderr — all framework print()/logging goes to stderr
sys.stdout = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _write_json(obj: dict):
    """Write JSON result to the real stdout (not the redirected one)."""
    data = json.dumps(obj, ensure_ascii=False) + "\n"
    if hasattr(_real_stdout, "write") and isinstance(_real_stdout, io.RawIOBase):
        _real_stdout.write(data.encode("utf-8"))
        _real_stdout.flush()
    else:
        out = io.TextIOWrapper(_real_stdout, encoding="utf-8", errors="replace")
        out.write(data)
        out.flush()
        out.detach()  # don't close underlying buffer


def _is_safe_literal(value: object) -> bool:
    """递归校验配置参数是安全字面量。"""
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
    """将输入配置标准化为安全的 Python 字面量字符串。"""
    config_text = raw_config.strip()
    if not config_text:
        return repr((factor_name, True, "", 1))

    parsed = ast.literal_eval(config_text)
    if not isinstance(parsed, (list, tuple)) or len(parsed) != 4:
        raise ValueError("factor_config must be a 4-item tuple")

    config_factor_name, is_ascending, parameter, weight = parsed
    if config_factor_name != factor_name:
        raise ValueError("factor_config factor name does not match selected factor")
    if not isinstance(is_ascending, bool):
        raise ValueError("factor_config sort flag must be bool")
    if not _is_safe_literal(parameter):
        raise ValueError("factor_config parameter contains unsafe literal")
    if not isinstance(weight, (int, float)):
        raise ValueError("factor_config weight must be numeric")

    return repr((config_factor_name, is_ascending, parameter, weight))


def main():
    parser = argparse.ArgumentParser(description="Run factor backtest")
    parser.add_argument("--factor", required=True, help="Factor name")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--name", required=True, help="Backtest name for cache folder")
    parser.add_argument("--data-path", required=True, help="Data center path")
    parser.add_argument("--framework-path", required=True, help="Framework root path")
    parser.add_argument("--factor-config", default="", help='Factor config tuple, e.g. ("Ret", True, 5, 1)')
    args = parser.parse_args()

    fw = args.framework_path

    factor_config_repr = _normalize_factor_config(args.factor_config, args.factor)

    # Generate temporary config.py that will be picked up by `import config`
    config_content = f'''\
import os
from pathlib import Path
from core.utils.path_kit import get_folder_path

start_date = "{args.start}"
end_date = "{args.end}"
performance_mode = "BAL"
stay_real = True
data_center_path = r"{args.data_path}"
runtime_data_path = get_folder_path("data")
clean_result_folder = False
backtest_name = "{args.name}"

strategy_list = [
    {{
        "name": "因子生成",
        "hold_period": "W",
        "offset_list": [0],
        "select_num": 3,
        "cap_weight": 1,
        "rebalance_time": "open",
        "factor_list": [{factor_config_repr}],
        "filter_list": [],
    }}
]

excluded_boards = ["bj"]
days_listed = 250
total_cap_usage = 1
initial_cash = 1_0000_0000
c_rate = 1.2 / 10000
t_rate = 1 / 1000

n_jobs = max(int(os.cpu_count() / 2), 4)
if os.name == "nt":
    n_jobs = min(n_jobs, 61)
factor_col_limit = 8

data_center_path = Path(data_center_path)
runtime_data_path = Path(runtime_data_path)
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.py"
        config_path.write_text(config_content, encoding="utf-8")

        # Make `import config` resolve to the temp file
        sys.path.insert(0, tmpdir)
        # Framework must be on sys.path for `core.*` imports
        if fw not in sys.path:
            sys.path.insert(1, fw)
        os.chdir(fw)

        from core.model.backtest_config import load_config  # noqa: I001
        from core.select_stock import calculate_factors, calc_cross_sections

        conf = load_config()
        runtime = conf.get_runtime_folder()

        t0 = time.time()

        # Step 1: prepare base data if not cached
        preprocessed = runtime / "股票预处理数据.pkl"
        if not preprocessed.exists():
            from core.data_center import prepare_data
            prepare_data(conf)

        # Step 2: calculate factors
        calculate_factors(conf, boost=True)
        calc_cross_sections(conf)

        elapsed = round(time.time() - t0, 1)

        pkl_path = runtime / f"factor_{args.factor}.pkl"
        result = {
            "factor_name": args.factor,
            "backtest_name": args.name,
            "pkl_exists": pkl_path.exists(),
            "elapsed_seconds": elapsed,
        }
        _write_json(result)


if __name__ == "__main__":
    main()
