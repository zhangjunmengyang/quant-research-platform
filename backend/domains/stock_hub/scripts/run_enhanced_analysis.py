"""
增强因子分析子进程脚本 — 支持早盘换仓 + 全offset分析
在Fuel Python环境中运行

用法: python run_enhanced_analysis.py --config <json_config_path>

输入JSON:
{
    "stock_framework_path": "D:\\select-stock-pro_v2.0.0",
    "factor_name": "市值",
    "period_offset_list": ["5_0","5_1","5_2","5_3","5_4"],
    "rebalance_time": "0955",
    "bins": 10,
    "limit": 100,
    "mode": "single",          // "single" | "batch" | "list_factors"
    "batch_max_workers": 3,
    "force_read": false
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


def list_available_factors(cfg):
    """列出运行缓存中的所有可用因子"""
    runtime_folder = cfg.get_runtime_folder()
    if not runtime_folder.exists():
        return []
    factors = [
        f[:-4]  # remove .pkl
        for f in os.listdir(runtime_folder)
        if f.startswith("factor_") and f.endswith(".pkl")
    ]
    factors.sort()
    return factors


def _default_data_process(df):
    """默认数据处理函数（不做额外过滤）"""
    return df


def run_single_analysis(factor_name, cfg, boost=True):
    """运行单因子分析，返回结果dict"""
    import tools.utils.pfunctions as pf
    import tools.utils.tfunctions as tf

    name = factor_name
    cfg.fa_name = name if name.startswith("factor_") else f"factor_{name}"

    cfg.func = _default_data_process
    cfg.keep_cols = [
        "交易日期", "股票代码", "股票名称",
        "下日_是否交易", "下日_开盘涨停", "下日_是否ST", "下日_是否退市",
        "上市至今交易天数", cfg.fa_name,
        "新版申万一级行业名称", "下周期涨跌幅", "下周期每天涨跌幅",
    ]
    cfg.ind_name_change = ({
        "采掘": "煤炭", "化工": "基础化工", "电气设备": "电力设备",
        "休闲服务": "社会服务", "纺织服装": "纺织服饰", "商业贸易": "商贸零售",
    },)

    start_time = datetime.datetime.now()

    # 读取因子数据
    factors_pkl = [
        d[:-4] for d in os.listdir(cfg.get_runtime_folder())
        if d.startswith("factor_")
    ]
    factor_list = []
    if cfg.fa_name in factors_pkl:
        factor_list.append(cfg.fa_name)
    else:
        raise ValueError(f"因子 {cfg.fa_name} 不在运行缓存中，可用: {factors_pkl[:10]}...")

    # 读取因子数据 (使用 _zq 版本支持早盘+全offset)
    factor_df = tf.get_data_zq(cfg, factor_list, boost)

    fig_list = []
    result_dict = {}

    # === IC分析 ===
    ic, ic_info, ic_month, ic_info_list = tf.get_ic_zq(factor_df, cfg)
    result_dict["name"] = name
    result_dict["ic"] = ic
    result_dict["ic_info"] = ic_info
    result_dict["ic_month"] = ic_month
    result_dict["abs_ic_mean"] = ic_info_list[0]
    result_dict["ic_mean"] = ic_info_list[1]
    result_dict["ic_std"] = ic_info_list[2]
    result_dict["icir"] = ic_info_list[3]
    result_dict["abs_icir"] = abs(ic_info_list[3])
    result_dict["ic_ratio"] = ic_info_list[4]

    # IC曲线图
    fig_list.append(
        pf.draw_ic_plotly(
            x=ic["交易日期"], y1=ic["RankIC"], y2=ic["累计RankIC"],
            title="因子RankIC图", info=ic_info
        )
    )
    # IC热力图
    fig_list.append(
        pf.draw_hot_plotly(
            x=ic_month.columns, y=ic_month.index, z=ic_month,
            title="RankIC热力图(行：年份，列：月份)"
        )
    )

    # === 分组分析 ===
    group_nv, group_value, group_hold_profit, group_hold_value = tf.get_group_net_value_zq(factor_df, cfg)
    result_dict["group_nv"] = group_nv
    result_dict["group_value"] = group_value
    result_dict["group_hold_profit"] = group_hold_profit
    result_dict["group_hold_value"] = group_hold_value

    cols_list = [col for col in group_nv.columns if "第" in col]
    # 分组资金曲线
    fig_list.append(
        pf.draw_line_plotly(
            x=group_nv["交易日期"], y1=group_nv[cols_list], y2=group_nv["多空净值"],
            if_log=True, title=f"分组资金曲线_费率{1 - cfg.fee_rate}"
        )
    )
    # 分组净值柱状图
    fig_list.append(pf.draw_bar_plotly(x=group_value["分组"], y=group_value["净值"], title="分组净值"))
    # 分组持仓涨跌幅
    fig_list.append(
        pf.draw_line_plotly(
            x=group_hold_profit["时间"], y1=group_hold_profit[cols_list],
            update_xticks=True, if_log=False, title="分组持仓涨跌幅"
        )
    )
    # 分组持仓走势
    fig_list.append(
        pf.draw_line_plotly(
            x=group_hold_value["时间"], y1=group_hold_value[cols_list],
            update_xticks=True, if_log=False, title="分组持仓走势"
        )
    )

    # === 风格暴露 ===
    style_corr = tf.get_style_corr(factor_df, cfg)
    fig_list.append(
        pf.draw_bar_plotly(
            x=style_corr["风格"], y=style_corr["相关系数"],
            title="因子风格暴露图", y_range=[-1.0, 1.0]
        )
    )
    result_dict["style_corr"] = style_corr

    # === 行业IC + 占比 ===
    industry_df = tf.get_class_ic_and_pct(factor_df, cfg)
    result_dict["industry_df"] = industry_df
    fig_list.append(
        pf.draw_bar_plotly(
            x=industry_df["新版申万一级行业名称"], y=industry_df["RankIC"],
            title="行业RankIC图"
        )
    )
    fig_list.append(
        pf.draw_double_bar_plotly(
            x=industry_df["新版申万一级行业名称"],
            y1=industry_df["因子第一组选股在各行业的占比"],
            y2=industry_df["因子最后一组选股在各行业的占比"],
            title="行业占比（可能会受到行业股票数量的影响）"
        )
    )

    # === 市值分组IC + 占比 ===
    market_df = tf.get_class_ic_and_pct(factor_df, cfg, is_industry=False)
    result_dict["market_df"] = market_df
    fig_list.append(
        pf.draw_bar_plotly(
            x=market_df["市值分组"], y=market_df["RankIC"],
            title="市值分组RankIC"
        )
    )
    info = "1-{bins}代表市值从小到大分{bins}组".format(bins=cfg.bins)
    fig_list.append(
        pf.draw_double_bar_plotly(
            x=market_df["市值分组"],
            y1=market_df["因子第一组选股在各市值分组的占比"],
            y2=market_df["因子最后一组选股在各市值分组的占比"],
            title="市值占比", info=info
        )
    )

    # === 因子得分 ===
    score = tf.get_factor_score(ic, group_value)
    start_date = factor_df["交易日期"].min().strftime("%Y/%m/%d")
    end_date = factor_df["交易日期"].max().strftime("%Y/%m/%d")
    result_dict["score"] = score
    result_dict["start_date"] = start_date
    result_dict["end_date"] = end_date
    result_dict["分析周期"] = cfg.period_offset_list
    result_dict["换仓时间"] = cfg.rebalance_time

    title = (
        f"{cfg.fa_name} 分析区间：{start_date} - {end_date}  "
        f"分析周期：{cfg.period_offset_list}  换仓时间：{cfg.rebalance_time}  "
        f"因子得分：{score:.2f}"
    )

    # === 生成HTML报告 ===
    save_path = cfg.factor_single_html_file_dir
    os.makedirs(save_path, exist_ok=True)
    html_path = pf.merge_html_not_open(
        save_path, fig_list=fig_list,
        strategy_file=f"{cfg.fa_name}因子分析报告{cfg.cfg_str}",
        bbs_id="31614", title=title
    )

    # === 保存PKL结果 ===
    import pickle
    pkl_dir = cfg.factor_single_dict_pkl_file_dir
    os.makedirs(pkl_dir, exist_ok=True)
    pkl_path = pkl_dir / f"{name}.pkl"
    with open(pkl_path, 'wb') as f:
        pickle.dump(result_dict, f)

    elapsed = (datetime.datetime.now() - start_time).total_seconds()
    print(f"{cfg.fa_name} 分析完成，耗时：{elapsed:.1f}秒")

    # 提取分组净值数据用于JSON输出
    group_values_dict = {}
    for _, row in group_value.iterrows():
        group_values_dict[str(row["分组"])] = float(row["净值"])

    # 风格暴露数据
    style_data = {}
    for _, row in style_corr.iterrows():
        style_data[str(row["风格"])] = float(row["相关系数"])

    return {
        "factor_name": name,
        "score": round(float(score), 4),
        "ic_mean": float(result_dict["ic_mean"]),
        "ic_std": float(result_dict["ic_std"]),
        "icir": float(result_dict["icir"]),
        "abs_icir": float(result_dict["abs_icir"]),
        "ic_ratio": str(result_dict["ic_ratio"]),
        "start_date": start_date,
        "end_date": end_date,
        "period_offset_list": cfg.period_offset_list,
        "rebalance_time": cfg.rebalance_time,
        "group_values": group_values_dict,
        "style_exposure": style_data,
        "html_path": str(html_path),
        "pkl_path": str(pkl_path),
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

        # 加入 sys.path 并切换工作目录
        if stock_framework_path not in sys.path:
            sys.path.insert(0, stock_framework_path)
        os.chdir(stock_framework_path)

        mode = params.get("mode", "single")

        # 覆盖 config 模块中的关键参数
        import config as _cfg_module
        backtest_name = params.get("backtest_name")
        if backtest_name:
            _cfg_module.backtest_name = backtest_name
        # 支持缩短日期范围以快速验证
        if params.get("start_date"):
            _cfg_module.start_date = params["start_date"]
        if params.get("end_date"):
            _cfg_module.end_date = params["end_date"]
        # 降低性能模式
        _cfg_module.n_jobs = params.get("n_jobs", 4)
        if hasattr(_cfg_module, 'performance_mode'):
            _cfg_module.performance_mode = "ECO"

        if mode == "list_factors":
            # 仅列出可用因子
            from core.model.backtest_config import load_config
            cfg = load_config()
            factors = list_available_factors(cfg)
            result["status"] = "ok"
            result["data"] = {"factors": factors, "total": len(factors)}
            print(f"\n__RESULT_JSON__:{json.dumps(result, ensure_ascii=False)}")
            return

        # 加载配置并设置分析参数
        from core.model.backtest_config import load_config
        cfg = load_config()

        cfg.bins = params.get("bins", 10)
        cfg.limit = params.get("limit", 100)
        cfg.fee_rate = (1 - cfg.c_rate) * (1 - cfg.c_rate - cfg.t_rate)
        cfg.period_offset_list = params.get("period_offset_list", ["5_0"])
        cfg.rebalance_time = params.get("rebalance_time", "0955")
        cfg.force_read_ret_and_style = params.get("force_read", False)

        # 配置输出目录
        cfg_str = '+'.join(str(i) for i in cfg.period_offset_list)
        cfg_str = cfg_str + '+' + cfg.rebalance_time
        cfg.cfg_str = cfg_str

        analysis_folder = Path(stock_framework_path) / "data" / "分析结果"
        pkl_folder_name = f"单因子_{cfg_str}_pkl"
        cfg.factor_single_dict_pkl_file_dir = analysis_folder / pkl_folder_name
        cfg.factor_single_html_file_dir = analysis_folder / "单因子分析"

        if mode == "single":
            factor_name = params.get("factor_name", "")
            if not factor_name:
                result["message"] = "factor_name is required"
                print(f"\n__RESULT_JSON__:{json.dumps(result, ensure_ascii=False)}")
                return

            data = run_single_analysis(factor_name, cfg, boost=True)
            result["status"] = "ok"
            result["message"] = "分析完成"
            result["data"] = data

        elif mode == "batch":
            # 批量分析所有因子
            from concurrent.futures import ProcessPoolExecutor
            max_workers = params.get("batch_max_workers", 3)

            available = list_available_factors(cfg)
            skip_existing = params.get("skip_existing", True)

            if skip_existing:
                pkl_dir = cfg.factor_single_dict_pkl_file_dir
                existing = set()
                if pkl_dir.exists():
                    existing = {f[:-4] for f in os.listdir(pkl_dir) if f.endswith(".pkl")}
                to_analyze = [f for f in available if f not in existing and f != "factor_总市值"]
            else:
                to_analyze = [f for f in available if f != "factor_总市值"]

            print(f"批量分析: {len(to_analyze)} 个因子 (跳过 {len(available) - len(to_analyze)} 个已有)")

            # 先分析一个以生成缓存
            batch_results = []
            failed = []
            if to_analyze:
                try:
                    first_result = run_single_analysis(to_analyze[0], cfg, boost=True)
                    batch_results.append(first_result)
                    cfg.force_read_ret_and_style = True  # 后续跳过缓存检查
                except Exception as e:
                    failed.append({"factor_name": to_analyze[0], "error": str(e)})

                # 并行处理剩余因子
                if len(to_analyze) > 1:
                    with ProcessPoolExecutor(max_workers=max_workers) as executor:
                        futures = {}
                        for name in to_analyze[1:]:
                            futures[executor.submit(run_single_analysis, name, cfg, False)] = name
                        for future in futures:
                            try:
                                r = future.result()
                                batch_results.append(r)
                            except Exception as e:
                                failed.append({"factor_name": futures[future], "error": str(e)})

            result["status"] = "ok"
            result["message"] = f"批量分析完成: {len(batch_results)} 成功, {len(failed)} 失败"
            result["data"] = {
                "results": batch_results,
                "total": len(to_analyze),
                "completed": len(batch_results),
                "failed_count": len(failed),
                "failed": failed[:10],  # 只返回前10个失败
            }

        else:
            result["message"] = f"Unknown mode: {mode}"

    except Exception as e:
        result["status"] = "error"
        result["message"] = f"{type(e).__name__}: {str(e)}"
        traceback.print_exc(file=sys.stderr)

    print(f"\n__RESULT_JSON__:{json.dumps(result, ensure_ascii=False, default=str)}")


if __name__ == "__main__":
    main()
