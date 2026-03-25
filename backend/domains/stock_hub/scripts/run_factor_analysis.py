"""
因子分析子进程脚本
在Fuel Python环境中运行

用法: python run_factor_analysis.py --config <json_config_path>

输入JSON: result_path, factor_name, hold_period, group_num
输出: stdout最后一行 __RESULT_JSON__:{...}
"""
import sys
import os
import json
import argparse
import traceback
import warnings
from pathlib import Path
import numpy as np

warnings.filterwarnings("ignore")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    result = {"status": "error", "message": "", "data": None}

    try:
        params = json.loads(Path(args.config).read_text(encoding="utf-8"))

        stock_framework_path = params.get("stock_framework_path", r"D:\select-stock-pro_v2.0.0")
        if stock_framework_path not in sys.path:
            sys.path.insert(0, stock_framework_path)
        os.chdir(stock_framework_path)

        import pandas as pd

        # 导入tfunctions
        try:
            import tfunctions as tf
        except ImportError:
            result["message"] = "tfunctions.py not found in stock framework directory"
            print(f"\n__RESULT_JSON__:{json.dumps(result, ensure_ascii=False)}")
            sys.exit(1)

        result_path = Path(params["result_path"])
        factor_name = params["factor_name"]
        hold_period = params.get("hold_period", "W")
        group_num = params.get("group_num", 10)

        # 查找选股结果文件
        select_files = list(result_path.glob("*选股结果*.csv")) + list(result_path.glob("*select*.csv"))
        if not select_files:
            select_files = list(result_path.rglob("*选股*.csv"))

        if not select_files:
            result["message"] = f"未找到选股结果文件: {result_path}"
            print(f"\n__RESULT_JSON__:{json.dumps(result, ensure_ascii=False)}")
            sys.exit(1)

        # 读取选股结果
        select_df = pd.read_csv(select_files[0], encoding="utf-8-sig", parse_dates=["选股日期"])

        # 检查因子列
        factor_col = None
        for col in select_df.columns:
            if factor_name in col:
                factor_col = col
                break

        if factor_col is None:
            result["message"] = f"因子 {factor_name} 不在选股结果中，可用列: {list(select_df.columns)}"
            print(f"\n__RESULT_JSON__:{json.dumps(result, ensure_ascii=False)}")
            sys.exit(1)

        analysis_data = {}

        # IC分析
        try:
            if hasattr(tf, "get_ic_zq"):
                ic_df = tf.get_ic_zq(select_df, factor_col, hold_period)
                if ic_df is not None and not ic_df.empty:
                    ic_values = ic_df["IC"].dropna()
                    n = len(ic_values)
                    ic_mean = float(ic_values.mean())
                    ic_std = float(ic_values.std())
                    analysis_data["ic"] = {
                        "ic_mean": ic_mean,
                        "ic_std": ic_std,
                        "icir": ic_mean / ic_std if ic_std > 0 else 0,
                        "ic_positive_ratio": float((ic_values > 0).mean()),
                        "t_stat": ic_mean / (ic_std / np.sqrt(n)) if n > 0 and ic_std > 0 else 0,
                        "count": n,
                    }
        except Exception as e:
            analysis_data["ic_error"] = str(e)

        # 分组收益分析
        try:
            if hasattr(tf, "get_group_net_value_zq"):
                group_df = tf.get_group_net_value_zq(select_df, factor_col, hold_period, group_num)
                if group_df is not None and not group_df.empty:
                    last_row = group_df.iloc[-1]
                    group_returns = {}
                    for col in group_df.columns:
                        if col not in ("candle_end_time", "交易日期"):
                            group_returns[str(col)] = float(last_row[col])
                    analysis_data["group_returns"] = group_returns
        except Exception as e:
            analysis_data["group_error"] = str(e)

        result["status"] = "ok"
        result["message"] = "分析完成"
        result["data"] = analysis_data

    except Exception as e:
        result["status"] = "error"
        result["message"] = f"{type(e).__name__}: {str(e)}"
        traceback.print_exc(file=sys.stderr)

    print(f"\n__RESULT_JSON__:{json.dumps(result, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
