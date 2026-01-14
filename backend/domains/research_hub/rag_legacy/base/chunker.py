"""
文档切块器基类

负责将文档切分为适合检索的块。
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from .component import AsyncComponent, ComponentConfig, ComponentType
from .parser import ParsedDocument, ContentType


class ChunkType(Enum):
    """切块类型"""
    TEXT = "text"
    TABLE = "table"
    FORMULA = "formula"
    FIGURE = "figure"
    CODE = "code"
    MIXED = "mixed"


@dataclass
class ChunkMetadata:
    """切块元数据"""
    # 来源信息
    document_id: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None

    # 位置信息
    chunk_index: int = 0
    total_chunks: int = 0

    # 内容信息
    chunk_type: ChunkType = ChunkType.TEXT
    has_table: bool = False
    has_formula: bool = False
    has_figure: bool = False

    # 层次信息（用于 TreeRAG）
    heading_path: List[str] = field(default_factory=list)  # 标题路径
    section_title: Optional[str] = None

    # 扩展信息
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """文档切块"""
    content: str
    metadata: ChunkMetadata = field(default_factory=ChunkMetadata)

    # 向量相关
    embedding: Optional[List[float]] = None
    sparse_embedding: Optional[Dict[str, float]] = None  # 稀疏向量

    # 标识
    chunk_id: Optional[str] = None

    # Token 统计
    token_count: Optional[int] = None

    def __post_init__(self):
        if self.chunk_id is None:
            import hashlib
            self.chunk_id = hashlib.md5(self.content.encode()).hexdigest()[:12]

    @property
    def text(self) -> str:
        """兼容性属性"""
        return self.content


@dataclass
class ChunkerConfig(ComponentConfig):
    """切块器配置"""
    # 切块大小
    chunk_size: int = 512  # tokens
    chunk_overlap: int = 50  # tokens

    # 分隔符
    separators: List[str] = field(
        default_factory=lambda: ["\n\n", "\n", "。", ".", " "]
    )

    # 特殊处理
    preserve_tables: bool = True  # 保持表格完整
    preserve_formulas: bool = True  # 保持公式完整
    preserve_code: bool = True  # 保持代码块完整

    # 元数据
    include_metadata: bool = True
    extract_headings: bool = True


class BaseChunker(AsyncComponent[ChunkerConfig, List[Chunk]]):
    """
    文档切块器基类

    负责将解析后的文档切分为适合检索的块。

    设计要点:
    1. 保持语义完整性（不在句子中间切分）
    2. 保持特殊内容完整（表格、公式、代码）
    3. 添加重叠以保持上下文连贯
    4. 提取层次信息（标题路径）

    示例:
        @component_registries.chunker.register("recursive")
        class RecursiveChunker(BaseChunker):
            async def chunk(self, document: ParsedDocument) -> List[Chunk]:
                # 递归切块逻辑
                ...
    """

    component_type = ComponentType.CHUNKER

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
        **kwargs,
    ):
        config = ChunkerConfig(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators or ["\n\n", "\n", "。", ".", " "],
            extra=kwargs,
        )
        super().__init__(config)

    @abstractmethod
    async def chunk(self, document: ParsedDocument) -> List[Chunk]:
        """
        切分文档

        Args:
            document: 解析后的文档

        Returns:
            切块列表
        """
        raise NotImplementedError

    async def execute(self, document: ParsedDocument) -> List[Chunk]:
        """执行切块"""
        return await self.chunk(document)

    def estimate_tokens(self, text: str) -> int:
        """
        估算 token 数量

        简单估算，实际应使用 tokenizer
        """
        # 中文约 1.5 字符/token，英文约 4 字符/token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)
