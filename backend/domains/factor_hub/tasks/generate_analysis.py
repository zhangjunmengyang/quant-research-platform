"""
分析生成任务 - 为因子生成因子分析文本
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

from domains.mcp_core.llm import get_llm_client
from ..services.prompt_engine import get_prompt_engine
from ..core.progress import get_progress_reporter
from ..core.store import get_factor_store, Factor
from ..services.field_filler import extract_pure_code


@dataclass
class GeneratedAnalysis:
    """生成的分析"""
    filename: str
    analysis: str = ""
    success: bool = True
    error: str = ""


@dataclass
class BatchAnalysisResult:
    """批次分析生成结果"""
    batch_id: int
    filenames: List[str]
    success: bool
    results: List[GeneratedAnalysis] = field(default_factory=list)
    error: str = ""
    raw_response: str = ""


def parse_analysis_response(content: str, expected_filenames: List[str]) -> List[GeneratedAnalysis]:
    """解析分析生成响应"""
    results = []

    # 尝试解析 JSON
    json_pattern = r'```json\s*([\s\S]*?)\s*```'
    json_matches = re.findall(json_pattern, content)

    for json_str in json_matches:
        try:
            data = json.loads(json_str)
            if isinstance(data, list):
                for item in data:
                    results.append(GeneratedAnalysis(
                        filename=item.get('filename', item.get('文件名', '')),
                        analysis=item.get('analysis', item.get('因子分析', '')),
                    ))
            elif isinstance(data, dict):
                results.append(GeneratedAnalysis(
                    filename=data.get('filename', data.get('文件名', '')),
                    analysis=data.get('analysis', data.get('因子分析', '')),
                ))
        except json.JSONDecodeError:
            continue

    # 如果 JSON 解析失败，尝试直接解析
    if not results:
        start = content.find('[')
        end = content.rfind(']')
        if start != -1 and end != -1:
            try:
                data = json.loads(content[start:end+1])
                if isinstance(data, list):
                    for item in data:
                        results.append(GeneratedAnalysis(
                            filename=item.get('filename', item.get('文件名', '')),
                            analysis=item.get('analysis', item.get('因子分析', '')),
                        ))
            except json.JSONDecodeError:
                pass

    # 确保所有预期因子都有结果
    result_filenames = {r.filename for r in results}
    for filename in expected_filenames:
        if filename not in result_filenames:
            results.append(GeneratedAnalysis(
                filename=filename,
                success=False,
                error="未能生成分析"
            ))

    return results


def build_analysis_prompt(
    factors: List[Dict[str, Any]],
    prompt_engine,
) -> Tuple[str, str]:
    """构建分析生成 prompt"""
    factors_info = []
    for i, factor in enumerate(factors, 1):
        factor_block = f"""
### {i}. {factor['filename']}

- 因子风格: {factor.get('style', '')}
- 核心公式: {factor.get('formula', '')}
- 输入数据: {factor.get('input_data', '')}
- 值域: {factor.get('value_range', '')}
- 刻画特征: {factor.get('description', '')}

```python
{factor.get('code', '')}
```
"""
        factors_info.append(factor_block)

    factors_text = "\n---\n".join(factors_info)

    rendered = prompt_engine.render(
        'generate_analysis',
        input_vars={
            'factors_text': factors_text,
            'factors_count': len(factors),
        }
    )

    return rendered['system'], rendered['user']


async def call_analysis_api(
    batch_factors: List[Dict[str, Any]],
    batch_id: int,
    semaphore: asyncio.Semaphore,
    prompt_engine,
) -> BatchAnalysisResult:
    """调用 API 生成分析"""
    async with semaphore:
        system_prompt, user_prompt = build_analysis_prompt(batch_factors, prompt_engine)
        filenames = [f['filename'] for f in batch_factors]

        try:
            llm_client = get_llm_client()
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            content = await llm_client.ainvoke(
                messages=messages,
                temperature=0.5,
                max_tokens=16000,
                caller="factor_hub.tasks.generate_analysis",
                purpose="生成因子分析",
            )

            if content:
                results = parse_analysis_response(content, filenames)
                return BatchAnalysisResult(
                    batch_id=batch_id,
                    filenames=filenames,
                    success=True,
                    results=results,
                    raw_response=content
                )

            return BatchAnalysisResult(
                batch_id=batch_id,
                filenames=filenames,
                success=False,
                error="响应内容为空"
            )

        except Exception as e:
            return BatchAnalysisResult(
                batch_id=batch_id,
                filenames=filenames,
                success=False,
                error=str(e)
            )


def create_batches(factors: List[Dict[str, Any]], batch_size: int) -> List[List[Dict[str, Any]]]:
    """将因子列表分成多个批次"""
    batches = []
    for i in range(0, len(factors), batch_size):
        batch = factors[i:i + batch_size]
        batches.append(batch)
    return batches


async def run_generate_analysis_async(
    factors: List[Factor],
    batch_size: int = 10,
    concurrency: int = 3,
    mode: str = 'incremental',
    save_to_store: bool = True,
) -> List[BatchAnalysisResult]:
    """
    异步执行分析生成任务

    Args:
        factors: 因子列表
        batch_size: 每批次因子数
        concurrency: 并发数
        mode: 模式 ('full'=全量, 'incremental'=增量填充空值)
        save_to_store: 是否保存到 store

    Returns:
        批次结果列表
    """
    prompt_engine = get_prompt_engine()
    progress = get_progress_reporter()
    store = get_factor_store() if save_to_store else None

    # 筛选需要处理的因子
    target_factors = []
    for factor in factors:
        if mode == 'incremental':
            # 只处理没有分析的因子
            if not factor.analysis or factor.analysis.strip() == '':
                target_factors.append(factor)
        else:
            # full 模式处理所有因子
            target_factors.append(factor)

    if not target_factors:
        print("没有需要生成分析的因子")
        return []

    # 准备因子数据
    factor_dicts = []
    for factor in target_factors:
        code = ""
        if factor.code_path:
            code = extract_pure_code(factor.code_path) or ""

        factor_dicts.append({
            'filename': factor.filename,
            'style': factor.style,
            'formula': factor.formula,
            'input_data': factor.input_data,
            'value_range': factor.value_range,
            'description': factor.description,
            'code': code,
        })

    # 创建批次
    batches = create_batches(factor_dicts, batch_size)

    progress.start_stage("分析生成", len(batches))

    all_results = []
    semaphore = asyncio.Semaphore(concurrency)

    tasks = []
    for batch_id, batch in enumerate(batches, 1):
        task = call_analysis_api(
            batch, batch_id, semaphore, prompt_engine
        )
        tasks.append(task)

    for coro in asyncio.as_completed(tasks):
        result = await coro
        all_results.append(result)

        if result.success:
            progress.increment(f"批次 {result.batch_id}")

            # 保存到 store
            if store:
                for analysis in result.results:
                    if analysis.success and analysis.analysis:
                        store.update(analysis.filename, analysis=analysis.analysis)
        else:
            progress.fail(f"批次 {result.batch_id}: {result.error[:50]}")

    success_count = sum(1 for r in all_results if r.success)
    fail_count = len(all_results) - success_count

    progress.finish_stage({
        '成功批次': success_count,
        '失败批次': fail_count,
        '生成分析数': sum(
            sum(1 for a in r.results if a.success and a.analysis)
            for r in all_results if r.success
        ),
    })

    return all_results


def run_generate_analysis(
    mode: str = 'incremental',
    batch_size: int = 10,
    concurrency: int = 3,
    save_to_store: bool = True,
) -> List[BatchAnalysisResult]:
    """
    执行分析生成任务（同步入口）

    Args:
        mode: 模式 ('full'=全量, 'incremental'=增量填充空值)
        batch_size: 每批次因子数
        concurrency: 并发数
        save_to_store: 是否保存到 store

    Returns:
        批次结果列表
    """
    store = get_factor_store()
    factors = store.get_all()

    if not factors:
        print("没有因子需要处理")
        return []

    print(f"找到 {len(factors)} 个因子")

    return asyncio.run(run_generate_analysis_async(
        factors=factors,
        batch_size=batch_size,
        concurrency=concurrency,
        mode=mode,
        save_to_store=save_to_store,
    ))
