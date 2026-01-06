"""
文档解析器基类

负责将 PDF/文档转换为结构化内容。
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
from enum import Enum

from .component import AsyncComponent, ComponentConfig, ComponentType


class ContentType(Enum):
    """内容类型"""
    TEXT = "text"
    MARKDOWN = "markdown"
    TABLE = "table"
    FORMULA = "formula"
    FIGURE = "figure"
    CODE = "code"
    HEADING = "heading"
    LIST = "list"


@dataclass
class ContentBlock:
    """内容块"""
    type: ContentType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 位置信息
    page_number: Optional[int] = None
    bbox: Optional[tuple] = None  # (x1, y1, x2, y2)

    # 结构化数据
    structured_data: Optional[Dict[str, Any]] = None  # 表格/公式的结构化表示


@dataclass
class ParsedPage:
    """解析后的页面"""
    page_number: int
    content: str  # Markdown 格式
    blocks: List[ContentBlock] = field(default_factory=list)

    # 原始数据
    raw_text: Optional[str] = None
    image_path: Optional[str] = None

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """解析后的文档"""
    # 必填字段
    content: str = ""  # 完整 Markdown

    # 内容类型
    content_type: ContentType = ContentType.TEXT

    # 来源信息
    source_path: Optional[str] = None
    file_path: Optional[str] = None  # 别名，兼容旧代码
    title: Optional[str] = None

    # 页面信息
    pages: List[ParsedPage] = field(default_factory=list)
    page_count: int = 0

    # 文档级元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 解析状态
    success: bool = True
    error: Optional[str] = None

    # 解析统计
    stats: Dict[str, Any] = field(default_factory=dict)

    def get_full_content(self) -> str:
        """获取完整内容"""
        if self.content:
            return self.content
        return "\n\n".join(page.content for page in self.pages)

    def get_blocks_by_type(self, content_type: ContentType) -> List[ContentBlock]:
        """按类型获取所有内容块"""
        blocks = []
        for page in self.pages:
            blocks.extend(b for b in page.blocks if b.type == content_type)
        return blocks


@dataclass
class ParserConfig(ComponentConfig):
    """解析器配置"""
    # 通用配置
    extract_images: bool = True
    extract_tables: bool = True
    extract_formulas: bool = True
    ocr_enabled: bool = True
    language: str = "zh"

    # 输出配置
    output_format: str = "markdown"  # markdown / json / html

    # 性能配置
    max_pages: Optional[int] = None
    timeout: int = 300  # 秒


class BaseParser(AsyncComponent[ParserConfig, ParsedDocument]):
    """
    文档解析器基类

    负责将 PDF/文档转换为结构化的 Markdown 内容。

    支持的文档类型:
    - PDF (重点支持量化研报)
    - Word
    - HTML

    实现要点:
    1. 保持公式/表格的结构
    2. 识别图表并生成描述
    3. 提取元数据（标题、作者等）

    示例:
        @component_registries.parser.register("mineru")
        class MinerUParser(BaseParser):
            async def parse(self, file_path: str) -> ParsedDocument:
                # 使用 MinerU 解析 PDF
                ...
    """

    component_type = ComponentType.PARSER

    def __init__(
        self,
        extract_images: bool = True,
        extract_tables: bool = True,
        extract_formulas: bool = True,
        **kwargs,
    ):
        config = ParserConfig(
            extract_images=extract_images,
            extract_tables=extract_tables,
            extract_formulas=extract_formulas,
            extra=kwargs,
        )
        super().__init__(config)

    @abstractmethod
    async def parse(self, file_path: str) -> ParsedDocument:
        """
        解析文档

        Args:
            file_path: 文档路径

        Returns:
            解析后的文档对象
        """
        raise NotImplementedError

    async def execute(self, file_path: str) -> ParsedDocument:
        """执行解析"""
        return await self.parse(file_path)

    def supports_format(self, file_path: str) -> bool:
        """检查是否支持该文件格式"""
        suffix = Path(file_path).suffix.lower()
        return suffix in self.supported_formats

    @property
    def supported_formats(self) -> List[str]:
        """支持的文件格式列表"""
        return [".pdf"]
