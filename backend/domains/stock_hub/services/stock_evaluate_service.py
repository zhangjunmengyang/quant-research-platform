"""Stock Hub AI 评估服务 - 基于分析结果调用 LLM 进行因子评估。"""

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# 评估类型
EVALUATION_TYPES = (
    "ic_performance",
    "grouping_ability",
    "style_profile",
    "market_cap",
    "comprehensive",
)

_PROMPTS_DIR = Path(__file__).resolve().parents[4] / "config" / "prompts" / "stock_hub"


def _load_prompt(eval_type: str) -> dict:
    """从 YAML 加载评估提示词配置。"""
    path = _PROMPTS_DIR / f"{eval_type}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _fmt(v: Any, max_items: int = 20) -> str:
    """格式化值为 prompt 可读字符串，截断超长列表。"""
    if v is None:
        return "无数据"
    if isinstance(v, list):
        if len(v) > max_items:
            return json.dumps(v[:max_items], ensure_ascii=False) + f" ... (共{len(v)}条)"
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False, indent=2)
    return str(v)


def _build_variables(eval_type: str, result: dict[str, Any]) -> dict[str, str]:
    """根据评估类型从分析结果中提取模板变量。"""
    base = {
        "factor_name": result.get("factor_name", "未知"),
        "group_values": _fmt(result.get("group_values")),
    }

    if eval_type == "ic_performance":
        base.update({
            "ic_mean": str(result.get("ic_mean", 0)),
            "ic_std": str(result.get("ic_std", 0)),
            "icir": str(result.get("icir", 0)),
            "abs_icir": str(result.get("abs_icir", 0)),
            "ic_ratio": str(result.get("ic_ratio", "")),
            "ic_summary": str(result.get("ic_summary", "无")),
            "ic_series_sample": _fmt(result.get("ic_series"), max_items=30),
            "ic_heatmap_summary": _fmt(result.get("ic_heatmap")),
        })

    elif eval_type == "grouping_ability":
        base.update({
            "group_nav_sample": _fmt(result.get("group_nav"), max_items=30),
            "group_holding_sample": _fmt(result.get("group_holding"), max_items=30),
        })

    elif eval_type == "style_profile":
        base["style_exposure"] = _fmt(result.get("style_exposure"))

    elif eval_type == "market_cap":
        base["market_cap_ic"] = _fmt(result.get("market_cap_ic"))

    elif eval_type == "comprehensive":
        base.update({
            "ic_mean": str(result.get("ic_mean", 0)),
            "ic_std": str(result.get("ic_std", 0)),
            "icir": str(result.get("icir", 0)),
            "abs_icir": str(result.get("abs_icir", 0)),
            "ic_ratio": str(result.get("ic_ratio", "")),
            "score": str(result.get("score", 0)),
            "ic_summary": str(result.get("ic_summary", "无")),
            "style_exposure": _fmt(result.get("style_exposure")),
            "market_cap_ic": _fmt(result.get("market_cap_ic")),
            "industry_ic": _fmt(result.get("industry_ic")),
            "start_date": str(result.get("start_date", "")),
            "end_date": str(result.get("end_date", "")),
            "period_offset_list": _fmt(result.get("period_offset_list")),
            "rebalance_time": str(result.get("rebalance_time", "")),
        })

    return base


def _render_template(template: str, variables: dict[str, str]) -> str:
    """简单 {{var}} 模板替换。"""
    result = template
    for key, value in variables.items():
        result = result.replace("{{" + key + "}}", value)
    return result


class StockEvaluateService:
    """因子 AI 评估服务，流式调用 LLM。"""

    def __init__(self) -> None:
        self._prompt_cache: dict[str, dict] = {}

    def _get_prompt(self, eval_type: str) -> dict:
        if eval_type not in self._prompt_cache:
            self._prompt_cache[eval_type] = _load_prompt(eval_type)
        return self._prompt_cache[eval_type]

    def get_prompt_config(self, eval_type: str) -> dict:
        """获取指定评估类型的提示词配置。"""
        if eval_type not in EVALUATION_TYPES:
            raise ValueError(f"Unknown evaluation type: {eval_type}")
        cfg = _load_prompt(eval_type)
        return {
            "eval_type": eval_type,
            "description": cfg.get("description", ""),
            "system": cfg.get("system", ""),
            "user": cfg.get("user", ""),
            "model": cfg.get("model", {}),
        }

    def update_prompt_config(self, eval_type: str, system: str, user: str) -> None:
        """更新指定评估类型的提示词配置并写回 YAML。"""
        if eval_type not in EVALUATION_TYPES:
            raise ValueError(f"Unknown evaluation type: {eval_type}")
        path = _PROMPTS_DIR / f"{eval_type}.yaml"
        cfg = _load_prompt(eval_type)
        cfg["system"] = system
        cfg["user"] = user
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        # 清除缓存
        self._prompt_cache.pop(eval_type, None)

    async def evaluate_stream(
        self,
        eval_type: str,
        analysis_result: dict[str, Any],
        model_key: str | None = None,
        prompt_override: dict[str, str] | None = None,
    ) -> AsyncIterator[str]:
        """流式返回 LLM 评估文本。

        Args:
            eval_type: 评估类型，见 EVALUATION_TYPES
            analysis_result: 单因子分析的完整结果 JSON
            model_key: LLM 模型 key，None 时使用 prompt 配置的默认值
            prompt_override: 可选的提示词覆盖，支持 "system" 和 "user" 键

        Yields:
            评估文本的增量 chunk
        """
        if eval_type not in EVALUATION_TYPES:
            raise ValueError(f"Unknown evaluation type: {eval_type}")

        prompt_cfg = self._get_prompt(eval_type)

        # Allow custom prompt override
        if prompt_override:
            if "system" in prompt_override:
                prompt_cfg = {**prompt_cfg, "system": prompt_override["system"]}
            if "user" in prompt_override:
                prompt_cfg = {**prompt_cfg, "user": prompt_override["user"]}

        variables = _build_variables(eval_type, analysis_result)

        system_content = _render_template(prompt_cfg["system"], variables)
        user_content = _render_template(prompt_cfg.get("user", "请开始评估。"), variables)

        model_cfg = prompt_cfg.get("model", {})
        effective_model = model_key or model_cfg.get("name", "claude")
        temperature = model_cfg.get("temperature", 0.3)
        max_tokens = model_cfg.get("max_tokens", 2000)

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        from domains.mcp_core.llm.client import get_llm_client

        client = get_llm_client()

        logger.info(
            "stock_evaluate_start",
            extra={"eval_type": eval_type, "factor": analysis_result.get("factor_name"), "model": effective_model},
        )

        async for chunk in client.astream(
            messages=messages,
            model_key=effective_model,
            temperature=temperature,
            max_tokens=max_tokens,
            caller="stock_evaluate",
            purpose=f"factor_{eval_type}_evaluation",
        ):
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content


_service_instance: StockEvaluateService | None = None


def get_stock_evaluate_service() -> StockEvaluateService:
    """获取评估服务单例。"""
    global _service_instance
    if _service_instance is None:
        _service_instance = StockEvaluateService()
    return _service_instance
