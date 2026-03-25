"""A股因子AI评估服务"""
import json
import logging
import os
import re
import time
import yaml
from typing import Optional, Dict, Any, List
from pathlib import Path

from domains.stock_hub.config import is_stock_framework_available
from domains.stock_hub.models.evaluation_model import (
    FactorEvaluation, ModuleScore, EvaluationRequest, EvaluationListItem,
)
from domains.stock_hub.services.stock_factor_service import get_stock_factor_service

logger = logging.getLogger(__name__)

# Directories
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
EVAL_DIR = Path(__file__).parent.parent / "evaluations"
EVAL_DIR.mkdir(exist_ok=True)

# Independent eval LLM config (env vars)
EVAL_API_URL = os.environ.get("STOCK_EVAL_API_URL", "")
EVAL_API_KEY = os.environ.get("STOCK_EVAL_API_KEY", "")
EVAL_MODEL = os.environ.get("STOCK_EVAL_MODEL", "gpt-5.4")
EVAL_API_TYPE = os.environ.get("STOCK_EVAL_API_TYPE", "responses")  # "responses" or "chat"


class StockEvalService:
    """因子AI评估服务"""

    def __init__(self):
        self._prompts: Dict[str, dict] = {}
        self._openai_client = None  # For independent mode (openai Responses API)
        self._llm_client = None     # For fallback mode (platform LangChain)
        self._llm_settings = None
        self._load_prompts()

    def _load_prompts(self):
        """Load YAML prompt templates"""
        if not PROMPTS_DIR.exists():
            logger.warning(f"Prompts directory not found: {PROMPTS_DIR}")
            return
        for yaml_file in PROMPTS_DIR.glob("*.yaml"):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                self._prompts[yaml_file.stem] = data
                logger.info(f"Loaded eval prompt: {yaml_file.stem}")
            except Exception as e:
                logger.error(f"Failed to load prompt {yaml_file}: {e}")

    def _has_independent_llm(self) -> bool:
        """Check if independent eval LLM is configured"""
        return bool(EVAL_API_URL and EVAL_API_KEY)

    def _get_openai_client(self):
        """Lazy-init independent OpenAI client"""
        if self._openai_client is None:
            from openai import OpenAI
            self._openai_client = OpenAI(
                api_key=EVAL_API_KEY,
                base_url=EVAL_API_URL,
            )
            logger.info(f"Eval LLM: independent mode ({EVAL_API_URL}, model={EVAL_MODEL})")
        return self._openai_client

    def _get_llm(self):
        """Lazy-init platform LLM client (fallback)"""
        if self._llm_client is None:
            try:
                from domains.mcp_core.llm import get_llm_client, get_llm_settings
                self._llm_client = get_llm_client()
                self._llm_settings = get_llm_settings()
                logger.info("Eval LLM: platform mode (mcp_core)")
            except Exception as e:
                logger.error(f"Failed to init LLM client: {e}")
                raise RuntimeError(f"LLM service unavailable: {e}")
        return self._llm_client, self._llm_settings

    def _render(self, template: str, variables: Dict[str, Any]) -> str:
        """Simple {{var}} template rendering"""
        result = template
        for key, value in variables.items():
            result = result.replace("{{" + key + "}}", str(value) if value else "N/A")
        return result

    async def _call_llm(self, prompt_key: str, variables: Dict[str, Any]) -> str:
        """Call LLM with a named prompt template"""
        prompt_config = self._prompts.get(prompt_key)
        if not prompt_config:
            raise ValueError(f"Prompt template not found: {prompt_key}")

        system = self._render(prompt_config.get("system", ""), variables)
        user = self._render(prompt_config.get("user", ""), variables)

        model_cfg = prompt_config.get("model", {})
        temperature = model_cfg.get("temperature", 0.4)
        max_tokens = model_cfg.get("max_tokens", 1500)

        if self._has_independent_llm():
            return await self._call_openai_responses(system, user, temperature, max_tokens)
        else:
            return await self._call_platform_llm(
                system, user, model_cfg, temperature, max_tokens, prompt_key
            )

    async def _call_openai_responses(
        self, system: str, user: str, temperature: float, max_tokens: int
    ) -> str:
        """Call LLM via OpenAI Responses API (independent mode).
        Uses curl subprocess to avoid Python SSL compatibility issues."""
        import asyncio
        import subprocess

        def _sync_call():
            # Combine system + user into a single user message
            # because the relay may override instructions with its own system prompt
            combined_input = f"{system}\n\n---\n\n{user}"
            payload = json.dumps({
                "model": EVAL_MODEL,
                "stream": True,
                "input": [
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": combined_input}],
                    }
                ],
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }, ensure_ascii=False)

            result = subprocess.run(
                [
                    "curl", "-sS", "-X", "POST",
                    f"{EVAL_API_URL}/responses",
                    "-H", f"Authorization: Bearer {EVAL_API_KEY}",
                    "-H", "Content-Type: application/json",
                    "-d", payload,
                ],
                capture_output=True, text=True, encoding="utf-8",
                timeout=120,
            )

            if result.returncode != 0:
                raise RuntimeError(f"curl failed: {result.stderr[:500]}")

            # Parse SSE stream — collect output_text delta events
            text_parts = []
            for line in result.stdout.split("\n"):
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    evt = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                evt_type = evt.get("type", "")
                if evt_type == "response.output_text.delta":
                    text_parts.append(evt.get("delta", ""))
                elif evt_type == "response.completed":
                    # Try to extract from completed response
                    resp_obj = evt.get("response", {})
                    for out_item in resp_obj.get("output", []):
                        if out_item.get("type") == "message":
                            for c in out_item.get("content", []):
                                if c.get("type") == "output_text":
                                    return c.get("text", "")

            return "".join(text_parts)

        content = await asyncio.to_thread(_sync_call)
        return (content or "").strip()

    async def _call_platform_llm(
        self, system: str, user: str,
        model_cfg: dict, temperature: float, max_tokens: int,
        prompt_key: str,
    ) -> str:
        """Call LLM via platform's mcp_core LLM client (fallback mode)"""
        client, settings = self._get_llm()
        model_key = model_cfg.get("name") or None

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        content = await client.ainvoke(
            messages=messages,
            model_key=model_key,
            temperature=temperature,
            max_tokens=max_tokens,
            caller="stock_eval",
            purpose=f"eval_{prompt_key}",
        )
        return content.strip()

    def _parse_score(self, text: str) -> float:
        """Extract a float score from LLM output"""
        match = re.search(r'(\d+\.?\d*)', text)
        if match:
            score = float(match.group(1))
            return max(1.0, min(5.0, score))
        return 3.0  # default

    def _parse_score_and_analysis(self, text: str) -> ModuleScore:
        """Parse LLM output that contains both score and analysis.
        Expected format: first line is score (float), rest is analysis.
        Or: SCORE: X.X followed by analysis text."""
        lines = text.strip().split("\n")

        # Try "SCORE: X.X" pattern
        score_match = re.search(
            r'(?:SCORE|评分|score)[:\s]*(\d+\.?\d*)', lines[0], re.IGNORECASE
        )
        if score_match:
            score = float(score_match.group(1))
            analysis = "\n".join(lines[1:]).strip()
        else:
            # Try first line as just a number
            first_match = re.match(r'^(\d+\.?\d*)$', lines[0].strip())
            if first_match:
                score = float(first_match.group(1))
                analysis = "\n".join(lines[1:]).strip()
            else:
                # Fallback: try to find score anywhere, use full text as analysis
                score = self._parse_score(text)
                analysis = text

        score = max(1.0, min(5.0, score))
        return ModuleScore(score=round(score, 1), analysis=analysis)

    async def evaluate_factor(self, request: EvaluationRequest) -> FactorEvaluation:
        """Run full modular evaluation on a factor"""

        # Get factor code if not provided
        code = request.factor_code
        if not code and is_stock_framework_available():
            try:
                factor_svc = get_stock_factor_service()
                code = factor_svc.get_factor_code(request.factor_name) or ""
            except Exception as e:
                logger.warning(f"Failed to get factor code: {e}")
                code = ""

        evaluation = FactorEvaluation(
            factor_name=request.factor_name,
            factor_category=request.factor_category,
            evaluated_at=time.time(),
            backtest_snapshot=request.backtest_result,
            ic_snapshot=request.ic_data,
        )

        base_vars = {
            "factor_name": request.factor_name,
            "factor_category": request.factor_category,
            "factor_description": request.factor_description,
            "factor_code": code or "N/A",
        }

        # Module 1: Logic evaluation (requires code)
        if code:
            try:
                result = await self._call_llm("logic_eval", base_vars)
                evaluation.logic = self._parse_score_and_analysis(result)
            except Exception as e:
                logger.error(f"Logic eval failed: {e}")

        # Module 2: Backtest evaluation (requires backtest data)
        if request.backtest_result:
            try:
                bt_vars = {
                    **base_vars,
                    "backtest_data": json.dumps(
                        request.backtest_result, ensure_ascii=False, indent=2
                    ),
                }
                result = await self._call_llm("backtest_eval", bt_vars)
                evaluation.backtest = self._parse_score_and_analysis(result)
            except Exception as e:
                logger.error(f"Backtest eval failed: {e}")

        # Module 3: IC/Effectiveness evaluation (requires IC data)
        if request.ic_data:
            try:
                ic_vars = {
                    **base_vars,
                    "ic_data": json.dumps(
                        request.ic_data, ensure_ascii=False, indent=2
                    ),
                }
                result = await self._call_llm("ic_eval", ic_vars)
                evaluation.effectiveness = self._parse_score_and_analysis(result)
            except Exception as e:
                logger.error(f"IC eval failed: {e}")

        # Module 4: Overall synthesis
        try:
            synthesis_vars = {
                **base_vars,
                "logic_score": str(evaluation.logic.score) if evaluation.logic else "N/A",
                "logic_analysis": evaluation.logic.analysis if evaluation.logic else "N/A",
                "backtest_score": str(evaluation.backtest.score) if evaluation.backtest else "N/A",
                "backtest_analysis": evaluation.backtest.analysis if evaluation.backtest else "N/A",
                "ic_score": str(evaluation.effectiveness.score) if evaluation.effectiveness else "N/A",
                "ic_analysis": evaluation.effectiveness.analysis if evaluation.effectiveness else "N/A",
            }
            result = await self._call_llm("overall_eval", synthesis_vars)

            # Parse overall: expect JSON-like output with score, summary, tags, verdict
            try:
                # Try JSON parse first — strip markdown fences if present
                json_text = result
                json_match = re.search(r'\{[\s\S]*\}', json_text)
                if json_match:
                    json_text = json_match.group(0)
                parsed = json.loads(json_text)
                evaluation.overall_score = max(1.0, min(5.0, float(parsed.get("score", 3.0))))
                evaluation.overall_summary = parsed.get("summary", "")
                evaluation.tags = parsed.get("tags", [])
                evaluation.verdict = parsed.get("verdict", "观望")
            except (json.JSONDecodeError, TypeError):
                # Fallback: parse score from text
                evaluation.overall_score = self._parse_score(result)
                evaluation.overall_summary = result
                evaluation.verdict = "观望"

                # Try to extract verdict
                if "推荐" in result:
                    evaluation.verdict = "推荐"
                elif "弃用" in result or "不推荐" in result:
                    evaluation.verdict = "弃用"
        except Exception as e:
            logger.error(f"Overall eval failed: {e}")
            # Calculate overall from available modules
            scores = []
            if evaluation.logic:
                scores.append(evaluation.logic.score)
            if evaluation.backtest:
                scores.append(evaluation.backtest.score)
            if evaluation.effectiveness:
                scores.append(evaluation.effectiveness.score)
            if scores:
                evaluation.overall_score = round(sum(scores) / len(scores), 1)

        # Save to file
        self._save_evaluation(evaluation)

        return evaluation

    def _save_evaluation(self, evaluation: FactorEvaluation):
        """Save evaluation to JSON file"""
        path = EVAL_DIR / f"{evaluation.factor_name}.json"
        path.write_text(
            json.dumps(evaluation.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"Evaluation saved: {path}")

    def get_evaluation(self, factor_name: str) -> Optional[FactorEvaluation]:
        """Get saved evaluation for a factor"""
        path = EVAL_DIR / f"{factor_name}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return FactorEvaluation(**data)
        except Exception as e:
            logger.error(f"Failed to load evaluation {factor_name}: {e}")
            return None

    def list_evaluations(self) -> List[EvaluationListItem]:
        """List all saved evaluations (lightweight)"""
        items = []
        for path in sorted(EVAL_DIR.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                items.append(EvaluationListItem(
                    factor_name=data["factor_name"],
                    factor_category=data.get("factor_category", ""),
                    evaluated_at=data["evaluated_at"],
                    overall_score=data.get("overall_score"),
                    verdict=data.get("verdict", ""),
                    tags=data.get("tags", []),
                ))
            except Exception:
                continue
        return items

    def delete_evaluation(self, factor_name: str) -> bool:
        """Delete a saved evaluation"""
        path = EVAL_DIR / f"{factor_name}.json"
        if path.exists():
            path.unlink()
            return True
        return False


# Singleton
_service: Optional[StockEvalService] = None


def get_stock_eval_service() -> StockEvalService:
    global _service
    if _service is None:
        _service = StockEvalService()
    return _service
