"""
批量字段更新任务 - 批量更新因子的指定字段
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable
from dataclasses import dataclass, field

import aiohttp

from ..core.config import get_config_loader
from ..services.prompt_engine import get_prompt_engine
from ..core.progress import get_progress_reporter
from ..core.store import get_factor_store, Factor
from ..services.field_filler import extract_pure_code


@dataclass
class FieldUpdate:
    """字段更新"""
    filename: str
    field: str
    old_value: str
    new_value: str
    success: bool = True
    error: str = ""


@dataclass
class BatchUpdateResult:
    """批次更新结果"""
    batch_id: int
    filenames: List[str]
    field: str
    success: bool
    updates: List[FieldUpdate] = field(default_factory=list)
    error: str = ""
    raw_response: str = ""


def parse_update_response(content: str, field: str, expected_filenames: List[str]) -> List[FieldUpdate]:
    """解析字段更新响应"""
    updates = []

    # 字段名映射
    field_mapping = {
        'style': ['style', '因子风格', '风格'],
        'formula': ['formula', '核心公式', '公式'],
        'input_data': ['input_data', '输入数据', '输入'],
        'value_range': ['value_range', '值域'],
        'description': ['description', '刻画特征', '描述'],
        'analysis': ['analysis', '因子分析', '分析'],
    }

    field_keys = field_mapping.get(field, [field])

    # 尝试解析 JSON
    json_pattern = r'```json\s*([\s\S]*?)\s*```'
    json_matches = re.findall(json_pattern, content)

    for json_str in json_matches:
        try:
            data = json.loads(json_str)
            if isinstance(data, list):
                for item in data:
                    filename = item.get('filename', item.get('文件名', ''))
                    new_value = None
                    for key in field_keys:
                        if key in item:
                            new_value = item[key]
                            break

                    if filename and new_value is not None:
                        updates.append(FieldUpdate(
                            filename=filename,
                            field=field,
                            old_value="",
                            new_value=str(new_value),
                        ))
        except json.JSONDecodeError:
            continue

    # 如果 JSON 解析失败，尝试直接解析
    if not updates:
        start = content.find('[')
        end = content.rfind(']')
        if start != -1 and end != -1:
            try:
                data = json.loads(content[start:end+1])
                if isinstance(data, list):
                    for item in data:
                        filename = item.get('filename', item.get('文件名', ''))
                        new_value = None
                        for key in field_keys:
                            if key in item:
                                new_value = item[key]
                                break

                        if filename and new_value is not None:
                            updates.append(FieldUpdate(
                                filename=filename,
                                field=field,
                                old_value="",
                                new_value=str(new_value),
                            ))
            except json.JSONDecodeError:
                pass

    # 确保所有预期因子都有结果
    update_filenames = {u.filename for u in updates}
    for filename in expected_filenames:
        if filename not in update_filenames:
            updates.append(FieldUpdate(
                filename=filename,
                field=field,
                old_value="",
                new_value="",
                success=False,
                error="未能生成更新"
            ))

    return updates


def build_update_prompt(
    factors: List[Dict[str, Any]],
    field: str,
    prompt_engine,
) -> Tuple[str, str]:
    """构建字段更新 prompt"""
    factors_info = []
    for i, factor in enumerate(factors, 1):
        factor_block = f"""
### {i}. {factor['filename']}

- 因子风格: {factor.get('style', '')}
- 核心公式: {factor.get('formula', '')}
- 输入数据: {factor.get('input_data', '')}
- 值域: {factor.get('value_range', '')}
- 刻画特征: {factor.get('description', '')}
- 因子分析: {factor.get('analysis', '')}

```python
{factor.get('code', '')}
```
"""
        factors_info.append(factor_block)

    factors_text = "\n---\n".join(factors_info)

    # 字段中文名映射
    field_cn = {
        'style': '因子风格',
        'formula': '核心公式',
        'input_data': '输入数据',
        'value_range': '值域',
        'description': '刻画特征',
        'analysis': '因子分析',
    }

    rendered = prompt_engine.render(
        'update_field',
        input_vars={
            'factors_text': factors_text,
            'factors_count': len(factors),
            'target_field': field,
            'target_field_cn': field_cn.get(field, field),
        }
    )

    return rendered['system'], rendered['user']


async def call_update_api(
    session: aiohttp.ClientSession,
    batch_factors: List[Dict[str, Any]],
    batch_id: int,
    field: str,
    semaphore: asyncio.Semaphore,
    api_config: Dict[str, Any],
    prompt_engine,
) -> BatchUpdateResult:
    """调用 API 更新字段"""
    async with semaphore:
        system_prompt, user_prompt = build_update_prompt(batch_factors, field, prompt_engine)
        filenames = [f['filename'] for f in batch_factors]

        headers = {
            "Authorization": f"Bearer {api_config['key']}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": api_config['model'],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "stream": False,
            "max_tokens": 16000
        }

        try:
            timeout = aiohttp.ClientTimeout(total=api_config['timeout'])
            async with session.post(
                api_config['url'],
                headers=headers,
                json=payload,
                timeout=timeout
            ) as response:
                if response.status == 200:
                    response_text = await response.text()
                    try:
                        data = json.loads(response_text)
                        choices = data.get('choices', [])
                        if choices and choices[0]:
                            message = choices[0].get('message', {})
                            content = message.get('content', '')
                            if content:
                                updates = parse_update_response(content, field, filenames)
                                return BatchUpdateResult(
                                    batch_id=batch_id,
                                    filenames=filenames,
                                    field=field,
                                    success=True,
                                    updates=updates,
                                    raw_response=content
                                )

                        return BatchUpdateResult(
                            batch_id=batch_id,
                            filenames=filenames,
                            field=field,
                            success=False,
                            error="响应格式错误"
                        )
                    except json.JSONDecodeError as e:
                        return BatchUpdateResult(
                            batch_id=batch_id,
                            filenames=filenames,
                            field=field,
                            success=False,
                            error=f"JSON 解析失败: {e}"
                        )
                else:
                    error_text = await response.text()
                    return BatchUpdateResult(
                        batch_id=batch_id,
                        filenames=filenames,
                        field=field,
                        success=False,
                        error=f"HTTP {response.status}: {error_text}"
                    )

        except Exception as e:
            return BatchUpdateResult(
                batch_id=batch_id,
                filenames=filenames,
                field=field,
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


def filter_factors(
    factors: List[Factor],
    mode: str,
    field: str,
    filter_condition: Optional[Dict[str, Any]] = None,
) -> List[Factor]:
    """
    根据模式筛选因子

    Args:
        factors: 因子列表
        mode: 模式 ('full', 'incremental', 'conditional')
        field: 目标字段
        filter_condition: 筛选条件

    Returns:
        筛选后的因子列表
    """
    if mode == 'full':
        # 全量模式：所有因子
        return factors

    elif mode == 'incremental':
        # 增量模式：只处理空值
        result = []
        for factor in factors:
            value = getattr(factor, field, '')
            if not value or str(value).strip() == '':
                result.append(factor)
        return result

    elif mode == 'conditional':
        # 条件模式：根据筛选条件
        if not filter_condition:
            return factors

        result = []
        for factor in factors:
            match = True
            for key, value in filter_condition.items():
                factor_value = getattr(factor, key, '')
                if str(factor_value) != str(value):
                    match = False
                    break
            if match:
                result.append(factor)
        return result

    return factors


async def run_update_async(
    factors: List[Factor],
    field: str,
    batch_size: int = 10,
    concurrency: int = 3,
    save_to_store: bool = True,
) -> List[BatchUpdateResult]:
    """
    异步执行字段更新任务

    Args:
        factors: 因子列表
        field: 目标字段
        batch_size: 每批次因子数
        concurrency: 并发数
        save_to_store: 是否保存到 store

    Returns:
        批次结果列表
    """
    config = get_config_loader()
    api_config = config.get_api_config()
    prompt_engine = get_prompt_engine()
    progress = get_progress_reporter()
    store = get_factor_store() if save_to_store else None

    # 准备因子数据
    factor_dicts = []
    for factor in factors:
        code = ""
        if factor.code_path:
            code = extract_pure_code(factor.code_path) or ""

        factor_dict = factor.to_dict()
        factor_dict['code'] = code
        factor_dicts.append(factor_dict)

    if not factor_dicts:
        return []

    # 创建批次
    batches = create_batches(factor_dicts, batch_size)

    progress.start_stage(f"更新 {field}", len(batches))

    all_results = []
    semaphore = asyncio.Semaphore(concurrency)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for batch_id, batch in enumerate(batches, 1):
            task = call_update_api(
                session, batch, batch_id, field, semaphore, api_config, prompt_engine
            )
            tasks.append(task)

        for coro in asyncio.as_completed(tasks):
            result = await coro
            all_results.append(result)

            if result.success:
                progress.increment(f"批次 {result.batch_id}")

                # 保存到 store
                if store:
                    for update in result.updates:
                        if update.success and update.new_value:
                            store.update(update.filename, **{field: update.new_value})
            else:
                progress.fail(f"批次 {result.batch_id}: {result.error[:50]}")

    success_count = sum(1 for r in all_results if r.success)
    fail_count = len(all_results) - success_count

    progress.finish_stage({
        '成功批次': success_count,
        '失败批次': fail_count,
        '更新因子数': sum(
            sum(1 for u in r.updates if u.success and u.new_value)
            for r in all_results if r.success
        ),
    })

    return all_results


def run_update_field(
    field: str,
    mode: str = 'incremental',
    filter_condition: Optional[Dict[str, Any]] = None,
    batch_size: int = 10,
    concurrency: int = 3,
    dry_run: bool = False,
    save_to_store: bool = True,
) -> List[BatchUpdateResult]:
    """
    执行字段更新任务（同步入口）

    Args:
        field: 目标字段
        mode: 模式 ('full', 'incremental', 'conditional')
        filter_condition: 筛选条件 (用于 conditional 模式)
        batch_size: 每批次因子数
        concurrency: 并发数
        dry_run: 是否只预览
        save_to_store: 是否保存到 store

    Returns:
        批次结果列表
    """
    store = get_factor_store()
    all_factors = store.get_all()

    if not all_factors:
        print("没有因子需要处理")
        return []

    # 筛选因子
    factors = filter_factors(all_factors, mode, field, filter_condition)

    if not factors:
        print(f"没有需要更新 {field} 的因子")
        return []

    print(f"找到 {len(factors)} 个因子需要更新 {field} (模式: {mode})")

    if dry_run:
        print("\n[DRY RUN] 预览:")
        for f in factors[:10]:
            current = getattr(f, field, '')
            print(f"  - {f.filename}: {current[:50] if current else '(空)'}")
        if len(factors) > 10:
            print(f"  ... 还有 {len(factors) - 10} 个因子")
        return []

    return asyncio.run(run_update_async(
        factors=factors,
        field=field,
        batch_size=batch_size,
        concurrency=concurrency,
        save_to_store=save_to_store,
    ))
