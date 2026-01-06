"""
递归切块器

使用递归分割策略将文档切分为适合检索的块。
支持:
- 多级分隔符递归分割
- 保持特殊内容完整（表格、公式、代码）
- 标题层次提取
- Token 估算
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..base.chunker import BaseChunker, Chunk, ChunkMetadata, ChunkType
from ..base.parser import ParsedDocument
from ..base.registry import component_registries

logger = logging.getLogger(__name__)


@component_registries.chunker.register("recursive")
class RecursiveChunker(BaseChunker):
    """
    递归切块器

    使用多级分隔符递归分割文档，保持语义完整性。

    策略:
    1. 首先尝试用最大的分隔符（如双换行）分割
    2. 如果块太大，用下一级分隔符继续分割
    3. 保持表格、公式、代码块完整
    4. 添加重叠以保持上下文连贯

    使用示例:
        chunker = RecursiveChunker(chunk_size=512, chunk_overlap=50)
        chunks = await chunker.chunk(parsed_doc)
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
        preserve_tables: bool = True,
        preserve_formulas: bool = True,
        preserve_code: bool = True,
        extract_headings: bool = True,
        **kwargs,
    ):
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            **kwargs,
        )
        self.preserve_tables = preserve_tables
        self.preserve_formulas = preserve_formulas
        self.preserve_code = preserve_code
        self.extract_headings = extract_headings

    async def chunk(self, document: ParsedDocument) -> List[Chunk]:
        """
        切分文档

        Args:
            document: 解析后的文档

        Returns:
            切块列表
        """
        if not document.content:
            return []

        content = document.content

        # 预处理：提取并保护特殊内容
        protected_content, protected_blocks = self._protect_special_blocks(content)

        # 提取标题结构
        heading_structure = self._extract_heading_structure(content)

        # 递归切分
        raw_chunks = self._split_text(
            protected_content,
            self.config.separators,
        )

        # 还原特殊内容并构建 Chunk 对象
        chunks = []
        for i, raw_chunk in enumerate(raw_chunks):
            # 还原被保护的内容
            restored_chunk = self._restore_special_blocks(raw_chunk, protected_blocks)

            # 检测切块类型
            chunk_type = self._detect_chunk_type(restored_chunk)

            # 获取标题路径
            heading_path = self._get_heading_path(
                i, len(raw_chunks), heading_structure, content
            )

            # 创建 Chunk 对象
            chunk = Chunk(
                content=restored_chunk,
                metadata=ChunkMetadata(
                    document_id=document.source_path,
                    chunk_index=i,
                    total_chunks=len(raw_chunks),
                    chunk_type=chunk_type,
                    has_table=self._has_table(restored_chunk),
                    has_formula=self._has_formula(restored_chunk),
                    heading_path=heading_path,
                    section_title=heading_path[-1] if heading_path else None,
                ),
                token_count=self.estimate_tokens(restored_chunk),
            )
            chunks.append(chunk)

        logger.info(f"Created {len(chunks)} chunks from document")
        return chunks

    def _protect_special_blocks(
        self, content: str
    ) -> Tuple[str, Dict[str, str]]:
        """
        保护特殊内容块（表格、公式、代码）

        将特殊内容替换为占位符，避免被切分。
        """
        protected_blocks = {}
        protected_content = content

        if self.preserve_code:
            # 保护代码块
            code_pattern = r"```[\s\S]*?```"
            for i, match in enumerate(re.finditer(code_pattern, content)):
                placeholder = f"__CODE_BLOCK_{i}__"
                protected_blocks[placeholder] = match.group()
                protected_content = protected_content.replace(
                    match.group(), placeholder
                )

        if self.preserve_formulas:
            # 保护块级公式
            formula_pattern = r"\$\$[\s\S]*?\$\$"
            for i, match in enumerate(re.finditer(formula_pattern, protected_content)):
                placeholder = f"__FORMULA_BLOCK_{i}__"
                protected_blocks[placeholder] = match.group()
                protected_content = protected_content.replace(
                    match.group(), placeholder
                )

        if self.preserve_tables:
            # 保护 Markdown 表格
            table_pattern = r"(\|[^\n]+\|\n)+(\|[-:\s|]+\|\n)(\|[^\n]+\|\n)+"
            for i, match in enumerate(re.finditer(table_pattern, protected_content)):
                placeholder = f"__TABLE_BLOCK_{i}__"
                protected_blocks[placeholder] = match.group()
                protected_content = protected_content.replace(
                    match.group(), placeholder
                )

        return protected_content, protected_blocks

    def _restore_special_blocks(
        self, chunk: str, protected_blocks: Dict[str, str]
    ) -> str:
        """还原被保护的特殊内容"""
        restored = chunk
        for placeholder, original in protected_blocks.items():
            restored = restored.replace(placeholder, original)
        return restored

    def _split_text(
        self, text: str, separators: List[str], depth: int = 0
    ) -> List[str]:
        """
        递归分割文本

        Args:
            text: 要分割的文本
            separators: 分隔符列表
            depth: 递归深度

        Returns:
            分割后的文本块列表
        """
        if not text.strip():
            return []

        # 如果文本足够小，直接返回
        if self.estimate_tokens(text) <= self.config.chunk_size:
            return [text.strip()] if text.strip() else []

        # 如果没有更多分隔符，强制按长度分割
        if not separators:
            return self._split_by_length(text)

        # 尝试用当前分隔符分割
        current_sep = separators[0]
        remaining_seps = separators[1:]

        splits = text.split(current_sep)

        if len(splits) == 1:
            # 当前分隔符无效，尝试下一个
            return self._split_text(text, remaining_seps, depth + 1)

        # 合并小块，分割大块
        result = []
        current_chunk = ""

        for split in splits:
            split = split.strip()
            if not split:
                continue

            potential_chunk = (
                f"{current_chunk}{current_sep}{split}" if current_chunk else split
            )

            if self.estimate_tokens(potential_chunk) <= self.config.chunk_size:
                current_chunk = potential_chunk
            else:
                # 当前块已满
                if current_chunk:
                    result.append(current_chunk)

                # 检查新块是否需要继续分割
                if self.estimate_tokens(split) > self.config.chunk_size:
                    # 递归分割
                    sub_chunks = self._split_text(split, remaining_seps, depth + 1)
                    result.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = split

        if current_chunk:
            result.append(current_chunk)

        # 添加重叠
        result = self._add_overlap(result)

        return result

    def _split_by_length(self, text: str) -> List[str]:
        """按字符长度强制分割"""
        # 估算每个 token 的平均字符数
        avg_chars_per_token = len(text) / max(self.estimate_tokens(text), 1)
        chunk_chars = int(self.config.chunk_size * avg_chars_per_token)

        chunks = []
        for i in range(0, len(text), chunk_chars):
            chunk = text[i:i + chunk_chars].strip()
            if chunk:
                chunks.append(chunk)

        return self._add_overlap(chunks)

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """为切块添加重叠"""
        if len(chunks) <= 1 or self.config.chunk_overlap <= 0:
            return chunks

        result = []
        overlap_chars = int(
            self.config.chunk_overlap * 4
        )  # 估算 token 对应的字符数

        for i, chunk in enumerate(chunks):
            if i == 0:
                result.append(chunk)
            else:
                # 从前一个块获取重叠部分
                prev_chunk = chunks[i - 1]
                overlap = prev_chunk[-overlap_chars:] if len(prev_chunk) > overlap_chars else prev_chunk
                result.append(f"{overlap}...{chunk}")

        return result

    def _extract_heading_structure(self, content: str) -> List[Tuple[int, str, int]]:
        """
        提取标题结构

        Returns:
            [(level, title, position), ...]
        """
        headings = []
        pattern = r"^(#{1,6})\s+(.+)$"

        for match in re.finditer(pattern, content, re.MULTILINE):
            level = len(match.group(1))
            title = match.group(2).strip()
            position = match.start()
            headings.append((level, title, position))

        return headings

    def _get_heading_path(
        self,
        chunk_index: int,
        total_chunks: int,
        heading_structure: List[Tuple[int, str, int]],
        original_content: str,
    ) -> List[str]:
        """获取切块的标题路径"""
        if not self.extract_headings or not heading_structure:
            return []

        # 简化实现：返回最近的标题
        # 完整实现需要更复杂的位置追踪
        relative_position = chunk_index / max(total_chunks, 1)

        path = []
        current_levels = {}  # level -> title

        for level, title, position in heading_structure:
            # 简单估算：按位置比例匹配
            heading_position = position / max(len(original_content), 1)
            if heading_position <= relative_position:
                current_levels[level] = title
                # 清除更低级别的标题
                for l in list(current_levels.keys()):
                    if l > level:
                        del current_levels[l]

        # 构建路径
        for level in sorted(current_levels.keys()):
            path.append(current_levels[level])

        return path

    def _detect_chunk_type(self, content: str) -> ChunkType:
        """检测切块类型"""
        if self._has_table(content):
            return ChunkType.TABLE
        if self._has_formula(content):
            return ChunkType.FORMULA
        if "```" in content:
            return ChunkType.CODE
        return ChunkType.TEXT

    def _has_table(self, content: str) -> bool:
        """检测是否包含表格"""
        return "| --- |" in content or (
            "|" in content and content.count("|") > 4
        )

    def _has_formula(self, content: str) -> bool:
        """检测是否包含公式"""
        return "$$" in content or (
            content.count("$") >= 2 and "$" in content
        )


@component_registries.chunker.register("sentence")
class SentenceChunker(BaseChunker):
    """
    句子级切块器

    按句子边界切分，适合需要精确定位的场景。
    """

    async def chunk(self, document: ParsedDocument) -> List[Chunk]:
        """按句子切分"""
        if not document.content:
            return []

        # 简单的句子分割
        sentences = re.split(r'(?<=[。！？.!?])\s*', document.content)

        chunks = []
        current_chunk = ""
        current_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            potential_chunk = f"{current_chunk} {sentence}".strip()

            if self.estimate_tokens(potential_chunk) <= self.config.chunk_size:
                current_chunk = potential_chunk
                current_sentences.append(sentence)
            else:
                if current_chunk:
                    chunks.append(
                        Chunk(
                            content=current_chunk,
                            metadata=ChunkMetadata(
                                document_id=document.source_path,
                                chunk_index=len(chunks),
                            ),
                            token_count=self.estimate_tokens(current_chunk),
                        )
                    )
                current_chunk = sentence
                current_sentences = [sentence]

        if current_chunk:
            chunks.append(
                Chunk(
                    content=current_chunk,
                    metadata=ChunkMetadata(
                        document_id=document.source_path,
                        chunk_index=len(chunks),
                    ),
                    token_count=self.estimate_tokens(current_chunk),
                )
            )

        # 更新 total_chunks
        for i, chunk in enumerate(chunks):
            chunk.metadata.total_chunks = len(chunks)
            chunk.metadata.chunk_index = i

        return chunks
