"""
通用字段填充器 - 对任意字段进行 LLM 生成/填充

核心能力：
1. 可对任意字段进行 LLM 生成/填充
2. 支持单字段、多字段批量生成
3. 字段配置驱动（每个字段的 prompt 模板可配置）
"""

import ast
import asyncio
import logging
import re
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

from ..core.config import get_config_loader
from ..core.store import get_factor_store, Factor
from ...mcp_core.llm import get_llm_client, get_llm_settings
from ...mcp_core.logging import setup_task_logger


# 不可由大模型生成的字段（系统管理）
PROTECTED_FIELDS = {'filename', 'code_path', 'code_content', 'created_at', 'updated_at', 'verified', 'verify_note'}

# 可生成字段及其依赖关系（生成时需要先有这些字段）
FIELD_DEPENDENCIES = {
    'style': ['code'],
    'tags': ['code', 'style', 'formula'],
    'formula': ['code'],
    'input_data': ['code'],
    'value_range': ['code'],
    'description': ['code', 'style', 'formula'],
    'analysis': ['code', 'style', 'formula', 'input_data', 'value_range', 'description'],
    'llm_score': ['code', 'style', 'formula', 'input_data', 'value_range', 'description', 'analysis'],
}

# 字段生成顺序（拓扑排序结果）
FIELD_ORDER = ['style', 'formula', 'input_data', 'value_range', 'tags', 'description', 'analysis', 'llm_score']


logger = setup_task_logger("field_filler")


@dataclass
class ModelConfig:
    """模型配置"""
    name: str = ""  # 模型 key (claude/gpt/gemini)，空则使用默认
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


@dataclass
class FieldConfig:
    """字段配置"""
    field: str
    description: str
    system_prompt: str
    user_prompt: str
    output_format: str = "text"
    max_length: int = 500
    required_vars: List[str] = field(default_factory=list)
    model: ModelConfig = field(default_factory=ModelConfig)


@dataclass
class FillResult:
    """单个因子单字段的填充结果"""
    filename: str
    field: str
    old_value: str
    new_value: str
    success: bool = True
    error: str = ""


@dataclass
class FieldFillResult:
    """单字段填充汇总结果"""
    field: str
    results: List[FillResult] = field(default_factory=list)
    success_count: int = 0
    fail_count: int = 0


class FieldFiller:
    """通用字段填充器"""

    def __init__(self):
        self.config_loader = get_config_loader()
        self.user_vars = self.config_loader.load_user_vars()
        self.llm_client = get_llm_client()
        self.llm_settings = get_llm_settings()
        self.field_configs: Dict[str, FieldConfig] = {}
        self._load_field_configs()

    def _load_field_configs(self):
        """加载所有字段配置"""
        # 项目根目录下的 config/prompts/fields
        # 从 backend/domains/factor_hub/services/field_filler.py 向上 5 级
        project_root = Path(__file__).parent.parent.parent.parent.parent
        fields_dir = project_root / "config" / "prompts" / "fields"
        if not fields_dir.exists():
            logger.warning(f"字段配置目录不存在: {fields_dir}")
            return

        for yaml_file in fields_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                field_name = config.get('field', yaml_file.stem)
                model_config = config.get('model', {})
                self.field_configs[field_name] = FieldConfig(
                    field=field_name,
                    description=config.get('description', ''),
                    system_prompt=config.get('system', ''),
                    user_prompt=config.get('user', ''),
                    output_format=config.get('output', {}).get('format', 'text'),
                    max_length=config.get('output', {}).get('max_length', 500),
                    required_vars=config.get('required_vars', []),
                    model=ModelConfig(
                        name=model_config.get('name', ''),
                        temperature=model_config.get('temperature'),
                        max_tokens=model_config.get('max_tokens'),
                    ),
                )
                logger.info(f"已加载字段配置: {field_name}")
            except Exception as e:
                logger.error(f"加载字段配置失败 {yaml_file}: {e}")

    def get_fillable_fields(self) -> List[str]:
        """获取可填充的字段列表"""
        return [f for f in FIELD_ORDER if f in self.field_configs]

    def _render_prompt(self, template: str, variables: Dict[str, Any]) -> str:
        """渲染 prompt 模板"""
        result = template

        # 处理条件块 {% if xxx %}...{% endif %}
        pattern = r'\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}'

        def replace_conditional(match):
            condition_var = match.group(1)
            content = match.group(2)
            value = variables.get(condition_var)
            if value:
                return content
            return ''

        result = re.sub(pattern, replace_conditional, result, flags=re.DOTALL)

        # 处理变量替换 {xxx}
        pattern = r'\{(\w+)\}'

        def replace_var(match):
            var_name = match.group(1)
            value = variables.get(var_name)
            if value is not None:
                return str(value)
            return match.group(0)

        result = re.sub(pattern, replace_var, result)

        return result

    def _build_prompt(
        self,
        field: str,
        factor: Dict[str, Any],
    ) -> Tuple[str, str]:
        """构建字段生成的 prompt"""
        if field not in self.field_configs:
            raise ValueError(f"未知字段: {field}")

        config = self.field_configs[field]

        # 合并变量
        variables = {**self.user_vars, **factor}

        # 渲染 prompt
        system = self._render_prompt(config.system_prompt, variables)
        user = self._render_prompt(config.user_prompt, variables)

        return system, user

    def _parse_response(self, content: str, field: str) -> str:
        """解析 API 响应"""
        config = self.field_configs.get(field)
        if not config:
            return content.strip()

        # 根据输出格式解析
        if config.output_format == 'number':
            # 提取数字
            match = re.search(r'(\d+\.?\d*)', content)
            if match:
                return match.group(1)
            return content.strip()

        # 文本格式直接返回
        return content.strip()[:config.max_length]

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        purpose: str = "",
        factor_name: str = "",
        field_config: Optional[FieldConfig] = None,
    ) -> Tuple[bool, str, str]:
        """
        调用 LLM（使用 mcp_core.llm 基础设施）

        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            purpose: 调用目的（用于日志）
            factor_name: 因子名称（用于日志）
            field_config: 字段配置（包含模型覆盖参数）

        Returns:
            (success, content, error)
        """
        # 从 field_config 解析模型参数
        model_key = None
        temperature = None
        max_tokens = None

        if field_config and field_config.model:
            model_key = field_config.model.name or None
            temperature = field_config.model.temperature
            max_tokens = field_config.model.max_tokens

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # 获取实际配置用于日志
        config = self.llm_settings.resolve_config(model_key, temperature, max_tokens)
        logger.info(
            f"LLM 调用: model={config['model']}, temperature={config['temperature']}, "
            f"max_tokens={config['max_tokens']}, factor={factor_name}"
        )

        try:
            content = await self.llm_client.ainvoke(
                messages=messages,
                model_key=model_key,
                temperature=temperature,
                max_tokens=max_tokens,
                caller="field_filler",
                purpose=purpose or "field_fill",
            )
            return True, content, ""
        except Exception as e:
            return False, "", str(e)

    async def _fill_single_factor(
        self,
        factor: Factor,
        field: str,
        store,
        semaphore: asyncio.Semaphore,
        delay: float,
        is_first: bool,
    ) -> FillResult:
        """填充单个因子的单个字段"""
        async with semaphore:
            # 非首个请求时，先等待延迟
            if not is_first and delay > 0:
                await asyncio.sleep(delay)

            factor_dict = factor.to_dict()
            # 添加 code
            if factor.code_path and Path(factor.code_path).exists():
                factor_dict['code'] = extract_pure_code(factor.code_path) or ""
            else:
                factor_dict['code'] = factor.code_content or ""

            try:
                system, user = self._build_prompt(field, factor_dict)
                field_config = self.field_configs.get(field)
                success, content, error = await self._call_llm(
                    system, user,
                    purpose=f"fill_{field}",
                    factor_name=factor.filename,
                    field_config=field_config,
                )

                if success:
                    new_value = self._parse_response(content, field)
                    result = FillResult(
                        filename=factor.filename,
                        field=field,
                        old_value=str(getattr(factor, field, '')),
                        new_value=new_value,
                        success=True,
                    )

                    # 保存到 store
                    if store and new_value:
                        if field == 'llm_score':
                            try:
                                await asyncio.to_thread(
                                    store.update, factor.filename, llm_score=float(new_value)
                                )
                            except ValueError:
                                pass
                        else:
                            await asyncio.to_thread(
                                store.update, factor.filename, **{field: new_value}
                            )

                    logger.info(f"  {factor.filename}: {field}={new_value[:50]}...")
                    return result
                else:
                    logger.error(f"  {factor.filename}: 失败 - {error}")
                    return FillResult(
                        filename=factor.filename,
                        field=field,
                        old_value=str(getattr(factor, field, '')),
                        new_value="",
                        success=False,
                        error=error,
                    )

            except Exception as e:
                logger.error(f"  {factor.filename}: 异常 - {e}")
                return FillResult(
                    filename=factor.filename,
                    field=field,
                    old_value="",
                    new_value="",
                    success=False,
                    error=str(e),
                )

    async def fill_field_async(
        self,
        factors: List[Factor],
        field: str,
        mode: str = 'incremental',
        concurrency: int = 1,
        delay: float = 15.0,
        save_to_store: bool = True,
    ) -> FieldFillResult:
        """
        异步填充单个字段

        Args:
            factors: 因子列表
            field: 要填充的字段
            mode: 模式 ('full'=全量, 'incremental'=只填充空值)
            concurrency: 并发数（同时进行的 LLM 请求数）
            delay: 每个请求之间的间隔（秒）
            save_to_store: 是否保存到 store

        Returns:
            FieldFillResult 填充结果
        """
        if field not in self.field_configs:
            logger.error(f"未知字段: {field}")
            return FieldFillResult(field=field)

        store = get_factor_store() if save_to_store else None

        # 筛选需要处理的因子
        target_factors = []
        for factor in factors:
            current_value = getattr(factor, field, '')
            if mode == 'incremental' and current_value and str(current_value).strip():
                continue
            target_factors.append(factor)

        if not target_factors:
            logger.info(f"没有需要填充 {field} 的因子")
            return FieldFillResult(field=field)

        logger.info(f"开始填充 {field}: {len(target_factors)} 个因子, 并发={concurrency}, 延迟={delay}s")

        semaphore = asyncio.Semaphore(concurrency)

        # 并发执行所有因子的填充
        tasks = [
            self._fill_single_factor(
                factor=factor,
                field=field,
                store=store,
                semaphore=semaphore,
                delay=delay,
                is_first=(i == 0),
            )
            for i, factor in enumerate(target_factors)
        ]

        results = await asyncio.gather(*tasks)

        # 统计
        success_count = sum(1 for r in results if r.success)
        fail_count = sum(1 for r in results if not r.success)
        logger.info(f"填充 {field} 完成: 成功 {success_count}, 失败 {fail_count}")

        return FieldFillResult(
            field=field,
            results=list(results),
            success_count=success_count,
            fail_count=fail_count,
        )

    async def fill_fields_async(
        self,
        factors: List[Factor],
        fields: List[str],
        mode: str = 'incremental',
        concurrency: int = 1,
        delay: float = 15.0,
        save_to_store: bool = True,
    ) -> Dict[str, FieldFillResult]:
        """
        异步填充多个字段（按依赖顺序）

        Args:
            factors: 因子列表
            fields: 要填充的字段列表
            mode: 模式
            concurrency: 并发数
            delay: 请求间隔
            save_to_store: 是否保存

        Returns:
            {field: FieldFillResult}
        """
        # 按依赖顺序排序
        sorted_fields = [f for f in FIELD_ORDER if f in fields]

        # 保存原始因子文件名列表，用于后续重新加载时筛选
        target_filenames = {f.filename for f in factors}

        results = {}
        for field in sorted_fields:
            logger.info(f"\n{'='*60}")
            logger.info(f"开始填充字段: {field}")
            logger.info(f"{'='*60}\n")

            # 重新加载因子（获取已更新的字段值），但只加载指定的因子
            if save_to_store:
                store = get_factor_store()
                all_factors = await asyncio.to_thread(store.get_all)
                factors = [f for f in all_factors if f.filename in target_filenames]

            field_result = await self.fill_field_async(
                factors=factors,
                field=field,
                mode=mode,
                concurrency=concurrency,
                delay=delay,
                save_to_store=save_to_store,
            )
            results[field] = field_result

        return results

    def fill_field(
        self,
        field: str,
        mode: str = 'incremental',
        filter_condition: Optional[Dict[str, Any]] = None,
        concurrency: int = 1,
        delay: float = 15.0,
        dry_run: bool = False,
    ) -> FieldFillResult:
        """
        填充单个字段（同步入口）

        Args:
            field: 要填充的字段
            mode: 模式 ('full', 'incremental')
            filter_condition: 筛选条件
            concurrency: 并发数
            delay: 请求间隔
            dry_run: 预览模式

        Returns:
            FieldFillResult
        """
        store = get_factor_store()

        if filter_condition:
            factors = store.query(filter_condition)
        else:
            factors = store.get_all()

        if not factors:
            logger.info("没有需要处理的因子")
            return FieldFillResult(field=field)

        if dry_run:
            target_count = sum(
                1 for f in factors
                if mode == 'full' or not getattr(f, field, '')
            )
            logger.info(f"[DRY RUN] 将填充 {target_count} 个因子的 {field} 字段")
            return FieldFillResult(field=field)

        return asyncio.run(self.fill_field_async(
            factors=factors,
            field=field,
            mode=mode,
            concurrency=concurrency,
            delay=delay,
            save_to_store=True,
        ))

    def fill_fields(
        self,
        fields: List[str],
        mode: str = 'incremental',
        filter_condition: Optional[Dict[str, Any]] = None,
        concurrency: int = 1,
        delay: float = 15.0,
        dry_run: bool = False,
    ) -> Dict[str, FieldFillResult]:
        """
        填充多个字段（同步入口）
        """
        store = get_factor_store()

        if filter_condition:
            factors = store.query(filter_condition)
        else:
            factors = store.get_all()

        if not factors:
            logger.info("没有需要处理的因子")
            return {}

        if dry_run:
            logger.info(f"[DRY RUN] 将填充 {len(factors)} 个因子的 {fields} 字段")
            return {}

        return asyncio.run(self.fill_fields_async(
            factors=factors,
            fields=fields,
            mode=mode,
            concurrency=concurrency,
            delay=delay,
            save_to_store=True,
        ))


# ========== 代码提取辅助函数 ==========

def remove_inline_comment(line: str) -> str:
    """移除行内注释，保留字符串中的 #"""
    in_string = False
    string_char = None
    for i, char in enumerate(line):
        if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False
        elif char == '#' and not in_string:
            return line[:i].rstrip()
    return line


def extract_code_simple(code: str) -> str:
    """简单提取代码（正则方式）"""
    lines = code.split('\n')
    cleaned_lines = []
    in_docstring = False
    docstring_char = None

    for line in lines:
        stripped = line.strip()

        # 跳过空行
        if not stripped:
            continue

        # 处理多行字符串/文档字符串
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[:3]
                if stripped.count(docstring_char) >= 2 and len(stripped) > 3:
                    # 单行文档字符串，跳过
                    continue
                in_docstring = True
                continue
        else:
            if docstring_char in stripped:
                in_docstring = False
            continue

        # 跳过纯注释行
        if stripped.startswith('#'):
            continue

        # 移除行内注释
        cleaned_line = remove_inline_comment(line)
        if cleaned_line.strip():
            cleaned_lines.append(cleaned_line)

    return '\n'.join(cleaned_lines)


def extract_pure_code(filepath: str) -> str:
    """
    使用 AST 提取纯代码（无注释和文档字符串）
    如果 AST 解析失败，回退到简单正则提取
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception:
        return ""

    try:
        tree = ast.parse(source)
    except SyntaxError:
        # AST 解析失败，使用简单方式
        return extract_code_simple(source)

    lines = source.split('\n')

    # 收集所有需要移除的行范围
    remove_ranges = []

    for node in ast.walk(tree):
        # 移除文档字符串
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                remove_ranges.append((node.lineno, node.end_lineno))

    # 移除指定范围的行
    remove_lines = set()
    for start, end in remove_ranges:
        for line_num in range(start, end + 1):
            remove_lines.add(line_num)

    # 过滤并清理
    cleaned_lines = []
    for i, line in enumerate(lines, 1):
        if i in remove_lines:
            continue

        stripped = line.strip()
        if not stripped:
            continue

        # 跳过纯注释行
        if stripped.startswith('#'):
            continue

        # 移除行内注释
        cleaned_line = remove_inline_comment(line)
        if cleaned_line.strip():
            cleaned_lines.append(cleaned_line)

    return '\n'.join(cleaned_lines)


# 单例
_field_filler: Optional[FieldFiller] = None


def get_field_filler() -> FieldFiller:
    """获取字段填充器单例"""
    global _field_filler
    if _field_filler is None:
        _field_filler = FieldFiller()
    return _field_filler
