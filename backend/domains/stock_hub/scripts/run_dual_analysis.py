"""
双因子分析子进程脚本 — 支持早盘换仓 + 全offset
在Fuel Python环境中运行

用法: python run_dual_analysis.py --config <json_config_path>

输入JSON:
{
    "stock_framework_path": "D:\\select-stock-pro_v2.0.0",
    "main_factor": "factor_G159",
    "sub_factor": "市值",
    "period_offset_list": ["5_0"],
    "rebalance_time": "0955",
    "bins": 10,
    "limit": 100,
    "backtest_name": "debug_test2",
    "start_date": "2024-01-01",
    "end_date": "2025-01-01",
    "n_jobs": 4
}

输出: stdout 最后一行 __RESULT_JSON__:{...}
"""
import sys
import os
import json
import argparse
import traceback
import warnings
import datetime
from pathlib import Path

warnings.filterwarnings("ignore")


def _default_data_process(df):
    """默认数据处理函数"""
    return df


def run_dual_analysis(main_factor, sub_factor, cfg, boost=True):
    """运行双因子分析，返回结果dict"""
    import tools.utils.pfunctions as pf
    import tools.utils.tfunctions as tf

    cfg.main = main_factor if main_factor.startswith("factor_") else f"factor_{main_factor}"
    cfg.sub = sub_factor if sub_factor.startswith("factor_") else f"factor_{sub_factor}"
    cfg.func = _default_data_process
    cfg.keep_cols = [
        "交易日期", "股票代码", "股票名称",
        "下日_是否交易", "下日_开盘涨停", "下日_是否ST", "下日_是否退市",
        "上市至今交易天数", cfg.main, cfg.sub,
        "新版申万一级行业名称", "下周期涨跌幅", "下周期每天涨跌幅",
    ]

    start_time = datetime.datetime.now()

    # 读取因子数据
    factors_pkl = [
        d[:-4] for d in os.listdir(cfg.get_runtime_folder())
        if d.startswith("factor_")
    ]
    factor_list = []
    for name in [cfg.main, cfg.sub]:
        if name in factors_pkl:
            factor_list.append(name)
        else:
            raise ValueError(f"因子 {name} 不在运行缓存中，可用: {factors_pkl[:10]}...")

    factor_df = tf.get_data_zq(cfg, factor_list, boost)

    fig_list = []

    # === 双因子热力图 ===
    mix_nv, mix_prop, filter_nv_ms, filter_nv_sm = tf.get_group_nv_double(factor_df, cfg)

    fig_list.append(pf.draw_hot_plotly(
        x=mix_nv.columns, y=mix_nv.index, z=mix_nv,
        title=f"双因子组合 - 日平均收益(‰)<br />主：{cfg.main}   次：{cfg.sub}_费率{1 - cfg.fee_rate}",
    ))
    fig_list.append(pf.draw_hot_plotly(
        x=mix_prop.columns, y=mix_prop.index, z=mix_prop,
        title=f"双因子组合 - 平均占比(%)<br />主：{cfg.main}   次：{cfg.sub}",
    ))
    fig_list.append(pf.draw_hot_plotly(
        x=filter_nv_ms.columns, y=filter_nv_ms.index, z=filter_nv_ms,
        title=f"双因子过滤 - 日平均收益(‰)<br />在【{cfg.main}】分组的基础上，对【{cfg.sub}】分组",
    ))
    fig_list.append(pf.draw_hot_plotly(
        x=filter_nv_sm.columns, y=filter_nv_sm.index, z=filter_nv_sm,
        title=f"双因子过滤 - 日平均收益(‰)<br />在【{cfg.sub}】分组的基础上，对【{cfg.main}】分组",
    ))

    # === 双因子风格暴露 ===
    style_corr, corr_txt = tf.get_style_corr_double(factor_df, cfg)
    fig_list.append(pf.draw_three_bar_plotly(
        x=style_corr["风格"],
        y1=style_corr["相关系数_主因子"],
        y2=style_corr["相关系数_次因子"],
        y3=style_corr["相关系数_双因子"],
        title=corr_txt,
    ))

    start_date = factor_df["交易日期"].min().strftime("%Y/%m/%d")
    end_date = factor_df["交易日期"].max().strftime("%Y/%m/%d")
    title = f"分析区间：{start_date} - {end_date}  分析周期：{cfg.period_offset_list}  换仓时间：{cfg.rebalance_time}"

    # === 生成HTML报告 ===
    save_path = cfg.dual_html_dir
    os.makedirs(save_path, exist_ok=True)
    html_path = pf.merge_html_not_open(
        save_path, fig_list=fig_list,
        strategy_file=f"{cfg.main}和{cfg.sub}_分析报告{cfg.cfg_str}",
        bbs_id="45302", title=title,
    )

    elapsed = (datetime.datetime.now() - start_time).total_seconds()
    print(f"双因子分析完成，耗时：{elapsed:.1f}秒")

    # 提取热力图数据用于JSON返回
    import math

    def safe_float(v):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return 0.0
        return float(v)

    def heatmap_to_dict(hm):
        return {
            "columns": [str(c) for c in hm.columns.tolist()],
            "index": [str(i) for i in hm.index.tolist()],
            "values": [[safe_float(v) for v in row] for row in hm.values.tolist()],
        }

    # 风格数据
    style_data = {}
    for _, row in style_corr.iterrows():
        s = str(row["风格"])
        style_data[s] = {
            "main": float(row["相关系数_主因子"]),
            "sub": float(row["相关系数_次因子"]),
            "dual": float(row["相关系数_双因子"]),
        }

    return {
        "main_factor": main_factor,
        "sub_factor": sub_factor,
        "start_date": start_date,
        "end_date": end_date,
        "period_offset_list": cfg.period_offset_list,
        "rebalance_time": cfg.rebalance_time,
        "mix_nv": heatmap_to_dict(mix_nv),
        "mix_prop": heatmap_to_dict(mix_prop),
        "filter_nv_ms": heatmap_to_dict(filter_nv_ms),
        "filter_nv_sm": heatmap_to_dict(filter_nv_sm),
        "style_exposure": style_data,
        "correlation_text": corr_txt,
        "html_path": str(html_path),
        "elapsed_seconds": round(elapsed, 1),
    }


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

        # 覆盖 config 模块参数
        import config as _cfg_module
        backtest_name = params.get("backtest_name")
        if backtest_name:
            _cfg_module.backtest_name = backtest_name
        if params.get("start_date"):
            _cfg_module.start_date = params["start_date"]
        if params.get("end_date"):
            _cfg_module.end_date = params["end_date"]
        _cfg_module.n_jobs = params.get("n_jobs", 4)
        if hasattr(_cfg_module, 'performance_mode'):
            _cfg_module.performance_mode = "ECO"

        from core.model.backtest_config import load_config
        cfg = load_config()
        cfg.bins = params.get("bins", 5)
        cfg.limit = params.get("limit", 100)
        cfg.fee_rate = (1 - cfg.c_rate) * (1 - cfg.c_rate - cfg.t_rate)
        cfg.period_offset_list = params.get("period_offset_list", ["5_0"])
        cfg.rebalance_time = params.get("rebalance_time", "0955")
        cfg.force_read_ret_and_style = params.get("force_read", False)

        cfg_str = '+'.join(str(i) for i in cfg.period_offset_list)
        cfg_str = cfg_str + '+' + cfg.rebalance_time
        cfg.cfg_str = cfg_str

        analysis_folder = Path(stock_framework_path) / "data" / "分析结果"
        cfg.dual_html_dir = analysis_folder / "双因子分析"

        main_factor = params.get("main_factor", "")
        sub_factor = params.get("sub_factor", "")
        if not main_factor or not sub_factor:
            result["message"] = "main_factor and sub_factor are required"
            print(f"\n__RESULT_JSON__:{json.dumps(result, ensure_ascii=False)}")
            return

        data = run_dual_analysis(main_factor, sub_factor, cfg, boost=True)
        result["status"] = "ok"
        result["message"] = "双因子分析完成"
        result["data"] = data

    except Exception as e:
        result["status"] = "error"
        result["message"] = f"{type(e).__name__}: {str(e)}"
        traceback.print_exc(file=sys.stderr)

    import math

    def clean_for_json(obj):
        """替换NaN/Inf为None以确保JSON可序列化"""
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, dict):
            return {k: clean_for_json(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean_for_json(i) for i in obj]
        return obj

    result = clean_for_json(result)
    print(f"\n__RESULT_JSON__:{json.dumps(result, ensure_ascii=False, default=str)}")


if __name__ == "__main__":
    main()
