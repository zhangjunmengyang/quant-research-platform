"""
审核任务 - 调用 LLM API 对因子进行代码审核和知识库修订

单因子审核模式: 每次 LLM 请求只审核一个因子，通过并发数和延迟控制请求频率。
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
    # 从 backend/domains/factor_hub/tasks/review.py 向上 5 级到项目根目录
    log_dir = Path(__file__).parent.parent.parent.parent.parent / "output" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logger = logging.getLogger("review")
    logger.setLevel(logging.INFO)

    # 清除已有处理器（避免重复添加）
    if logger.handlers:
        logger.handlers.clear()

    # 文件处理器
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.INFO)

    # 控制台处理器
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
class Revision:
    """知识库修订"""
    factor_name: str
    field: str
    new_value: str


@dataclass
class CodeIssue:
    """代码问题"""
    factor_name: str
    issue_type: str  # 'delete' | 'warning'
    reason: str
    lessons_learned: str = ""


@dataclass
class ReviewResult:
    """单个因子的审核结果"""
    filename: str
    passed: bool = True
    should_delete: bool = False
    delete_reason: str = ""
    lessons_learned: str = ""
    revisions: List[Revision] = field(default_factory=list)
    code_issues: List[CodeIssue] = field(default_factory=list)
    error: str = ""
    raw_response: str = ""


@dataclass
class ReviewSummary:
    """审核汇总结果"""
    results: List[ReviewResult] = field(default_factory=list)
    success_count: int = 0
    fail_count: int = 0
    delete_count: int = 0
    revision_count: int = 0


def parse_review_response(content: str, filename: str) -> ReviewResult:
    """
    解析单个因子的审核响应

    Args:
        content: LLM 响应内容
        filename: 因子文件名

    Returns:
        ReviewResult
    """
    result = ReviewResult(filename=filename, raw_response=content)

    # 解析删除建议（文本部分）
    delete_patterns = [
        r'(\w+\.py)\s*(?:因子)?(?:建议)?删除[，,]?\s*理由[为是]?[：:]?\s*(.+?)(?:[，,]\s*有启发的想法[为是]?[：:]?\s*(.+?))?(?:\n|$)',
        r'建议删除\s*(\w+\.py)[，,]?\s*理由[为是]?[：:]?\s*(.+?)(?:[，,]\s*有启发的想法[为是]?[：:]?\s*(.+?))?(?:\n|$)',
        r'(?:建议)?删除[，,]?\s*理由[为是]?[：:]?\s*(.+?)(?:[，,]\s*有启发的想法[为是]?[：:]?\s*(.+?))?(?:\n|$)',
    ]

    for pattern in delete_patterns:
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            # 检查是否匹配到当前因子
            groups = match.groups()
            if len(groups) >= 2:
                # 带文件名的模式
                matched_name = groups[0] if groups[0] else filename
                reason = groups[1].strip() if groups[1] else ""
                lessons = groups[2].strip() if len(groups) > 2 and groups[2] else ""
            else:
                # 不带文件名的模式
                matched_name = filename
                reason = groups[0].strip() if groups[0] else ""
                lessons = groups[1].strip() if len(groups) > 1 and groups[1] else ""

            # 检查文件名是否匹配
            if matched_name == filename or matched_name.replace('.py', '') == filename.replace('.py', ''):
                result.passed = False
                result.should_delete = True
                result.delete_reason = reason
                result.lessons_learned = lessons
                result.code_issues.append(CodeIssue(
                    factor_name=filename,
                    issue_type='delete',
                    reason=reason,
                    lessons_learned=lessons
                ))
                break

    # 解析 JSON 修订块
    json_pattern = r'```json\s*([\s\S]*?)\s*```'
    json_matches = re.findall(json_pattern, content)

    for json_str in json_matches:
        try:
            revisions_data = json.loads(json_str)
            if isinstance(revisions_data, list):
                for item in revisions_data:
                    factor_name = item.get('因子名', item.get('factor_name', ''))
                    field_name = item.get('字段', item.get('field', ''))
                    new_value = item.get('新值', item.get('new_value', ''))

                    if factor_name and field_name and new_value:
                        # 检查是否是当前因子的修订
                        if factor_name == filename or factor_name.replace('.py', '') == filename.replace('.py', ''):
                            revision = Revision(
                                factor_name=factor_name,
                                field=field_name,
                                new_value=new_value
                            )
                            result.revisions.append(revision)
        except json.JSONDecodeError:
            continue

    return result


def build_review_prompt(
    factor: Dict[str, Any],
    prompt_engine,
    review_fields: Optional[List[str]] = None,
) -> Tuple[str, str]:
    """
    构建单个因子审核的 prompt

    Args:
        factor: 因子信息字典
        prompt_engine: Prompt 引擎实例
        review_fields: 要审核的字段列表（可选）

    Returns:
        (system_prompt, user_prompt)
    """
    # 构建因子信息文本
    factor_block = f"""
### 1. {factor['filename']}

<因子知识库>
**因子信息:**
- 因子风格: {factor.get('style', '')}
- 因子标签: {factor.get('tags', '')}
- 核心公式: {factor.get('formula', '')}
- 输入数据: {factor.get('input_data', '')}
- 值域: {factor.get('value_range', '')}
- 刻画特征: {factor.get('description', '')}
- 因子分析: {factor.get('analysis', '')}
</因子知识库>

<因子原始代码>
```python
{factor.get('code', '')}
```
</因子原始代码>
"""

    # 渲染 prompt
    review_fields_str = ', '.join(review_fields) if review_fields else ''
    rendered = prompt_engine.render(
        'review',
        input_vars={
            'factors_text': factor_block,
            'factors_count': 1,
            'review_fields': review_fields_str,
        }
    )

    return rendered['system'], rendered['user']


async def _review_single_factor(
    session: aiohttp.ClientSession,
    factor: Dict[str, Any],
    factor_index: int,
    total_factors: int,
    semaphore: asyncio.Semaphore,
    api_config: Dict[str, Any],
    prompt_engine,
    delay: float = 0.0,
    review_fields: Optional[List[str]] = None,
    output_dir: Optional[Path] = None,
) -> ReviewResult:
    """
    审核单个因子

    Args:
        session: HTTP 会话
        factor: 因子信息字典
        factor_index: 因子索引（从1开始）
        total_factors: 因子总数
        semaphore: 并发信号量
        api_config: API 配置
        prompt_engine: Prompt 引擎
        delay: 请求间隔（秒）
        review_fields: 要审核的字段列表
        output_dir: 输出目录

    Returns:
        ReviewResult
    """
    filename = factor['filename']

    async with semaphore:
        # 请求间隔，避免触发限流
        if delay > 0:
            logger.info(f"[{factor_index}/{total_factors}] {filename} 等待 {delay}s...")
            await asyncio.sleep(delay)

        logger.info(f"[{factor_index}/{total_factors}] {filename} 开始审核...")
        system_prompt, user_prompt = build_review_prompt(factor, prompt_engine, review_fields)

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
            "temperature": 0.7,
            "stream": False,
            "max_tokens": 16384
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
                            finish_reason = choices[0].get('finish_reason')
                            if finish_reason == 'length':
                                result = ReviewResult(
                                    filename=filename,
                                    passed=False,
                                    error="输出太长，超出 max_tokens 限制"
                                )
                            else:
                                message = choices[0].get('message', {})
                                content = message.get('content', '')
                                if content:
                                    result = parse_review_response(content, filename)
                                    logger.info(f"[{factor_index}/{total_factors}] {filename} 审核完成")
                                else:
                                    result = ReviewResult(
                                        filename=filename,
                                        passed=False,
                                        error="响应内容为空"
                                    )
                        else:
                            result = ReviewResult(
                                filename=filename,
                                passed=False,
                                error=f"响应格式错误: {response_text[:500]}"
                            )
                    except json.JSONDecodeError as e:
                        result = ReviewResult(
                            filename=filename,
                            passed=False,
                            error=f"JSON 解析失败: {e}"
                        )
                else:
                    error_text = await response.text()
                    result = ReviewResult(
                        filename=filename,
                        passed=False,
                        error=f"HTTP {response.status}: {error_text}"
                    )

        except Exception as e:
            import traceback
            result = ReviewResult(
                filename=filename,
                passed=False,
                error=f"{str(e)}\n{traceback.format_exc()}"
            )

        # 保存单个因子结果
        if output_dir:
            _save_review_result(result, factor_index, output_dir)

        return result


def _save_review_result(result: ReviewResult, factor_index: int, output_dir: Path):
    """保存单个因子的审核结果到文件"""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"review_{factor_index:04d}_{result.filename.replace('.py', '')}.md"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# 审核结果: {result.filename}\n\n")

        if result.error:
            f.write(f"## 错误\n\n{result.error}\n")
        elif result.should_delete:
            f.write(f"## 建议删除\n\n")
            f.write(f"**理由**: {result.delete_reason}\n\n")
            if result.lessons_learned:
                f.write(f"**经验教训**: {result.lessons_learned}\n\n")
        elif result.revisions:
            f.write(f"## 需要修订\n\n")
            for rev in result.revisions:
                f.write(f"- {rev.field}: {rev.new_value}\n")
            f.write("\n")
        else:
            f.write(f"## 通过\n\n无需修改。\n")

        if result.raw_response:
            f.write("\n## 原始响应\n\n")
            f.write(result.raw_response)


async def run_review_async(
    factors: List[Factor],
    concurrency: int = 1,
    output_dir: Optional[Path] = None,
    dry_run: bool = False,
    apply_revisions: bool = False,
    delay: float = 15.0,
    review_fields: Optional[List[str]] = None,
) -> ReviewSummary:
    """
    异步执行审核任务

    Args:
        factors: 待审核因子列表
        concurrency: 并发数
        output_dir: 输出目录
        dry_run: 是否只预览
        apply_revisions: 是否自动应用修订到 store
        delay: 请求间隔（秒），用于避免触发 API 限流
        review_fields: 要审核的字段列表

    Returns:
        ReviewSummary
    """
    config = get_config_loader()
    api_config = config.get_api_config()
    prompt_engine = get_prompt_engine()
    progress = get_progress_reporter()
    store = get_factor_store() if apply_revisions else None

    # 提取代码，构建有效因子列表
    valid_factors = []
    for factor in factors:
        code_path = factor.code_path
        if not code_path or code_path == '文件不存在':
            continue

        code = extract_pure_code(code_path)
        if code is None:
            continue

        factor_dict = factor.to_dict()
        factor_dict['code'] = code
        valid_factors.append(factor_dict)

    if not valid_factors:
        return ReviewSummary()

    total_factors = len(valid_factors)

    if dry_run:
        logger.info(f"[DRY RUN] 共 {total_factors} 个因子待审核")
        logger.info(f"并发数: {concurrency}, 请求间隔: {delay}s")
        for i, factor in enumerate(valid_factors[:5], 1):
            logger.info(f"  {i}. {factor['filename']}")
        if total_factors > 5:
            logger.info(f"  ... 还有 {total_factors - 5} 个因子")
        return ReviewSummary()

    # 开始处理
    progress.start_stage("审核", total_factors)

    summary = ReviewSummary()
    all_revisions = []
    delete_candidates = []
    semaphore = asyncio.Semaphore(concurrency)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, factor in enumerate(valid_factors, 1):
            task = _review_single_factor(
                session=session,
                factor=factor,
                factor_index=i,
                total_factors=total_factors,
                semaphore=semaphore,
                api_config=api_config,
                prompt_engine=prompt_engine,
                delay=delay,
                review_fields=review_fields,
                output_dir=output_dir,
            )
            tasks.append(task)

        for coro in asyncio.as_completed(tasks):
            result = await coro
            summary.results.append(result)

            if result.error:
                summary.fail_count += 1
                progress.fail(f"{result.filename}: {result.error[:50]}")
            else:
                summary.success_count += 1
                progress.increment(result.filename)

                # 收集修订和删除建议
                if result.should_delete:
                    delete_candidates.append({
                        'filename': result.filename,
                        'reason': result.delete_reason,
                        'lessons': result.lessons_learned,
                    })
                    summary.delete_count += 1

                all_revisions.extend(result.revisions)

    summary.revision_count = len(all_revisions)

    # 应用修订
    if apply_revisions and store and all_revisions:
        # 字段映射
        field_mapping = {
            '风格': 'style',
            '因子风格': 'style',
            '标签': 'tags',
            '因子标签': 'tags',
            '公式': 'formula',
            '核心公式': 'formula',
            '输入': 'input_data',
            '输入数据': 'input_data',
            '值域': 'value_range',
            '刻画特征': 'description',
            '描述': 'description',
            '分析': 'analysis',
            '因子分析': 'analysis',
        }

        applied_count = 0
        for revision in all_revisions:
            field_name = field_mapping.get(revision.field, revision.field)
            if store.update(revision.factor_name, **{field_name: revision.new_value}):
                applied_count += 1

        logger.info(f"已应用 {applied_count} 条修订")

    # 统计
    progress.finish_stage({
        '成功': summary.success_count,
        '失败': summary.fail_count,
        '待删除': summary.delete_count,
        '修订条目': summary.revision_count,
    })

    return summary


def run_review(
    concurrency: int = 1,
    output_dir: Optional[str] = None,
    dry_run: bool = False,
    apply_revisions: bool = False,
    delay: float = 15.0,
    filter_condition: Optional[Dict[str, Any]] = None,
    review_fields: Optional[List[str]] = None,
) -> ReviewSummary:
    """
    执行审核任务（同步入口）

    Args:
        concurrency: 并发数
        output_dir: 输出目录
        dry_run: 是否只预览
        apply_revisions: 是否自动应用修订
        delay: 请求间隔（秒），用于避免触发 API 限流
        filter_condition: 筛选条件（如 style=动量）
        review_fields: 要审核的字段列表

    Returns:
        ReviewSummary
    """
    store = get_factor_store()

    # 支持筛选条件
    if filter_condition:
        factors = store.query(filter_condition)
        logger.info(f"筛选条件: {filter_condition}")
    else:
        factors = store.get_all()

    if not factors:
        logger.info("没有需要审核的因子")
        return ReviewSummary()

    logger.info(f"找到 {len(factors)} 个待审核因子")
    if review_fields:
        logger.info(f"审核字段: {', '.join(review_fields)}")

    output_path = Path(output_dir) if output_dir else None

    return asyncio.run(run_review_async(
        factors=factors,
        concurrency=concurrency,
        output_dir=output_path,
        dry_run=dry_run,
        apply_revisions=apply_revisions,
        delay=delay,
        review_fields=review_fields,
    ))
