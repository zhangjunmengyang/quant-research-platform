"""
元信息提取任务 - 从因子代码中提取元信息（风格、公式、输入等）
"""

import asyncio
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

import aiohttp

# 设置日志
def setup_logger():
    """设置日志，同时输出到控制台和文件"""
    # 从 backend/domains/factor_hub/tasks/extract_metadata.py 向上 5 级到项目根目录
    log_dir = Path(__file__).parent.parent.parent.parent.parent / "output" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logger = logging.getLogger("extract_metadata")
    logger.setLevel(logging.INFO)

    # 文件处理器
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.INFO)

    # 控制台处理器 - 强制刷新
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)

    # 格式
    formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    print(f"\n日志文件: {log_file}\n", flush=True)
    return logger

logger = setup_logger()

from ..core.config import get_config_loader
from ..services.prompt_engine import get_prompt_engine
from ..core.progress import get_progress_reporter
from ..core.store import get_factor_store, Factor
from ..services.field_filler import extract_pure_code


@dataclass
class ExtractedMetadata:
    """提取的元信息"""
    filename: str
    style: str = ""
    formula: str = ""
    input_data: str = ""
    value_range: str = ""
    description: str = ""
    success: bool = True
    error: str = ""


@dataclass
class BatchExtractResult:
    """批次提取结果"""
    batch_id: int
    filenames: List[str]
    success: bool
    results: List[ExtractedMetadata] = field(default_factory=list)
    error: str = ""
    raw_response: str = ""


def parse_extraction_response(content: str, expected_filenames: List[str]) -> List[ExtractedMetadata]:
    """解析元信息提取响应"""
    results = []

    # 尝试解析 JSON
    json_pattern = r'```json\s*([\s\S]*?)\s*```'
    json_matches = re.findall(json_pattern, content)

    for json_str in json_matches:
        try:
            data = json.loads(json_str)
            if isinstance(data, list):
                for item in data:
                    results.append(ExtractedMetadata(
                        filename=item.get('filename', item.get('文件名', '')),
                        style=item.get('style', item.get('因子风格', '')),
                        formula=item.get('formula', item.get('核心公式', '')),
                        input_data=item.get('input_data', item.get('输入数据', '')),
                        value_range=item.get('value_range', item.get('值域', '')),
                        description=item.get('description', item.get('刻画特征', '')),
                    ))
            elif isinstance(data, dict):
                results.append(ExtractedMetadata(
                    filename=data.get('filename', data.get('文件名', '')),
                    style=data.get('style', data.get('因子风格', '')),
                    formula=data.get('formula', data.get('核心公式', '')),
                    input_data=data.get('input_data', data.get('输入数据', '')),
                    value_range=data.get('value_range', data.get('值域', '')),
                    description=data.get('description', data.get('刻画特征', '')),
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
                        results.append(ExtractedMetadata(
                            filename=item.get('filename', item.get('文件名', '')),
                            style=item.get('style', item.get('因子风格', '')),
                            formula=item.get('formula', item.get('核心公式', '')),
                            input_data=item.get('input_data', item.get('输入数据', '')),
                            value_range=item.get('value_range', item.get('值域', '')),
                            description=item.get('description', item.get('刻画特征', '')),
                        ))
            except json.JSONDecodeError:
                pass

    # 确保所有预期因子都有结果
    result_filenames = {r.filename for r in results}
    for filename in expected_filenames:
        if filename not in result_filenames:
            results.append(ExtractedMetadata(
                filename=filename,
                success=False,
                error="未能提取元信息"
            ))

    return results


def build_extract_prompt(
    factors: List[Dict[str, Any]],
    prompt_engine,
) -> Tuple[str, str]:
    """构建元信息提取 prompt"""
    factors_info = []
    for i, factor in enumerate(factors, 1):
        factor_block = f"""
### {i}. {factor['filename']}

```python
{factor.get('code', '')}
```
"""
        factors_info.append(factor_block)

    factors_text = "\n---\n".join(factors_info)

    rendered = prompt_engine.render(
        'extract_metadata',
        input_vars={
            'factors_text': factors_text,
            'factors_count': len(factors),
        }
    )

    return rendered['system'], rendered['user']


async def call_extract_api(
    session: aiohttp.ClientSession,
    batch_factors: List[Dict[str, Any]],
    batch_id: int,
    semaphore: asyncio.Semaphore,
    api_config: Dict[str, Any],
    prompt_engine,
    delay: float = 0.0,
) -> BatchExtractResult:
    """调用 API 提取元信息"""
    async with semaphore:
        # 请求间隔，避免触发限流
        if delay > 0:
            logger.info(f"批次 {batch_id}: 等待 {delay}s...")
            await asyncio.sleep(delay)

        logger.info(f"批次 {batch_id}: 开始请求 API...")
        system_prompt, user_prompt = build_extract_prompt(batch_factors, prompt_engine)
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
                                results = parse_extraction_response(content, filenames)
                                logger.info(f"批次 {batch_id}: 成功提取 {len(results)} 个因子")
                                return BatchExtractResult(
                                    batch_id=batch_id,
                                    filenames=filenames,
                                    success=True,
                                    results=results,
                                    raw_response=content
                                )

                        logger.warning(f"批次 {batch_id}: 响应格式错误")
                        return BatchExtractResult(
                            batch_id=batch_id,
                            filenames=filenames,
                            success=False,
                            error=f"响应格式错误"
                        )
                    except json.JSONDecodeError as e:
                        logger.error(f"批次 {batch_id}: JSON 解析失败: {e}")
                        return BatchExtractResult(
                            batch_id=batch_id,
                            filenames=filenames,
                            success=False,
                            error=f"JSON 解析失败: {e}"
                        )
                else:
                    error_text = await response.text()
                    logger.error(f"批次 {batch_id}: HTTP {response.status}")
                    return BatchExtractResult(
                        batch_id=batch_id,
                        filenames=filenames,
                        success=False,
                        error=f"HTTP {response.status}: {error_text}"
                    )

        except Exception as e:
            logger.error(f"批次 {batch_id}: 异常 - {e}")
            return BatchExtractResult(
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


async def process_extract_batch(
    session: aiohttp.ClientSession,
    batch_factors: List[Dict[str, Any]],
    batch_id: int,
    semaphore: asyncio.Semaphore,
    api_config: Dict[str, Any],
    prompt_engine,
    delay: float = 0.0,
) -> BatchExtractResult:
    """处理一个批次的元信息提取"""
    return await call_extract_api(
        session, batch_factors, batch_id, semaphore, api_config, prompt_engine, delay
    )


async def run_extract_async(
    factor_files: List[Path],
    batch_size: int = 5,
    concurrency: int = 3,
    save_to_store: bool = True,
    delay: float = 0.0,
) -> List[BatchExtractResult]:
    """
    异步执行元信息提取任务

    Args:
        factor_files: 因子文件路径列表
        batch_size: 每批次因子数
        concurrency: 并发数
        save_to_store: 是否保存到 store
        delay: 请求间隔（秒），用于避免触发 API 限流

    Returns:
        批次结果列表
    """
    config = get_config_loader()
    api_config = config.get_api_config()
    prompt_engine = get_prompt_engine()
    progress = get_progress_reporter()
    store = get_factor_store() if save_to_store else None

    # 准备因子数据
    factors = []
    for file_path in factor_files:
        code = extract_pure_code(str(file_path))
        if code:
            factors.append({
                'filename': file_path.name,
                'code': code,
                'code_path': str(file_path),
            })

    if not factors:
        return []

    # 创建批次
    batches = create_batches(factors, batch_size)

    logger.info(f"开始元信息提取: {len(batches)} 个批次, 并发={concurrency}, 间隔={delay}s")
    progress.start_stage("元信息提取", len(batches))

    all_results = []
    semaphore = asyncio.Semaphore(concurrency)

    async def save_result_to_store(result):
        """保存结果到 store"""
        if store and result.success:
            saved_count = 0
            for meta in result.results:
                if meta.success:
                    code_path = ""
                    for f in factors:
                        if f['filename'] == meta.filename:
                            code_path = f['code_path']
                            break
                    factor = Factor(
                        filename=meta.filename,
                        style=meta.style,
                        formula=meta.formula,
                        input_data=meta.input_data,
                        value_range=meta.value_range,
                        description=meta.description,
                        code_path=code_path,
                    )
                    if store.add(factor):
                        saved_count += 1
                        logger.info(f"  已保存: {meta.filename}")
            logger.info(f"批次 {result.batch_id}: 保存 {saved_count} 个因子到数据库")

    async with aiohttp.ClientSession() as session:
        # 统一使用并发模式，日志已在 call_extract_api 中输出
        tasks = []
        for batch_id, batch in enumerate(batches, 1):
            task = process_extract_batch(
                session, batch, batch_id, semaphore, api_config, prompt_engine, delay
            )
            tasks.append(task)

        for coro in asyncio.as_completed(tasks):
            result = await coro
            all_results.append(result)

            if result.success:
                progress.increment(f"批次 {result.batch_id}")
                await save_result_to_store(result)
            else:
                progress.fail(f"批次 {result.batch_id}: {result.error[:50] if result.error else 'Unknown'}")

    success_count = sum(1 for r in all_results if r.success)
    fail_count = len(all_results) - success_count

    progress.finish_stage({
        '成功批次': success_count,
        '失败批次': fail_count,
        '提取因子数': sum(len(r.results) for r in all_results if r.success),
    })

    return all_results


def run_extract(
    factor_dir: Optional[str] = None,
    factor_files: Optional[List[str]] = None,
    batch_size: int = 5,
    concurrency: int = 3,
    save_to_store: bool = True,
    delay: float = 0.0,
) -> List[BatchExtractResult]:
    """
    执行元信息提取任务（同步入口）

    Args:
        factor_dir: 因子目录
        factor_files: 指定的因子文件列表
        batch_size: 每批次因子数
        concurrency: 并发数
        save_to_store: 是否保存到 store
        delay: 请求间隔（秒），用于避免触发 API 限流

    Returns:
        批次结果列表
    """
    from tasks.diff_catalog import discover_factors

    # 获取待入库因子列表
    if factor_files:
        files = [Path(f) for f in factor_files if Path(f).exists()]
        logger.info(f"指定处理 {len(files)} 个因子文件")
    else:
        # 使用 discover 获取待入库因子
        result = discover_factors(factor_dir)
        if not result.pending:
            print("没有待入库的因子")
            return []

        # 获取因子目录
        if factor_dir:
            base_dir = Path(factor_dir)
        else:
            # 从 backend/domains/factor_hub/tasks/extract_metadata.py 向上 5 级到项目根目录
            base_dir = Path(__file__).parent.parent.parent.parent.parent / "factors"

        # 只处理待入库的因子
        files = [base_dir / filename for filename in result.pending]
        files = [f for f in files if f.exists()]
        logger.info(f"发现 {len(result.pending)} 个待入库因子，实际存在 {len(files)} 个文件")

    if not files:
        print("没有找到要处理的因子文件")
        return []

    print(f"将处理 {len(files)} 个待入库因子")

    return asyncio.run(run_extract_async(
        factor_files=files,
        batch_size=batch_size,
        concurrency=concurrency,
        save_to_store=save_to_store,
        delay=delay,
    ))
